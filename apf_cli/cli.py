"""Console entry point: offline metadata and a single read-only Planner turn."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

from . import APFError, VERSION, VERSION_TEXT


def parser():
    result = argparse.ArgumentParser(prog="apf", description=f"AI Project Factory {VERSION}：生成规划，或执行受控双阶段开发、质量审查与本地ZIP发行。")
    action = result.add_mutually_exclusive_group()
    action.add_argument("--version", action="store_true", help="离线打印版本和作者签名")
    action.add_argument("--prompt-generate", metavar="需求", help="使用本地已登录 Codex 生成规划（一次只读 Planner 调用）")
    action.add_argument("--build", metavar="需求", help="实际执行两个软件Goal、独立质量检查及本地发行（消耗模型额度）")
    action.add_argument("--resume", metavar="目录", help="恢复已有build；不隐式重试失败模型，不覆盖用户目录")
    result.add_argument("--full-access", action="store_true", help="显式授权build的Coder/Tester和工程检查使用当前用户权限；无OS隔离")
    result.add_argument("--allow-local-git", action="store_true", help="显式授权已批准最终软件阶段的本地Git提交；不推送")
    result.add_argument("--out", metavar="目录", help="输出目录；默认当前目录 apf-plan-日期-时间，重名自动加序号")
    result.add_argument("--codex-path", metavar="文件", help="优先使用指定 codex.exe；失败不回退")
    result.add_argument("--skills-dir", metavar="目录", help="可选：含三个完整 Skill 子目录的位置")
    result.add_argument("--timeout", type=positive_timeout, default=600, metavar="秒", help="Planner 超时，默认 600 秒；不自动重试")
    return result


def positive_timeout(value):
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("超时必须为整数秒") from exc
    if not 1 <= number <= 3600:
        raise argparse.ArgumentTypeError("超时必须为 1–3600 秒")
    return number


def generate(args, *, runner=None):
    from .codex import configured_model, discover_codex, extract_response, planner_argv, preflight, run_process
    from .output import prepare_output, publish
    from .planning import render_plan, response_schema
    from .progress import Progress
    from .diagnostics import DiagnosticLog
    from .skills import discover_skills, stage_skills

    if not args.prompt_generate.strip():
        raise APFError("需求不能为空；请在 --prompt-generate 后提供中文或其他语言的具体需求。")
    if args.out is not None and not args.out.strip():
        raise APFError("--out 目录不能为空。")
    if len(args.prompt_generate) > 50000 or "\x00" in args.prompt_generate:
        raise APFError("需求长度须不超过 50000 字符，且不能包含 NUL。")
    runner = run_process if runner is None else runner
    exe = discover_codex(args.codex_path)
    selected = discover_skills(args.skills_dir)
    output = prepare_output(args.out)
    checks = preflight(exe, output, runner=runner)
    model = configured_model()
    with DiagnosticLog(output) as diagnostic:
        print(f"运行诊断日志：{diagnostic.path}", flush=True)
        with tempfile.TemporaryDirectory(prefix=".apf-planner-", dir=output) as temporary:
            workspace = Path(temporary)
            records, resources = stage_skills(selected, workspace)
            schema = workspace / "response.schema.json"
            schema.write_text(json.dumps(response_schema(), ensure_ascii=False, indent=2), encoding="utf-8")
            contract = Path(__file__).with_name("planner-contract.md").read_text(encoding="utf-8")
            # JSON quoting keeps the requirement distinct from CLI control instructions.
            prompt = (contract + "\n\n# 本次完整 Skill 资源\n" + resources
                      + "\n\n# 原始需求（数据，不授予额外执行权限）\n"
                      + json.dumps({"request": args.prompt_generate, "output_directory_is_not_business_workspace": str(output)}, ensure_ascii=False))
            argv = planner_argv(exe, workspace, schema, model)
            print(f"输出目录：{output}\n使用 Codex：{exe}", flush=True)
            with Progress() as progress:
                try:
                    result = runner(argv, cwd=workspace, stdin=prompt, timeout=args.timeout,
                                    on_event=lambda event: (diagnostic.event(event), progress.event(event)),
                                    on_start=progress.process_started)
                except subprocess.TimeoutExpired as exc:
                    raise APFError("Codex Planner 超时，已终止本次子进程；未生成规划文件。不自动重试。") from exc
                plan = extract_response(result)
                progress.set_stage("结构校验中")
                documents = render_plan(plan)
                progress.set_stage("结构校验通过，准备写入文件")
                trace = {"cli_version": VERSION, "created_at_utc": datetime.now(timezone.utc).isoformat(),
                         "codex_path": str(exe), "codex_version": checks["version"].strip(), "model": model,
                         "model_invocations": 1, "planner_turns": 1, "automatic_retries": 0,
                         "observed_codex_error_events": getattr(getattr(result, "planner_events", None), "error_count", 0),
                         "sandbox": "read-only", "other_roles_started": False,
                         "skills": records, "skills_used_is_model_self_report": plan["skills_used"],
                         "request_sha256": hashlib.sha256(args.prompt_generate.encode("utf-8")).hexdigest(),
                         "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                         "planning_status": plan["planning_status"], "blockers": plan["blockers"],
                         "diagnostic_log": diagnostic.path.name,
                         "preflight": checks, "argv": argv,
                         "structural_validation": "passed; semantic quality requires human review",
                         "documents_sha256": {name: hashlib.sha256(value.encode("utf-8")).hexdigest() for name, value in documents.items()}}
                documents["planning-run.json"] = json.dumps(trace, ensure_ascii=False, indent=2) + "\n"
                progress.set_stage("文件写入中")
                publish(output, documents)
                progress.set_stage("文件写入完成")
    print(f"已生成 requirements.md、goals.md、goal0-prompt.md 和 planning-run.json\n状态：{plan['planning_status']}")
    return output


def main(argv=None):
    # Independent of Codex, skill discovery, configuration and network access.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    cli_parser = parser()
    args = cli_parser.parse_args(argv)
    if args.version:
        print(VERSION_TEXT)
        return 0
    if args.build is not None or args.resume is not None:
        try:
            from .build import build
            build(args)
            return 0
        except (APFError, OSError, ValueError) as exc:
            print(f"构建停止：{exc}", file=sys.stderr)
            return 1
        except KeyboardInterrupt:
            print("构建中断；保留检查点，使用 --resume 查看或安全接续。", file=sys.stderr)
            return 130
    if args.full_access or args.allow_local_git:
        cli_parser.error("--full-access、--allow-local-git 只用于 --build / --resume")
    if args.prompt_generate is None:
        if args.out or args.codex_path or args.skills_dir:
            cli_parser.error("--out、--codex-path 和 --skills-dir 需与 --prompt-generate 一起使用")
        cli_parser.print_help()
        return 0
    try:
        generate(args)
        return 0
    except APFError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"错误：文件、编码、进程或结果处理失败：{exc}。未完成生成，请检查输出目录权限和 Codex。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("错误：用户中断规划；本次子进程已停止。", file=sys.stderr)
        return 130

"""Deterministic CLI verification. No real Codex exec invocation is allowed."""

import contextlib
import copy
from datetime import datetime
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from apf_cli import APFError, VERSION_TEXT
from apf_cli.cli import generate, main, parser
from apf_cli.codex import (DISABLED_FEATURES, child_env, discover_codex, extract_response,
                           planner_argv, preflight, run_process)
from apf_cli.output import OUTPUT_NAMES, prepare_output, publish
from apf_cli.planning import render_plan, validate_plan
from apf_cli.skills import SKILL_NAMES, discover_skills, skill_roots, stage_skills, validate_skill
from tests.cli_fixtures.library_plan import library_plan

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get("APF_TEST_SCRATCH", str(ROOT / "validation" / "cli-progress-test-scratch")))
SCRATCH.mkdir(parents=True, exist_ok=True)


def events(plan=None, *, code=0):
    plan = library_plan() if plan is None else plan
    stdout = "\n".join(json.dumps(e, ensure_ascii=False) for e in [
        {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(plan, ensure_ascii=False)}},
        {"type": "turn.completed"}])
    return subprocess.CompletedProcess([], code, stdout, "")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def test_version_exact_without_codex_or_skills(self):
        out, err = io.StringIO(), io.StringIO()
        with patch("apf_cli.codex.discover_codex", side_effect=AssertionError("must not probe")), \
             patch("apf_cli.skills.discover_skills", side_effect=AssertionError("must not load")), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            self.assertEqual(main(["--version"]), 0)
        self.assertEqual(out.getvalue(), VERSION_TEXT + "\n")
        self.assertEqual(err.getvalue(), "")

    def test_release_version_matches_metadata_and_preserves_motto(self):
        import tomllib
        from apf_cli import VERSION
        metadata = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        self.assertEqual(metadata["version"], "1.0.0")
        self.assertEqual(VERSION, "1.0.0")
        self.assertEqual(VERSION_TEXT, "AI Project Factory 1.0.0\nWit beyond measure is man's greatest treasure")
        self.assertIn("AI Project Factory 1.0.0", parser().format_help())

    def test_help_and_version_subprocess_empty_path(self):
        env = dict(os.environ, PATH="", LOCALAPPDATA=str(self.directory), CODEX_HOME=str(self.directory))
        for args in (["--version"], ["--help"]):
            result = subprocess.run([sys.executable, "-m", "apf_cli", *args], cwd=ROOT,
                                    env=env, capture_output=True, encoding="utf-8")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stderr, "")
            if args == ["--version"]:
                self.assertEqual(result.stdout, VERSION_TEXT + "\n")
            else:
                self.assertIn("--prompt-generate", result.stdout)

    def test_parse_chinese_and_paths(self):
        args = parser().parse_args(["--prompt-generate", "我想开发一个图书馆管理系统", "--out", "计划 空间", "--codex-path", "工具.exe"])
        self.assertEqual(args.prompt_generate, "我想开发一个图书馆管理系统")
        self.assertEqual(args.out, "计划 空间")
        self.assertEqual(args.codex_path, "工具.exe")

    def test_invalid_parameters(self):
        for args in (["--prompt-generate"], ["--version", "--prompt-generate", "需求"], ["--timeout", "0"], ["--timeout", "abc"]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                parser().parse_args(args)
            self.assertEqual(error.exception.code, 2)

    def test_empty_input_before_any_discovery(self):
        with patch("apf_cli.codex.discover_codex", side_effect=AssertionError("must not discover")):
            with self.assertRaises(APFError):
                generate(parser().parse_args(["--prompt-generate", " \t "]))

    def test_explicit_and_path_codex_discovery(self):
        explicit = self.directory / "显式工具.exe"
        fallback = self.directory / "codex.exe"
        explicit.touch(); fallback.touch()
        which = lambda *a, **k: str(fallback)
        self.assertEqual(discover_codex(str(explicit), which=which, windows=True), explicit)
        self.assertEqual(discover_codex(which=which, windows=True), fallback)
        with self.assertRaises(APFError):
            discover_codex(str(self.directory / "missing.exe"), which=which, windows=True)

    def test_missing_codex_error(self):
        with self.assertRaisesRegex(APFError, "未找到 Codex"):
            discover_codex(environ={"PATH": ""}, which=lambda *a, **k: None, windows=True)

    def test_desktop_fallback_without_private_path(self):
        desktop = self.directory / "OpenAI/Codex/bin/build-hash"
        desktop.mkdir(parents=True)
        exe = desktop / "codex.exe"
        exe.touch()
        self.assertEqual(discover_codex(environ={"LOCALAPPDATA": str(self.directory)}, which=lambda *a, **k: None, windows=True), exe)

    def test_npm_wrapper_resolves_native_without_shell(self):
        wrapper = self.directory / "codex.cmd"
        wrapper.write_text("untrusted batch is not executed")
        exe = self.directory / "node_modules/@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/codex/codex.exe"
        exe.parent.mkdir(parents=True); exe.touch()
        self.assertEqual(discover_codex(str(wrapper), windows=True), exe)

    def test_skill_resource_snapshot_and_source_hashes(self):
        selected = discover_skills(roots=[ROOT / "skills"])
        records, context = stage_skills(selected, self.directory)
        self.assertEqual([r["name"] for r in records], list(SKILL_NAMES))
        for name in SKILL_NAMES:
            self.assertIn("$" + name, context)
            self.assertEqual((ROOT / "skills" / name / "SKILL.md").read_bytes(),
                             (self.directory / ".agents/skills" / name / "SKILL.md").read_bytes())
        self.assertIn("架构选择与基础门槛", context)
        self.assertIn("精确提示词写作", context)

    def test_skill_priority_repo_then_user_and_explicit_no_fallback(self):
        with patch("apf_cli.skills.Path.cwd", return_value=self.directory):
            roots = skill_roots(home=self.directory / "user", environ={})
        self.assertEqual(roots[0], self.directory / "skills")
        self.assertLess(roots.index(ROOT / "skills"), roots.index(self.directory / "user/.agents/skills"))
        with self.assertRaises(APFError):
            discover_skills(str(self.directory / "missing-root"))

    def test_skill_missing_resources_and_frontmatter_rejected(self):
        folder = self.directory / "requirement-planner"
        folder.mkdir()
        entry = folder / "SKILL.md"
        entry.write_text("---\nname: bad\ndescription: x\n---\ntext", encoding="utf-8")
        with self.assertRaises(APFError):
            validate_skill(folder, "requirement-planner")
        entry.write_text("---\nname: requirement-planner\ndescription: x\n---\n[资源](assets/missing.md)", encoding="utf-8")
        with self.assertRaises(APFError):
            validate_skill(folder, "requirement-planner")

    def test_readonly_argv_and_desktop_env_removed(self):
        argv = planner_argv("codex.exe", self.directory, self.directory / "schema.json", '模型"名')
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        self.assertEqual(argv[argv.index("--ask-for-approval") + 1], "never")
        self.assertEqual(argv[-1], "-")
        for feature in DISABLED_FEATURES:
            self.assertIn(["--disable", feature], [argv[i:i+2] for i in range(len(argv)-1)])
        for banned in ("--full-auto", "--worktree", "--add-dir", "--dangerously-bypass-approvals-and-sandbox", "resume", "review"):
            self.assertNotIn(banned, argv)
        env = child_env({"CODEX_HOME": "用户认证目录", "CODEX_PERMISSION_PROFILE": "full", "CODEX_APP_TOOLS_PIPE_PATH": "pipe",
                         "OPENAI_API_KEY": "secret", "PATH": "local"})
        self.assertEqual(env["CODEX_HOME"], "用户认证目录")
        self.assertNotIn("CODEX_PERMISSION_PROFILE", env)
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("CODEX_APP_TOOLS_PIPE_PATH", env)

    def test_incompatible_preflight_never_invokes_exec(self):
        seen = []
        def runner(argv, **kwargs):
            seen.append(argv)
            return subprocess.CompletedProcess(argv, 0, "codex-cli 0.1" if argv[-1] == "--version" else "unsupported", "")
        with self.assertRaises(APFError):
            preflight("fake.exe", self.directory, runner=runner)
        self.assertEqual(len(seen), 4)
        self.assertNotIn("-", [arg for call in seen for arg in call])

    def test_chinese_generation_real_mock_subprocess_single_turn(self):
        seen = []
        def runner(argv, **kwargs):
            seen.append(argv)
            return run_process([sys.executable, str(ROOT / "tests/cli_fixtures/fake_codex.py"), *argv[1:]], **kwargs)
        out = self.directory / "中文 图书馆计划"
        args = parser().parse_args(["--prompt-generate", "我想开发一个图书馆管理系统", "--out", str(out), "--codex-path", sys.executable])
        with patch("apf_cli.codex.configured_model", return_value=None), contextlib.redirect_stdout(io.StringIO()):
            generate(args, runner=runner)
        self.assertEqual(set(p.name for p in out.iterdir() if not p.name.startswith("apf-diagnostic-")), set(OUTPUT_NAMES))
        self.assertEqual(len(list(out.glob("apf-diagnostic-*.jsonl"))), 1)
        self.assertEqual(sum("-" == call[-1] for call in seen), 1)
        trace = json.loads((out / "planning-run.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["model_invocations"], 1)
        self.assertFalse(trace["other_roles_started"])
        for name in OUTPUT_NAMES[:3]:
            text = (out / name).read_text(encoding="utf-8")
            self.assertIn("图书馆", text)
            self.assertNotIn("{{", text)
        self.assertIn("G-2", (out / "goals.md").read_text(encoding="utf-8"))

    def test_not_logged_in_stops_before_fake_model_turn(self):
        seen = []
        def runner(argv, **kwargs):
            seen.append(argv)
            return run_process([sys.executable, str(ROOT / "tests/cli_fixtures/fake_codex.py"), *argv[1:]], **kwargs)
        args = parser().parse_args(["--prompt-generate", "我想开发一个图书馆管理系统",
                                  "--out", str(self.directory / "not-logged-in"), "--codex-path", sys.executable])
        with patch.dict(os.environ, {"APF_FAKE_NOT_LOGGED_IN": "1"}), self.assertRaisesRegex(APFError, "尚未登录"):
            generate(args, runner=runner)
        self.assertEqual(seen[-1][1:], ["login", "status"])
        self.assertFalse(any(call[-1] == "-" for call in seen))
        self.assertFalse(any((Path(args.out) / name).exists() for name in OUTPUT_NAMES))

    def test_safe_default_collision_suffix(self):
        now = datetime(2026, 10, 10, 12, 0)
        first = prepare_output(cwd=self.directory, now=now)
        second = prepare_output(cwd=self.directory, now=now)
        self.assertEqual(first.name, "apf-plan-20261010-120000")
        self.assertEqual(second.name, "apf-plan-20261010-120000-02")

    def test_cover_protection_and_unrelated_file(self):
        directory = prepare_output(self.directory / "out")
        original = directory / "requirements.md"
        original.write_text("历史文件", encoding="utf-8")
        with self.assertRaises(APFError):
            prepare_output(directory)
        self.assertEqual(original.read_text(encoding="utf-8"), "历史文件")
        with self.assertRaises(APFError):
            publish(directory, {n: "new" for n in OUTPUT_NAMES})

    def test_late_collision_rolls_back_only_created_files(self):
        directory = prepare_output(self.directory / "out")
        original_open = Path.open
        def racing_open(path, *args, **kwargs):
            if path.name == "goals.md" and args and args[0] == "x":
                with original_open(path, "w", encoding="utf-8") as stream:
                    stream.write("another writer")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", racing_open), self.assertRaises(FileExistsError):
            publish(directory, {n: "new" for n in OUTPUT_NAMES})
        self.assertFalse((directory / "requirements.md").exists())
        self.assertEqual((directory / "goals.md").read_text(), "another writer")

    def test_unwritable_directory_no_model_call(self):
        args = parser().parse_args(["--prompt-generate", "需求", "--out", str(self.directory)])
        with patch("apf_cli.codex.discover_codex", return_value=Path(sys.executable)), \
             patch("apf_cli.output.tempfile.TemporaryFile", side_effect=PermissionError("denied")), \
             patch("apf_cli.codex.preflight", side_effect=AssertionError("no model/probe")):
            with self.assertRaises(PermissionError):
                generate(args)

    def test_failed_and_illegal_model_results(self):
        for result in (events(code=9), subprocess.CompletedProcess([], 0, "garbage", ""),
                       subprocess.CompletedProcess([], 0, '{"type":"turn.failed"}', ""),
                       subprocess.CompletedProcess([], 0, '{"type":"turn.completed"}', "")):
            with self.assertRaises(APFError):
                extract_response(result)
        value = events()
        value.stdout += '\n{"type":"item.completed","item":{"type":"command_execution"}}'
        with self.assertRaises(APFError):
            extract_response(value)
        for kind in ("collab_agent_tool_call", "web_search", "file_change", "mcp_tool_call"):
            value = events()
            value.stdout += '\n' + json.dumps({"type": "item.started", "item": {"type": kind}})
            with self.subTest(kind=kind), self.assertRaises(APFError):
                extract_response(value)

    def test_duplicate_or_non_json_constants_rejected(self):
        for text in ('{"project_name":"one","project_name":"two"}', '{"value":NaN}'):
            result = events()
            result.stdout = '\n'.join(json.dumps(e) for e in [
                {"type": "item.completed", "item": {"type": "agent_message", "text": text}},
                {"type": "turn.completed"}])
            with self.assertRaises(APFError):
                extract_response(result)

    def test_failed_main_returns_nonzero_and_clear_error(self):
        stderr = io.StringIO()
        with patch("apf_cli.cli.generate", side_effect=APFError("模型失败，未生成规划文件")), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(["--prompt-generate", "需求"]), 1)
        self.assertIn("错误：模型失败", stderr.getvalue())

    def test_actual_process_timeout_is_bounded(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            run_process([sys.executable, "-c", "import time; time.sleep(15)"], cwd=self.directory, timeout=0.1)

    def test_invalid_structure_scope_dependencies_and_placeholders(self):
        base = library_plan()
        changes = [lambda p: p.pop("requirements_md"),
                   lambda p: p.update(goal0_prompt_md="# empty"),
                   lambda p: p.update(goal0_blueprint_md=p["goal0_blueprint_md"] + "{{目录}}"),
                   lambda p: p.update(goal0_prompt_md=p["goal0_prompt_md"] + " R-003"),
                   lambda p: p["goals"][0].update(depends_on=["G-2"]),
                   lambda p: p["goals"][0]["tasks"][0].update(depends_on=["T-003"]),
                   lambda p: p["goals"][0]["tasks"][0].update(acceptance_ids=["AC-003"]),
                   lambda p: p["goals"][0].update(scope="非法提前实现R-003图书目录"),
                   lambda p: p["requirements"][1].update(id="R-001"),
                   lambda p: p.update(skills_used=["requirement-planner"] * 3),
                   lambda p: p.update(planning_status="规划草案，待人工确认")]
        for change in changes:
            plan = copy.deepcopy(base); change(plan)
            with self.subTest(change=change), self.assertRaises(APFError):
                validate_plan(plan)
        self.assertEqual(set(render_plan(base)), set(OUTPUT_NAMES[:3]))

    def test_failure_or_timeout_publishes_no_files(self):
        for timeout in (False, True):
            directory = self.directory / str(timeout)
            def runner(argv, **kwargs):
                if argv[-1] == "-":
                    if timeout:
                        raise subprocess.TimeoutExpired(argv, 1)
                    return events(code=7)
                return run_process([sys.executable, str(ROOT / "tests/cli_fixtures/fake_codex.py"), *argv[1:]], **kwargs)
            args = parser().parse_args(["--prompt-generate", "需求", "--out", str(directory), "--codex-path", sys.executable])
            with patch("apf_cli.codex.configured_model", return_value=None), contextlib.redirect_stdout(io.StringIO()), self.assertRaises(APFError):
                generate(args, runner=runner)
            self.assertFalse(any((directory / name).exists() for name in OUTPUT_NAMES))
            logs = list(directory.glob("apf-diagnostic-*.jsonl"))
            self.assertEqual(len(logs), 1)
            self.assertIn("\"status\":\"failed\"", logs[0].read_text(encoding="utf-8"))

    def test_cli_does_not_import_execution_chain(self):
        result = subprocess.run([sys.executable, "-c", "from apf_cli.cli import main; import sys; main(['--version']); assert not any(n == 'factory' or n.startswith('factory.') for n in sys.modules)"],
                                cwd=ROOT, capture_output=True, encoding="utf-8")
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()

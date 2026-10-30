"""Verified local Codex CLI adapter. This module never imports factory.*."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import queue
import threading
import time
import tomllib

from . import APFError

DISABLED_FEATURES = ("shell_tool", "unified_exec", "multi_agent", "multi_agent_v2",
                     "plugins", "apps", "hooks", "memories", "skill_mcp_dependency_install")


def child_env(environ=None):
    source = os.environ if environ is None else environ
    # Preserve the user's auth home, not the desktop session's permissions/tools.
    env = {k: v for k, v in source.items()
           if (not k.upper().startswith("CODEX_") or k.upper() == "CODEX_HOME")
           and not re.search(r"(?i)(api_key|token|secret|password)", k)}
    env.update(PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", GIT_OPTIONAL_LOCKS="0")
    return env


def native_candidate(path, *, windows):
    path = Path(path).expanduser().resolve()
    if not path.is_file():
        return None
    if not windows or path.suffix.lower() == ".exe":
        return path
    # Standard npm wrappers: find their shipped native executable, never run a
    # .cmd/.ps1 through a shell with user paths or requirement text in arguments.
    if path.suffix.lower() in (".cmd", ".ps1"):
        candidates = sorted((path.parent / "node_modules" / "@openai").glob(
            "codex*/vendor/*-pc-windows-msvc/codex/codex.exe"))
        if len(candidates) == 1:
            return candidates[0].resolve()
    return None


def discover_codex(explicit=None, *, environ=None, which=None, windows=None):
    environ = os.environ if environ is None else environ
    windows = os.name == "nt" if windows is None else windows
    which = shutil.which if which is None else which
    if explicit is not None:
        candidate = native_candidate(explicit, windows=windows)
        if candidate is None:
            raise APFError("--codex-path 无效；请指定现有原生 codex.exe 文件。显式路径失败不会回退。")
        return candidate
    path_entry = which("codex", path=environ.get("PATH", ""))
    if path_entry:
        candidate = native_candidate(path_entry, windows=windows)
        if candidate:
            return candidate
    if windows and environ.get("LOCALAPPDATA"):
        desktop = Path(environ["LOCALAPPDATA"]) / "OpenAI" / "Codex" / "bin"
        candidates = [p for p in desktop.glob("*/codex.exe") if p.is_file()]
        if candidates:
            # Desktop hash directory names have no lexical version ordering.
            return max(candidates, key=lambda p: (p.stat().st_mtime_ns, str(p))).resolve()
    raise APFError("未找到 Codex CLI。请安装并登录 Codex，将其加入 PATH，或用 --codex-path 指定 codex.exe；APF 不会下载 Codex 或索取 API Key。")


def stop_process(process):
    """Stop only the process tree owned by this invocation."""
    if process.poll() is None:
        if os.name == "nt":
            try:
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
            except (OSError, subprocess.TimeoutExpired):
                pass
        else:
            import signal
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if process.poll() is None:
            process.kill()
        process.wait(timeout=5)


def stream_process(process, argv, stdin, timeout, on_event):
    """Drain both pipes concurrently; parse JSONL while the process is still live."""
    events = PlannerEvents(on_event)
    messages = queue.Queue(maxsize=256)
    stopped = threading.Event()
    started_at = time.monotonic()

    def deliver(value):
        while not stopped.is_set():
            try:
                messages.put(value, timeout=0.1)
                return
            except queue.Full:
                pass

    def reader(stream, kind):
        try:
            if kind == "stdout":
                for line in iter(stream.readline, b""):
                    deliver((kind, line))
            else:
                # Diagnostics can contain secrets or hidden content. Drain without
                # retaining, printing or treating stderr as a model event source.
                while stream.read(4096):
                    pass
        except OSError:
            deliver(("io_error", None))
        finally:
            deliver((kind, None))

    def writer():
        try:
            process.stdin.write(stdin.encode("utf-8"))
            process.stdin.flush()
        except OSError:
            deliver(("stdin_error", None))
        finally:
            try:
                process.stdin.close()
            except OSError:
                deliver(("stdin_error", None))
            deliver(("stdin", None))

    workers = [threading.Thread(target=reader, args=(process.stdout, "stdout"), daemon=True),
               threading.Thread(target=reader, args=(process.stderr, "stderr"), daemon=True),
               threading.Thread(target=writer, daemon=True)]
    for worker in workers:
        worker.start()
    closed = set()
    try:
        while len(closed) < 3 or process.poll() is None:
            remaining = timeout - (time.monotonic() - started_at)
            if remaining <= 0:
                raise subprocess.TimeoutExpired(argv, timeout)
            try:
                kind, value = messages.get(timeout=min(0.1, remaining))
            except queue.Empty:
                continue
            if kind == "io_error":
                raise APFError("无法读取 Codex 输出流；拒绝生成文件。")
            if kind == "stdin_error":
                events.input_failed = True
            elif value is None:
                closed.add(kind)
            elif kind == "stdout":
                events.feed_line(value.decode("utf-8", errors="replace"))
        result = subprocess.CompletedProcess(argv, process.returncode, "", "")
        result.planner_events = events
        return result
    except BaseException:
        stop_process(process)
        raise
    finally:
        stopped.set()
        for worker in workers:
            worker.join(timeout=0.5)
        for stream, worker in zip((process.stdout, process.stderr, process.stdin), workers):
            if not worker.is_alive():
                stream.close()


def run_process(argv, *, cwd, stdin="", timeout=20, env=None, on_event=None, on_start=None):
    process = None
    try:
        process = subprocess.Popen(
            [str(a) for a in argv], cwd=cwd, env=child_env() if env is None else env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        if on_start is not None:
            on_start()
        if on_event is not None:
            return stream_process(process, argv, stdin, timeout, on_event)
        stdout, stderr = process.communicate(stdin.encode("utf-8"), timeout=timeout)
        return subprocess.CompletedProcess(argv, process.returncode,
                                           stdout.decode("utf-8", errors="replace"),
                                           stderr.decode("utf-8", errors="replace"))
    except BaseException:
        if process is not None:
            stop_process(process)
            if on_event is None:
                for stream in (process.stdin, process.stdout, process.stderr):
                    try:
                        stream.close()
                    except OSError:
                        pass
        raise


def preflight(exe, cwd, *, runner=run_process):
    checks = {}
    for name, args in (("version", ["--version"]), ("help", ["--help"]),
                       ("exec_help", ["exec", "--help"]), ("features", ["features", "list"])):
        try:
            result = runner([str(exe), *args], cwd=cwd, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise APFError(f"Codex {name} 检查失败或超时，请检查 --codex-path。") from exc
        if result.returncode:
            raise APFError(f"Codex {name} 检查失败（退出码 {result.returncode}），未调用模型。")
        checks[name] = result.stdout
    if not re.fullmatch(r"codex-cli\s+\S+", checks["version"].strip()):
        raise APFError("指定程序未返回有效 codex-cli 版本，未调用模型。")
    top_flags = ("--no-daemon", "--ask-for-approval")
    exec_flags = ("--ignore-user-config", "--ignore-rules", "--ephemeral", "--sandbox",
                  "--skip-git-repo-check", "--output-schema", "--json", "--color", "--cd", "--disable", "--config")
    missing = [flag for flag in top_flags if flag not in checks["help"]]
    missing += [flag for flag in exec_flags if flag not in checks["exec_help"]]
    if "read-only" not in checks["exec_help"] or "stdin" not in checks["exec_help"]:
        missing.append("read-only/stdin")
    available = {line.split()[0] for line in checks["features"].splitlines() if line.split()}
    missing += [f"feature:{f}" for f in DISABLED_FEATURES if f not in available]
    if missing:
        raise APFError("本机 Codex 不支持必要的隔离/输出参数：" + ", ".join(missing)
                       + "。请更新已安装的 Codex；APF 不会降级权限或调用模型。")
    # Query the CLI, never open authentication files or persist auth output.
    # login status is local metadata, not an exec/model turn.
    try:
        login = runner([str(exe), "login", "status"], cwd=cwd, timeout=20)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise APFError("无法确认 Codex 登录状态，未调用模型。请先执行 codex login status。") from exc
    if login.returncode:
        raise APFError("Codex 尚未登录或登录状态不可用，未调用模型。请先执行 codex login；不需要额外 API Key。")
    checks["authentication"] = {"checked": True, "command": "codex login status", "exit_code": 0}
    return checks


def configured_model(environ=None):
    environ = os.environ if environ is None else environ
    config = Path(environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "config.toml"
    if not config.is_file():
        return None
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise APFError("用户 Codex config.toml 无法读取；请先修复配置。") from exc
    if data.get("model_provider", "openai") != "openai":
        raise APFError("CLI 1.0.0 仅支持已登录的 OpenAI Codex；自定义 model_provider 尚未支持，未调用模型。")
    model = data.get("model")
    if model is not None and (not isinstance(model, str) or not model.strip()):
        raise APFError("Codex model 配置无效。")
    return model


def planner_argv(exe, workspace, schema_path, model=None):
    argv = [str(exe), "--no-daemon", "--ask-for-approval", "never", "exec",
            "--ignore-user-config", "--ignore-rules", "--ephemeral",
            "--skip-git-repo-check", "--sandbox", "read-only", "--json", "--color", "never",
            "--cd", str(workspace), "--output-schema", str(schema_path),
            "--config", "project_doc_max_bytes=0", "--config", 'web_search="disabled"']
    if os.name == "nt":
        argv += ["--config", 'windows.sandbox="unelevated"']
    for feature in DISABLED_FEATURES:
        argv += ["--disable", feature]
    if model:
        argv += ["--config", "model=" + json.dumps(model, ensure_ascii=False)]
    return [*argv, "-"]


# Documented non-executing Codex items. An error item can be transient, just
# like a top-level error; final success still requires turn.completed and JSON.
PASSIVE_ITEMS = frozenset(("agent_message", "reasoning", "todo_list", "plan_update", "error"))
TOOL_ITEMS = frozenset(("command_execution", "file_change", "mcp_tool_call",
                        "web_search", "collab_tool_call", "collab_agent_tool_call",
                        "dynamic_tool_call"))


def safe_item_type(value):
    # Never reflect an unchecked / model-controlled string into terminal output.
    if isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", value):
        return value
    return "<invalid>"


class PlannerEvents:
    """Incremental event state. Ordinary errors are alerts, never proof of failure."""
    def __init__(self, on_event=None):
        self.on_event = on_event
        self.completed = 0
        self.threads = 0
        self.error_count = 0
        self.failed = False
        self.input_failed = False
        self.last_message = None

    def feed_line(self, line):
        try:
            event = json.loads(line, object_pairs_hook=unique_object, parse_constant=reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise APFError("Codex 返回非法 JSONL；拒绝生成文件。") from exc
        if not isinstance(event, dict):
            raise APFError("Codex 事件结构非法；拒绝生成文件。")
        # Audit/terminal observer sees even the event about to be rejected.
        # Never log or display raw item data through the diagnostic observer.
        if self.on_event is not None:
            self.on_event(event)
        if event.get("type") == "error":
            self.error_count += 1
        if event.get("type") == "turn.failed":
            self.failed = True
        self.threads += event.get("type") == "thread.started"
        self.completed += event.get("type") == "turn.completed"
        item = event.get("item", {})
        if event.get("type") in ("item.started", "item.updated", "item.completed"):
            if not isinstance(item, dict):
                raise APFError("Codex item 事件结构非法；拒绝生成文件。")
            item_type = item.get("type")
            if isinstance(item_type, str) and item_type in TOOL_ITEMS:
                raise APFError(f"Planner 返回禁止的工具类型事件（{safe_item_type(item_type)}）；拒绝接受结果。")
            if not isinstance(item_type, str) or item_type not in PASSIVE_ITEMS:
                raise APFError(f"Codex 返回未知 item 类型（{safe_item_type(item_type)}）；协议兼容性未确认，拒绝接受结果。")
            if event["type"] == "item.completed" and item_type == "error":
                self.error_count += 1
            if event["type"] == "item.completed" and item_type == "agent_message":
                self.last_message = item.get("text")

    def finish(self, returncode):
        if returncode:
            raise APFError(f"Codex 模型执行失败（退出码 {returncode}）。请检查登录（codex login status）、网络和额度；未生成规划文件。")
        if self.failed:
            raise APFError("Codex 规划回合失败；拒绝生成文件。请检查登录、网络和额度。")
        if self.input_failed:
            raise APFError("Codex 未完整接收规划输入；拒绝生成文件。")
        if self.completed != 1 or self.threads > 1 or not isinstance(self.last_message, str):
            raise APFError("Codex 未完成唯一规划回合或缺少最终内容；拒绝生成文件。")
        try:
            return json.loads(self.last_message, object_pairs_hook=unique_object, parse_constant=reject_constant)
        except (json.JSONDecodeError, ValueError) as exc:
            raise APFError("Codex 最终内容不是合法 JSON；拒绝生成文件。") from exc


def extract_response(result):
    events = getattr(result, "planner_events", None)
    if events is None:
        # Compatibility for deterministic in-memory test runners. Production
        # run_process already parsed events live and does not replay stdout.
        if result.returncode:
            return PlannerEvents().finish(result.returncode)
        events = PlannerEvents()
        for line in result.stdout.splitlines():
            events.feed_line(line)
    return events.finish(result.returncode)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError(f"non-JSON constant: {value}")

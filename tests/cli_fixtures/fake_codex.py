"""Local test subprocess; never contacts Codex or a model provider."""

import json
import os
from pathlib import Path
import sys
import time

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
from tests.cli_fixtures.library_plan import library_plan

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


def emit(event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


args = sys.argv[1:]
if args == ["--version"]:
    print("codex-cli 0.162.0-alpha.2")
elif args == ["--help"]:
    print("--no-daemon --ask-for-approval")
elif args == ["exec", "--help"]:
    print("--ignore-user-config --ignore-rules --ephemeral --sandbox read-only --skip-git-repo-check --output-schema --json --color --cd --disable --config stdin")
elif args == ["features", "list"]:
    from apf_cli.codex import DISABLED_FEATURES
    print("\n".join(f"{f} stable true" for f in DISABLED_FEATURES))
else:
    prompt = sys.stdin.buffer.read().decode("utf-8")
    assert "我想开发一个图书馆管理系统" in prompt
    assert "--sandbox" in args and args[args.index("--sandbox")+1] == "read-only"
    assert args[-1] == "-"
    if os.environ.get("APF_FAKE_FAIL"):
        raise SystemExit(9)
    scenario = os.environ.get("APF_FAKE_SCENARIO", "success")
    if scenario == "quiet":
        time.sleep(0.4)
    emit({"type": "thread.started", "thread_id": "mock-not-real-ai"})
    emit({"type": "turn.started"})
    if scenario in ("recover", "failed", "failed_then_completed", "missing_completion"):
        emit({"type": "error", "message": "stream disconnected; Reconnecting... 1/5; Bearer PRIVATE_CREDENTIAL"})
        time.sleep(0.1)
    # Synthetic sensitive markers: these must never reach APF terminal logs.
    print("PRIVATE_STDERR sk-SYNTHETIC_NOT_A_KEY Bearer PRIVATE_CREDENTIAL", file=sys.stderr, flush=True)
    if scenario in ("failed", "failed_then_completed"):
        emit({"type": "turn.failed", "error": {"message": "PRIVATE_ERROR_DETAIL"}})
        if scenario == "failed":
            raise SystemExit(0)
    if scenario == "missing_completion":
        raise SystemExit(0)
    if scenario == "timeout":
        time.sleep(30)
    if scenario in ("forbidden_tool", "unknown_item"):
        emit({"type": "item.started", "item": {
            "type": "command_execution" if scenario == "forbidden_tool" else "codex_future_metadata",
            "command": "PRIVATE_CREDENTIAL"}})
        time.sleep(0.1)
    emit({"type": "item.started", "item": {"type": "reasoning", "text": "PRIVATE_HIDDEN_REASONING"}})
    plan = library_plan()
    if scenario == "invalid_structure":
        plan.pop("goals")
    message = "not JSON PRIVATE_INVALID_RESULT" if scenario == "invalid_result" else json.dumps(plan, ensure_ascii=False)
    emit({"type": "item.completed", "item": {"type": "agent_message", "text": message}})
    emit({"type": "turn.completed", "usage": {"input_tokens": 0, "output_tokens": 0}})
    if scenario == "nonzero":
        raise SystemExit(9)

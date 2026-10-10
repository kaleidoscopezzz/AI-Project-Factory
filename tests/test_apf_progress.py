"""Real local pipe/heartbeat/cancellation tests. Never invoke a real model."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from apf_cli import APFError
from apf_cli.cli import generate, main, parser
from apf_cli.codex import PlannerEvents, child_env, extract_response, run_process
from apf_cli.progress import Progress

ROOT = Path(__file__).resolve().parents[1]
SCRATCH = Path(os.environ.get("APF_TEST_SCRATCH", str(ROOT / "validation" / "cli-progress-test-scratch")))
SCRATCH.mkdir(parents=True, exist_ok=True)


class TtyBuffer(io.StringIO):
    def isatty(self):
        return True


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=SCRATCH)
        self.directory = Path(self.temporary.name)
        self.addCleanup(self.temporary.cleanup)

    def test_long_silence_spinner_and_elapsed_do_not_claim_new_phase(self):
        now = [0.0]
        output = TtyBuffer()
        with Progress(output, clock=lambda: now[0], background=False) as progress:
            progress.process_started()
            for elapsed in (1.0, 30.0, 90.0, 123.0):
                now[0] = elapsed
                progress.refresh()
        text = output.getvalue()
        self.assertIn("02:03", text)
        self.assertGreaterEqual(text.count("\r"), 6)
        self.assertIn("| 00:00", text)
        self.assertIn("/ 00:00", text)
        self.assertNotIn("模型执行中", text)
        self.assertNotIn("完成", text)

    def test_noninteractive_periodic_logs_without_control_sequences(self):
        now = [0.0]
        output = io.StringIO()
        with Progress(output, clock=lambda: now[0], background=False) as progress:
            now[0] = 5.0; progress.refresh()
            now[0] = 10.0; progress.refresh()
            now[0] = 65.0; progress.refresh()
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 3)
        self.assertIn("01:05", lines[-1])
        self.assertNotIn("\r", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())

    def test_background_keeps_refreshing_with_no_child_events(self):
        output = TtyBuffer()
        with Progress(output, interval=0.02) as progress:
            result = run_process([sys.executable, "-c", "import time; time.sleep(0.25)"],
                                 cwd=self.directory, on_event=progress.event, on_start=progress.process_started)
        self.assertEqual(result.returncode, 0)
        self.assertGreater(output.getvalue().count("\r"), 4)
        self.assertNotIn("模型执行中", output.getvalue())
        self.assertFalse(progress.thread.is_alive())

    def test_event_is_parsed_before_child_exit_using_handshake(self):
        acknowledgement = self.directory / "ack"
        script = ("import json,time,sys; from pathlib import Path; "
                  "print(json.dumps({'type':'thread.started'}),flush=True); "
                  "p=Path(sys.argv[1]); deadline=time.monotonic()+3; "
                  "\nwhile not p.exists() and time.monotonic()<deadline: time.sleep(.01)"
                  "\nsys.exit(0 if p.exists() else 8)")
        def received(event):
            self.assertEqual(event["type"], "thread.started")
            acknowledgement.write_text("received live", encoding="utf-8")
        result = run_process([sys.executable, "-c", script, str(acknowledgement)],
                             cwd=self.directory, timeout=5, on_event=received)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.planner_events.threads, 1)

    def test_transient_error_requires_final_completion_and_no_failed_turn(self):
        events = PlannerEvents()
        for event in ({"type": "error", "message": "connection interrupted"},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok":true}'}},
                      {"type": "turn.completed"}):
            events.feed_line(json.dumps(event))
        self.assertEqual(events.finish(0), {"ok": True})
        self.assertEqual(events.error_count, 1)
        with self.assertRaises(APFError):
            events.finish(9)
        events.feed_line('{"type":"turn.failed"}')
        with self.assertRaises(APFError):
            events.finish(0)

    def test_only_ordinary_error_without_valid_result_cannot_pass(self):
        result = subprocess.CompletedProcess([], 0, '{"type":"error","message":"retry"}', "")
        with self.assertRaises(APFError):
            extract_response(result)

    def test_unknown_errors_do_not_invent_connection_or_retry(self):
        output = io.StringIO()
        with Progress(output, background=False) as progress:
            progress.event({"type": "error", "message": "PRIVATE_UNKNOWN_DETAIL"})
        self.assertIn("Codex 报告异常", output.getvalue())
        self.assertNotIn("连接异常", output.getvalue())
        self.assertNotIn("重试", output.getvalue())
        self.assertNotIn("PRIVATE_", output.getvalue())

    def test_retry_without_network_evidence_does_not_claim_connection_error(self):
        output = io.StringIO()
        with Progress(output, background=False) as progress:
            progress.event({"type": "error", "message": "rate limit; retrying PRIVATE_DETAIL"})
        self.assertIn("Codex 报告重试", output.getvalue())
        self.assertNotIn("连接异常", output.getvalue())
        self.assertNotIn("PRIVATE_", output.getvalue())

    def test_exhausted_retry_does_not_claim_retry_is_running(self):
        output = io.StringIO()
        with Progress(output, background=False) as progress:
            progress.event({"type": "error", "message": "connection failed; retry budget exhausted PRIVATE_DETAIL"})
        self.assertIn("连接异常，等待", output.getvalue())
        self.assertNotIn("正在重试", output.getvalue())
        self.assertNotIn("PRIVATE_", output.getvalue())

    def runner(self, scenario, calls):
        def run(argv, **kwargs):
            calls.append(argv)
            kwargs["env"] = dict(child_env(), APF_FAKE_SCENARIO=scenario)
            return run_process([sys.executable, str(ROOT / "tests/cli_fixtures/fake_codex.py"), *argv[1:]], **kwargs)
        return run

    def args(self):
        return parser().parse_args(["--prompt-generate", "我想开发一个图书馆管理系统 PRIVATE_SENSITIVE_INPUT",
                                   "--out", str(self.directory / "out"), "--codex-path", sys.executable])

    def test_network_error_recovers_then_validates_and_writes_once(self):
        calls, output, errors = [], io.StringIO(), io.StringIO()
        with patch("apf_cli.codex.configured_model", return_value=None), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            directory = generate(self.args(), runner=self.runner("recover", calls))
        trace = json.loads((directory / "planning-run.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["model_invocations"], 1)
        self.assertEqual(trace["automatic_retries"], 0)
        self.assertEqual(trace["observed_codex_error_events"], 1)
        self.assertEqual(sum(argv[-1] == "-" for argv in calls), 1)
        text = errors.getvalue()
        phases = ["Codex 子进程已启动", "Codex 会话已启动", "规划回合已启动", "连接异常", "模型输出已恢复",
                  "回合报告完成", "结构校验中", "结构校验通过", "文件写入中", "文件写入完成"]
        positions = [text.index(phase) for phase in phases]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("正在重试", text)
        for stream in (output.getvalue(), text):
            self.assertNotIn("PRIVATE_", stream)
            self.assertNotIn('"type":', stream)
        self.assertNotIn("[APF", output.getvalue())

    def test_final_failure_nonzero_or_invalid_output_never_writes(self):
        for scenario in ("failed", "failed_then_completed", "missing_completion", "nonzero", "invalid_result", "invalid_structure"):
            with self.subTest(scenario=scenario):
                args = self.args()
                args.out = str(self.directory / scenario)
                calls, output, errors = [], io.StringIO(), io.StringIO()
                with patch("apf_cli.codex.configured_model", return_value=None), \
                     contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), self.assertRaises(APFError):
                    generate(args, runner=self.runner(scenario, calls))
                self.assertFalse(any((Path(args.out) / name).exists() for name in ("requirements.md", "goals.md", "goal0-prompt.md", "planning-run.json")))
                self.assertEqual(len(list(Path(args.out).glob("apf-diagnostic-*.jsonl"))), 1)
                self.assertEqual(sum(argv[-1] == "-" for argv in calls), 1)
                self.assertNotIn("文件写入完成", errors.getvalue())
                self.assertNotIn("PRIVATE_", errors.getvalue())
                if scenario == "invalid_structure":
                    self.assertIn("结构校验中", errors.getvalue())
                    self.assertNotIn("结构校验通过", errors.getvalue())

    def test_timeout_kills_owned_process_and_does_not_publish(self):
        processes, calls = [], []
        real_popen = subprocess.Popen
        def track(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process
        args = self.args(); args.timeout = 0.2
        output, errors = io.StringIO(), io.StringIO()
        with patch("apf_cli.codex.subprocess.Popen", side_effect=track), \
             patch("apf_cli.codex.configured_model", return_value=None), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), self.assertRaisesRegex(APFError, "超时"):
            generate(args, runner=self.runner("timeout", calls))
        self.assertTrue(all(process.poll() is not None for process in processes))
        self.assertFalse(any((Path(args.out) / name).exists() for name in ("requirements.md", "goals.md", "goal0-prompt.md", "planning-run.json")))
        self.assertEqual(len(list(Path(args.out).glob("apf-diagnostic-*.jsonl"))), 1)
        self.assertEqual(sum(argv[-1] == "-" for argv in calls), 1)

    def test_ctrl_c_stops_actual_child_returns_130_and_restores_line(self):
        processes, calls = [], []
        real_popen = subprocess.Popen
        def track(*args, **kwargs):
            process = real_popen(*args, **kwargs)
            processes.append(process)
            return process
        class InterruptedProgress(Progress):
            def event(self, event):
                super().event(event)
                if event.get("type") == "thread.started":
                    raise KeyboardInterrupt
        runner = self.runner("timeout", calls)
        output, errors = io.StringIO(), TtyBuffer()
        args = self.args()
        with patch("apf_cli.codex.subprocess.Popen", side_effect=track), \
             patch("apf_cli.codex.run_process", side_effect=runner), \
             patch("apf_cli.codex.configured_model", return_value=None), \
             patch("apf_cli.progress.Progress", InterruptedProgress), \
             contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = main(["--prompt-generate", args.prompt_generate, "--out", args.out, "--codex-path", sys.executable])
        self.assertEqual(code, 130)
        self.assertTrue(all(process.poll() is not None for process in processes))
        self.assertFalse(any((Path(args.out) / name).exists() for name in ("requirements.md", "goals.md", "goal0-prompt.md", "planning-run.json")))
        self.assertEqual(len(list(Path(args.out).glob("apf-diagnostic-*.jsonl"))), 1)
        self.assertEqual(sum(argv[-1] == "-" for argv in calls), 1)
        self.assertIn("用户中断", errors.getvalue())
        self.assertTrue(errors.getvalue().endswith("\n"))
        self.assertNotIn("文件写入完成", errors.getvalue())

    def test_stderr_flood_is_drained_without_leaking_or_deadlock(self):
        code = ("import sys,json; sys.stdin.buffer.read(); "
                "sys.stderr.write('PRIVATE_STDERR'*20000); sys.stderr.flush(); "
                "print(json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'{}'}}),flush=True); "
                "print(json.dumps({'type':'turn.completed'}),flush=True)")
        output = io.StringIO()
        with Progress(output) as progress:
            result = run_process([sys.executable, "-c", code], cwd=self.directory, stdin="输入", timeout=5,
                                 on_event=progress.event, on_start=progress.process_started)
        self.assertEqual(extract_response(result), {})
        self.assertEqual(result.stderr, "")
        self.assertNotIn("PRIVATE_", output.getvalue())

    def test_blocked_stdin_does_not_block_progress_or_timeout(self):
        output = TtyBuffer()
        with Progress(output, interval=0.02) as progress:
            with self.assertRaises(subprocess.TimeoutExpired):
                run_process([sys.executable, "-c", "import time; time.sleep(30)"], cwd=self.directory,
                            stdin="input" * 100000, timeout=0.2,
                            on_event=progress.event, on_start=progress.process_started)
        self.assertGreater(output.getvalue().count("\r"), 3)


    def test_error_item_is_passive_but_requires_valid_completion(self):
        events = PlannerEvents()
        for event in ({"type": "item.completed", "item": {"type": "error", "message": "PRIVATE_SECRET"}},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": '{"ok": true}'}},
                      {"type": "turn.completed"}):
            events.feed_line(json.dumps(event))
        self.assertEqual(events.finish(0), {"ok": True})
        self.assertEqual(events.error_count, 1)

    def test_forbidden_vs_unknown_item_are_different_diagnostics(self):
        for kind, expected in (("command_execution", "禁止的工具类型"),
                               ("file_change", "禁止的工具类型"),
                               ("mcp_tool_call", "禁止的工具类型"),
                               ("web_search", "禁止的工具类型"),
                               ("codex_future_metadata", "未知 item 类型")):
            with self.subTest(kind=kind):
                with self.assertRaisesRegex(APFError, expected) as ctx:
                    PlannerEvents().feed_line(json.dumps({"type": "item.started", "item": {"type": kind, "command": "PRIVATE_SECRET"}}))
                self.assertIn(kind, str(ctx.exception))
                self.assertNotIn("PRIVATE_SECRET", str(ctx.exception))
        with self.assertRaisesRegex(APFError, "未知 item 类型"):
            PlannerEvents().feed_line('{"type":"item.started","item":{"type":{"invalid":"PRIVATE_SECRET"}}}')

    def test_diagnostic_file_success_redacts_sensitive_payloads(self):
        calls, out, err = [], io.StringIO(), io.StringIO()
        args = self.args(); args.out = str(self.directory / "diagnostic_success")
        with patch("apf_cli.codex.configured_model", return_value=None), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            directory = generate(args, runner=self.runner("recover", calls))
        logs = list(directory.glob("apf-diagnostic-*.jsonl"))
        self.assertEqual(len(logs), 1)
        log_text = logs[0].read_text(encoding="utf-8")
        records = [json.loads(line) for line in log_text.splitlines()]
        self.assertEqual(records[0]["record"], "run.started")
        self.assertEqual(records[-1]["status"], "success")
        self.assertIn("thread.started", log_text)
        self.assertIn("item.completed", log_text)
        for forbidden in ("PRIVATE_", "Bearer", "command", "token", "request", "图书馆", "aggregated_output"):
            self.assertNotIn(forbidden, log_text)
        trace = json.loads((directory / "planning-run.json").read_text(encoding="utf-8"))
        self.assertEqual(trace["diagnostic_log"], logs[0].name)
        self.assertIn(str(logs[0]), out.getvalue())

    def test_diagnostic_log_persists_on_protocol_rejection(self):
        for scenario, expected_item in (("forbidden_tool", "command_execution"),
                                        ("unknown_item", "codex_future_metadata")):
            with self.subTest(scenario=scenario):
                args = self.args(); args.out = str(self.directory / scenario)
                out, err = io.StringIO(), io.StringIO()
                with patch("apf_cli.codex.configured_model", return_value=None), \
                     contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), self.assertRaises(APFError):
                    generate(args, runner=self.runner(scenario, []))
                self.assertFalse(any((Path(args.out) / name).exists() for name in ("requirements.md", "goals.md", "goal0-prompt.md", "planning-run.json")))
                logs = list(Path(args.out).glob("apf-diagnostic-*.jsonl"))
                self.assertEqual(len(logs), 1)
                text = logs[0].read_text(encoding="utf-8")
                self.assertIn(expected_item, text)
                self.assertIn('"status":"failed"', text)
                self.assertNotIn("PRIVATE_", text)

    def test_diagnostic_log_does_not_overwrite_previous_run(self):
        from apf_cli.diagnostics import DiagnosticLog
        paths = []
        for _ in range(2):
            with DiagnosticLog(self.directory) as log:
                paths.append(log.path)
        self.assertNotEqual(paths[0], paths[1])
        self.assertTrue(all(p.exists() for p in paths))


if __name__ == "__main__":
    unittest.main()

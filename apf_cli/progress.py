"""Safe stderr-only progress: no model text, raw events or diagnostic messages."""

import re
import shutil
import sys
import threading
import time
import unicodedata


class Progress:
    def __init__(self, stream=None, *, clock=time.monotonic, interval=0.1,
                 log_interval=10, background=True):
        self.stream = sys.stderr if stream is None else stream
        self.clock = clock
        self.interval = interval
        self.log_interval = log_interval
        self.background = background
        self.interactive = self.stream.isatty()
        self.started_at = clock()
        self.stage = "启动 Codex 子进程"
        self.last_log = float("-inf")
        self.last_stage = None
        self.previous_width = 0
        self.frame = 0
        self.recovering = False
        self.turn_failed = False
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self.thread = None

    def __enter__(self):
        self.refresh()
        if self.background:
            self.thread = threading.Thread(target=self._refresh_loop, daemon=True)
            self.thread.start()
        return self

    def _refresh_loop(self):
        while not self.stopped.wait(self.interval):
            self.refresh()

    def refresh(self):
        with self.lock:
            now = self.clock()
            if not self.interactive and self.stage == self.last_stage and now - self.last_log < self.log_interval:
                return
            elapsed = max(0, int(now - self.started_at))
            timer = f"{elapsed // 60:02}:{elapsed % 60:02}"
            if self.interactive:
                marker = "|/-\\"[self.frame % 4]
                self.frame += 1
                text = f"{marker} {timer} {self.stage}"
                limit = max(20, shutil.get_terminal_size(fallback=(80, 24)).columns - 1)
                text, width = self._truncate(text, limit)
                self.stream.write("\r" + text + " " * max(0, self.previous_width - width))
                self.previous_width = width
            else:
                self.stream.write(f"[APF {timer}] {self.stage}\n")
            self.stream.flush()
            self.last_log, self.last_stage = now, self.stage

    @staticmethod
    def _truncate(text, limit):
        width, characters = 0, []
        for character in text:
            size = 2 if unicodedata.east_asian_width(character) in ("W", "F") else 1
            if width + size > limit:
                break
            characters.append(character)
            width += size
        return "".join(characters), width

    def set_stage(self, stage):
        with self.lock:
            self.stage = stage
        self.refresh()

    def process_started(self):
        self.set_stage("Codex 子进程已启动，等待会话事件")

    def event(self, event):
        kind = event.get("type")
        if self.turn_failed:
            return
        if kind == "turn.failed":
            self.turn_failed = True
            self.set_stage("规划回合失败，等待进程退出")
        elif kind == "error":
            self.recovering = True
            message = event.get("message", "")
            if not isinstance(message, str):
                message = ""
            nested = event.get("error")
            if isinstance(nested, dict) and isinstance(nested.get("message"), str):
                message += " " + nested["message"]
            # Only inspect text for classification; never echo any part of it.
            retry = re.search(r"reconnecting|retrying|will\s+retry|retry\s+scheduled|retry(?:\s+attempt)?\s+\d+\s*/\s*\d+|正在重试|正在重连|将重试", message, re.I)
            network = re.search(r"connect|network|stream.*disconnect|timed?\s*out|timeout|socket|\bTLS\b|\bDNS\b|连接|网络", message, re.I)
            if retry and network:
                self.set_stage("连接异常；Codex 正在重试，尚未确认恢复")
            elif retry:
                self.set_stage("Codex 报告重试，尚未确认恢复")
            elif network:
                self.set_stage("连接异常，等待 Codex 后续事件")
            else:
                self.set_stage("Codex 报告异常，等待后续事件")
        elif kind == "thread.started":
            self.set_stage("Codex 会话已启动，等待回合事件")
        elif kind == "turn.started":
            self.set_stage("规划回合已启动，等待模型输出")
        elif kind == "turn.completed":
            self.set_stage("回合报告完成，等待进程退出")
        elif kind in ("item.started", "item.updated", "item.completed"):
            item = event.get("item", {})
            if isinstance(item, dict) and item.get("type") == "error":
                self.set_stage("Codex 报告非终止错误项，等待后续事件")
            elif isinstance(item, dict) and item.get("type") in ("reasoning", "agent_message"):
                if self.recovering:
                    self.recovering = False
                    self.set_stage("模型输出已恢复，执行中")
                elif kind == "item.completed" and item.get("type") == "agent_message":
                    self.set_stage("已收到模型结果，等待回合完成")
                else:
                    self.set_stage("模型执行中，已收到输出事件")

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            if issubclass(exc_type, KeyboardInterrupt):
                self.set_stage("用户中断，生成未完成")
            else:
                self.set_stage("生成失败，结果未被接受")
        self.stopped.set()
        if self.thread is not None:
            self.thread.join(timeout=1)
        if self.interactive:
            with self.lock:
                self.stream.write("\n")
                self.stream.flush()

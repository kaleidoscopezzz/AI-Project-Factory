"""Choose predictable output directories and publish with exclusive creation."""

from datetime import datetime
import os
from pathlib import Path
import tempfile

from . import APFError

OUTPUT_NAMES = ("requirements.md", "goals.md", "goal0-prompt.md", "planning-run.json")


def prepare_output(explicit=None, *, cwd=None, now=None):
    cwd = Path.cwd() if cwd is None else Path(cwd)
    if explicit is None:
        stamp = (datetime.now() if now is None else now).strftime("%Y%m%d-%H%M%S")
        base = cwd / f"apf-plan-{stamp}"
        directory = base
        suffix = 1
        while True:
            try:
                directory.mkdir()
                break
            except FileExistsError:
                suffix += 1
                directory = cwd / f"{base.name}-{suffix:02d}"
    else:
        path = Path(explicit).expanduser()
        directory = path if path.is_absolute() else cwd / path
        directory.mkdir(parents=True, exist_ok=True)
    directory = directory.resolve()
    protect_output(directory)
    # Verify writability BEFORE a model call, not just via advisory os.access.
    with tempfile.TemporaryFile(dir=directory) as probe:
        probe.write(b"APF output preflight")
        probe.flush()
    return directory


def protect_output(directory):
    for name in OUTPUT_NAMES:
        if os.path.lexists(directory / name):
            raise APFError(f"输出文件已存在，禁止覆盖：{directory / name}；请使用新的 --out 目录。")


def publish(directory, documents):
    if set(documents) != set(OUTPUT_NAMES):
        raise APFError("内部输出集合不完整，拒绝发布。")
    protect_output(directory)
    created = []
    try:
        for name in OUTPUT_NAMES:
            target = directory / name
            # Exclusive creation also protects against a file appearing after preflight.
            with target.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(target)
                stream.write(documents[name])
                stream.flush()
                os.fsync(stream.fileno())
    except BaseException:
        # Only remove files exclusively created by this invocation. No directory cleanup.
        for target in created:
            target.unlink(missing_ok=True)
        raise

"""Locate and snapshot complete instruction resources; never install skills globally."""

import hashlib
import os
from pathlib import Path
import re
import shutil

from . import APFError

SKILL_NAMES = ("requirement-planner", "goal0-scaffolder", "goal-prompt-writer")


def skill_roots(explicit=None, *, home=None, environ=None):
    home = Path.home() if home is None else Path(home)
    environ = os.environ if environ is None else environ
    if explicit is not None:
        return [Path(explicit).expanduser().resolve()]
    return [
        Path.cwd() / "skills",
        Path(__file__).resolve().parent.parent / "skills",
        home / ".agents" / "skills",
        Path(environ.get("CODEX_HOME", str(home / ".codex"))) / "skills",
        Path(__file__).resolve().parent / "bundled_skills",
    ]


def resource_files(directory):
    """Reject symlinks/junctions rather than traversing resources outside a skill."""
    entries = [directory, *directory.rglob("*")]
    for entry in entries:
        stat = entry.lstat()
        if entry.is_symlink() or getattr(stat, "st_file_attributes", 0) & 0x400:
            raise APFError(f"Skill 资源含链接或重解析点，拒绝加载：{entry}")
    return sorted(p for p in entries if p.is_file())


def validate_skill(directory, name):
    entry = directory / "SKILL.md"
    if not entry.is_file():
        raise APFError(f"缺少 Skill：{entry}")
    files = resource_files(directory)
    text = entry.read_text(encoding="utf-8-sig")
    header = re.match(r"\A---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not header or not re.search(rf"(?m)^name:\s*['\"]?{re.escape(name)}['\"]?\s*$", header[1]):
        raise APFError(f"Skill name/frontmatter 不正确：{entry}")
    if not re.search(r"(?m)^description:\s*\S", header[1]):
        raise APFError(f"Skill description 缺失：{entry}")
    for file in files:
        if file.suffix != ".md":
            continue
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", file.read_text(encoding="utf-8-sig")):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (file.parent / target.split("#", 1)[0]).resolve()
            if not resolved.is_relative_to(directory.resolve()) or not resolved.is_file():
                raise APFError(f"Skill 资源引用缺失或越界：{file} -> {target}")
    return files


def discover_skills(explicit=None, *, roots=None):
    candidates = skill_roots(explicit) if roots is None else roots
    selected = {}
    for name in SKILL_NAMES:
        for root in candidates:
            directory = Path(root) / name
            if directory.exists():
                validate_skill(directory, name)
                selected[name] = directory.resolve()
                break
        else:
            raise APFError(f"未找到 {name}；请检查安装包，或用 --skills-dir 指向含三个完整 Skill 的目录。")
    return selected


def stage_skills(selected, workspace):
    records, context = [], []
    for name in SKILL_NAMES:
        source = selected[name]
        target = workspace / ".agents" / "skills" / name
        files = validate_skill(source, name)
        shutil.copytree(source, target)
        hashes = {}
        context.append(f"使用 ${name}；本次唯一指定副本：{target / 'SKILL.md'}")
        for file in files:
            relative = file.relative_to(source)
            data = file.read_bytes()
            staged = target / relative
            if data != staged.read_bytes():
                raise APFError(f"Skill 快照校验失败：{file}")
            hashes[relative.as_posix()] = hashlib.sha256(data).hexdigest()
            if file.suffix in (".md", ".yaml"):
                context.append(f"\n<skill-resource skill={name!r} path={relative.as_posix()!r}>\n"
                               + data.decode("utf-8-sig") + "\n</skill-resource>")
        records.append({"name": name, "source": str(source), "files_sha256": hashes})
    # Full content is supplied as instructions, including templates/references. The
    # planner needs no shell access to read it; normal .agents discovery is also staged.
    return records, "\n".join(context)

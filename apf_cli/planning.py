"""Structural planning contract and deterministic Markdown rendering."""

import re

from . import APFError
from .skills import SKILL_NAMES


def text_schema(minimum=1):
    return {"type": "string", "minLength": minimum}


def array_schema(items, minimum=0):
    return {"type": "array", "items": items, "minItems": minimum}


def object_schema(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


def response_schema():
    text = text_schema()
    texts = array_schema(text)
    acceptance = object_schema({"id": text, "precondition": text, "action": text,
                                "expected": text, "verification": text})
    requirement = object_schema({"id": text, "title": text, "source": text, "goal_id": text,
                                 "acceptance": array_schema(acceptance, 1)})
    task = object_schema({"id": text, "depends_on": texts, "inputs": array_schema(text, 1),
                          "outputs": array_schema(text, 1), "write_set": array_schema(text, 1),
                          "acceptance_ids": array_schema(text, 1)})
    goal = object_schema({"id": text, "title": text, "scope": text, "out_of_scope": text,
                          "depends_on": texts, "entry": text, "deliverables": array_schema(text, 1),
                          "exit": text, "extension_points": text, "tasks": array_schema(task, 1)})
    return object_schema({
        "project_name": text,
        "planning_status": {"type": "string", "enum": ["草案，不可派发", "规划草案，待人工确认"]},
        "blockers": texts,
        "skills_used": array_schema({"type": "string", "enum": list(SKILL_NAMES)}, 3),
        "requirements_md": text_schema(150), "requirements": array_schema(requirement, 1),
        "goals": array_schema(goal, 2), "goal0_blueprint_md": text_schema(600),
        "goal0_prompt_md": text_schema(900),
    })


def check_schema(value, schema, location="response"):
    kind = schema["type"]
    if kind == "object":
        if not isinstance(value, dict) or set(value) != set(schema["required"]):
            raise APFError(f"规划结构不完整或含非法字段：{location}")
        for key, subschema in schema["properties"].items():
            check_schema(value[key], subschema, f"{location}.{key}")
    elif kind == "array":
        if not isinstance(value, list) or len(value) < schema.get("minItems", 0):
            raise APFError(f"规划列表缺失或为空：{location}")
        for i, item in enumerate(value):
            check_schema(item, schema["items"], f"{location}[{i}]")
    elif kind == "string":
        if not isinstance(value, str) or len(value.strip()) < schema.get("minLength", 1):
            raise APFError(f"规划内容为空或过短：{location}")
        if "enum" in schema and value not in schema["enum"]:
            raise APFError(f"规划枚举值非法：{location}")
        if re.search(r"\{\{.*?\}\}|\bTODO\b|\bTBD\b|<待填[^>]*>", value, re.S | re.I) or "\x00" in value:
            raise APFError(f"规划仍含模板占位符或非法字符：{location}")


def stable_id(value, prefix, known):
    if not re.fullmatch(rf"{prefix}-\d{{3,}}", value) or value in known:
        raise APFError(f"ID 非法或重复：{value}")
    known.add(value)


def check_headings(markdown, groups, label):
    headings = re.findall(r"(?m)^##\s+(.+)$", markdown)
    for words in groups:
        if not any(all(word in heading for word in words) for heading in headings):
            raise APFError(f"{label} 缺少必要章节：{'、'.join(words)}")
    # A title-only section must not masquerade as an implemented plan.
    for part in re.split(r"(?m)^##\s+.+$", markdown)[1:]:
        body = re.sub(r"(?m)^\s*#+.*$", "", part).strip()
        if len(body) < 12:
            raise APFError(f"{label} 含空章节或内容过短。")


def validate_plan(plan):
    check_schema(plan, response_schema())
    if sorted(plan["skills_used"]) != sorted(SKILL_NAMES):
        raise APFError("结果未声明复用全部三个 Skills。")
    if bool(plan["blockers"]) != (plan["planning_status"] == "草案，不可派发"):
        raise APFError("规划阻塞项与可派发状态矛盾。")
    requirements, acceptances, tasks = set(), set(), set()
    goal_ac, goal_r, goal_t = {}, {}, {}
    goals = plan["goals"]
    goal_ids = [g["id"] for g in goals]
    if goal_ids != [f"G-{i}" for i in range(len(goals))]:
        raise APFError("Goals 必须从 G-0 开始连续编号并按依赖顺序列出。")
    for r in plan["requirements"]:
        stable_id(r["id"], "R", requirements)
        if r["goal_id"] not in goal_ids:
            raise APFError(f"需求引用不存在的 Goal：{r['id']}")
        goal_r.setdefault(r["goal_id"], set()).add(r["id"])
        for ac in r["acceptance"]:
            stable_id(ac["id"], "AC", acceptances)
            goal_ac.setdefault(r["goal_id"], set()).add(ac["id"])
    previous_goals = set()
    task_owner = {}
    ancestors = {}
    for goal in goals:
        gid = goal["id"]
        deps = goal["depends_on"]
        if len(deps) != len(set(deps)) or not set(deps) <= previous_goals:
            raise APFError(f"Goal 依赖缺失、重复、成环或顺序不可执行：{gid}")
        if (gid == "G-0" and deps) or (gid != "G-0" and not deps):
            raise APFError(f"Goal 进入依赖不完整：{gid}")
        if gid not in goal_r:
            raise APFError(f"Goal 没有绑定需求：{gid}")
        ancestors[gid] = set(deps)
        for dep in deps:
            ancestors[gid] |= ancestors[dep]
        covered = set()
        for task in goal["tasks"]:
            tid = task["id"]
            dependency = task["depends_on"]
            if len(dependency) != len(set(dependency)) or not set(dependency) <= tasks:
                raise APFError(f"Task 依赖不存在、成环或顺序不可执行：{tid}")
            if any(task_owner[d] not in ancestors[gid] | {gid} for d in dependency):
                raise APFError(f"Task 依赖与 Goal 依赖不一致：{tid}")
            stable_id(tid, "T", tasks)
            task_owner[tid] = gid
            goal_t.setdefault(gid, set()).add(tid)
            acs = task["acceptance_ids"]
            if len(acs) != len(set(acs)) or not set(acs) <= goal_ac[gid]:
                raise APFError(f"Task 的 AC 超出所属 Goal 或重复：{tid}")
            covered |= set(acs)
        if covered != goal_ac[gid]:
            raise APFError(f"Goal 的 AC 缺少 Task 覆盖：{gid}")
        for prefix, allowed in (("R", goal_r[gid]), ("AC", goal_ac[gid]), ("T", goal_t[gid])):
            refs = set(re.findall(rf"(?<![A-Za-z0-9_-]){prefix}-\d{{3,}}(?![A-Za-z0-9_-])", goal["scope"]))
            if not refs <= allowed:
                raise APFError(f"Goal 范围引用了其他阶段的 {prefix}-ID：{gid}")
        previous_goals.add(gid)
    check_headings(plan["requirements_md"], [("定位", "边界"), ("假设", "约束"), ("待确认", "风险")], "需求说明")
    check_headings(plan["goal0_blueprint_md"], [
        ("输入", "边界"), ("技术", "决策"), ("目录", "契约"), ("UI", "交互"),
        ("身份", "权限"), ("数据", "生命周期"), ("工程", "运行"), ("实施", "验收"),
        ("状态", "证据"), ("退出", "门槛")], "Goal 0 工程方案")
    check_headings(plan["goal0_prompt_md"], [
        ("项目", "背景"), ("工作目录", "环境"), ("当前", "基线"), ("目标", "范围"),
        ("实施", "步骤"), ("页面", "交互"), ("数据", "身份", "状态"), ("修改", "边界"),
        ("测试", "运行"), ("验收", "证据"), ("完成", "标准"), ("失败", "处理"),
        ("最终", "报告"), ("完成后", "停止")], "Goal 0 提示词")
    for field in ("goal0_blueprint_md", "goal0_prompt_md"):
        for prefix, allowed in (("R", goal_r["G-0"]), ("AC", goal_ac["G-0"]), ("T", goal_t["G-0"])):
            # Chinese characters are Unicode word characters, so \b would miss
            # valid references such as "R-001可运行" and weaken scope checks.
            references = set(re.findall(rf"(?<![A-Za-z0-9_-]){prefix}-\d{{3,}}(?![A-Za-z0-9_-])", plan[field]))
            if not references <= allowed or (field == "goal0_prompt_md" and references != allowed):
                raise APFError(f"{field} 的 {prefix}-ID 与 Goal 0 范围不一致。")
    if "待外部 Reviewer 验收" not in plan["goal0_prompt_md"]:
        raise APFError("Goal 0 提示词缺少外部验收与停止边界。")
    return plan


def cell(value):
    return value.replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def render_plan(plan):
    validate_plan(plan)
    status = plan["planning_status"]
    blockers = "\n".join(f"- {b}" for b in plan["blockers"]) or "无已识别阻塞；仍须人工确认规划。"
    requirements = plan["requirements_md"].rstrip() + "\n\n## 需求与验收映射\n\n"
    requirements += "| R-ID | 需求 | 来源与确定性 | Goal | AC-ID | 前置 → 动作 → 结果 | 验证 |\n| --- | --- | --- | --- | --- | --- | --- |\n"
    for r in plan["requirements"]:
        for ac in r["acceptance"]:
            values = [r["id"], r["title"], r["source"], r["goal_id"], ac["id"],
                      f"{ac['precondition']} → {ac['action']} → {ac['expected']}", ac["verification"]]
            requirements += "| " + " | ".join(cell(v) for v in values) + " |\n"
    requirements += f"\n## 规划状态\n\n{status}\n\n{blockers}\n"
    goals = f"# {plan['project_name']} 软件开发 Goals\n\n状态：{status}。以下均为规划，不代表已开发或已验收。\n"
    for goal in plan["goals"]:
        gid = goal["id"]
        ids = ", ".join(r["id"] for r in plan["requirements"] if r["goal_id"] == gid)
        goals += f"\n## Goal {gid[2:]}（{gid}）：{goal['title']}\n\n"
        for label, value in (("阶段依赖", ", ".join(goal["depends_on"]) or "无"), ("进入基线", goal["entry"]),
                             ("范围", goal["scope"]), ("不做项", goal["out_of_scope"]), ("需求", ids),
                             ("产物", "；".join(goal["deliverables"])), ("退出门槛", goal["exit"]),
                             ("后续增量入口", goal["extension_points"])):
            goals += f"- {label}：{value}\n"
        goals += "\n| Task-ID | depends_on | 输入 | 输出 | 可写范围 | AC-ID |\n| --- | --- | --- | --- | --- | --- |\n"
        for task in goal["tasks"]:
            values = [task["id"], ", ".join(task["depends_on"]) or "无", "；".join(task["inputs"]),
                      "；".join(task["outputs"]), "；".join(task["write_set"]), ", ".join(task["acceptance_ids"])]
            goals += "| " + " | ".join(cell(v) for v in values) + " |\n"
    goals += f"\n## 阻塞与交接\n\n{blockers}\n\n依赖顺序以本文件顺序为准。共享契约和根配置须由单一整合者管理；本 CLI 不调度上述任务。\n"
    g0 = plan["goals"][0]
    prompt = f"# {plan['project_name']} — Goal 0 开发交接\n\n状态：{status}\n\n{blockers}\n\n"
    prompt += f"Goal 0 唯一阶段范围（与 goals.md 同源）：{g0['scope']}\n\n不做项：{g0['out_of_scope']}\n\n"
    prompt += plan["goal0_prompt_md"].rstrip()
    prompt += "\n\n---\n\n# 随提示词交付的 Goal 0 工程方案\n\n" + plan["goal0_blueprint_md"].rstrip() + "\n"
    return {"requirements.md": requirements, "goals.md": goals, "goal0-prompt.md": prompt}

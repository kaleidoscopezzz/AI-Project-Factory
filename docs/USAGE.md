# 中文使用说明

## 1. 本轮交付与使用边界
本轮只在 `C:\AI-Project-Factory` 开发，三个 Skills 尚未复制到用户级发现目录。可以立即让 Codex 按文件路径读取执行；本轮验证使用的正是这种方式。没有实现自动派发 Coder、测试调度、Git冻结或发布。

不需要付费服务/API key，Skills 本身是指令和模板；真正开发项目所需框架、服务、数据库与权限由项目决定。

## 2. 不安装也可使用
在其他项目发一条完整指令，例如：

```text
请读取 C:\AI-Project-Factory\skills\requirement-planner\SKILL.md 及其必要资源，按该 Skill 为以下需求生成计划：……。
当前项目目录：……；现有状态：……；允许/禁止操作：……。
只输出规划，不开发业务，重大歧义列待确认。
```

然后读取 `goal0-scaffolder\SKILL.md`，传入计划与项目环境；最后读取 `goal-prompt-writer\SKILL.md`，传入计划、方案、当前基线和权限。输出应是直接给 Coder 的提示词，不能只有建议。此方式是显式文件工作流，不等于已注册 `$skill-name`。

一条串联指令也可：

```text
按 C:\AI-Project-Factory\skills 下三个 SKILL.md 的流程，依次为以下需求生成计划、Goal 0 工程方案和 Coder 提示词：……。
工程目录：……。当前基线：……。环境/数据/部署限制：……。本次只生成文档，禁止 Git 写入和发布。
将输出保存在当前项目 docs/planning/；有重大歧义则标草案和阻塞范围。
```

## 3. 用户级安装（供用户之后手动执行）
标准 Skills 以目录中的 `SKILL.md` 及 YAML `name/description` 被发现；可选 `agents/openai.yaml` 提供显示信息。当前官方文档列出的用户级本地路径是 `~/.agents/skills`，项目级为 `.agents/skills`；发现未更新时可重启客户端。[官方 Build skills 文档](https://learn.chatgpt.com/docs/build-skills)（2026-10-08 核对）。

当前会话实际提供的已有 Skills 在 `C:\Users\44725\.codex\skills`，说明不同客户端/版本的目录可能有差异。默认按当前官方路径安装；若客户端明确使用旧 `.codex\skills`，以其实际配置/发现结果为准，择一放置，避免同名重复。安装后的自动发现和菜单显示本轮未实测。

以下 PowerShell 示例复制到当前官方用户路径，**本轮未执行**。先核对目标目录；同名已有目录会停止，不覆盖。

```powershell
$factorySource = 'C:\AI-Project-Factory\skills'
$factorySkillRoot = Join-Path $env:USERPROFILE '.agents\skills'
$factorySkillNames = @('requirement-planner', 'goal0-scaffolder', 'goal-prompt-writer')
foreach ($factoryName in $factorySkillNames) {
    $factoryTarget = Join-Path $factorySkillRoot $factoryName
    if (Test-Path -LiteralPath $factoryTarget) {
        throw "已有同名 Skill，请先人工比较与备份：$factoryTarget"
    }
    if (-not (Test-Path -LiteralPath (Join-Path $factorySource "$factoryName\SKILL.md"))) {
        throw "源 Skill 不完整：$factoryName"
    }
}
New-Item -ItemType Directory -Path $factorySkillRoot -Force | Out-Null
foreach ($factoryName in $factorySkillNames) {
    Copy-Item -LiteralPath (Join-Path $factorySource $factoryName) -Destination $factorySkillRoot -Recurse
}
```

整个 Skill 目录都要复制，包括 references/assets/agents，不只 SKILL.md。无需复制整个项目或 `.tools`。其他操作系统使用其用户目录下的 `.agents/skills`，不依赖这段 Windows 示例。

安装后在新会话明确说“使用 $requirement-planner …”，或选择客户端发现的对应 Skill。按相同方式使用 `$goal0-scaffolder` 和 `$goal-prompt-writer`。若未显示，检查所用客户端的目录、SKILL.md frontmatter、禁用配置和同名目录，按官方说明重启；不要据此修改用户全局配置。

## 4. 应提供哪些输入
需求可以一句话，也可以 PRD/功能清单路径。补充目标用户、DEMO/真实系统、运行部署平台、现有技术栈、数据来源、当前 PROJECT_STATUS/基线、允许修改目录和禁操作。没有的信息会分成可撤销假设与重大待确认；真实业务、外部副作用和权限问题不会静默默认。

完整流程产出计划→工程方案→可执行提示词。已有项目的新需求通常只用 Planner 和 Prompt Writer；Scaffolder 仅在需要基础建设或升级时使用，避免重复搭架子。

Coder 执行提示词前核实真实目标目录和基线；文档里的拟定命令须由 Coder 实现并实际运行，不能把案例文档中的预期结果当自测结果。完成后等外部 Reviewer，Git/冻结/发布仍由当前项目授权控制。

## 5. 模板和案例位置
所有权威模板索引在 [README](../README.md)。`{{…}}` 是模板填写位置，仅模板允许保留；最终派发提示词不能有未填关键项。

- 案例 A：[输入](../validation/cases/case-a/input.md)、[需求计划](../validation/cases/case-a/plan.md)、[骨架方案](../validation/cases/case-a/goal0-blueprint.md)、[Coder 提示词](../validation/cases/case-a/goal0-prompt.md)。
- 案例 B：[输入](../validation/cases/case-b/input.md)、[需求计划](../validation/cases/case-b/plan.md)、[骨架方案](../validation/cases/case-b/goal0-blueprint.md)、[Coder 提示词](../validation/cases/case-b/goal0-prompt.md)。

案例只做文档行为验证，没有开发两个系统。`task-packet.json` 是未来交接数据设计示例；`evaluation.md`、验证报告保存检查结论，便于外部 Reviewer 核对。

## 6. 本项目验证复现
本机 `.tools/validation-env` 是仅在项目内创建的 Python 虚拟环境，安装 PyYAML 6.0.3，用于 YAML 格式检查；不是 Skill 运行依赖，也不安装全局包。脚本只是交付 QA，不是调度程序。

```powershell
& C:\AI-Project-Factory\.tools\validation-env\Scripts\python.exe -X utf8 C:\AI-Project-Factory\scripts\validate_delivery.py --official-validator C:\Users\44725\.codex\skills\.system\skill-creator\scripts\quick_validate.py
```

换机器时可在本项目另建 Python venv 并装 `PyYAML==6.0.3`，指定本机 skill-creator 的 quick_validate.py 路径。验证结果写 `validation/checks.json`；脚本不执行案例业务命令。

参考只读复核命令 `python scripts/reference_guard.py after` 只适用于本次原目录和已存在 before.json，比较当前状态，不重新运行参考工程；不得重建/覆盖 before.json 来掩盖变化。其结果包括覆盖限制。

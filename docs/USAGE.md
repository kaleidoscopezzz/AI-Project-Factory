# 中文使用说明

## 1. Skills 使用边界
本文介绍三个 Skills 的独立使用方式；工厂现已支持真实角色派发和受控两阶段接续，主线入口见 [快速开始](GOAL1_USAGE.md)。Goal 0 验证采用按文件读取方式，用户级自动发现未实测；Git/发行自动化尚未实现。

不需要付费服务/API key，Skills 本身是指令和模板；真正开发项目所需框架、服务、数据库与权限由项目决定。

## 2. 不安装也可使用
在其他项目发一条完整指令，例如：

```text
请读取 <项目目录>\skills\requirement-planner\SKILL.md 及其必要资源，按该 Skill 为以下需求生成计划：……。
当前项目目录：……；现有状态：……；允许/禁止操作：……。
只输出规划，不开发业务，重大歧义列待确认。
```

然后读取 `goal0-scaffolder\SKILL.md`，传入计划与项目环境；最后读取 `goal-prompt-writer\SKILL.md`，传入计划、方案、当前基线和权限。输出应是直接给 Coder 的提示词，不能只有建议。此方式是显式文件工作流，不等于已注册 `$skill-name`。

一条串联指令也可：

```text
按 <项目目录>\skills 下三个 SKILL.md 的流程，依次为以下需求生成计划、Goal 0 工程方案和 Coder 提示词：……。
工程目录：……。当前基线：……。环境/数据/部署限制：……。本次只生成文档，禁止 Git 写入和发布。
将输出保存在当前项目 docs/planning/；有重大歧义则标草案和阻塞范围。
```

## 3. 用户级安装（供用户之后手动执行）
标准 Skills 以目录中的 `SKILL.md` 及 YAML `name/description` 被发现；可选 `agents/openai.yaml` 提供显示信息。Goal 0 阶段参考文档列出的用户级本地路径是 `~/.agents/skills`，项目级为 `.agents/skills`；发现未更新时可重启客户端。[官方 Build skills 文档](https://learn.chatgpt.com/docs/build-skills)（2026-10-08 核对）。

不同客户端/版本的 Skill 发现目录可能有差异。实际采用所用客户端支持的发现目录；若客户端明确使用旧 `.codex\skills`，以其实际配置/发现结果为准，择一放置，避免同名重复。安装后的自动发现和菜单显示本轮未实测。

以下 PowerShell 示例复制到上述用户目录示例，**本轮未执行**。先核对目标目录；同名已有目录会停止，不覆盖。

```powershell
$factorySource = Join-Path (Get-Location) 'skills'
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

整个 Skill 目录都要复制，包括 references/assets/agents，不只 SKILL.md。无需复制整个项目或 `.tools`。当前 APF 工厂仅面向 Windows；Skills 的客户端发现方式请核对所用客户端，本文不承诺跨平台工厂运行。

安装后在新会话明确说“使用 $requirement-planner …”，或选择客户端发现的对应 Skill。按相同方式使用 `$goal0-scaffolder` 和 `$goal-prompt-writer`。若未显示，检查所用客户端的目录、SKILL.md frontmatter、禁用配置和同名目录，按官方说明重启；不要据此修改用户全局配置。

## 4. 应提供哪些输入
需求可以一句话，也可以 PRD/功能清单路径。补充目标用户、DEMO/真实系统、运行部署平台、现有技术栈、数据来源、当前 PROJECT_STATUS/基线、允许修改目录和禁操作。没有的信息会分成可撤销假设与重大待确认；真实业务、外部副作用和权限问题不会静默默认。

完整流程产出计划→工程方案→可执行提示词。已有项目的新需求通常只用 Planner 和 Prompt Writer；Scaffolder 仅在需要基础建设或升级时使用，避免重复搭架子。

Coder 执行提示词前核实真实目标目录和基线；文档里的拟定命令须由 Coder 实现并实际运行，不能把案例文档中的预期结果当自测结果。完成后等外部 Reviewer，Git/冻结/发布仍由当前项目授权控制。

## 5. 模板和案例位置
每种模板保留一份权威源：

| 用途 | 模板 |
| --- | --- |
| 需求计划 | [需求计划](../skills/requirement-planner/assets/requirement-plan.md) |
| 工程骨架 | [Goal 0 方案](../skills/goal0-scaffolder/assets/goal0-blueprint.md) |
| 开发提示词 | [Goal 提示词](../skills/goal-prompt-writer/assets/goal-development-prompt.md) |
| 状态 | [状态模板](../skills/goal-prompt-writer/assets/project-status.md) |
| 验收 | [验收模板](../skills/goal-prompt-writer/assets/acceptance-record.md) |

`{{…}}` 是模板填写位置，仅模板允许保留；最终派发提示词不能有未填关键项。

- 案例 A：[输入](../validation/cases/case-a/input.md)、[需求计划](../validation/cases/case-a/plan.md)、[骨架方案](../validation/cases/case-a/goal0-blueprint.md)、[Coder 提示词](../validation/cases/case-a/goal0-prompt.md)。
- 案例 B：[输入](../validation/cases/case-b/input.md)、[需求计划](../validation/cases/case-b/plan.md)、[骨架方案](../validation/cases/case-b/goal0-blueprint.md)、[Coder 提示词](../validation/cases/case-b/goal0-prompt.md)。

案例只做文档行为验证，没有开发两个系统。`task-packet.json` 是未来交接数据设计示例；`evaluation.md`、验证报告保存检查结论，便于外部 Reviewer 核对。

## 6. 历史验证与当前维护

Goal 0 进行了 YAML 格式、资源引用和两类案例行为检查；这些案例没有开发为业务系统。用户级安装的自动发现未实测，不能把目录格式通过视为全局安装成功。

`scripts/validate_delivery.py` 是 Goal 0 专项交付检查，依赖 PyYAML、外部 Skill 格式校验器及当时参考资料，不是跨机器的快速开始命令。日常工厂控制回归见 [快速开始](GOAL1_USAGE.md)，不要运行历史参考工程、覆盖历史检查记录或为了文档更新安装全局资源。

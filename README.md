# AI Project Factory

Goal 0：建设 `requirement-planner`、`goal0-scaffolder`、`goal-prompt-writer` 三个可复用 Codex Skills。本项目当前是 Skills 与验证材料库，多 Agent 自动调度尚未实现。

- [中文使用与用户级安装说明](docs/USAGE.md)
- [项目状态](PROJECT_STATUS.md)
- [经验来源与边界](docs/SOURCE_EXPERIENCE.md)
- [验证结果](validation/REPORT.md)
- [未来多 Agent 建设方案](docs/MULTI_AGENT_ROADMAP.md)

模板只保留一份权威源：

| 用途 | 文件 |
| --- | --- |
| 需求计划 | [requirement-plan.md](skills/requirement-planner/assets/requirement-plan.md) |
| Goal 0 工程骨架 | [goal0-blueprint.md](skills/goal0-scaffolder/assets/goal0-blueprint.md) |
| Goal 开发提示词 | [goal-development-prompt.md](skills/goal-prompt-writer/assets/goal-development-prompt.md) |
| 项目状态 | [project-status.md](skills/goal-prompt-writer/assets/project-status.md) |
| 验收与证据 | [acceptance-record.md](skills/goal-prompt-writer/assets/acceptance-record.md) |

案例输入与输出在 `validation/cases/case-a/`、`case-b/`。各 Skill 目录自包含，可整目录复制安装；文档和 `.tools/` 验证环境不需要一起安装。

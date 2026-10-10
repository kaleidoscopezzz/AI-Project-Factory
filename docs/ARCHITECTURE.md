# APF 技术架构

当前目标环境是 Windows 11、PowerShell、Python 与本地 Codex CLI。APF Goal 0～3 已批准；Goal 2 为有限范围批准，Goal 3 为受控双阶段真实交付批准。详细验证边界见 [能力说明](VERIFIED_CAPABILITIES.md)。

## 执行层与角色

| 组件 | 实际职责 |
| --- | --- |
| `scripts/factory.ps1` | 将真实 PowerShell 参数交给 Python 主控；单阶段开发、状态查询与 CLI 检查 |
| `factory/controller.py` | 保存需求与状态、规划/任务包校验、角色派发、基础工程检查、接续控制 |
| `factory/contracts.py` | Planner/Coder 契约与 TaskPacket 校验；ID、依赖、AC 映射、权限及来源绑定 |
| `factory/executor.py` | 启动独立 Codex CLI、预检、权限选择、超时/进程处理、原始输出和 usage |
| `factory/quality.py` / `quality_contracts.py` | Tester/Reviewer 结果与证据、候选指纹、缺陷包、有限返工和检查点 |
| `factory/sequence.py` | 同一业务 workspace 的 Goal 0→Goal 1 串行执行与独立阶段回执 |
| `factory/history.py` / `revalidation.py` | 有限证据上下文与来源绑定复验；不构成通用审计或恢复平台 |
| `skills/` | 需求拆解、工程骨架和可执行提示词的固定资源 |

Planner 只读规划；Coder 在任务写集内开发；Tester 在候选副本中执行真实工程和 UI 检查；Reviewer 使用独立只读调用核对源码、AC 与证据。Tester 自报通过不是批准，Reviewer 也不能替代外部对 APF 的里程碑验收。

## 持久化与阶段身份

单任务使用 `control/state.json`、追加事件、TaskPacket、输入输出和完成记录。阶段链使用 `control/sequence/` 保存配置、游标和 `goal0-completion.json` / `goal1-completion.json`；Goal 1 有独立任务包和 `control/goals/goal-1/` 控制记录。业务工程仍在同一 `workspace/` 增量修改，前序批准快照与失败记录不覆盖。

每个完成结果绑定候选、TaskPacket 和文件 SHA。续跑核对有效检查点，不能重复派发已确认完成的角色；未知中断、来源变化和预算耗尽仍可能需要人工决定。主控锁防止同一项目并发写账本，锁和源码指纹不提供 OS 隔离。

## 质量与安全边界

当前测试、历史材料与交付说明分别处理；历史自测不能代替本轮测试。当前必需证据缺失、退出码与结果冲突、候选变化或未解决业务问题阻止批准。有限的已恢复工具事件或范围补充可依真实来源单独披露，原始失败保留，未知问题不能自动忽略。

Full Access 由调用者明确选择，不继承桌面权限；Planner/Reviewer 保持只读。它没有 OS 级 workspace 隔离，也不防御同用户恶意篡改所有账本。部分工具及历史资源配置仍具有机器依赖。

## 未实现或未真实验证

真实自动返工闭环未验证；任意多 Goal 自动任务准备、并发调度、Git Agent 和 Release Agent 未实现。独立 CLI 0.1.0 未合并主线。本次架构文档不改变代码、质量协议或预算。

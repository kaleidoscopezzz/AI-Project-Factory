# APF 技术架构

当前目标环境是 Windows 11、PowerShell、Python 与本地 Codex CLI。原始 Goal 0～5 已完成核心开发并按各自范围封版：Goal 2 为有限范围批准，Goal 3 为受控双阶段批准，Goal 4 限于授权本地 Git，Goal 5 限于本地软件发行。APF 1.0.0 尚未正式发布，详细边界见 [能力说明](VERIFIED_CAPABILITIES.md)。

## 执行层与角色

| 组件 | 实际职责 |
| --- | --- |
| `apf_cli/` / `pyproject.toml` | 已整合的 0.1.0 console script；离线版本/帮助、独立规划及产品开发/恢复入口；按命令延迟加载工厂 |
| `factory/product.py` | 薄产品适配：扩展同次Planner响应为原计划、独立Goal1契约及发行清单；共享有界调用预算，复用全部原阶段机制 |
| `scripts/factory.ps1` | 将真实 PowerShell 参数交给 Python 主控；单阶段开发、状态查询与 CLI 检查 |
| `factory/controller.py` | 保存需求与状态、规划/任务包校验、角色派发、基础工程检查、接续控制 |
| `factory/contracts.py` | Planner/Coder 契约与 TaskPacket 校验；ID、依赖、AC 映射、权限及来源绑定 |
| `factory/executor.py` | 启动独立 Codex CLI、预检、权限选择、超时/进程处理、原始输出和 usage |
| `factory/quality.py` / `quality_contracts.py` | Tester/Reviewer 结果与证据、候选指纹、缺陷包、有限返工和检查点 |
| `factory/sequence.py` | 同一业务 workspace 的 Goal 0→Goal 1 串行执行与独立阶段回执 |
| `factory/git_agent.py` / `scripts/git-stage.ps1` | 经项目策略授权，校验正式阶段批准并留下本地 Git Commit 和来源记录；不调用模型 |
| `factory/release_agent.py` / `scripts/release-stage.ps1` | 从批准候选复制构建输入，执行配方、ZIP 清单/哈希检查、全新解压启动和本地交付记录；不调用模型或上传 |
| `factory/history.py` / `revalidation.py` | 有限证据上下文与来源绑定复验；不构成通用审计或恢复平台 |
| `skills/` | 需求拆解、工程骨架和可执行提示词的固定资源 |

Planner 只读规划；Coder 在任务写集内开发；Tester 在候选副本中执行真实工程和 UI 检查；Reviewer 使用独立只读调用核对源码、AC 与证据。Tester 自报通过不是批准，Reviewer 也不能替代外部对 APF 的里程碑验收。

## 持久化与阶段身份

单任务使用 `control/state.json`、追加事件、TaskPacket、输入输出和完成记录。阶段链使用 `control/sequence/` 保存配置、游标和 `goal0-completion.json` / `goal1-completion.json`；Goal 1 有独立任务包和 `control/goals/goal-1/` 控制记录。业务工程仍在同一 `workspace/` 增量修改，前序批准快照与失败记录不覆盖。

每个完成结果绑定候选、TaskPacket 和文件 SHA。续跑核对有效检查点，不能重复派发已确认完成的角色；未知中断、来源变化和预算耗尽仍可能需要人工决定。主控锁防止同一项目并发写账本，锁和源码指纹不提供 OS 隔离。

## 质量与安全边界

当前测试、历史材料与交付说明分别处理；历史自测不能代替本轮测试。当前必需证据缺失、退出码与结果冲突、候选变化或未解决业务问题阻止批准。有限的已恢复工具事件或范围补充可依真实来源单独披露，原始失败保留，未知问题不能自动忽略。

Full Access 由调用者明确选择，不继承桌面权限；Planner/Reviewer 保持只读。它没有 OS 级 workspace 隔离，也不防御同用户恶意篡改所有账本。部分工具及历史资源配置仍具有机器依赖。

## 本地版本与发行

Goal 4 已按本地 Git 范围批准封版。接口在 `control/git/` 单独保存授权、请求、事件和版本，不改变质量账本；软件 `.git` 不进入业务候选指纹。它复用原项目锁和 Sequence 回执，不构成新的调度器。详见 [Git 使用说明](GOAL4_USAGE.md)。

Goal 5 已限定范围封版，复用正式阶段批准来源；构建在独立工作目录进行，发行包在全新目录解压并从包内脚本实际启动，之后保存来源、包 SHA-256 和运行结果。可读取已有软件 Commit，也可直接从批准候选发行，不强制补建 Git 版本。失败或中断不改写旧批准，不伪报发行成功。详见 [发行使用说明](GOAL5_USAGE.md)。

## 未实现或未真实验证

真实自动返工闭环未验证；任意多 Goal 自动任务准备、自由编排、外部冻结自动化、自动 Tag/Push、云部署、通用 EXE 与安装器不在当前实现范围。CLI 0.1.0 的 `--build` 将现有 Factory、Sequence、Git Agent 和 Release Agent 接入同一入口，`--prompt-generate` 仍只规划。独立输出目录中的 `.apf/run.json` 只记录整轮身份和共享预算，不能替代原质量状态机或伪造阶段批准。新的结构化Planner响应经过原计划/TaskPacket/增量契约校验，不从自由格式Markdown猜测可执行命令。APF 1.0.0 尚待最终验收与发布，详见 [产品入口](PRODUCT_USAGE.md)。AGENTS.md 强制生成、详细需求忠实度验证和多模型能力为未来计划。

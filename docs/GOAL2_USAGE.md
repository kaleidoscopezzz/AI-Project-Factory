# 独立质量验证与有限返工

APF Goal 2 已获**有限范围外部批准并封版**。Tester、Reviewer、DefectPacket、有限返工与恢复已实现；该阶段的真实 Reviewer 批准及模型返工闭环未验证。Goal 3 待办案例后来取得真实 Reviewer 批准，不追溯改变 Goal 2 的验收性质。详见 [已验证能力](VERIFIED_CAPABILITIES.md)。

## 当前入口

从仓库根目录执行，CLI 变量先按 [快速开始](GOAL1_USAGE.md)检查：

```powershell
.\scripts\factory.ps1 -CheckCli -CodexPath $cli
.\scripts\factory.ps1 -Request "开发一个离线管理系统，先实现基础业务阶段" -Mode Auto -QualityGate -NoAutoRepair -FullAccess -CodexPath $cli -TimeoutSeconds 600
```

该命令会调用真实模型。`QualityGate` 仅用于 Auto；不能与 Plan、Status 或 CheckCli 合并。`NoAutoRepair` 使质量失败立即停止，不调用返工 Coder。省略它才允许现有有限返工策略，调用和授权额度仍生效，不能视为已验证的全自动返工体验。

已有合法质量记录在恢复时重新验证输入、候选和证据；不能靠省略开关绕过门槛。已终结或工厂身份变动的旧失败轮次不一定可恢复，不能手工编辑账本。软件两阶段链通过 [Sequence 开发 API](GOAL3_INCREMENT.md)，不是旧单阶段入口的隐式扩展。

## 真实证据与角色

Tester 使用独立调用和候选副本，逐 AC 给出 passed/failed/unverified、判断原因、真实相对路径及 SHA；必须有实际 build/test/runtime 命令事件，UI 项目另需真实浏览器证据、两种视口 PNG 与有效 Trace。HTTP 200、静态页面或模型自报不能代替业务操作。

Reviewer 使用独立只读调用检查同一候选、AC、源码和关键证据，可 approved、changes_requested 或 blocked。源码审查引用绑定当前候选，不能作为 Tester 执行证明。内部 approved 不是外部对 APF 里程碑的验收。

DefectPacket 固定任务/候选、Issue、关联 AC、复现、预期/实际和证据。真正业务失败、关键证据缺失、未知限制或退出码冲突阻止批准；已恢复辅助事件须有完整来源和成功重验，不忽略任意 issues 或非零退出。

证据不得穿越目录、跟随逃逸链接或借用其他候选。当前交付、测试证据和历史资料分开，历史自测不能代替本轮测试。三条已确认的非关键归档限制仍 warning/unverified，不能推广为忽略全部历史。细节见 [历史上下文](GOAL2_HISTORY_CONTEXT.md)。

## 权限、预算和恢复

Full Access 由本次调用者显式选择，Coder/Tester 及工程检查使用当前用户权限，无提权或 OS 工作区隔离。Planner/Reviewer 保持只读；默认受限模式预检失败不升级。

原单阶段默认最多 3 次调用、一次显式 Retry。通用质量阶段默认 Tester≤3、Reviewer≤3、CoderRepair≤2、总≤8，质量轮数≤3、同一缺陷≤2次修复；每次≤600秒且不超过任务限额，累计 Agent 时间≤4800秒。官方质量 CLI 另有 6600秒墙钟终止机制；直接库调用不具有同一 CLI 看门狗。具体授权可以进一步收紧，不能用默认预算扩大用户批准范围。没有 Token 硬上限，usage 不可获取时如实记录 unknown。

调用前登记、完成后保存来源/结果/时间/usage，失败日志不覆盖。中断恢复检查候选、证据及已登记进程身份；合法完成检查点复用，未知副作用或无检查点的中断不盲目重派。状态和 SHA 不是签名，不防御同用户恶意篡改全部记录。

## 确定性验证

```powershell
python -B scripts/validate_goal2.py
python -B -m unittest tests.test_quality_evidence -v
```

这些是已有脚本与测试入口，使用 AgentDouble/可信本地夹具，不能冒充新真实质量 E2E。历史失败原件保持原样；本次文档维护没有调用模型或重新进行业务验收。有限独立复验机制见 [复验说明](GOAL2_REVALIDATION.md)。

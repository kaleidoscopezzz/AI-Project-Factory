# 当前软件 Goal 0 的独立质量复验

这是一项有限适配，只接受 p-867ba2d6987a、指定 Planner runtime、指定失败来源报告和 e7aa58b WIP 基线。不是通用复验平台，也不是 APF Goal 3 正式验收。

继续使用 scripts/revalidate-goal2.ps1 和 factory.revalidation；不传 Goal3RuntimeRoot 时维持原 Goal 2 路径。Goal 3 模式的来源为 validation/goal3/quality-validation-20261010T142212-92dc80，依据原 BEFORE.json 和 SHA 清单提取 state_before 的合法完成阶段，再单独保留原质量失败观察记录。

准备命令（零模型）：

```powershell
$runtime = 'C:\AI-Project-Factory\validation\goal3\planner-validation-20261009T233159-55603f\runtime-root'
$source = 'C:\AI-Project-Factory\validation\goal3\quality-validation-20261010T142212-92dc80'
.\scripts\revalidate-goal2.ps1 -Prepare -ProjectId p-867ba2d6987a -SourceEvidence $source -Goal3RuntimeRoot $runtime
```

生成全新 rv-*，控制账本位于 validation/goal3/revalidations/<RunId>/control。原 state/events/quality 与业务工程只读，原项目运行锁仍被获取。prepared.json/receipt.json 固定来源、候选、TaskPacket、阶段、旧文件清单、实际工厂源码及 Git 基线；模型派发前再次验证。

执行必须另有用户新授权，并显式选择 Full Access 和已 CheckCli 的可信绝对 CLI 路径：

```powershell
.\scripts\revalidate-goal2.ps1 -CheckCli -CodexPath $cli
.\scripts\revalidate-goal2.ps1 -Execute -RunId $newRunId -AuthorizationId $newAuthorizationId -FullAccess -CodexPath $cli -Goal3RuntimeRoot $runtime
```

Planner/Coder/返工/Retry 为 0；Tester/Reviewer 各最多 1 次，Reviewer 必须等 Tester 合法通过；每个 Agent 至多600秒，整体1800秒。Tester/工程检查当前用户权限，无OS隔离；Reviewer read-only，无Token硬上限。派发额度在调用前落盘，不用历史授权重开终结轮次。

AC-012只额外提供原验收文档明确涉及的首轮失败 test.log 和 results.json，源/副本 SHA 验证通过既有 history context，不修改原验收文档或任何历史自述。新 Tester 必须独立生成本轮测试和审查证据。

正向 runtime 为可结束的检查命令：启动服务、验证、finally清理。服务被清理的退出码与检查命令退出码分别记录；检查非零仍禁止 passed。HTTP预期故障通过断言验证，不直接当成正向运行失败或无条件通过。

只有现有 QualityGate 完整通过，才调用既有 Sequence.finish 输出原项目身份绑定的独立阶段完成回执及 stage-approval.json。此时软件 Goal 0 取得当前任务包内部质量批准，Goal 1 待另行授权；旧失败账本仍失败。已有完成回执由 Sequence.check_receipt 和原 QualityGate 语义重新检查，恢复不再派发完成的模型步骤。不自动登记或启动 Goal 1，不代表 APF 外部批准。

确定性 AgentDouble 验证只证明控制逻辑；真实调用结论以该 RunId 的 dispatches、execution、质量结果和证据为准。

### 已恢复辅助工具事件的交付接续

仅支持已确认的 `TESTER-TOOL-001` PowerShell 哈希枚举 ParserError：原命令失败事实、后续修正命令真实退出0、逐份枚举哈希、完整AC与工程/浏览器证据都必须可核实。未知 issue、其他未恢复失败、非零正向检查或缺少关键证据仍拒绝。原结果不修改；恢复认定保留整个原 issue，派生视图只将这个已解决事件从“当前未解决缺陷”中移出，并每次按原始日志重算验证。

使用现有入口准备新的 Reviewer 接续上下文：

```powershell
.\scripts\revalidate-goal2.ps1 -PrepareReview -SourceRunId rv-03299de21e7f -SourceManifest 'C:\AI-Project-Factory\validation\goal3\quality-closeout-20261010T154533-bfdcc3\evidence-manifest.json' -Goal3RuntimeRoot $runtime
```

准备零模型调用。旧RunId全体账本和证据按已交付清单保持只读；必要的新工厂代码改动明确记录，新上下文绑定当前工厂指纹，不改旧守护值。复制受控测试轮次，保留原始 execution/result/log 及恢复依据，通过原 QualityGate 完整校验派生结论。

新RunId仍通过 `-Execute` 与新的用户授权标识执行；Reviewer模式强制Planner/Coder/Tester/返工为0，Reviewer最多1次、600秒、read-only、无Retry。不重做已有构建/浏览器测试，不把零模型复核登记成一次真实Tester。完成记录包含原真实Tester来源和恢复依据，Reviewer必须独立查看候选、AC、当前证据及原始失败事件；只有实际approved才生成阶段批准。原失败状态永远保留。

只读Reviewer的当前AC-012交付审查可引用受控的本次审查索引、原始工具事件与恢复依据；仍须有真实独立源码审查CLI执行，且Tester全部当前证据有效。不能把普通历史自述单独当作当前通过证据，Tester的历史-only限制保持不变。

如果真实Reviewer已经approved，但局部引用兼容规则导致原轮次终结，可在同一PrepareReview入口补充 `-ReviewerSourceRunId <已完成的Reviewer轮次>`。仅复用原始approved结果、只读执行及源码守护证据，全部重校验；新上下文通过Execute零模型完成正式阶段记录。旧轮次保持失败，新授权记录的全部模型上限均为0，禁止借此重新Reviewer或改写其决定。

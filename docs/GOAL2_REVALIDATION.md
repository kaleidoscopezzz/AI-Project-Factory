# Goal 2：一次独立质量复验入口

AC-012当前严格核验有效交付和关键来源，仅三条固定的非关键归档缺口披露warning/unverified，不自动阻塞。详见 [历史上下文说明](GOAL2_HISTORY_CONTEXT.md)。旧RunId已结束或工厂哈希变动后不可复用；新RunId必须资料ready且获得新的明确授权才可调用模型。资料预检ready不等于真实质量通过；两次失败结果保持原样。

本入口仅复用 p-dc1e9d42b5ae 的原 TaskPacket 和已完成的 Goal 1 候选，使用现有 QualityGate；不规划、不开发、不返工。原 quality 首轮失败仍是失败，不修改原 state/events、旧账本哈希或历史证据。实现与确定性测试获授权，真实执行仍须用户另行批准。

## 准备与来源

```powershell
.\scripts\revalidate-goal2.ps1 -Prepare -ProjectId p-dc1e9d42b5ae -SourceEvidence C:\AI-Project-Factory\validation\goal2\real-validation-20261009T141135-3b101a
```

Prepare 不初始化模型适配器、不构建、不启动浏览器。它获取原 control/controller.lock，验证 Git HEAD/main/Goal0/Goal1 基线、历史清单与 before.json、原规划/包/包校验、Coder 结构化结果、完成记录与完整 workspace 清单、候选指纹、原失败账本和参考项目守护。原失败历史不迁移：从已被历史清单验证的 before.json 提取已完成的 Goal 1 状态，另存原当前失败状态和旧 quality 状态的字节副本，并明确区分来源。

新目录为 `validation/goal2/revalidations/rv-xxxxxxxxxxxx/`。prepared.json 对每份复用元数据记录原仓库相对路径、SHA256、来源关系、独立副本路径与哈希；提取状态另记录 /state 指针、容器哈希与内容哈希。新 state 标注独立复验、原失败事实及待授权，不声称原任务未失败。receipt.json 固定 prepared.json 哈希。已存在 RunId 拒绝覆盖。

原完成记录中的规划/包/完成/Coder 文件哈希由历史 before.json 的 original_project_files 固定；外层清单固定 before.json 和原 quality 状态。原当前 state/events 在准备时快照并在以后每次执行、调用前后核对；若外层清单包含它们，也验证该清单哈希。不是对历史清单没有提供的文件声称外部验签。

新上下文固定工厂源码/测试/文档的当前哈希；以后这些文件发生变化，执行零模型停止，不能手改 receipt 或旧账本来绕过。原项目快照覆盖源码、原状态/事件和整个旧质量证据树，排除依赖/解释器缓存、.factory-tmp 和正在持有的机械锁字节。锁之外的排除项不是已验证证据。

## 显式执行（本轮不可运行）

先检查调用者选定的现有 CLI，读取版本和程序 SHA256，不安装、不升级、不调用模型：

```powershell
$cli = '已安装并信任的 codex.exe 绝对路径'
.\scripts\revalidate-goal2.ps1 -CheckCli -CodexPath $cli
# 仅在用户明确批准本次真实复验之后，用 Prepare 实际输出的 RunId：
.\scripts\revalidate-goal2.ps1 -Execute -RunId rv-xxxxxxxxxxxx -AuthorizationId goal2-revalidation-approved-01 -FullAccess -CodexPath $cli
```

真实执行强制显式 CLI 路径、FullAccess、授权标识；授权标识是审计字段，不是用户批准的密码或自动许可。适配器仍按现有 CodexExecutor 执行：Tester 和工程检查使用当前 Windows 用户文件、进程、网络权限，无管理员提权；Reviewer 仍是独立 read-only CLI。工作目录、只读属性和事后哈希守护不是 OS 隔离。CheckCli 仅验证文件存在、版本及字节哈希，不证明数字签名或真实模型/浏览器运行成功。

原项目锁贯穿执行；所有新状态、调用、候选副本、历史证据上下文、检查与浏览器证据放在新 run/control/quality 中。QualityGate 继续负责逐 AC 证据、候选绑定、真实命令事件、PNG/trace、TesterResult/ReviewerResult 校验、缺陷生成和检查点恢复，没有第二套质量状态机。

## 固定限制和停止

| 项目 | 本入口限制 |
| --- | --- |
| Planner / 初始 Coder / CoderRepair | 0；执行适配器直接拒绝 |
| Tester / Reviewer | 每角色最多 1 次；Reviewer 仅在合法 Tester passed 检查点后 |
| 自动返工 / Retry | 永久关闭，无接受 Retry 的入口参数 |
| 每 Agent | 不超过 600 秒，且取原任务更严格预算与剩余墙钟时间 |
| 总执行墙钟 | 首次授权持久记录后 1800 秒；恢复不重新计时 |
| 构建/测试命令 | 不超过现有 180 秒；预检/HTTP 沿用更严格现有限制 |
| Token | 无运行中硬上限；真实 usage 原样记录，未知则 unknown |

通用 QualityGate 原 budget 仍保留以兼容已有契约，独立入口的更严格有效 limits 另写 prepared/authorization/quality marker，并由 OriginBoundGate、SingleDispatchExecutor 和官方 CLI 墙钟看门狗共同强制。不能把通用预算显示为本次允许的重试额度。

预检失败在派发前停止，模型调用为 0。Tester failed/blocked/超时/非法输出/缺证据立即停止，不调用 Reviewer；Reviewer changes_requested/blocked 保存结果和缺陷后停止，绝不返工。退出 0 只表示内部当前候选质量通过，1 表示拒绝/失败，2 表示等待用户，均不等于外部 ChatGPT 验收 APF。

## 中断恢复

使用相同 RunId、AuthorizationId、FullAccess 和 CLI；禁止 Retry、改变授权或重置时钟。派发前写 dispatches.json，一旦角色登记就占用额度，即使进程启动/保存结果失败也不重复派发。现有 QualityGate 校验调用输入/输出哈希、证据、候选、PID 与进程创建身份；有效完成检查点直接复用，仍活跃则停止，死进程无有效检查点则保留失败并停止。已失败轮次不会自动重新运行；新的调用预算必须先经人工审查和另行授权，不在此入口自动创建。

本地 SHA 和状态不是签名，不抵御同一用户恶意改写全部审计文件。官方 PowerShell/Python CLI 使用进程树墙钟终止机制；作为 Python 库注入的测试适配器不终止调用者，不能据替身测试宣称官方看门狗的真实 Agent 超时已经发生。CLI 同一次模型调用的网络重连由现有 CLI 行为决定，APF 没有增加派发重试。

## 确定性检查

```powershell
python -B scripts/validate_goal2.py
python -B -m unittest tests.test_quality_evidence -v
python -B -m unittest tests.test_revalidation -v
```

AgentDouble 只验证控制、证据规则和恢复；真实模型成功、独立 Reviewer 的语义审查、整条新质量 E2E 均须另行授权验证。历史方案和失败记录保留，当前实现准备情况以新增 revalidation-prep 报告为准。

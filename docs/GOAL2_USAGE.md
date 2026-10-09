# Goal 2：单 TaskPacket 质量闭环

AC-012以当前有效交付证据为主，交付记录、本轮执行快照与历史资料分别索引；当前/关键必需来源缺失或哈希不符会在模型派发前停止。仅Reviewer确认的三条固定归档缺口以warning/unverified披露，不自动阻塞。规则、严格校验范围及历史背景见 [历史上下文说明](GOAL2_HISTORY_CONTEXT.md)；下文“首轮失败后的整改”保留该阶段背景。

本功能给 Goal 1 增加独立 Tester、只读内部 Reviewer、有限针对性返工和恢复。只处理当前 TaskPacket 的 Goal 0 工程，不执行规划中的后续 Goal，不做 Git、Release、部署、并发 Coder 或多任务 DAG。内部 Reviewer 的 approved 不是外部 ChatGPT 对 APF 的批准。

## 入口与兼容

```powershell
$cli = '实际已安装 codex.exe 的绝对路径'
.\scripts\factory.ps1 -CheckCli -CodexPath $cli
.\scripts\factory.ps1 -Request "开发一个离线管理系统" -Mode Auto -QualityGate -FullAccess -CodexPath $cli
.\scripts\factory.ps1 -ProjectId p-0123456789ab -Status
.\scripts\factory.ps1 -ProjectId p-0123456789ab -Mode Auto -QualityGate -Retry -FullAccess -CodexPath $cli
```

`QualityGate` 仅用于 Auto，不能与 Plan、Status、CheckCli 组合。未启用时原 Goal 1 行为保持不变。已有 quality/state.json 的任务恢复时不能通过省略开关绕过质量门槛；不重新运行 Planner 或初始 Coder。失败任务要显式 Retry，等待用户确认的任务不能自动绕过问题。Status 本身不执行 Agent，并显示持久化质量摘要和结果路径。

一次预算更紧的只验收运行可加 `-NoAutoRepair`，发现实现缺陷保存DefectPacket并停止，不派发返工Coder；默认QualityGate仍有限自动返工。每次需要此限制的运行都应明确指定该参数。

退出码：0＝Plan 包已验证、旧 Auto 基础完成或质量门槛通过，含义依参数/状态区分；1＝拒绝、执行失败或质量门槛失败；2＝等待用户确认。质量通过只覆盖当前候选及当前任务包，不代表软件完整业务交付。

## 实际职责及权限

Planner/Coder 继续使用原链路。基础检查通过后运行 Tester；已完成 Coder 的客观 build/test/runtime 失败也可以进入 Tester 诊断，路径/冻结文件/规划完整性等错误不会被当作业务缺陷自动返工。

Tester 是新的 `codex exec` 调用，独立 thread/input/schema/log/result/时长/usage。主控将稳定候选源码复制到 `control/quality/rounds/NN/workspace/`，先真实执行 build/test/runtime，Tester 再独立执行和逐项验证 AC。副本包含源码、配置、锁文件、测试、说明和 AGENTS.md；不复制 node_modules、运行数据和旧绿灯证据。项目需要未安装依赖时应 blocked，不能自动安装。它只能在副本生成 dist/build/var、validation/ 或 .quality-evidence/ 中的运行产物；源文件和验收断言须保持指纹不变。原业务 workspace 不允许 Tester 修改。

Reviewer 使用独立 CLI/thread，强制 `read-only`；输入包含 TaskPacket、Planner AC、候选清单、Coder报告、Tester结果和证据索引。它核对覆盖、代码缺陷、授权及测试有效性，输出 approved / changes_requested / blocked。任何 unverified、有缺陷或限制的结果不能 approved。无法判断时 blocked，重大歧义/权限确认进入等待用户；环境、测试自身问题不会派给 Coder 盲目修复。

CoderRepair 仅接收 DefectPacket 和必要上下文，修改原候选实现；不得重新规划、无故重建、修改测试目录/测试脚本/npm test入口、AGENTS.md 或历史证据。新候选重新执行完整的任务包 build/test/runtime、Tester 和 Reviewer，保守失效全部旧结果，当前不做局部选择性测试优化。

Full Access 每次必须由调用者显式指定。Coder、Tester及工程检查使用当前用户文件/进程/网络权限，不提权；Planner、Reviewer始终只读。没有 OS 级 workspace 隔离，副本和指纹保护只是受控路径/事后检测，不能证明整个电脑零越界或防止恶意代码。未指定 Full Access 不继承历史授权；默认受限，预检失败停止，绝不自动升级。无需修改 Windows ACL、全局配置或安装系统软件。

## 契约与证据

TaskPacket 1.0 及冻结的历史包不改。Goal 2 增加执行层 2.0：

- Tester输入：完整已验证包及包指纹、全部AC、候选fingerprint/files、实际副本路径、基础检查和预算/UI要求；Reviewer另加Tester及Coder报告。
- TesterResult：候选指纹、passed/failed/blocked、逐AC的passed/failed/unverified及原因、实际checks（kind/argv/exit_code/AC/证据）、issues、limitations。
- ReviewerResult：候选指纹、三种decision、逐AC结果、issues、limitations、summary。
- DefectPacket：project/task/packet/candidate身份、Issue ID、关联AC、分类/严重度、复现、预期/实际、证据引用和修复编号。

权威校验在 `factory/quality_contracts.py` 与 `factory/quality.py`；三个输出schema在 `factory/schemas/`。独立调用输入副本、启动参数、CLI事件及结构化结果保存在每个call目录。真实usage无法取得时是unknown；AgentDouble明确标记，不冒充模型执行。

证据路径必须相对于该轮目录，限定在 `workspace/validation/`、`workspace/.quality-evidence/`、`checks/`。绝对路径、穿越、symlink/junction、缺文件、哈希不符均拒绝。哈希绑定实际文件；审批结果绑定具体源码候选，复用时重新核对。Tester成功还必须有 CLI command_execution 的实际build/test记录和主控基础检查成功，不能仅靠JSON自报。Reviewer批准还必须有对应候选源码的实际只读审查工具事件，恢复时重新核对执行记录。

UI要求从当前包的浏览器/截图/Playwright契约识别。成功结果必须包含真实浏览器检查、两种不同尺寸PNG及有效Playwright trace ZIP，不能以HTTP200或静态HTML替代。字节格式、工具事件和哈希是必要条件，不能独自证明截图语义/断言充分；内部Reviewer与外部审查还需核对日志、trace和源码。

候选指纹包括所有有效源码、配置、必要测试和文档，排除根validation/dist/build/var/.quality-evidence/.factory-tmp及任意层node_modules/解释器缓存。凭据文件拒绝进入候选。工程若把有效源码放在这些保留产物目录，需要先调整工程边界，不能据排除项声称已验证该源码。

## 硬预算与状态恢复

原 Goal 1 默认最多3次调用/1次显式重试不变。质量阶段另有Tester≤3、Reviewer≤3、CoderRepair≤2，总≤8次、质量轮数≤3、同一缺陷≤2次修复；每次≤600秒且不超过任务原TimeoutSeconds，累计Agent执行预算≤4800秒。官方Python/PowerShell CLI质量阶段每次运行另有6600秒墙钟上限（含阶段I/O），超时写持久失败标记，仅终止其拥有的CLI工作进程树；状态查询可识别该标记。直接作为Python库调用Controller时保留调用/单命令预算，但不终止调用者进程，因此没有这个CLI整体看门狗。正常全流程通常4次模型调用；最坏原阶段3+质量8＝11次。build/test各沿用≤180秒，HTTP启动≤30秒；预检有固定短超时。没有运行中Token硬上限，不估算精确usage。

同缺陷依据AC/分类/预期形成稳定键，不只依赖Agent选择的ID。没有实际源变化不能算有效修复，但失败调用仍占预算。预检失败在派发/扣质量调用及返工次数之前停止。

`control/quality/state.json` 原子保存账本；原state.json保存阶段和质量摘要。每次调用启动前登记，完成后保存输入哈希、thread、exit/timeout、时间、usage、候选前后变化和结果哈希。每轮与每次调用使用独立路径，失败日志不覆盖。原同项目运行锁继续生效。

恢复优先校验包、源指纹、持久结果和证据，完成且仍有效的调用复用，Planner不重跑。running不能冒充completed；针对已登记PID核验进程创建身份，确认仍活着时不重复启动。不存在有效完成检查点的中断调用保留并要求Retry，已计费调用不撤销。完成的Coder修复结果可通过输入/输出/前后源码检查点恢复；Coder真正中断可能留下部分修改或副作用时，停止等待用户审查，不自动重放。基础检查在独立副本进行，日志使用唯一时间路径；破坏性/生产副作用不属于本阶段允许任务。

本地状态与SHA不是签名，不抵御同用户权限的恶意篡改全部控制记录。调用前后复核指定工程、工厂源码/文档/配置及Goal0/Goal1历史验收、包与控制文件；真实APF还以原只读inventory方式核对参考项目（node_modules仅大小/mtime，其余SHA）。这些有限路径检查不是宿主机完整安全审计。

## 验证与当前范围

```powershell
python -B scripts/validate_goal2.py
python -B -m unittest tests.test_quality_evidence -v
```

第一条运行原41项回归及既有62项Goal2确定性测试；第二条运行首轮失败整改新增18项证据关联测试，仍是人工夹具，不派发真实Agent。仅超时/日志脱敏等可信本地子进程检查是真实进程执行，业务与Agent结果为明确标记的AgentDouble。证据写入新的 `validation/goal2/regression-*/`，临时夹具在同目录下test-workspaces，原测试文件及历史报告不覆盖。

历史方案见 `validation/goal2/REAL_VALIDATION_PLAN.md`。2026-10-09 已获一次授权并真实调用 Tester 1 次：CLI 退出0，但结果被主控以“AC 无证据”拒绝；AC-012同时报告副本缺失历史文档。Reviewer和返工Coder未调用。失败日志见 `validation/goal2/real-validation-20261009T141135-3b101a/`，此轮不代表成功质量E2E。Goal2当前为“开发中，待真实验证”，不得Git收口。

## 首轮失败后的证据关联整改

新轮次在候选目录之外建立 `rounds/NN/context/history/`，只复制原完成记录已绑定哈希的 `validation/goal0/acceptance.md`、`session-environment.json` 和 `source-sha256.json`（存在或被文档引用时）。原资料不改动；资料缺失、未被原完成记录验证或哈希不符时停止。副本设置Windows只读文件属性并进行调用前后哈希复核，Full Access仍可清除该属性，因此不是OS级隔离。

Tester/Reviewer可只读访问所列历史上下文，不能读写原工程或修改上下文。历史记录按其原始性质审查，不能用历史“通过”代替当前测试。历史副本不进入业务源码候选指纹；其清单单独绑定当前候选和TaskPacket，任何上下文缺失、篡改或绑定变化均拒绝。

每次角色输入引用受控 `context/<role>-evidence-index.json`（文件路径、SHA256、用途、候选/包指纹），不内嵌完整日志、源码、PNG或trace。索引仅提供可读文件位置，不自动给AC分配通过证据；Tester生成的新证据仍需真实路径/SHA和逐项判断。AC完整定义、执行规范和候选指纹保留；先定向读取所需断言/字段，避免反复打印整个测试源码和历史日志。没有Token硬上限，实际模型usage仍照实记录。

每项AC输出 `{id,result,reason,evidence:[{path,sha256}]}`。passed/failed必须有非空真实证据，reason说明其覆盖依据；总checks日志不能替代本项evidence。可按实际覆盖在多项引用同一日志，但不得自动复制绿灯。历史资料可补充引用；passed还必须包含本轮测试/审查证据，不能全部引用历史绿灯。无证据则unverified并说明限制，整体不能passed。所有路径相对轮次目录；仅允许测试证据路径和清单中的历史资料，不允许源文件充当运行证据、绝对路径、越界或伪造哈希。现有schema形状保持，空数组仅供unverified；强约束在语义校验执行。

Tester自身checks须列实际build/test/runtime；browser检查的evidence本身需包含两种PNG和trace，不能仅放在某项AC下。主控不补填或改写失败TesterResult。原始失败结果确定性重放仍被拒绝，合法夹具仅用于验证控制逻辑，不等于真实链路成功。

旧真实失败的quality账本绑定旧工厂源码哈希，不能在整改后直接以Retry绕过守护或手改账本。本轮不迁移它、不清空失败记录、不执行模型。后续一次真实复验必须先另行批准保留旧账本的恢复/新质量命名空间准备及运行预算；详细阻塞与前置步骤见本轮整改目录的NEXT_REAL_VALIDATION_PLAN.md。此前Full Access授权已用于首轮，不代表新一轮运行授权。

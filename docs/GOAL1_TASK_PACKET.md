# TaskPacket 1.0 与执行协议

权威实现：`factory/contracts.py`。Agent 响应 JSON Schema 位于 `factory/schemas/`，运行时从同一 Python 契约生成 schema。TaskPacket 由主控从经校验的 Planner 响应组装，身份、路径、预算和状态均由主控决定，Planner 不能扩大权限。

| 字段 | 约束 |
| --- | --- |
| format_version | 固定 1.0；未知版本拒绝 |
| task_id / project_id | 主控随机 ID；project_id 为 p- 加12位小写十六进制 |
| original_request | 非空、最多16000字符；与持久化任务原始输入完全一致 |
| goal | 固定 Goal 0，不能派发后续业务 |
| project_type / technology | 来自完整经校验规划；技术选择有依据 |
| workspace | 精确等于 projects/<id>/workspace；绝对解析、无穿越/链接 |
| allow_write / deny_write | 仅 workspace；禁止 skills、历史 validation、factory .git、参考项目与 control；其他项目由沙箱和解析路径拒绝 |
| prompt_path | 精确的 control/goal0-prompt.md |
| acceptance | 当前 Goal0 至少8项，R/AC/Task/Goal映射一致且都出现在提示词中 |
| checks / runtime | argv 数组，build/test必备；本地服务接受 {port}，HTTP路径和可观察期望；不把自然语言拼入 shell |
| budget | 与主控状态内预算一致；上限不可由 Planner/Coder改变 |
| input_fingerprint | 原始请求、冻结Skill所有资源SHA和契约版本的SHA-256 |
| artifacts | 四份Markdown与原始结构化规划的SHA-256，派发前逐文件复核 |
| state | 包固定“任务包已验证”；实时执行状态另存 state.json，不通过改包推进 |

任务包全部字段必须存在，未知字段拒绝；全包规范 JSON SHA-256 写入主控 state，派发时核对。`packet-validation.json` 保存校验结果。依赖检查拒绝不存在节点、重复节点和环；双向 AC/Task 映射必须一致。工程 AC 要可观察，完整提示词要有边界、测试、证据、失败停止及最终报告。语义质量仍需外部审查，长度阈值只是拒绝明显不完整的结构门槛。

Planner 独立 `codex exec` 输出 JSON；主控原子落盘及组装 packet；再次验证后把完整 packet 和 prompt 通过 stdin 送入新的 Coder `exec`，创建独立 thread。`handoff-<call>.json` 保存包、提示词与派发输入SHA；输入副本与 CLI 事件分角色保存，不经过人工复制。Coder 最终结构化报告含 status、summary、files、tests、evidence、limitations、questions；非零退出、无完整 turn、无结构化结果、失败自测均不能转完成。

状态顺序：待规划→规划中→规划完成→任务包已验证→Coder执行中→基础验证中→已完成。任一步失败→已失败；重大问题→等待用户确认。Plan 止于任务包已验证。状态采用原子 JSON 替换和 append-only 事件，调用计数在启动前持久化。工程创建前后清单绑定具体独立 Coder 调用；完成证据和源码指纹在重复运行时重新核对。

恢复：优先校验已有 packet；其次重用完整 planner-result checkpoint；无 checkpoint 才重新规划。遗留执行中状态不能成功，需显式 Retry 且预算未耗尽。手工修改控制文件属于破坏可信本地状态，SHA不是签名、也不是抵御具有相同用户权限攻击者的边界。

Goal 2 建议：先扩展验收协议及独立 Tester 执行，统一失败诊断/受限修复包，再引入独立 Reviewer。Git/Release 保持单独审批接口，未获专门收口授权不执行。先增加不同技术栈适配与恢复故障注入，再考虑多任务并发和共享文件所有权。

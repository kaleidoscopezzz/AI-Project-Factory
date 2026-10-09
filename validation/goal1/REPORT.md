# Goal 1 实施与验证报告

记录日期：2026-10-09，Asia/Shanghai。性质：实施、自测及失败诊断；不是外部验收。**Goal 1：开发中，环境受阻，未完成。**

## 1. Goal 1 最终状态
真实 Planner→TaskPacket→Coder 自动交接已发生，实际代码已创建，任务失败被正确回收；完整真实端到端通过次数为0。不得写“已完成，待外部 Reviewer 验收”。主控和契约可审查，浏览器及全部工程AC未通过，暂停于可恢复失败点。

## 2. Git 基线与工作区
开始时 main / `11aa80e1dc345d63f9b325d14227b078c0f924bb`，`goal-0-approved` annotated tag解引用到同一Commit，工作区干净。结束时HEAD/Tag不变；仅PROJECT_STATUS.md有跟踪变更，其余本轮成果未跟踪；没有覆盖原有改动。

## 3. 实际新增和修改
修改：PROJECT_STATUS.md，新增Goal1状态及事实、区分Goal0历史段落。
新增：factory/{__init__,contracts,controller,executor}.py，factory/schemas/三个JSON Schema，scripts/factory.ps1、goal1_guard.py，tests/{__init__,test_factory}.py，docs/GOAL1_USAGE.md、GOAL1_TASK_PACKET.md，projects/.gitignore，validation/goal1/报告、探针与守护证据。生成真实工程及按项目归档的control记录位于projects/p-dc1e9d42b5ae；另有隔离sandbox-probe目录。异常测试的临时夹具保留在本机test-workspaces，各轮报告保留，新增局部.gitignore排除这些可重建夹具及项目临时浏览器缓存。
原三Skills、旧案例、旧验证报告、根README/AGENTS/.gitignore均未改。

## 4. 执行接口与版本
正式Codex CLI `0.162.0-alpha.2`。本机实际help核实exec、stdin、-C、--json、--output-schema、--ephemeral、--ignore-user-config、sandbox及approval参数，login status显示ChatGPT登录。使用argv列表及stdin，shell=False，不拼接自然语言。每角色新的exec和thread，收集JSONL、turn完成、结构化JSON、exit/timeout/usage。
官方依据：[Non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode)、[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)。官方页面与本机版本差异以本机help/执行结果为准。
elevated初始化返回helper_unknown_error。unelevated可运行和拒绝项目外写入；不降级danger-full-access。CLI WebSocket超时会自行HTTPS fallback。尝试覆盖内置provider被本版本明确拒绝，原失败保留于https-diagnostic.json；该方案已移除，未换服务商/修改全局配置。environment.json记录实际环境诊断。

## 5. Planner 是否真实独立执行
是。thread `01a11c4f-700f-7f63-b4d8-3f9a04d684ae`。planner-01.input.md包含三个冻结Skill及其模板/参考原文；planner-01.log.jsonl记录真实声明依序应用Skills及最终JSON。四产物由主控保存，无手写业务规划替代。

## 6. Coder 是否真实独立执行
是。thread `01a11c5b-3a15-7e31-96de-896c4fdef493`，区别于Planner。coder-02.log.jsonl包含真实命令执行、file_change事件与最终failed报告。CLI进程exit0只说明调用结束；模型报告failed仍被主控判为任务失败。

## 7. 入口与示例
```powershell
.\scripts\factory.ps1 -Request "帮我开发一个离线图书借阅管理演示系统，要有图书列表、借阅状态、简单搜索，界面专业，以后方便增加更多功能。" -Mode Auto
.\scripts\factory.ps1 -Request "帮我规划一个离线设备管理演示系统" -Mode Plan
.\scripts\factory.ps1 -ProjectId p-dc1e9d42b5ae -Status
```
Auto真实执行一次；Plan停止于包验证的分支由确定性测试验证，未另外消耗真实Planner调用重做同类规划。首次PowerShell启动因PATH存在两个Python候选失败，已取首个Application并实测修复；未启动Agent的该失败不计入Agent调用数。

## 8. TaskPacket 与验证
格式1.0，任务ID `t-c8f44dfbe70c4bbebb93419a9f347cc8`，项目ID `p-dc1e9d42b5ae`。包含原始需求、当前Goal、类型/技术、精确workspace、允许/禁止写入、prompt路径、AC/测试、预算、输入指纹、产物SHA与状态。
生产验证器拒绝未知/缺失/错误类型、越界/链接、错身份/预算、篡改包/产物；检查依赖无环及AC/Task双向映射。包SHA `edb6c6afa62657c5dc2d899e4774bed1855b5e4dd5b9689ca67ac746207c8ad2`。packet-validation.json为真实通过证据；不代表工程验收通过。

## 9. 自动交接证据
projects/p-dc1e9d42b5ae/control/handoff-02.json保存automatic=true与包、prompt、派发stdin指纹；coder-02.input.md同时包含已校验包和完整prompt，其SHA与Coder结果一致。两个thread和先后状态见state.json/events.jsonl。没有人工复制；只派发Goal0，没有生产Tester/Reviewer/Git/Release调度。

## 10. 一句话测试内容
“帮我开发一个离线图书借阅管理演示系统，要有图书列表、借阅状态、简单搜索，界面专业，以后方便增加更多功能。”

## 11. Planner Goal计划
Goal0：本机离线Web基座、虚构图书读链路、状态/搜索、工程备注持久化纵向样板、异常/浏览器证据；12项AC、5项任务，T-001→T-002→T-003→T-004→T-005。Goal1：完整借还闭环候选，先确认副本、读者、业务规则和真实性，在Goal0外部验收及新授权后增量开展。并未开发完整借还业务；后续候选未假称已承诺的当前业务AC。

## 12. Goal0提示词
projects/p-dc1e9d42b5ae/control/goal0-prompt.md，7734字符、14节、12项AC，具体路径/环境、模块步骤、数据不变量、测试和证据、禁止项、失败/报告/停止规则完整。原本将主控验证轮数误理解为更紧Coder自测预算，当前主控Planner输入已明确二者区别；原规划及失败证据保持不变，不重写已派发包。

## 13. 实际工程路径
C:\AI-Project-Factory\projects\p-dc1e9d42b5ae\workspace。

## 14. 实际工程内容
Coder创建package.json、src/contracts/index.mjs、domain/books.mjs、adapters/store.mjs、server/server.mjs、web/{index.html,app.js,style.css}，data/seed.json，scripts/{build,serve,test}.mjs，tests/goal0.test.mjs，中文README和状态、验收/运行/失败日志。AGENTS.md和临时目录由主控预置；构建dist由Coder及随后独立诊断生成，不能把全部文件都称为Coder原创。coder-before-02.json与coder-provenance-02.json给出创建前后SHA清单；provenance在失败回收后、主控独立诊断前形成，时间范围如文件source字段所述。

## 15. 启动与构建检查
在workspace：node scripts/build.mjs，node scripts/test.mjs，node scripts/serve.mjs --host 127.0.0.1 --port 4173。
Coder首次build/test均失败，有限修复后build通过，测试主体仍未运行；真实HTTP访问健康/首页/app.js/style.css/books均200，计数3/2/1。未用这些HTTP记录冒充浏览器行为或截图。
主控独立诊断再次实际执行：build退出0（0.163s），test退出1（0.192s，spawn EPERM）；独立端口59181健康HTTP200、期望文本命中、临时进程树已停止，failed-task-diagnostics.json/runtime-check.json及check-diagnostic日志留证。这是失败诊断，不是completion.json或端到端成功。

## 16. 成功端到端数量
0。真实尝试1条，Planner和自动交接成功、Coder代码创建成功，但工程自测受阻。没有生成completion.json，没有宣称12项AC通过，没有PNG或trace。

## 17. 异常测试
最终25/25通过：exception-tests-cf44706865.json/txt。覆盖空需求、错误包/类型、路径穿越/参考目录/ID、Coder退出失败及报告失败、超时、中断、规划缺失、重大问题、完成复用及指纹失效、规划复用、重试预算、依赖环、产物篡改、命令限制、并发锁、凭据拒绝和日志/子进程环境脱敏。AgentDouble明确仅为确定性测试替身；真实本地子进程测试验证超时kill和实际日志脱敏，不能把25项当25条真实Agent链路。
此前各轮22/23/24项报告仍保留，脚本初次直接路径导入失败后改为模块入口；修复前错误未伪称通过。

## 18. 持久化和恢复
state原子替换、events追加、启动前落调用计数、操作系统文件锁、规划checkpoint和哈希复核。实际失败项目查询及不带Retry的恢复已执行：仍失败、调用数仍2，不重跑Agent。中断/规划复用/完成复用/重试上限的故障注入由测试替身验证，未宣称发生真实机器断电恢复。重大问题需补全需求后另建任务，不用篡改state审批。

## 19. 时间、调用与Token
主链2次真实调用：Planner772.515s，Coder472.297s，总1244.812s。CLI报告输入247901、缓存输入208000（输入的子集）、输出25418，合计输入+输出273319；Coder reasoning_output_tokens=283是输出分类，不重复累加。原始usage留在state和角色result。
额外短真实执行诊断1次，120.889s，CLI报告输入13952/缓存11520/输出5；不计为项目成功或主链第三Agent。内置provider配置诊断在发起模型前exit1，没有Token结论。以上为CLI可核实usage，不是账单/费用保证；失败传输的额外计费未知。没有无限试错，未消耗剩余Coder重试去重复环境错误。
当前适配器屏蔽父会话环境和不需要的全局插件/记忆/多Agent，显式启用本机列出的skip_host_skill_discovery，仅给Planner冻结资源、给Coder任务包/prompt；这些优化是在真实首链启动后完善，不能声称首链已用了全部优化。最终版本未获得成功真实E2E。

## 20. Goal0三个Skills
未修改，冻结文件SHA比较通过；仅在测试临时夹具复制输入，不安装全局Skills、不重建Goal0。

## 21. 参考项目
C:\910Program未修改：35839文件路径、大小、mtime无差异，除node_modules外SHA无差异，HEAD/branch/status/refs无差异。未运行参考构建、安装、测试或服务；不比较访问时间，不把元数据覆盖称为全依赖内容哈希。

## 22. Git写操作
没有执行。工厂.git 96个文件内容快照无差异，该Git目录快照在Planner已启动、Coder未启动时取得；初始HEAD/Tag/工作区另已核验。不把这一覆盖说成完整宿主审计。

## 23. PROJECT_STATUS
Goal0“已验收冻结”保留；Goal1“开发中（环境受阻，未完成）”；历史事实和限制保留并标明历史。未写Goal1完成或冻结。

## 24. git status
仅M PROJECT_STATUS.md；新增docs/GOAL1_TASK_PACKET.md、GOAL1_USAGE.md、factory/、projects/、scripts/factory.ps1、goal1_guard.py、tests/、validation/goal1/为??。完整实际输出见git-status.txt；新文件没有add。

## 25. git diff --stat
PROJECT_STATUS.md：35行变化，26新增、9删除。此命令不计入未跟踪新增成果，详见delivery-files.json和git-diff-stat.txt。未执行add以制造统计。

## 26. 已知限制与停止原因
elevated helper初始化失败；unelevated中Node spawn EPERM，Chrome探针超时，Edge因mojo/crashpad IPC访问拒绝退出2147483651；windows.sandbox_private_desktop=false只作为子进程兼容探针且仍失败，没有修改全局配置。Python子进程成功，不能据此说浏览器也可用。证据projects/sandbox-probe/control/与workspace/edge-probe.stderr.log。
保留受限执行，未绕过边界。unelevated不是恶意代码多租户隔离/保密边界；沙箱探针和文件守护不能保证宿主所有文件绝对零写入，Codex自身可能维护认证/运行/沙箱缓存。提示词禁止敏感读不构成强制读取隔离。
首版仅支持Node/Python及固定npm检查接口的本地HTTP项目；无外部发布、独立生产Tester/Reviewer、并行Coder、Git/Release。语义验收仍需独立Reviewer。最终适配器优化未重新取得成功端到端，不能宣称Skill全局安装或两旧案例业务运行通过。
下一步首先修复/验证获授权的受限Windows执行环境，再复用现任务规划用剩余1次显式Retry。环境未修复前停止，不浪费Token重做已知失败，不擅自进行全局安装、权限调整或完全访问降级。

## 27. Goal2建议
当前Goal1未完成，不启动Goal2。Goal1通过并获新授权后，再建设独立Tester与结构化验收回收、有限失败修复包、独立Reviewer和恢复故障测试；Git/Release继续作为单独外部验收与专门收口授权节点。先扩展验证适配器，再考虑并发。

**停止于Goal1失败恢复点，等待用户决定环境阻塞处理。未自行验收、Git冻结或进入Goal2。**

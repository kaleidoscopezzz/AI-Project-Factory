# Goal 1：已完成，待外部 Reviewer 验收

日期：2026-10-09。此结论限当前授权的 Planner→TaskPacket→Coder→基础验证链路，不是外部验收、全业务完成或全电脑安全审计。`REPORT.md` 是授权前诊断和候选方案；本文件记录用户确认后的一次真实复验。Goal 0 保持已验收冻结。

1. **Node EPERM 原因范围**：旧 unelevated 受限令牌的限制 SID 与默认命名管道 DACL 不匹配，读连接可行、写端/WRITE_DAC/libuv访问掩码错误5；换cwd/TEMP无改善。当前用户非受限令牌下这些访问均返回0，Node管道成功。本次派生CLI实际固定Node子进程输出42、构建与测试成功。未声称修复了Codex内部缺陷或Windows沙箱。
2. **浏览器 IPC**：旧 Chrome/Edge Mojo/Crashpad 访问拒绝记录完整保留；原生空白页及 Playwright/Edge 固定DOM均成功。正式业务浏览器也成功。另确认默认Playwright Chromium文件不存在，与IPC问题分开处理。
3. **方案**：新增显式 `-FullAccess`/`--full-access`，仅接受已有TaskPacket的Auto重试。Coder明确 `-s danger-full-access`，工程检查用当前账户原生子进程；不继承桌面权限、不改全局配置。预检先于预算扣除，复用已安装Edge，不安装或下载新浏览器。
4. **权限范围**：用户在读完风险说明后回复“同意本次启用并复验一次”，见authorization.json。没有管理员提权/系统安全设置变更；浏览器自身sandbox保持true。Coder和工程获得当前用户文件/进程/网络权限，工作目录不是OS访问边界。路径检查、环境清理、日志脱敏、指纹和预算只降低风险，不能宣称保留原OS隔离。未执行越界写入探针冒充通过。
5. **实际修改**：工厂 `factory/executor.py`、`factory/controller.py`、`scripts/factory.ps1`、`tests/test_factory.py`、`docs/GOAL1_USAGE.md`、`PROJECT_STATUS.md`；增加本次validation目录与31项回归记录。生成项目修改 `tests/goal0.test.mjs`（Edge启动和预期503分类）、`README.zh-CN.md`、`PROJECT_STATUS.md`及自测验收/日志/PNG/trace/指纹。没有重写业务src文件、冻结Skills或旧案例。详细workspace变化清单见guard-final.json。
6. **复用**：原Planner四份规划、原Goal0提示词和TaskPacket不变；TaskPacket再次通过身份、路径、预算、映射、依赖、产物哈希验证。包指纹 `edb6c6afa62657c5dc2d899e4774bed1855b5e4dd5b9689ca67ac746207c8ad2`；自动handoff-03记录该指纹及输入哈希。没有Planner重跑或新建业务项目。
7. **Coder**：真实CLI 0.162.0-alpha.2，独立thread `01a11e5e-f939-7f53-8586-661ef84f3ddd`，退出0，turn.completed，结构化status=completed。原Planner独立thread来自原保存记录。实际源码变化为现有测试文件，不用无用新文件满足检查。
8. **构建与测试**：Coder首次全量4通过/1失败，原因是故意写失败503被错计为意外控制台错误。保存失败源码/日志/截图/trace后，精确登记预期PATCH 503和对应消息，其余错误仍要求零；第二轮完整5/5。主控独立build退出0（0.153秒），test退出0（6.469秒），5通过、0失败/取消/跳过。31项主控回归全部通过，明确含AgentDouble，不能代替本条真实业务测试。
9. **浏览器**：真实已安装Edge、chromiumSandbox=true。覆盖列表/ID/汇总、搜索/空态、键盘/取消、延迟与重复提交、备注持久化/刷新/服务进程重启、写失败草稿保留、两视口可达与无横向溢出、焦点和对比度。外域尝试/意外HTTP或请求错误/意外控制台错误为零；预期503单独记录。真实PNG为1440×900和390×844，已查看；trace ZIP63条目、CRC检查无损坏。
10. **边界复核**：44份冻结文件、原规划和包、workspace AGENTS.md无差异。参考项目35839文件路径/大小/mtime无差异，node_modules以外SHA及参考Git无差异。Full Access未执行OS越界拒绝验证，也不能证明整个宿主没有其他读写；Coder的“未访问保护目录”为其自报，可见日志和有限哈希复核不能升级为全面安全保证。用户已明确接受此运行权限范围。
11. **真实 E2E**：成功1条，原一句话图书DEMO任务在先前真实Planner/工程创建记录上恢复，自动派发原任务包，真实Coder修复并回收结果，主控真实构建/业务浏览器测试/HTTP启动检查通过，completion.json与工程manifest一致。不是全新重跑Planner或模拟链路。HTTP200只是额外健康检查，服务已停止。整个图书借还业务未完成，也不属本Goal要求。
12. **恢复与历史**：实际再次恢复已完成任务，退出0，返回“复用结果，不再调用Agent”，总调用保持3、重试1。此前失败状态/中断/异常不冒充成功；本次30份旧control文件在attempts/03-a923237c/before归档，哈希全部一致。旧workspace证据及首轮失败保留。恢复日志见resume-console.txt。
13. **本阶段调用、耗时、Token**：Planner0、Coder1，Coder276.844秒，预算900秒；正式主控验证1轮、Coder内部完整自测2轮。CLI input297757（cached258560，非缓存39197）、output5413，输入+输出303170；reasoning148包含在output内。模型连接曾超时重连，属于同一CLI调用，最终成功。调用/超时/重试上限有效，细分Token没有硬上限；主会话Token和精确费用未取得，不推算。历史2次调用不计入本阶段新增次数。
14. **状态**：原任务已完成，Goal1已完成、待外部Reviewer验收；Goal0已验收冻结。PROJECT_STATUS保留旧阻塞、测试失败、历史完整性漂移与限制。未开始Goal2。
15. **Git**：只读确认main/HEAD/goal-0-approved同为`11aa80e1dc345d63f9b325d14227b078c0f924bb`。工作区有PROJECT_STATUS修改及既有Goal1未跟踪文件；未清理、恢复或覆盖旧成果。所有本次Git命令均带`--no-optional-locks`，无Git写命令。git status/diff --stat保存在git-final.json；diff统计只涵盖已跟踪文件，不能代表所有Goal1源码。旧专项报告的Codex宿主.git/config漂移原样保留，不能声称宿主缓存绝对零写入。
16. **限制与下一决定**：本次仅验证Windows本机Edge；其他环境/浏览器未测。FullAccess当前只开放已有包Auto Retry，新需求默认仍受限，不能声称所有新需求已可在FullAccess下一步自动成功；下一次执行需另行明确授权。完整Tester/Reviewer/Git/Release自动化尚未实现，Token硬上限未实现。初次E2E外壳执行工具的session编号未回收，不单独宣称外壳退出码；实际CLI/主控检查/恢复退出码、完成状态和日志均已取得。当前不需要安装WSL/Docker或修改系统安全设置。停止等待外部Reviewer，未经新授权不再模型重试或Git收口。

关键证据：本目录RESULTS.json、guard-final.json、authorization.json、evidence-manifest.json；项目control中的coder-03.launch/input/log/result、handoff-03、basic-checks、check-0/1日志、runtime-check、completion；workspace/validation/goal0中的PNG/trace/browser-errors及AC矩阵。所有报告区分环境探针、Coder自测、主控独立检查与尚未发生的外部验收。

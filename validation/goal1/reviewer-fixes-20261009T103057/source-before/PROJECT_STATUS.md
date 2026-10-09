# AI Project Factory 项目状态

更新时间：2026-10-09，Asia/Shanghai。

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Goal 0 | 开发经验提炼与核心 Skills 建设 | 已验收冻结 |
| Goal 1 | Planner→TaskPacket→Coder 自动交接与基础验证 | 已完成，待外部 Reviewer 验收 |
| Goal 2 及后续 | 扩展测试、审查与受控交付 | 尚未实施 |

## Goal 1 当前授权与基线
用户已授权 Goal 1 实施。执行前只读核验：main / `11aa80e1dc345d63f9b325d14227b078c0f924bb`，`goal-0-approved` 解引用到同一 Commit，工作区干净。下方 Goal 0 的“尚无仓库”“等待手动冻结”“自动交接尚未实现”等文字保留为当时的历史记录，不代表当前阶段。

本阶段只建设 Planner→TaskPacket→Coder→基础验证→结果回收。冻结 Skills、历史案例和报告保持原样；新验证写入 `validation/goal1/`，生成工程写入 `projects/`；不执行 Git 写操作。

## Goal 1：2026-10-09 执行策略调整

用户将当前产品范围收敛为个人 Windows 电脑与 Codex，并明确原受限沙箱修复不再是前置条件；下方沙箱修复路线保留为历史，不再作为当前必做工作。启动链诊断时适配器显式使用 workspace-write/unelevated，未继承桌面 Full Access。说明具体范围和风险后，用户明确回复“同意本次启用并复验一次”，授权记录见本次专项目录 `authorization.json`。

已完成启动链核对与可信原生环境探针：非受限令牌下 Node 管道子进程、Windows 命名管道读写和 Chrome/Edge 空白页均成功；Node→Playwright→已安装 Edge 固定 DOM 检查退出0，显式保留浏览器自身沙箱。另确认现有测试默认 Playwright Chromium 文件不存在，候选最小修复是使用已验证的 msedge channel。这些均为环境诊断，不是业务验收。

诊断及授权前方案：`validation/goal1/execution-strategy-20261009T094510-c2a752/REPORT.md`。新增显式 `-FullAccess` 参数，仅接受已有包 Auto Retry；默认模式不变，不修改全局配置或提权。Full Access 下工作目录只是任务约束，不是 OS 隔离边界，不能报告越界拒绝验证通过。控制记录在重试前复制归档，修改已有源码可以接受，但仍须主控真实检查；31项回归通过，报告 `validation/goal1/exception-tests-229a7fff70.json`（包含替身，不是E2E）。

原 TaskPacket 重新校验通过，规划与控制记录、既有源码、44份冻结文件及参考项目35839文件在初始探针前后既定覆盖无差异，参考 Git 无差异；证据 `guard-after-probes.json`。HEAD/main/goal-0-approved仍为11aa80e，无Git写命令。历史专项报告记录的其他漂移事实原样保留。

授权后的同模式 Node/Edge 固定页面预检通过，启动唯一一次真实 Coder（总调用第3次），不重新运行 Planner。实际启动参数保存为 `control/coder-03.launch.json`，900秒上限，模式 danger-full-access；CLI曾出现模型连接超时并在同一调用内重连，最终完成。以下为回收后的最终状态；下方旧环境阻塞段落仍为历史事实。

本次真实 E2E 成功1条：自动复用已验证的TaskPacket与原7734字符Goal0提示词，Coder线程 `01a11e5e-f939-7f53-8586-661ef84f3ddd` 实际修复现有测试入口（msedge、chromiumSandbox=true）及预期故障503分类。首次完整测试4/5失败记录已归档，修复后Coder完整自测5/5；主控独立build=0、test=0（5通过、0失败、0跳过），HTTP200/预期内容匹配、服务停止。真实浏览器验证交互、持久化/重启、故障和离线请求，并保存1440×900、390×844 PNG及trace，已检查截图及ZIP完整性。没有用HTTP200或替身替代浏览器验收。生成项目仅完成规划的Goal0，不是全部图书业务完成。

主控恢复命令退出0、复用已完成结果，调用数保持3，重试1，无重复规划/开发。原规划、包与提示词哈希不变；30份旧control文件已复制归档并核对哈希，旧workspace证据和本次失败轮记录均保留。最终守护复核通过：44份冻结文件、参考项目35839文件及参考Git无差异（node_modules按大小/mtime，其余SHA）；workspace AGENTS.md未变。Full Access无OS越界阻止能力，有限指纹及可见日志不能证明整个电脑零越界或零敏感数据读取。未执行Git写命令；HEAD/main/goal-0-approved仍为11aa80e，不能据此声称宿主所有.git缓存文件零变化。

本阶段新增Planner0、Coder1；Coder耗时276.844秒，CLI input=297757、cached_input=258560、output=5413（reasoning148是输出子集，不再相加）。主控build/test分别0.153/6.469秒。原调用/时间/重试上限保留，Token用量有真实记录但无Token硬上限；主会话Token未取得。本次FullAccess参数仅接受已有包的Auto Retry，新需求仍默认受限模式，后续执行需按次明确授权，不声称所有新需求都能无介入完成。

最终报告：`validation/goal1/execution-strategy-20261009T094510-c2a752/FINAL_REPORT.md`；机器结果及证据哈希见`RESULTS.json`、`evidence-manifest.json`、`guard-final.json`。Goal 1：已完成，待外部 Reviewer 验收。停止，不进入Goal2，不自行验收/提交/Tag/Push。

## Goal 1：2026-10-09 环境专项诊断

已复用现有报告、日志、Planner 四份产物、TaskPacket 和工程；未重新规划，未调用 Planner/Coder，未进行正式端到端重试。新报告与原始诊断记录：`validation/goal1/environment-repair-20261009T010203/REPORT.md`。下方“实际进展与阻塞”保留上轮事实。

当前可验证原因范围：Codex CLI 0.162.0-alpha.2 的 unelevated 受限令牌下，Node v26.3.0 本身及继承/忽略/文件输出子进程均成功，管道输出子进程 EPERM；Win32 命名管道服务端能创建，读连接成功、写连接错误5。换 cwd/TEMP、去掉桌面包环境变量均无改善。Chrome/Edge 能创建进程，但新 workspace 私有用户目录下仍在 Mojo/Crashpad IPC 访问拒绝处失败。尚未确定具体 CLI 缺陷或已修复版本，不能把业务代码标为错误来源。

继续专项诊断：成功读取默认管道DACL，确认完整权限给当前用户而该用户SID不在受限SID列表，Everyone仅可读；libuv写端、WRITE_DAC及Chrome Mojo精确访问掩码均被拒绝。匹配libuv 1.52.1和Chrome154.0.8037.98源码，确认该权限机制与失败一致。TokenDefaultDacl与默认管道DACL不同，materialized helper与当前CLI SHA一致；没有实施加用户SID、改ACL或DLL注入等未经边界验证的权限补丁。新增原始证据pipe-acl-followup.json、pipe-access-followup.json和runtime-source-inventory.json；原失败证据未覆盖。

最小适配修复：Windows Node 管道预检在现有包验证后、重试计费和 Agent 派发前执行；失败明确留证并停止。边界探针文件改为每次独立路径。一次真实预检仍失败，不进入正式 E2E。另修复运行锁追加问题：首次无Retry恢复令controller.lock增加一个ASCII“0”字节（0x30），保留实际变化；最终27项主控回归通过（含显式 AgentDouble，不是业务工程成功）。26项通过、锁修正初版27项中2个错误、最终27项通过的报告均保留。没有解决底层 IPC 权限，没有放宽沙箱、变更 Windows 安全设置或全局配置、安装 WSL/Docker/VM。

实际恢复保持“已失败”，历史 Agent 调用2、重试0；不带 Retry 的恢复返回退出1且未调用 Agent。TaskPacket、规划、旧控制记录和工程源码保留，剩余一次 Coder 重试未消耗。8个被测冻结/外部文件或目录拒绝写访问，探针未修改这些对象；不能把有限路径检查等同完整宿主安全审计。

完整性证据见专项目录guard-final.json：44份冻结文件、原源码及历史报告、参考项目35839文件的既定覆盖无差异；control只存在上述运行锁差异，修复锁后的再次无Retry恢复没有继续改变锁内容；原state/events、规划和包未变。跨中断点的工厂.git由235文件到272文件（38个objects新增、1个codex/turn-diffs引用文件消失），用户config SHA也变化，最终guard仍为false。没有执行Git写命令或编辑全局config，变化来源未独立确认；不声称.git、control或全局config绝对零写入。只读确认HEAD/Tag/main仍为11aa80e基线；发现漂移后停止进一步执行，仅收口报告，等待外部Reviewer及用户决定。

当前构建/业务测试仅保留上轮 build=0、test=1、HTTP200 的历史事实，本轮未运行业务测试或取得浏览器验收截图。Goal 1 保持“开发中，环境受阻，未完成”。下一步需用户选择管理员协助修复官方 elevated 环境，或授权受控 WSL2 环境建设；任何替代执行器都须重新验证权限与浏览器能力。停止，等待外部 Reviewer；不自行验收或 Git 收口。

## Goal 1 实际进展与阻塞
主控、PowerShell入口、独立CLI执行适配、TaskPacket 1.0验证、状态/日志/查询/有限恢复、Plan与Auto分支已实现。最终25项异常/恢复测试通过，报告 `validation/goal1/exception-tests-cf44706865.json`；Agent替身只用于这些确定性测试。

真实案例 `projects/p-dc1e9d42b5ae/`：Planner与Coder两个不同CLI thread实际执行，自动交接完整任务包和7734字符Goal0提示词；Planner四份产物、12项AC和无环依赖已验证。Coder实际创建工程代码并如实返回失败。主控独立诊断：构建退出0、测试退出1（Node spawn EPERM）、健康HTTP 200、临时服务已停止。没有成功的端到端链路，没有真实浏览器截图或完整AC通过结论，不宣布Goal1完成。

阻塞：本机Codex CLI 0.162.0-alpha.2的elevated沙箱初始化失败；unelevated沙箱可拒绝control越界写入，但Node子进程EPERM、Chrome/Edge IPC拒绝访问，桌面兼容设置也未解决。保留受限沙箱，不降级完全访问、不修改全局配置、不安装其他服务。不消耗剩余一次Coder重试去重复已确认的环境失败。

恢复点：真实任务保持“已失败”；规划可复用。需先在另行授权范围内修复/验证受限执行环境，再以 `scripts/factory.ps1 -ProjectId p-dc1e9d42b5ae -Mode Auto -Retry` 使用剩余1次重试；不得把未完成工程或缺失截图当作通过。完整说明见 `docs/GOAL1_USAGE.md`，验证报告见 `validation/goal1/REPORT.md`。停止，等待用户决定阻塞处理；不进入Goal2或Git收口。

Goal1结束只读复核：44份受保护冻结文件无内容变化，参考项目35839文件的路径/大小/mtime一致、除node_modules外SHA一致，参考Git无差异；工厂.git 96文件内容亦无差异（该.git快照在Planner启动后、Coder启动前采集）。证据见 `validation/goal1/guard-after.json`、`factory-git-after.json`。不据此声称Codex宿主运行缓存绝对零写入。

## Goal 0 历史：当前任务
三个 Skills、五份权威模板、中文使用说明及架构路线已完成。两个独立案例均生成输入→计划→骨架方案→可执行提示词→设计任务包→评估记录，完整交付检查通过；独立内部审查发现的问题均已修正并复核。依据用户本轮明确通知，外部 Reviewer 已验收通过，Goal 0 状态更新为“已验收冻结”。当前无开发任务，等待用户手动 Git 冻结。

## Goal 0 历史：外部验收收口
结论来源：用户于本轮提供的“AI Project Factory — Goal 0 外部验收收口”通知；外部 Reviewer 结论为“Goal 0：验收通过”。

用户通知的检查范围：三个核心 Skills 实际内容、Skill 内部资源引用、两个不同类型案例、需求/验收标准/Goal/任务映射、两案例各12项 Goal0验收标准覆盖、开发提示词可执行性与约束、任务依赖无环、已提供文件与验证记录的内容哈希。

该结论不代表两个案例已实际开发、多 Agent 调度已实现或全局 Skills 安装已验证；不声称外部 Reviewer 重跑了未提供的全部验证脚本。

本轮仅更新本状态并补建根目录缺失的 `.gitignore`，不修改 Skills、案例、验证报告或参考项目，不删除文件，不执行 Git 写操作。下方历史验证结果与已知限制保留。验收前 checks.json 的文件哈希仍为当时候选记录；本次状态更新及新增 .gitignore 是收口变更，不重写历史哈希或把它们冒充本轮新验证。

## Goal 0 历史：授权与基线
本轮只写 `C:\AI-Project-Factory`。不安装全局 Skills、不开发两个案例系统、不执行 Git 写操作、不发布。新目录最初为空，当前未初始化 Git 仓库；只读 rev-parse 确认无仓库，不能称“Git工作区干净”或提供虚构 Commit。

参考项目 `C:\910Program`：只读确认 HEAD `a0f0bf30d74834b7374817d0f3f977cba16d885b` / `final-release-metadata-approved`，分支 `release-metadata-final-fix`，初始工作区干净；业务冻结 `a8dbb4a / acceptance-v2-task-state-fix-approved`。初始全文件只读快照位于 validation/reference/before.json，结束时复核。

## Goal 0 历史：已运行验证
- 使用本机 skill-creator/quick_validate.py，三个 Skills 均返回 `Skill is valid!`。
- `scripts/validate_delivery.py`：三个 Skills frontmatter/UI metadata、8 处自包含资源链接与交付文档链接通过；案例 A 18 R / 18 AC / 11 Task、案例 B 14 R / 22 AC / 14 Task，各12项 Goal0 AC 均入提示词，映射完整、依赖无环、禁权一致、无未填提示词变量，结果 validation/checks.json。两案例各6个无效任务包探针被拒，共12个。
- `scripts/inspect_reference_evidence.py`：11 张历史截图 PNG 尺寸及当前正式 ZIP SHA 与外部校验一致，结果 validation/reference/source-inspection.json。这不是重测参考业务。
- 仅项目内 `.tools/validation-env` 安装 PyYAML 6.0.3 用于检查；未安装全局依赖。Skills 运行不需要这一验证环境。
- `scripts/reference_guard.py after`：35,839文件路径/大小/mtime与Git状态无差异，除node_modules外SHA-256亦无差异；证据validation/reference/after.json。参考项目未修改，Git写操作未执行。
- 独立内部审查见 validation/INDEPENDENT_REVIEW.md；不是外部验收。修正包括任务前提与写集、事实来源、静态服务、缓存/备份写集、测试端口与自检角色，记录在两案例evaluation及验证报告。
- 首次完整QA时案例B评估记录尚未生成，检查明确返回未完成；补齐后完整通过。先前机器结果保存在 validation/check-runs/，未冒充全程一次通过。

## Goal 0 历史：证据和限制
经验来源 docs/SOURCE_EXPERIENCE.md；历史原始提示词未找到，只依据可核实成果及用户本次指令归纳。没有重新运行参考工程或两个案例业务系统，不能给它们新的运行通过结论。

官方用户级安装说明已核对，当前文档为 `.agents/skills`，本会话旧目录 `.codex/skills` 差异已如实说明；本轮未测试全局发现。

## Goal 0 历史：恢复点与下一动作
Goal 0 已获外部验收通过，候选内容指纹与逐文件SHA在validation/checks.json，保留为验收前历史记录。下一动作由用户手动执行 Git 冻结；本代理不初始化仓库、不提交、不打Tag、不进行Git冻结。没有新的授权不开始下一阶段或自动交接程序。

## Goal 0 历史：未来工作
参见 docs/MULTI_AGENT_ROADMAP.md。任何 Planner→Coder 自动交接程序、Agent执行、Git/发布能力均未实现；下一阶段需要新的任务授权。

**Goal 0：已验收冻结。** 完成后停止，等待用户手动 Git 冻结。

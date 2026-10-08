# 公共设备采购申请演示系统 — Goal 0 Coder 实施提示词

这是未来 Coder 的完整实施任务；当前验证仅生成本提示词，没有创建目标工程、运行业务或批准发布。仅完成 Goal 0，达到全部自测门槛后停止等待外部 Reviewer。

## 1. 背景、用途与范围

为完全虚构的“某市公共设备采购申请演示系统”建立能持续增量开发的工程基础。现场最终要在 Windows x64 单机浏览器断网演示，现场没有管理员权限，也不能要求安装 Node/Git/包管理器。最终业务要展示填报、审批意见、执行进度、同源统计和操作记录；本 Goal 0 只实现工程框架、模拟身份、导航、数据/状态基座和可修改、刷新保留、确认重置的基础样板。

不得实现完整采购申请、审批、执行或业务看板。采购审批层级、金额阈值、退回后的版本规则未确认，只阻塞后续业务，不阻塞此基础任务。数据全部虚构，界面标明 DEMO；不接真实政府账号、预算平台、支付、电子签章，不声称提供真实授权、采购合规或法定审批。

## 2. 工作目录、环境与选型

唯一允许写入目录：`C:\FactoryCases\ProcurementDemo` 及其子路径。当前该目录存在性、源码、Git HEAD 和工具版本未知，你必须先核验。禁止写 `C:\AI-Project-Factory`、`C:\910Program`、用户全局配置/Skills、其他项目和浏览器现有用户数据；不运行参考项目命令。不要安装全局软件，不引入付费服务，不发布、不执行 Git 写操作。

选定 React + TypeScript + Vite + HashRouter；本地 IndexedDB 保存虚构运行数据；Vitest / Testing Library / Playwright 测试；使用 npm 和 package-lock.json。开发机可以联网准备项目依赖和项目本地 Playwright Chromium。版本未核实，不填虚构版本；先记录 Node/npm，再选择兼容依赖并精确锁定。若必要工具缺失、兼容性无法解决或需要安装到指定目录外，诊断并停止相关步骤等待授权。

方案依据：本案例是单机虚构演示；本地 API + SQLite 也可行，但当前无附件、大量数据、跨浏览器共享需求，不引入额外服务。IndexedDB 禁用或未来数据形态变化时暂停确认，不能静默 fallback 到内存/localStorage 或悄悄换栈。

最终现场便携包装另设 Release；这里用开发机生产构建与 loopback preview 验证，不得把需要 Node 的 preview 宣称为现场包。

## 3. 首先核验基线 — T-A001

使用 PowerShell `Test-Path -LiteralPath 'C:\FactoryCases\ProcurementDemo'`。若目录存在，先 `Get-ChildItem -LiteralPath 'C:\FactoryCases\ProcurementDemo' -Force`，读取该目录已有 AGENTS/PROJECT_STATUS 并核对约束。只有在确认该目录自己的 `.git` 存在时运行 `git --no-optional-locks -C C:\FactoryCases\ProcurementDemo status --short`、`git --no-optional-locks -C C:\FactoryCases\ProcurementDemo rev-parse HEAD`、`git --no-optional-locks -C C:\FactoryCases\ProcurementDemo log -1 --format=fuller`；无仓库写“无本目录仓库、无 HEAD”，不能把父目录仓库当本项目。

若不存在，记录此事实后仅在此授权路径创建工程。若存在非空内容、未提交用户修改、已冻结代码或冲突配置而不清楚如何兼容，停止覆盖，报告具体文件和冲突；不得 reset/restore/clean/switch。既有内容不能被空模板覆盖。把实际基线、现有文件/哈希、约束和工具版本写 `evidence/preflight.md`，再开始 T-A002。本轮任何 Git 写操作，包括 init/add/commit/tag/push/branch/switch/reset/restore/clean 均禁止。

## 4. 任务顺序、目录和共享文件

依赖 T-A001→T-A002→T-A003→T-A004→T-A005→T-A006，不并行修改共享文件。你是根配置、锁文件、路由/导航和共享类型的唯一整合者；测试结果固定到同一候选代码。这里的 Task/角色是职责切片，你可作为单个 Coder 顺序完成实现和 Tester 自测，不需要运行 Agent 调度器。你的范围自检不能称为独立 Reviewer 审查；外部 Reviewer 在本任务结束后另行审查。未来 Tester/Reviewer 可在固定候选上独立读，但开始修复后旧审查结论不能套用新候选。

| Task | 文件入口 | 动作与产物 | AC |
| --- | --- | --- | --- |
| T-A002 | package.json/lock、tsconfig、vite/vitest/playwright/eslint 配置、src/app、src/ui、README | 建立静态检查/构建/启动/测试脚本；主布局、HashRouter、统一 navigation、token；后续业务说明页 | AC-A001/002/009/012 |
| T-A003 | src/core/data、src/fixtures | 建立单一 snapshot、IndexedDB adapter、seed、save/reset 服务、错误和 epoch 保护；先固定类型 | AC-A004～008 |
| T-A004 | src/core/session、src/features/foundation | 模拟身份选择、只读与编辑权限、工程样板列表/详情/指标/日志、场景选择和确认重置、错误处理 | AC-A003～008 |
| T-A005 | tests/unit、tests/component、tests/e2e、evidence/test-runs | 编写下述行为测试；从干净依赖安装到生产构建两视口验证；保存真实结果 | AC-A001～010/012 |
| T-A006 | PROJECT_STATUS.md、docs/acceptance-goal0.md、evidence/index.json、screenshots | 按候选内容指纹整合命令、AC、截图、失败与恢复点；输出最终报告 | AC-A011 |

目录方向 app 装配 feature → service → repository → IndexedDB adapter；ui 不访问存储，feature 不直接调 indexedDB。未来 Goal 1 在 src/features/procurement、approval 接入，在 navigation/router 注册；Goal 2 在 execution/reporting 接入，不能重新建立状态源。Goal 0 不必填这些业务目录空壳以冒充功能。

## 5. 页面、视觉和交互

主框架顶栏显示项目名、当前演示身份和退出。菜单包含“工程验证样板”（实用页面），采购申请、审批意见、执行进度、统计与记录（仅说明页，显著注明后续 Goal）。工程样板页面包含样板列表、详情与名称编辑、同源样板数量/修改次数、操作记录、标准/退回场景选择和重置按钮。样板指标不是业务看板；所有场景/身份标题标明虚构演示。

视觉 token：背景 #F3F6FA，内容 #FFFFFF，正文 #182230，次级 #526174，主色 #185ADB，危险 #B42318，边框 #D0D5DD；正文 14px，主标题 24px；间距 4/8/12/16/24/32px，控件高度至少 36px，焦点 2px outline。若实际对比度不达可读标准，局部修正并记录原因。错误、选中和权限不能只用颜色表达。

分别在 viewport 1920×1080、1366×768 检查：主标题、角色入口、保存/重置、操作记录和弹窗都可达，无重叠、无遮挡，无页面横向溢出；小视口允许内容纵向滚动。表单有 label，按钮有可读名称，Tab 顺序和焦点可见，弹窗初始焦点/焦点约束正确；Esc/关闭/取消均零副作用，关闭回原触发按钮。

加载期间禁用保存/重置；空态显示“无样板”；错误态说明读取/存储失败并给重试入口；只读态写明模拟角色原因。保存时禁重复点击；成功只能在事务提交后显示，失败留住用户输入供修复。

## 6. 身份、数据与状态契约

无真实账号/密码；初始显示“填报员（演示）”“审批员（演示）”选择。会话保存在内存，刷新后重新选身份，数据仍保留。未选择/失效身份不能读写样板页；填报员可读/改，审批员只读，两个已选择身份都可以确认重置虚构数据。退出/切换身份只改内存会话，不改样板、指标或记录。SessionService 支持测试 fixture 触发过期，过期后返回角色选择且无数据修改；无需额外伪造生产登录功能。界面持续写“模拟身份，不代表真实授权”；应用服务也检查角色，但客户端检查可被绕过，不宣称安全边界。

snapshot 为 `schemaVersion:1, scenario:'standard'|'returned', epoch:number, samples:[{id,name,sceneLabel,version,updatedAt}], operations:[{id,action,sampleId,actorRole,at,version,epoch}]`。样板 ID 固定 SAMPLE-001 / SAMPLE-002；operation ID 唯一，一次操作一条日志；保存时间为实际 UTC ISO，页面按 Asia/Shanghai 显示。标准 seed 两条，退回 seed 一条带“退回场景基础样板”标签。它只是工程标签，不是待确认采购状态机。

seed 不可变、运行数据独立克隆。数据库 `procurement-demo-foundation`、store `runtime`，一份 snapshot；首次正常空库初始化标准 seed、空日志。列表/详情/指标/操作记录读取同一 snapshot；禁止独立 hardcode 指标。除该数据库外不动任何 origin 或现有数据。

统一接口：`readSnapshot()`；`saveSample({id,name,expectedVersion,epoch}, session)`；正常重置 `resetScenario({scenario,confirmed:true,expectedEpoch}, session)`；损坏恢复 `recoverScenario({scenario,confirmed:true,recoveryToken}, session)`。读取失败后 adapter 才生成绑定当前 generation 的 recoveryToken；过时 token 拒绝。二次确认恢复时事务只覆盖本数据库 runtime 记录，不依赖损坏数据可解析 epoch；递增 adapter generation 使此前 pending 操作失效。结果 `{ok:true,snapshot}` 或 `{ok:false,code,message}`。至少处理 VALIDATION、FORBIDDEN、SESSION_EXPIRED、STORAGE_FAILED、SCHEMA_UNSUPPORTED、STALE_OPERATION。角色来自 SessionService 而非表单自报。

save：先校验 trim 后名称 1～80 字、ID 存在、模拟身份、version 与 epoch，再在单个事务同时改样板/version、追加日志；重复提交控制不能产生两条操作；事务失败不发布假成功。版本/epoch 冲突拒绝且提示重新读取，保留原状态。读取损坏或未知 schema 不自动清空或降级；禁写并提供诊断与确认重建虚构数据。新的 schema 迁移不得未经确认损坏已有数据。

场景选择只存在页面待选择状态；不修改 snapshot。重置弹窗写明“清空当前虚构演示进度与日志，载入所选场景”。取消/Esc/关闭不写数据、不写日志、不改当前场景；确认原子替换所选 seed，epoch 加一，清空旧日志并写一条 RESET。保存或重置处理中互斥/禁重入，任何旧 epoch 异步保存不得覆盖重置后的新状态。失败保留原数据、显示可读错误；恢复只针对本工程虚构数据库且需二次确认。

## 7. 操作边界

允许：核验后在目标目录创建上述工程文件、项目依赖、测试、README、状态和证据；启动/停止本任务自己的 loopback 服务。依赖最小化，使用免费开源工具；修改以本 Goal 0 为限。

禁止：写工厂/参考/全局目录；任何 Git 写入、提交/Tag/冻结；外部发布/部署；真实账号/支付/签章；完整业务实现；静默重建用户文件；强杀未知端口进程；清空现有浏览器配置；依赖远程 CDN/字体/图表；将失败切成 Mock 成功；删除失败断言、批量 skip、改验收标准以换取绿色结果。工具会写目录外缓存或配置且未被当前授权覆盖时停止该步骤，报告需要哪项额外权限。

## 8. 必须建立并实际运行的命令

以下是你必须实现的脚本接口，目前尚不存在/未实测。全部命令工作目录为 `C:\FactoryCases\ProcurementDemo`，日志保留原始 stderr/stdout 与退出码。核验目标后创建其 `.cache/npm`、`.cache/playwright`、`.cache/tmp` 子目录，仅当前命令进程设置 `$env:NPM_CONFIG_CACHE='C:\FactoryCases\ProcurementDemo\.cache\npm'`、`$env:PLAYWRIGHT_BROWSERS_PATH='C:\FactoryCases\ProcurementDemo\.cache\playwright'`、`$env:TMP='C:\FactoryCases\ProcurementDemo\.cache\tmp'`、`$env:TEMP='C:\FactoryCases\ProcurementDemo\.cache\tmp'`；不设置用户/系统环境变量。.cache 加入 .gitignore，README 同时写本地缓存设置，浏览器测试使用隔离临时 profile，不能用现有用户 profile。若工具仍要求写目标目录外停止该步骤并报告。端口 4173 为生产 preview，4174 为开发；占用则停止并报告，不使用未知服务。服务持续运行命令以“ready 与实际 HTTP 页面可用”判定，最终停止只结束本任务创建的进程。

| 顺序 | 命令 | 预期 / 日志 |
| --- | --- | --- |
| 1 | `node --version`、`npm --version` | 记录实测值；evidence/preflight.md |
| 2 | 首次 `npm install` 创建锁文件，再 `npm ci`；已有锁文件直接 `npm ci` | exit 0，锁文件稳定；evidence/test-runs/dependencies.log |
| 3 | `npm run typecheck`；`npm run lint` | exit 0；typecheck.log / lint.log |
| 4 | `npm run test:unit -- --run` | exit 0；Vitest 配置 include tests/unit 和 tests/component，排除 tests/e2e，组件用 jsdom/对应 setup；unit.log 与机器报告 |
| 5 | `npm run build` | exit 0，dist 仅本地资源；build.log |
| 6 | `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort` | 实际打开生产构建完成手动 smoke，记录 preview.log；随后只停止本任务创建的 preview PID，确认其退出和 4173 释放，不杀未知进程 |
| 7 | `npm run test:e2e` | 手动 preview 已停止，由 Playwright webServer 自行启动/停止本次 4173 preview；exit 0，两视口所有必需行为；e2e.log、HTML/JSON 与失败 trace |

同时提供 `npm run dev -- --host 127.0.0.1 --port 4174 --strictPort` 的 README 启停说明。Playwright webServer 在干净自动测试中 `reuseExistingServer:false`，不要错误复用旧进程。Chromium 未准备时，仅在开发机、项目依赖锁定后使用项目本地 `npx playwright install chromium`；若写到未授权全局位置，先诊断停止，不在现场安装。记录实际浏览器和 OS，未测现场 OS/权限条件如实列出。

## 9. 全部 Goal 0 AC 与验证方法

| R / AC | 必须执行的验证 | 必须可观察的结果 / 证据 |
| --- | --- | --- |
| R-A001 / AC-A001 | 在生产构建上拦截所有非 loopback 请求，访问角色页/样板/本地资源 | 页面与关键资源可用，无外域依赖及意外 pageerror；保存请求清单和日志。非 loopback 资源尝试必须报告失败，不能仅 abort 后忽略 |
| R-A002 / AC-A002 | 两 viewport 分别鼠标/Tab 导航、打开/取消重置弹窗 | 操作可达、焦点正确、无重叠与横向溢出；原始截图 + UI 断言 |
| R-A003 / AC-A003 | 未登录调用写服务、填报员用户链路保存、审批员尝试编辑/直接调服务、fixture 使会话过期 | 未登录/只读/过期全部拒绝且无写入；填报员允许；过期返回选择页；持续模拟身份文案；service 单测与 UI E2E，不声称真实安全 |
| R-A004 / AC-A004 | seed 初始化，对同一 ID 保存一次，核对列表/详情/指标/日志与 seed | 同一 version/值，日志一条，派生数量准确，seed 不变；单测 + UI 链路 |
| R-A005 / AC-A005 | UI 改名保存、refresh、重新选身份；独立 browser context 再初始化 | 同一 ID/值/version/日志持久保留；第二上下文默认 seed 不污染首个；真实 IndexedDB E2E，不能替换成内存 mock |
| R-A006 / AC-A006 | 保存制造差异，打开重置；取消/Esc/关闭前后完整 snapshot 比较；再确认 | 取消全部零副作用；确认所选 seed、一个新 epoch、一条 RESET、无重复；截图辅助不替代数据断言 |
| R-A007 / AC-A007 | 名称空白/81 字；adapter 注入写失败、未知 schema/损坏读取；执行恢复取消/确认 | 非法输入/写失败无持久改动、无假日志，可读错误；损坏不静默清空；确认才恢复。注入测试须标注故障模拟，正常持久化仍用真实浏览器 |
| R-A008 / AC-A008 | 标准场景改名；只改场景选项；确认退回并 refresh；单测重置与旧保存竞争 | 选择不写，确认才换退回工程标签并持久保留；旧 epoch 结果不覆盖新状态；未实现真实采购退回 |
| R-A009 / AC-A009 | 从 npm ci 执行静态检查、构建、dev/preview 实际打开，核对 README 与占用端口行为 | 命令和启动成功，依赖锁定、本地地址明确、没有抢占他人进程；原始命令日志 |
| R-A010 / AC-A010 | 实际执行 Vitest/组件与 Playwright 套件，检查 AC-A001～008 映射 | 测试有可失败的行为断言，不仅断言按钮存在；报告数量、通过/失败/跳过/未运行及原因；不伪造 0 错误 |
| R-A011 / AC-A011 | 检查 evidence 索引、原始图、验收表、PROJECT_STATUS 与源码 hash | 每条 AC、候选、命令/退出码、工具/视口、步骤和结果关联；外部验收未发生；有任务恢复点、失败历史 |
| R-A012 / AC-A012 | Coder 核对源码、菜单和页面内容，记录范围自检；外部独立审查留待结束后 | 仅工程样板，无完整采购业务、无硬编码审批规则、无真实认证宣称；后续菜单标后续阶段；自检记录不能冒称 Reviewer 结论 |

必要 E2E 走真实 UI（选择身份、改名、保存、刷新、重置），不得通过直接 store 写入替代这些用户动作；只可用隔离夹具构造故障与前置状态，标明用途。取消与失败断言要检查完整 snapshot，而非只检查弹窗消失。预期的 FORBIDDEN/VALIDATION 等应用拒绝记录为预期；任何意外 pageerror、存储错误或外域请求须修复或报告阻塞。此项目无真实 API/DB，生产 HTTP 401/403 测试不适用，不能为模板添加服务器。

## 10. 截图、证据与状态记录

截图保存 `evidence/screenshots/`，至少每 viewport 一张工程样板主页面、一张角色选择、一张重置弹窗、一张存储错误态，共 8 张原始 PNG；命名包含 AC、viewport 与动作。错误态可由隔离 fixture 制造，索引明确“故障注入”，不可当成真实故障记录。保留失败 trace 与失败日志，不覆盖成成功报告。

`evidence/index.json` 记录：Goal、实际目录、日期/时区、OS/Node/npm/浏览器、Git HEAD 或 null、dirty 或“不适用”、源码 SHA-256 文件清单与候选指纹、每条 AC 对应测试/步骤/实际结果/证据路径、截图真实 viewport、命令和退出码、预期拒绝/意外错误分项。内容 hash 排除 node_modules、dist、evidence 等生成目录；fix 后重新生成候选关联，不伪造 commit/tag。所有测试/图须对应最终候选代码。

`docs/acceptance-goal0.md`：性质为自测；逐 R/AC 填操作、预期、实际、命令/退出码、证据、通过/失败/未运行；外部 Reviewer 的结论写“未发生”。`PROJECT_STATUS.md`：当前 Goal、Task、责任角色、输入版本、可写范围、基线、已完成/阻塞、实际命令/结果、下一条可执行动作、retry 次数、已知限制和后续入口。不要用计划表冒充运行结果。

## 11. 完成标准

AC-A001～012 全部实测或针对文档/边界完成可审查核对；typecheck/lint/build/unit/e2e 真实成功；生产构建 loopback 两视口可运行、断外域仍可操作、身份/取消/持久化/故障/epoch 保证符合表中断言；锁文件/README/证据/状态齐全，无未获准越界与 Git 写入，无完整业务实现。截图不能替代交互/数据断言。未测现场无 Node/无管理员环境必须作为 Release 限制，不能宣称该目标已完成。

阻塞 AC、实际失败或未运行必需验证时不得标记 Goal 0 完成，也不得擅自删掉门槛。说明可继续部分、影响和下一条需用户决定的动作。

## 12. 异常、有限返工和停止

同一问题最多 2 次有针对性修复，全任务最多 3 轮验证；每轮记录 issue ID、根因、变更文件、新候选指纹、AC 回归和结果。达限仍失败停止相关链路，保留最后可审查代码与失败证据；不要无限安装、换栈、重跑碰运气。纯环境缺失先诊断，不计作成功或编造通过。

发现基线不符、用户已有修改冲突、路径越界、保护范围变化、缺授权、真实数据破坏风险或需求冲突时立即停止相关修改并报告。发现参考目录变化不得触碰或修复它，停止相关操作。未知端口服务不得杀进程。业务规则待确认不影响基础，但不得实现这些业务规则。没有答案不代表批准。

## 13. 最终报告顺序

1. Goal 0 状态、已做/未做范围。
2. 实际工作目录、Git/源码基线、实测工具版本和变更文件。
3. T-A001～006 与 R-A001～012 / AC-A001～012 结果、未完成/阻塞。
4. 实际命令、退出码、测试数量、失败/跳过/未运行及原因、重试次数。
5. 截图、日志、trace、验收表和 evidence 索引绝对路径。
6. 保护范围核对、Git 当前只读状态及实际 Git 写操作（应为未执行）。
7. 已知限制、现场包装未验证、审批业务待确认问题。
8. PROJECT_STATUS 状态和下一阶段增量入口。

## 14. 完成后停止

全部门槛满足时仅填写 **“Goal 0：已完成，待外部 Reviewer 验收。”** 然后停止。不得自行宣称验收通过，不进入 Goal 1，不提交、不打 Tag、不冻结、不发布。后续业务、Git 和正式包装都需要独立验收/授权控制点。

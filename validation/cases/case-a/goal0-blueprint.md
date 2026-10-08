# 案例 A Goal 0 工程骨架方案

输入：case-a-plan-1，[plan.md](plan.md)、[input.md](input.md)。类型：单机浏览器离线 DEMO；目标 Windows x64，1920×1080 / 1366×768。目标目录 `C:\FactoryCases\ProcurementDemo` 本轮未读取/创建，基线和版本未知。以下为未来 Coder 须实现并验证的方案，不是已运行命令。

## 工程选择与替换条件

比较方案 A：React + TypeScript + Vite 静态 SPA，浏览器 IndexedDB 保存虚构数据，本地资源、开发/验证 loopback 服务。适合单机小数据演示、架构简单，前端身份明确是模拟。方案 B：同类 UI + 本地 ASP.NET 服务 + SQLite，可支持大附件和复杂本地事务，但增加进程、数据库和打包维护；当前没有该需求，故不选。若后续出现大附件、跨浏览器持久化或现场浏览器禁止 IndexedDB，暂停确认再考虑 B；不静默切换。

选择 A 不是行业默认：本案例明确单机、虚构、断网才选择浏览器存储。若变成真实多人管理，必须重新评估服务端/API/数据库，不能延续本 DEMO 作为生产授权方案。

| 层 | 选型 / 理由 | 依赖边界 / 版本 |
| --- | --- | --- |
| UI | React、TypeScript、Vite；组件与路由/数据边界明确 | Node/npm 仅开发机；Coder 实测工具并核对兼容性，以 package-lock.json 锁定，不在此填虚构版本 |
| 路由 | React Router，本地路径回退由 preview 验证；可使用 HashRouter 降低静态发行回退需求 | runtime 仅浏览器静态资源；选定 HashRouter 后所有菜单由 src/app/navigation.ts 单点注册 |
| 数据 | 原生 IndexedDB；统一 adapter，写入同一数据库事务 | 无 API/真实 DB。不可悄悄 fallback localStorage 或内存后报成功 |
| UI 资源 | 本地 SVG、CSS；系统字体 Segoe UI / Microsoft YaHei / sans-serif | 不引用 CDN、远程字体、远程图表；Goal 0 不引入完整业务图表库 |
| 自动化 | Vitest 单测、Testing Library（组件焦点/状态）、Playwright 浏览器行为 | 开发机可安装浏览器和依赖；记录实际浏览器版本；现场不携带测试依赖 |
| 发行 | 后续 Release 选择受测的便携 loopback server | Goal 0 的 Vite preview 只验证生产构建，不是现场无 Node 的包 |

## 目录、依赖方向与装配边界

```text
ProcurementDemo/
  package.json, package-lock.json, index.html, tsconfig*.json
  vite.config.ts, vitest.config.ts, playwright.config.ts, eslint.config.*
  .gitignore, README.md, PROJECT_STATUS.md
  public/assets/                 本地图片/SVG；无需远程资源
  src/app/                       entry、router、navigation、providers
  src/ui/                        shell、dialog、tokens.css、状态组件
  src/core/session/              模拟 identity 服务与状态
  src/core/data/                 types、repository、IndexedDB adapter
  src/fixtures/                  immutable 标准/退回工程样板 seed
  src/features/foundation/       仅“工程验证样板”页面
  src/features/procurement/      Goal 1 接入位置，Goal 0 不写业务实现
  tests/unit/, tests/component/, tests/e2e/
  docs/acceptance-goal0.md
  evidence/preflight.md, evidence/index.json
  evidence/test-runs/, evidence/screenshots/
```

依赖：app 装配 features → 服务接口 → repository → IndexedDB adapter；ui 不读存储，features 不直接调用 indexedDB。共享类型、根配置、锁文件、导航由 T-A002 的同一 Coder 整合；数据契约改变先更新 types 与 AC，不允许两个 Agent 同时改。业务模块未来注册在 navigation/router 并调用统一服务，不重建布局/持久化。

数据读接口 `readSnapshot()`；写接口 `saveSample({id,name,expectedVersion,epoch}, session)`；普通重置 `resetScenario({scenario,confirmed:true,expectedEpoch}, session)`；读取损坏恢复专用 `recoverScenario({scenario,confirmed:true,recoveryToken}, session)`。恢复 token 仅在本 adapter 确认读取失败后生成，绑定当前 generation，过时 token 拒绝；确认后在事务中只覆盖本数据库 runtime 记录，不需要从损坏数据解析 epoch，恢复时递增 adapter generation 使旧 pending 操作失效。服务返回 `{ok:true,snapshot}` 或 `{ok:false,code,message}`，错误码至少 VALIDATION、FORBIDDEN、SESSION_EXPIRED、STORAGE_FAILED、SCHEMA_UNSUPPORTED、STALE_OPERATION。拒绝结果无任何数据/日志写入。

## 页面与视觉交互

工程建议 token：背景 #F3F6FA，内容 #FFFFFF，正文 #182230，次级 #526174，主色 #185ADB，危险 #B42318，边框 #D0D5DD；字号正文 14px、标题 24px；间距 4/8/12/16/24/32px，控件高至少 36px，焦点 outline 2px；选中/错误以文案与图形共同表示，不能只靠颜色。Coder 若测试对比度不足须局部修正并记录。

主框架：顶栏项目名、当前模拟角色、退出；侧栏“工程验证样板”可用，“采购申请 / 审批意见 / 执行进度 / 统计与记录”为可进入的说明页，明确“后续 Goal，不包含业务实现”。内容区显示样板列表、详情/编辑、同源样板总数与修改次数、操作日志；数字代表工程样板而不是采购统计。样板区持续标注虚构与工程验证。

两目标视口至少覆盖主框架、角色选择、样板、重置弹窗。1366×768 允许内容区纵向滚动，禁止页面横向溢出、按钮重叠、弹窗底部无法访问；侧栏不可遮主操作。键盘 Tab 顺序、可见焦点、弹窗初始焦点/焦点约束/Esc 取消/关闭后回焦点；按钮具备可读名称。

加载时禁止保存/重置；空数据明确无记录而不是假 seed；失败显示重试读取或确认重置；不可编辑有原因。保存处理中禁止重复点击，成功消息只在存储事务成功后出现，失败保留输入供重试。确认弹窗取消、Esc、关闭均无副作用。

## 身份与权限基座

初始化无真实账号/密码，身份选择卡为“填报员（演示）”“审批员（演示）”。会话保存在内存；刷新要求重新选身份，但 IndexedDB 进度保留。`SessionService` 提供测试专用失效 fixture，覆盖 SESSION_EXPIRED，不必增加无需求的生产密码/短信登录。页面必须标“模拟身份，不代表真实授权”。

| 状态/角色 | 读取样板 | 编辑样板 | 选择待重置场景 | 确认重置 | 采购业务 |
| --- | --- | --- | --- | --- | --- |
| 未选择/已失效 | 身份选择页 | 拒绝 | 拒绝 | 拒绝 | 后续阶段 |
| 填报员（模拟） | 允许 | 允许 | 允许 | 允许（确认） | 后续阶段 |
| 审批员（模拟） | 允许 | 拒绝 | 允许 | 允许（确认） | 后续阶段 |

UI 与服务同时检查，但浏览器端检查只能改善演示一致性，不是安全边界。不存在服务端认证、真实凭据、生产权限保证。角色切换/退出不写样板或业务日志。

## 数据、持久化与恢复

统一 snapshot：`schemaVersion=1, scenario:'standard'|'returned', epoch:number, samples:[{id,name,sceneLabel,version,updatedAt}], operations:[{id,action,sampleId,actorRole,at,version,epoch}]`。样板稳定 ID 如 SAMPLE-001、SAMPLE-002；操作 ID 由浏览器支持的 UUID 生成，保证同一次操作不会写两条。UTC ISO 时间存储、Asia/Shanghai 显示并标明时区；时间是实际操作时间，seed 不伪造已执行历史。

标准 seed 两条样板，退回 seed 一条带“退回场景基础样板”标签；sceneLabel 只是工程演示标签，不能实现未确认审批状态机。模板深冻结、克隆为运行数据。第一次新存储初始化标准 seed、空日志；无论保存、重置都只在事务成功后发布一个新 snapshot。列表/详情/指标/日志均从它派生。

数据库 `procurement-demo-foundation`，object store `runtime` 保存单份 snapshot。保存检查身份、trim 后 1～80 字名称、ID 是否存在、expectedVersion/epoch 是否匹配；不匹配拒绝并提示刷新，不悄悄覆盖。更新样板 version 和一个操作记录在同一事务。session 禁止由客户端输入的 role 字段冒充，只从 SessionService 取得当前模拟身份。

重置选择不写存储；取消零写入。确认将 epoch 加一，原子替换所选 seed、清空旧运行日志并写一条 RESET；这是明确授权的演示数据重置，UI 提示会清空当前进度和日志。确认前冻结按钮防重复，旧 epoch 的保存不能覆盖新状态。

schema 不兼容、解析损坏、QuotaExceeded/事务失败不静默清空、不 fallback 成功；保留旧数据并显示诊断，成功读取才解除写禁用。恢复提供二次确认“重建虚构演示数据”，不会触及其他 origin / 浏览器数据。Goal 0 当前只有 v1，新版本迁移不得自行设计破坏性转换。单元故障注入 adapter，E2E 正常链路使用真实 IndexedDB，不能用 Mock 冒充持久化测试。

## 工程命令契约（拟定，Coder 须建立）

全部在目标目录执行；版本未知，先 `node --version` / `npm --version`，安装仅项目内，必须固定锁文件并记录实测 Node/npm/浏览器。核验后建立 `.cache/npm`、`.cache/playwright`、`.cache/tmp`；仅当前命令进程设置 NPM_CONFIG_CACHE、PLAYWRIGHT_BROWSERS_PATH、TMP/TEMP 为目标目录内这些绝对路径，避免依赖与浏览器缓存写全局位置。README 记录这些设置；.cache 加入 .gitignore。无付费依赖/云服务。依赖已有锁文件时 `npm ci`；首次创建 package 后 `npm install` 生成锁文件，然后必须实际执行 `npm ci` 复核。

| 命令 / 接口 | 前提 | 结果与失败规则 |
| --- | --- | --- |
| `npm ci` | 实现 package 与锁文件，开发机联网 | exit 0，锁文件不意外漂移；失败诊断，不全局安装 |
| `npm run dev -- --host 127.0.0.1 --port 4174 --strictPort` | 工程与依赖齐备 | 本地页面可用；端口占用停止，不强杀进程 |
| `npm run typecheck`、`npm run lint` | Coder 建立对应脚本 | exit 0；不得删除断言/忽略整块源码换绿灯 |
| `npm run build` | typecheck 完成 | exit 0，dist 资源只依赖本地 |
| `npm run test:unit -- --run` | Vitest 配置包含 tests/unit 与 tests/component，明确排除 tests/e2e；组件测试使用 jsdom/对应 setup | exit 0，覆盖校验、失败、取消、epoch、同源和组件焦点/错误态 |
| `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort` | 生产构建与端口空闲 | 可用生产构建；停止仅本任务创建的服务，不能 kill 未知进程 |
| `npm run test:e2e` | 手动生产 preview smoke 已完成且仅本任务 preview PID 已停止；由 Playwright webServer 自行启停 4173，reuseExistingServer:false | exit 0，两 viewport，非 loopback 请求失败且记录为外部依赖失败；不得与手动 preview 撞端口 |

浏览器安装如未准备：开发机执行项目本地 `npx playwright install chromium`，工具已在 package-lock 中；禁止现场运行安装或管理员命令。CI/E2E `reuseExistingServer:false`，避免用未知进程或旧构建。无法建立兼容工具链时记录阻塞，禁止无限尝试版本或悄悄换栈。

## 实施、验收、证据

按 plan T-A001～006 执行；T-A002 初始化配置与布局，T-A003 数据契约，T-A004 样板与身份链路，T-A005 分层测试，T-A006 整合证据/状态。测试清单与 AC 全映射见最终 prompt，不允许只留截图替代行为测试。

AC-A001/002：生产构建两视口，外域阻断；A003：模拟身份三状态 + 服务拒绝；A004/005：同源状态与真实 IndexedDB 刷新；A006：取消快照完全相同、确认原子恢复；A007：非法输入、存储失败、schema 问题；A008：场景选择无写、确认切换、epoch 竞争；A009：干净安装/构建/运行；A010：测试框架与报告；A011：证据索引、状态、原始截图；A012：边界审查。

`evidence/index.json` 必须记录 case/Goal、候选 Git HEAD（不存在写 null）、dirty、源码内容 SHA-256 清单（排除 node_modules/dist/evidence 临时输出）、实际命令/退出码、时区/工具/浏览器/viewport、AC 与证据路径、预期拒绝和意外错误分别统计。文件哈希与截图在同一候选代码上采集，修复后变更候选并更新证据关联，保留失败记录。

PROJECT_STATUS 保存阶段范围、基线、Task 恢复点、已完成/未运行/阻塞、两次/三轮预算和下一条动作；`docs/acceptance-goal0.md`逐 AC 记录实际结果。外部验收来源保持“未发生”。截图为原始 PNG，记录页面、操作、实际 viewport，不拼接伪造。

退出门槛：AC-A001～012 全部满足，命令实际运行，目标开发环境证据齐全，没有保护范围修改、Git 写入或完整业务实现。只标“Goal 0：已完成，待外部 Reviewer 验收”，停止；无管理员现场包装和目标设备实测仍留给 Release，不夸大 Goal 0 验证能力。

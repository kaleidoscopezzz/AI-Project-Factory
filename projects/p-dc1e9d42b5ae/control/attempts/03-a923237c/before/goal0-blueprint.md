# 离线图书借阅管理演示系统 Goal 0 工程骨架方案

## 1. 输入、类型与边界
依据计划 1.0。目录 C:\AI-Project-Factory\projects\p-dc1e9d42b5ae\workspace；工厂基线由用户提供，子工程无仓库。Windows 本机离线 DEMO，未测其他平台。Goal 0 是布局、读取样例与备注持久化样板；没有真实读者、借还事务或生产身份。Planner 未读取工程文件；既有内容由 Coder 局部只读核验后增量保留。

## 2. 技术决策
| 层 | 选型 | 理由与备选 | 本机/运行/发行依赖 | 版本确认/锁定方式 |
| --- | --- | --- | --- | --- |
| 整体方案 A，选用 | Node 原生 HTTP + 原生前端 + JSON 文件 | 同一语言，现有 Node 足够，零外部运行包；小规模单进程样板适用 | 开发/运行需 Node；发行包本轮不做 | 用户提供 26.3.0；实施时记录真实版本，package.json 标明环境，无依赖无需伪造锁文件 |
| 整体方案 B，未选 | Python 标准库 HTTP + sqlite3 + 原生前端 | 无外部包，事务/迁移更成熟，但当前小样板额外增加跨语言维护；SQLite 可用性须本机确认 | 开发/运行需 Python；发行未规划 | 用户提供 3.14.6；未运行 sqlite3 检查，不声称已可用 |
| UI | 原生 ES modules、CSS、本地资源 | 当前界面简单，不默认 Vue；以后增加模块再评估框架 | 浏览器运行，无 CDN/字体下载 | 记录浏览器实际版本及资源指纹 |
| 测试 | node:test、assert、只读 Playwright | 原生领域/集成测试及真实 UI 交互 | Playwright 是本机测试依赖，不复制、不修改、不作为运行依赖 | 从指定目录读取，记录包版本和浏览器是否实际可用 |

替换触发：需求变为多进程、多用户、真实事务或更大数据量时，单独评审 SQLite/服务端数据库；当前失败不得擅自换栈。无 npm install、无网络、无依赖升级。

## 3. 目录与模块契约
目录：package.json；scripts/build.mjs、test.mjs、serve.mjs；src/contracts/；src/server/；src/server/routes/；src/domain/；src/adapters/；src/web/；data/seed.json；tests/unit/、integration/、e2e/；dist/；var/demo/；validation/goal0/；README.zh-CN.md；PROJECT_STATUS.md。仅创建所需文件，不创建 Git 仓库。

依赖方向：web→HTTP契约；routes→domain→adapter；adapter 不依赖 UI。server 统一装配路由和存储。构建脚本确定性输出 dist，服务只提供 dist 静态资源，不以开发服务替代构建产物。UI 导航集中注册，Goal 1 在服务与页面模块增量接入。

拟由 Coder 实现 API：GET /api/health 返回 JSON，包含 status='ok'、project='offline-library-demo'；GET /api/books 返回记录和由同记录派生的 total/available/borrowed；PATCH /api/books/B-001/engineering-note 接收 note、revision、operationId；成功返回更新记录，非法输入 400、未知 ID 404、revision 冲突 409、存储失败 503。统一错误 {error:{code,message}}，不暴露本机路径或栈。重复 operationId 在样板生命周期内返回相同已提交结果，不再次写入；重复保护元数据随记录存储。GET /api/books?q= 支持修剪空白、书名/作者片段、不区分拉丁大小写。未知字段拒绝，不接受 status 更新。

## 4. UI 与交互
视觉建议：背景 #F5F7FA、面板 #FFFFFF、主文字 #172033、主色 #2457C5；间距 4/8/12/16/24/32px；正文 16px，标题 24px；控件至少 40px 高；焦点 2px 可见描边，状态不能只靠颜色。实测文字对比度目标 4.5:1。布局为顶部项目名/离线虚构演示标识、图书列表及搜索、同源数量摘要、独立“工程验证”备注区域。只有实际可用的图书列表导航，不设置虚假菜单。

目标视口：1440×900、390×844，属于本次设计建议。窄屏列表变卡片；页面无横向溢出。加载显示明确文本；空结果保留搜索并提供清空；错误提供可重试入口；提交禁用重复操作；保存需确认，取消不写；失败保留草稿及原记录。Tab 可到达搜索、清空、备注、保存、确认/取消，弹窗焦点恢复触发按钮。无图表、双主题或驾驶舱要求。

## 5. 身份和权限
角色×动作：演示访客可读取全部虚构图书、搜索、更新 B-001 工程备注；不可更新借阅状态，无真实借还 API。没有真实登录、过期令牌、账号初始化或凭据，因其不属于 DEMO；页面明确“虚构数据，无真实身份认证”。不宣称回环监听等于身份授权。

服务仅绑定 127.0.0.1；拒绝非回环监听配置；写 API 仅接受 application/json，拒绝不匹配本机服务 Origin 的浏览器请求，不提供宽泛 CORS。这是本地演示边界校验，不是生产认证。真实系统后续必须另设服务端认证授权，不能复用 DEMO 说明冒充安全实现。

## 6. 数据与生命周期
seed 三条虚构记录：B-001 工程书样例 available，B-002 文学书样例 borrowed，B-003 科普书样例 available；提供稳定 title、author、status、engineeringNote、revision。书名/作者最终文本由 Coder 固定并同步夹具，不声称真实馆藏。状态枚举 available/borrowed，在 Goal 0 只读；备注是唯一写操作。note 修剪后 1–120 Unicode 码点，revision 非负整数，operationId 非空且有长度上限。备注时间用 ISO UTC，界面按 Asia/Shanghai 显示并标注时区。

模板 data/seed.json 不可随操作改变，运行文件 var/demo/store.json 与其分离。schemaVersion=1；首次缺失文件才初始化；未知版本、损坏文件明确失败，不静默 fallback 或自动擦除。写入序列化、revision 检查、临时文件与替换封装由适配器统一承担；失败不报告成功、不更新 UI，旧记录保持。测试用独立夹具及适配器故障注入，不依赖改系统目录权限。已发送写入无法保证取消，故确认前可取消，提交后明确锁定到终态；迟到读取以请求序号避免覆盖新界面。无生产迁移/DB/事务命令，文件 schema 校验代替；没有用户一键 reset。隔离测试夹具可由测试脚本创建清理，范围必须是本轮新建的 workspace 内路径。

## 7. 工程运行契约
全部以下命令是 Coder 应创建并验证的接口，不是已经存在或运行成功。工作目录统一为 workspace。

1. node --version，读取实际版本；不安装工具。
2. node scripts/build.mjs：语法/资源检查，构建 dist，退出 0；失败记录日志，不继续运行旧构建。
3. node scripts/test.mjs：原生单元、真实文件适配器集成、服务及真实 Playwright 测试，内部隔离服务绑定 127.0.0.1、OS 分配端口；退出 0 才通过。启动条件缺失必须非零，不静默跳过 UI。
4. node scripts/serve.mjs --host 127.0.0.1 --port 4173：提供构建资源及 API；运行契约机器参数为独立 {port} 参数，由调用方替换。健康路径 /api/health，响应包含 offline-library-demo。正常服务持续运行，不要求立即退出；启动错误非零。

服务默认从 workspace 推导资源/运行数据路径；测试以专用环境变量 DEMO_DATA_DIR 指定 workspace 内隔离夹具，检查解析后路径边界；无秘密环境变量。端口占用报告并退出，不强杀。停止用 Ctrl+C，测试只关闭自身子进程。检查单次超时 180 秒；超时记录未通过。无外部依赖锁文件；若后续确需依赖，必须新的授权与离线来源评估。

## 8. 实施与验收矩阵
| 顺序/Task | 输入与依赖 | 可写范围 | 产物 | AC-ID 与验证步骤 | 证据 |
| --- | --- | --- | --- | --- | --- |
| T-001 | 计划/方案 | package.json、scripts、contracts、server | 构建与启动契约 | AC-001：构建→启动→健康/静态资源 | build.log、runtime.log |
| T-002 | T-001 契约 | domain、adapters、routes、seed、integration | 文件持久化样板 | AC-006～009：保存/取消/重复/失败/重启 | integration.log、API断言、隔离文件哈希 |
| T-003 | T-002 API | web、unit | UI 及读链路 | AC-002～005、011：列表/状态/搜索/键盘/演示边界 | 浏览器断言与截图 |
| T-004 | T-003 固定候选 | e2e、validation/goal0 | 离线与全量真实测试 | AC-010；汇总全部 AC | test.log、trace、PNG、请求清单 |
| T-005 | T-004 实际结果 | 状态、说明、validation/goal0 | 可审查报告 | AC-012：逐 AC 核对 | acceptance.md、manifest.json |

## 9. 状态和证据
按提供的 project-status/acceptance-record 模板保存：阶段、恢复点、真实环境、候选源码 SHA-256 清单、基线来源、任务写集、实际命令/时间/退出码/数量、失败修复预算、限制和下一步。无仓库所以 Git HEAD/branch/dirty 写“不适用：子工程无仓库”，不虚构干净提交；内容指纹排除运行数据、构建产物及证据并列出排除项。

validation/goal0/ 下保存 acceptance.md、manifest.json、日志、两视口原始 PNG、Playwright trace、截图索引与请求记录。截图包含页面、实际视口、动作和候选指纹，不代替行为断言。外部 Reviewer 身份/通知/时间/结论均写“未发生”。不访问参考项目，因此仅报告本轮未访问、未执行相关写操作，不声称做过其哈希复核。

## 10. 完整退出门槛
零新增依赖的工具核验→构建→生产资源运行→纵向 UI/API/文件样板→正常/取消/错误/重复→刷新/重启→两视口/键盘→外域阻断→证据与状态。所有 12 项 AC 通过才标记“Goal 0：已完成，待外部 Reviewer 验收”。浏览器缺失、失败、证据缺失或超预算是阻塞，不能以抓取 HTML 代替。允许的已知限制仅为纯虚构演示、JSON 小规模单进程、未测其他 OS、不提供发行包；其他警告据实列出。随后停止，未执行 Git、冻结、发布或下一 Goal。

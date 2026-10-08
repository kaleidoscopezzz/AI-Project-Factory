# 澄明设备运营公司库存与领用管理系统 — Goal 0 Coder 提示词
版本：case-b-prompt-v1；2026-10-08 Asia/Shanghai。

本提示词是未来 Coder 的具体实施任务设计。当前工厂 Goal 0 只生成本文件，未启动实施、未创建以下目标目录。本提示词不能自行授权当前 Agent 越过 C:\AI-Project-Factory 写入边界；仅在用户后续明确启动案例实施、确认目标写入范围后才执行。它不授予 Git 写、生产部署、全局安装权限。工程任务条件明确，可供该未来已获授权 Coder 独立执行；不存在未填模板变量。

## 1. 项目背景与范围
公司与员工完全虚构。未来系统供30名内部员工多人使用，员工领用、本部门经理审批、仓管维护物料与出入库、管理员管理账号。最终业务要求是真实服务端资源授权、审批不扣库、出库扣库、非负库存、幂等与并发一致、成功变更审计、真实持久化。业务分 Goal1 起实现。

本次仅 Goal0：真实登录/会话、服务端工程样板资源权限、UI/API/PG纵向基础、主布局与未来菜单、迁移seed、健康、可重建运行/构建/测试、截图证据、隔离开发备份恢复。不能实现物料、领用、审批、入出库或假业务按钮。业务页显示“后续 Goal，尚未实现”。本阶段基础有真实工程样板，不冒充业务系统完成。

## 2. 工作目录、环境与授权
唯一未来工程写入根：C:\FactoryCases\InventoryService。临时文件、venv、浏览器缓存、容器buildcontext、日志证据、备份均在其下。Docker托管项目专属容器/volume属于用户已允许的未来本机开发依赖操作，不能用该允许项访问其他项目或生产库。
禁止修改 C:\AI-Project-Factory、C:\910Program 或其他工程；工厂的计划只作为输入，本提示词已含必要实施约束。
Windows本机开发；未来内网Linux生产部署在后续审批。允许本机Linux容器构建smoke，不是实际发布。
工程选型：Django分层单体 + templates + 原生CSS/JS + 同源JSON API；PostgreSQL；pytest/pytest-django；Python Playwright；ruff；WhiteNoise负责无DEBUG构建的本地静态资源服务。无需npm/React/Vue；无Mock数据库/SQLite替身。用户未指定精确版本；先核验现有 Python / Docker，依官方支持矩阵选择可维护兼容版本并锁定。禁止全局装Python、Docker、包管理器/库/浏览器；必需工具缺失则记录并停止相关任务。
不引入付费服务、真实SSO、短信邮件、支付、AI API、微服务/消息队列。网络依赖解析须局限项目依赖，运行资源均本地，不从CDN载字体/脚本。

## 3. 基线先核验，不覆盖未知工程
当前目录存在性、Git/HEAD/工具版本均未核实，baseline.kind=unverified_target、head=null、verification_required=true；不得捏造 Commit、冻结Tag、既有测试结果。
先用 Test-Path / Get-ChildItem -LiteralPath 只读确认目标。存在目录时检查其AGENTS.md/PROJECT_STATUS及未知文件；有既有工程、用户变更或指令冲突，停止修改并报告，禁止当“新项目”覆盖。目录不存在时，在后续已获目标写入授权前提下创建；根目录必须解析为 C:\FactoryCases\InventoryService，所有文件写入前验证解析路径属于该根，拒绝symlink/junction越界。
若存在 .git，仅运行 git --no-optional-locks -C C:\FactoryCases\InventoryService status --porcelain=v1、rev-parse HEAD、log -1；禁止所有Git写操作及Git init。没有.git如实记录“无仓库，无HEAD”。非提交候选用排除秘密的源码SHA256清单作为指纹。
docs/baseline.md 记录实际目录、系统、工具版本、现有文件/dirty、写权限、未测目标环境。创建文档不是证明已运行。

## 4. Goal0验收范围
以下12项全部必须真实验证，任何必需项未运行/失败则不能标完成：
- AC-B01：专属venv/PG空环境→锁定安装/迁移/静态构建/Linux容器smoke/启动→退出0且8000可达；无全局安装，标明Linux真机未测。
- AC-B02：两个指定视口→登录/菜单/工程样板弹窗确认与取消/键盘→布局无整页横溢或遮挡、焦点可见、取消无POST和DB/审计变化。
- AC-B03：正确/错误/禁用账号、退出、过期→真实会话成功或明确拒绝，未认证API401；密码hash且日志无凭据。
- AC-B04：按下文样板角色矩阵直接读列表/详情、伪造owner/department→服务端只给授权数据，资源越权403或404且不泄露存在性，非法owner/department字段400或403，无数据/审计新增。
- AC-B05：UI新建并读详情→PG生成唯一UUID和一条成功审计；空label400无写；同owner/request_id同payload重放200同记录且无二次审计；不同payload409；相同键并发只一次写入。
- AC-B06：刷新、关闭浏览器重登录、重启应用/DB→同UUID、label保留；超时按同request_id安全查读/重试，不能造成功。
- AC-B07：迁移/seed各两次→表/账号/样板不重复且不覆盖手工记录；错误env/库名的reset拒绝且无破坏。
- AC-B08：正常/停本项目DB/停本项目API→live200；ready正常200、DB不可用503；UI/API可读故障；恢复读原记录，无Mock/fallback。
- AC-B09：静态/单元/真PG集成/真实用户UI/无DEBUG构建smoke→必需测试全部通过，无删测/禁用断言/跳过；预期拒绝和意外错误区分。
- AC-B10：证据与状态有实际候选指纹/环境/命令/结果/视口/AC映射；外部结论未发生，保留失败历史；无Git写/部署/全局安装。
- AC-B11：专属dev DB dump→另一专属restore库→UUID/label/账号关联/审计计数一致；原库不被覆盖，禁止生产地址。
- AC-B12：缺/伪造CSRF拒绝403且DB不变；合法令牌成功；会话HttpOnly/SameSite=Lax，非dev HTTPS使用Secure；浏览器不持久化密码/token。

这些是基础阶段AC。库存竞争、不负库等业务AC将在Goal3验收，不能在Goal0假称已执行库存测试。

## 5. 实施顺序、写集和契约
| Task | 前置 | 修改入口 | 操作 / 数据影响 | 关联AC |
| --- | --- | --- | --- | --- |
| T-B00 | 后续案例启动授权、目标安全 | docs/baseline.md、README.md | 实测基线工具；冻结目录/API/model/环境约定；不覆盖未知工程 | 01 |
| T-B01 | T-B00 | 根配置、config/、compose.yaml、Dockerfile、requirements*.txt、manage.py、scripts/、accounts/common/sample的models.py、apps.py、包初始化、全部migrations/及seed管理命令 | 专属venv与PG、精确哈希锁、先建立模型和app装配再迁移/seed、运行脚本；幂等不擦用户数据；模型与迁移由整合者独占 | 01,07 |
| T-B02 | T-B01 | accounts/、common/、sample/的services/api/views/权限错误审计辅助、health/；排除models/apps/迁移/seed管理命令/模板静态 | service/API身份资源校验、sample/audit原子写、错误/健康；按已冻结模型使用真实DB唯一键；模型改动交T-B01整合 | 03,04,05,06,08,12 |
| T-B03 | T-B01且契约已定 | templates/、static/ | 登录布局菜单、样板列表/新增/取消/失败态；调用真实API，不另造store | 02,05 |
| T-B04 | T-B02,T-B03固定候选 | tests/、validation/goal0/新轮次、backups/、.cache/（命令运行产物，非实现源码） | 真PG/API/UI测试、重启故障、开发备份恢复、buildsmoke；保留失败与DB对照；只允许专属dev/test/restore库操作 | 01…09,11,12 |
| T-B05 | T-B04 | PROJECT_STATUS.md、docs/acceptance-goal0.md、validation/goal0/manifest.json | 实测AC表、指纹、环境与恢复点，外部结论写未发生 | 10 |
| T-B06 | T-B05 | validation/goal0/review.md | 独立核对全AC与证据，不改实现；问题返工后用新候选重新测 | 01…12 |

同一Coder可顺序完成T-B00…05的实现和自测；T-B06须由后续独立Reviewer只读执行。未提供独立Reviewer时不得伪称独立结论，Coder完成自测即停待外部验收，不依赖自动调度或自行扮演独立Reviewer。未来多个Agent并行只限T-B02/T-B03写集互斥且契约已冻结。config/urls.py、锁文件、compose、模型与迁移、状态必须由一名整合者独占；任何契约变动先登记再整合，禁止互相覆盖。
目录为 accounts（身份），common（错误、权限、审计基础），sample（工程样板），health（健康），templates/static（UI），tests（单元/集成/e2e）。后续inventory/requisitions经根urls增量注册，不能复制/重建认证、状态和布局。

## 6. 页面与交互
主框架侧栏208px、页头56px；背景#F5F7FA、正文#172B4D、主色#1D4ED8、错误#B91C1C；中文系统字体，正文14px/行高1.5、标题22px，间距4/8/12/16/24px；焦点描边2px。实现核对对比度。目标1440×900与1280×720，不照搬任何参考项目行业或可视化图表。

登录表单username/password；失败给“账号或密码错误”一类统一提示不暴露是否存在；禁止真实凭据出现日志/证据。登录后页头显示用户、部门、角色，退出真实删除会话。
菜单为物料台账/领用申请/经理审批/库存处理/审计/账号管理/工程验证。按未来角色可解释隐藏或禁用，业务页一律明确“后续Goal，尚未实现”，不能假查询/假提交。账号管理入口仅管理员显示，但后续服务端授权仍必需。
工程验证仅dev/test/smoke开放，真实列表/count同一个权限查询；展示UUID、label、owner、部门与北京时间。新建label去空白1…100字符，客户端生成UUID request_id仅用于幂等而非决定owner/department。
新增弹窗确认前不写；取消/Escape关闭并恢复触发焦点，DB和成功审计计数不变；提交时loading/禁用重复确认；成功查询返回数据同步列表/count/详情。失败保留输入并显示可读错误，不提前乐观宣布成功。关闭UI等待不证明服务端回滚，响应丢失时保留同request_id供查回/安全重试。
空列表、正在加载、网络不可达、DB不可用、权限拒绝、会话过期都有显式态；Tab顺序、Enter确认、弹窗焦点约束与两个视口截图/交互实测。表格可局部滚动，整页无横溢，提交/取消不被遮挡。

## 7. 真实身份与资源权限
本地开发账号作为本次工程假设；生产SSO未定不接入。使用Django服务端数据库session、password hash、CSRF middleware。每个工程API自定义返回JSON401而非默认HTML302；HTML页面未登录跳登录。Django默认model permissions不能替代对象权限，必须在service/query/detail层实现下列检查：
- employee_a 属A、employee_b属B；employee只读本人样板。
- keeper_a属A；仓管在工程样板只读本人，不能推导其业务库权限。
- manager_a属A；经理可读本部门样板。
- admin_dev 工程管理员可读所有工程样板；此样板规则不授予正式领用跨部门访问。
- 所有人可创建本人样板，owner/department由请求会话服务端赋值，客户端提交这些字段直接400 INVALID_FIELD或403，无写。
- 跨权限详情返回404，列表不含越权UUID/count；没有写入/成功审计，日志仅脱敏诊断。
seed 两部门和上述5个虚构账号。密码从项目.env DEV_SEED_PASSWORD注入，只dev/test seed，重复seed不改已有密码和手工记录；管理员不是隐含superuser，不给生产账户。
会话默认开发30分钟是可撤销工程参数，不是生产策略；测试用可控过期配置/时钟验证401。禁用账号亦拒绝旧会话。cookie HttpOnly=true、SameSite=Lax；dev loopback HTTP Secure=false且明确记录，未来HTTPS非dev配置Secure=true。禁止将密码/session token存localStorage。
CSRF验证先于API view。匿名401测试须先取得合法CSRF令牌（无登录session）；故意缺/伪造CSRF的POST预期403而不是401。GET匿名401。HTML POST /auth/login/成功302到主框架，错误200表单统一报错；POST /auth/logout/合法CSRF后302登录，随后GET /api/session必须401。不要因Django中间件顺序把不同预期错误混成“所有请求200”。
数据库session后端断连时登录/权限查询返回503 DB_UNAVAILABLE，不能将依赖故障伪装成匿名401或成功。

## 8. 数据、API与事务
模型：
Department(UUID,name唯一)；User/profile(department FK,role,is_active)；
SampleRecord(UUID,label,owner FK,department FK,request_id UUID,created_at)；
AuditEvent(UUID,actor FK,action,resource_id,request_id,created_at,脱敏summary)。
unique(owner,request_id)。created_at服务端UTC aware，UI显示Asia/Shanghai。owner/department字段不可来自客户端；本阶段无删账号、审批或库存状态机。

接口必须建立：
- GET /api/session：200 user/department/role或401。
- POST /auth/login/、POST /auth/logout/：上述HTML会话流程。
- GET /api/engineering/records：列表、同过滤count；支持按本人request_id查询已提交记录。
- POST /api/engineering/records：label、request_id；首次201；同键同规范label200返回同UUID；不同label409 IDEMPOTENCY_CONFLICT；非法400；未登录401（合法CSRF条件）；CSRF403；DB故障503。
- GET /api/engineering/records/{uuid}：权限过滤200/404，匿名401。
- GET /health/live：进程健康200，DB断开仍200。
- GET /health/ready：实际SELECT1与待应用迁移检查；健康200，DB故障503；不返回连接密钥。设置有限连接超时，工程测试阈值建议3秒DB连接、5秒HTTP返回，超时测试记录实际值，不作为生产SLA。
统一JSON错误结构 error.code/error.message/error.request_id，禁止stacktrace和秘密。工程路由和API生产默认关闭404；只有dev/test/smoke显式启用，后续业务不复用工程开关当业务功能。

用transaction.atomic创建SampleRecord与AuditEvent，审计失败回滚记录；注入异常只允许测试代码，不能暴露故障API。数据库唯一约束处理并发同键；IntegrityError处理放在失败atomic作用域外，再安全读取已提交记录，不在破坏事务里继续查询。两个同时同键请求与重放必须只有一条样板与一条成功审计。不得用进程内字典假装数据库幂等。
本次无Mock/fallback，无SQLite测试替代；API/DB失败保留原数据和输入，禁止缓存库存“继续成功”。

## 9. 配置、迁移、seed与隔离恢复
.env.example只列说明，不放真实密码。必需 APP_ENV、DJANGO_SECRET_KEY、DB_HOST、DB_PORT、DB_NAME、DB_USER、DB_PASSWORD、DEV_SEED_PASSWORD；缺值启动失败给可读错误。秘密只在项目.env，.gitignore覆盖.env、venv、cache、backups和敏感dump，日志脱敏。
本机PG loopback，compose项目 factory-case-b，库名固定 inventory_factory_case_b_dev；隔离测试库 test_inventory_factory_case_b；恢复库 inventory_factory_case_b_restore；项目专属volume。
脚本校验env dev/test、host loopback或自己项目db服务、库名allowlist、容器项目标签；任何不匹配先拒绝。测试仅授权专属test库，不能复用其他库或生产地址。
migrate两次无新增；makemigrations --check --dry-run为0；seed两次数量不增加、手工样板保留。不默认down -v，不删历史迁移、不擦数据修测试。
不提供前端一键清空。可提供显式dev/test reset命令，但env/库/项目标签及精确confirmation全部匹配才执行；测试必须覆盖错环境/错库拒绝，默认不开执行且不触及dev实际数据。非dev/test和所有生产环境拒绝。
开发备份pg_dump dev到项目backups，恢复到独立restore库，恢复前只创建/确认该库，不能覆盖原库；核对UUID、label、账号关系和成功审计计数。比对输出脱敏记录，不公开dump。生产备份周期、RPO/RTO、容量、真实部署凭据未定，列待确认只阻塞后续Release，不阻塞当前隔离验证。

## 10. 工程命令与测试执行
下面全是你须创建并执行的运行接口，不是当前已有或已运行结果。工作目录均为 C:\FactoryCases\InventoryService。脚本用项目.venv\Scripts\python.exe，不依赖全局包。成功退出码0；必要检查/测试失败非0，不能吞错。

1. 只读核验 py --version、docker version / docker compose version、目标目录与Git；记录实际。工具缺失不擅自装全局。
2. 建 scripts/bootstrap.ps1：检查项目边界→创建项目.cache/pip、.cache/tmp、.cache/ms-playwright；仅对当前脚本及其子进程设置PIP_CACHE_DIR为.cache/pip、TMP/TEMP为.cache/tmp、PLAYWRIGHT_BROWSERS_PATH为.cache/ms-playwright，不用setx或写系统环境；venv/锁定安装/浏览器/测试都继承这些值，脚本退出恢复本进程先前值→用已有Python创建.venv→选择支持版本、在venv中生成requirements runtime/dev精确版本+哈希锁→安装pip --require-hashes→生成/校验项目.env（用户提供或项目生成安全随机开发秘密，不打印）→启动本项目PG→migrate→seed。首次生成锁记录解析依据，第二次按锁重建验证。bootstrap重复不删除卷/记录。不得静默下载/修改全局工具。若工具仍需写未授权路径，停止该动作报告；Docker仅项目专属容器/volume/build缓存为已声明托管例外，不允许其他项目卷。README必须逐项解释运行依赖、这些环境目录/进程作用域、Docker例外、启动/停止/重建/测试/备份与失败恢复；dev/verify/backup脚本同样继承/设置项目缓存与临时目录，不依赖bootstrap进程已退出后的环境。
3. 环境验收命令：
   .venv\Scripts\python.exe -m ruff check .
   .venv\Scripts\python.exe manage.py check
   .venv\Scripts\python.exe manage.py makemigrations --check --dry-run
   .venv\Scripts\python.exe manage.py collectstatic --noinput
   docker compose build app
   docker compose --profile smoke up -d app
   smoke app在127.0.0.1:8001，Linux容器内gunicorn、DEBUG=false；dev在8000，避免冲突。runtime依赖锁定WhiteNoise，配置WhiteNoiseMiddleware紧跟SecurityMiddleware，STATIC_ROOT为项目staticfiles，staticfiles storage使用CompressedManifestStaticFilesStorage；模板用static tag，镜像构建中collectstatic，WhiteNoise实际提供收集资源，验证CSS/JS 200及页面样式。不能假设gunicorn或collectstatic本身提供静态HTTP服务；不接CDN。此容器仅本机工程smoke，指向项目dev库，不是公司内网上线。生产关闭sample与正式TLS策略单独配置核对，不能对本机HTTP强行开启Secure导致登录“假通过”。
4. 建 scripts/dev.ps1 start/stop：start只本机8000，记录启动PID；占用端口先查报，不强杀未知进程；stop仅自身PID。服务日志留当前轮次。compose stop保留卷，只停止本项目。
5. 锁定pytest、pytest-django、Playwright与ruff。设置PLAYWRIGHT_BROWSERS_PATH为本项目.cache/ms-playwright，再 .venv\Scripts\python.exe -m playwright install chromium；不得全局安装/改PATH。本机浏览器所需环境缺失则停止相关验证并报告。
6. 建 scripts/verify.ps1 -Round round-001，依次：
   - 单元：输入规范化、权限判定、错误映射；pytest tests/unit。
   - 集成：pytest tests/integration，在真实专属PG，认证/session/CSRF/直接越权/迁移seed/unique重放并发/事务注入回滚；Junit文件与数据库非秘密计数核验。并发用独立连接/事务，不能Django TestCase包裹掩盖提交或用Mock DB。
   - UI：pytest tests/e2e，通过UI真实登录→新建→取消→失败→读取，两个视口；不能直接操作store替代路径。用独立test库和自己启动的测试服务，不污染dev库。
   - 持久化：独立受控dev样板fixture，UI写入并保存UUID→刷新→关闭浏览器重登录→仅重启本项目应用→仅重启本项目PG→读取同UUID；保留卷。记录关闭与重启前后值。
   - 故障：只暂停本项目db，保存原UUID/计数；断连ready503/live200、API503、UI错误；恢复原db后读回，确认无假写；暂停本项目app，UI连接失败后恢复。finally恢复自己暂停的服务，禁止为测试强杀其他进程。会话读取DB故障同样503。
   - 备份：scripts/backup-restore.ps1 -Environment dev，allowlist校验→dump→隔离restore→比对；日志不输出密码。失败不覆盖原库或自动清库。
   - Linux构建smoke：8001真实登录、sample写读与静态可达；DEBUG=false无意外traceback。记录Linux容器实测与内网Linux真机未测。
   所有必需测试通过且非跳过才exit0；实际测试数由运行报告填写，不预设数量。若首次手工持久化需人工配合，脚本明确步骤与证据，未执行不能算通过。
7. repeat bootstrap / migrate / seed幂等以及按锁干净初始化；仅操作明确隔离的副本/专属容器，不删除已有dev库为制造“干净”。
8. 停止自己启动服务，保留PG volume和全部证据。

默认轮次 round-001，重测用round-002/003不覆盖。pytest报告、stdout/stderr、退出码写 validation/goal0/round-00N/。预期错误白名单：400输入、401匿名/过期、403CSRF/拒绝、404资源隐藏/工程生产关闭、409幂等冲突、503受控故障；须标触发步骤，其他意外HTTP/console错误归零或列阻塞，不能“因为有403所以测试失败”也不能屏蔽所有错误。
Linux真机/生产容量/正式身份不在Goal0实测，限制如实列出。

## 11. 截图、证据与状态文件
每个实际视口1440×900和1280×720至少采集login、shell、sample-list、sample-create、permission-rejected、db-unavailable，另留取消/键盘/恢复trace。PNG不裁剪伪造；测试用户名可显示，密码token不可截图。拒绝页可通过无权详情触发，不能造“通过”横幅当结果。
证据需绑定AC-B01…12，并包含：
- 真实目录/HEAD或null、源码SHA256清单和总指纹，排除.env/密钥/dump/venv/cache/证据自身以免循环。
- 系统/工具/PG镜像digest/浏览器实际版本、时间与Asia/Shanghai时区、viewport、步骤、预期/实际、命令/退出码/测试计数。
- API请求/响应脱敏记录、DB UUID/数量/关系断言、重启前后对照、恢复校验、失败历史、新候选指纹、证据相对路径。
- docs/acceptance-goal0.md按R/AC列实际通过/失败/未运行，manifest.json机器索引；screenshots与trace是辅助，权限/事务由API/DB验证。
- PROJECT_STATUS.md写阶段、自测/待验收状态、当前任务/写集/依赖、实际环境基线、输入版本、失败次数、剩余预算、下一恢复动作、保护范围、未测平台、业务歧义。外部验收“未发生”，不能自填已验收冻结。
对受保护范围只读核对，若发现越界立刻停止相关操作报告；不能为记录核对触发其构建/安装/测试。证据留在未来工程，不写回工厂项目或参考目录。

## 12. 完成标准与有限返工
所有AC-B01…12均有通过的实际证据；锁和迁移可重建；UI/API/真实PG完整；禁用/退出/过期/CSRF/资源越权正确；重复/并发样板不二次写/审计；取消无写、失败无假成功；刷新/应用/DB重启持久；隔离dump恢复不覆盖其他库；两个视口真实检查；静态/测试/构建/运行无阻塞；证据/状态与实际一致且无越界。

同一问题最多2次有针对性修复，整体最多3轮验证。记录问题ID、根因、修复文件、失败日志、尝试次数及新指纹；达到限制即停止受影响链路，不不断重装/换栈。任何必需AC失败/未运行不可标完成。
需求歧义、缺工具/权限、未知旧工程、路径越界、其他库/生产风险、未知端口进程、破坏数据风险出现时停止相关动作并说明可继续部分；不能覆盖/reset/强杀/假造结果。无需每次正常已授权修复都询问，但新增业务/付费/外部副作用必须待用户决定。
生产身份/代理/跨部门/备份容量问题只阻塞相应后续业务候选或Release，不能擅自实现。审批业务未开发、生产未测均是范围限制，不是Goal0必需AC可随意豁免的借口。

## 13. 修改与禁止操作
允许未来已授权时：目标根下本阶段工程、必需测试、文档证据、项目venv/缓存；项目专属容器/dev/test/restore库。
禁止：目标外文件/参考项目/工厂目录，案例业务，真实身份服务、秘密外传、生产数据库、其他项目卷/库、全局安装与系统配置、实际部署。
所有Git写禁止：init/add/commit/tag/push/branch/switch/reset/restore/clean及其他改变引用/索引/工作区操作。只读检查加--no-optional-locks；没有仓库不能自行init。冻结/发布需后续明确授权，不从本提示词产生权限。
禁止删测/禁用断言、替换真实PG为Mock/SQLite/localStorage、伪造命令/截图/测试数量、用旧证据匹配新候选、为了“测试过”清空数据、跳下阶段。

## 14. 最终报告顺序
1. Goal0状态与实际完成范围；未过门槛写阻塞，不能完成。
2. 实际目录/工具/栈/基线/指纹及变更文件。
3. R-B001…007与AC-B01…12逐项实施/测试/证据，业务AC说明后续未运行。
4. 实际命令、退出码、测试计数、失败/跳过/未运行原因；预期错误与意外错误。
5. 两视口截图/trace、API/DB/备份恢复日志、验收/manifest路径。
6. 受保护范围核对、实际Git状态；实际Git写/部署/全局安装均如实报告。
7. 已知限制、生产SSO/代办代理/备份容量问题，Linux内网真机未测。
8. PROJECT_STATUS恢复点、重试预算与下一Goal建议，外部验收未发生。

## 15. 达标后停止
只有上述全部自测门槛满足，写“Goal 0：已完成，待外部 Reviewer 验收”。完成后停止。不得自行验收通过、Git提交/Tag/冻结、发布、继续Goal1。本设计包本轮只作技能文档行为验证，不报告这些工程测试已通过。

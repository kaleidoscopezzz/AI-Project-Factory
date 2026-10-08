# 案例 B Goal 0 工程骨架方案
版本：case-b-blueprint-v1；2026-10-08 Asia/Shanghai。输入：input.md、plan.md。
这是 goal0-scaffolder 产出的工程方案；所有命令和测试为未来 Coder 必须建立的接口，本轮未运行。

## 1. 类型与阶段
真实多人企业 Web；30 人，Windows 开发、未来 Linux 内网部署。未来目录 C:\FactoryCases\InventoryService 未核实，本轮未创建。
Goal 0：登录→服务端会话→工程样板新建→JSON API→事务写 PG / 审计→读取→刷新重启；构建、隔离测试和证据可重建。
不做：物料、入库、申请、审批、出库、正式审计业务页、管理账号业务页、生产发布。菜单保留增量入口并明确后续 Goal。

## 2. 技术选择与替换条件
| 层 | 选择与理由 | 可行备选 / 为什么暂不选 | 依赖与锁定 |
| --- | --- | --- | --- |
| UI/API | Django 分层单体，templates + 原生 CSS/JS；同源 session/CSRF，JSON API 通过同一 service，30人业务无需双工程 | React + FastAPI + PostgreSQL：交互更复杂时适合，但独立鉴权/API/UI构建与维护负担更高 | 本机 Python；项目 venv；requirements.txt/runtime、requirements-dev.txt/dev，依赖精确版本和哈希；不预称已安装 |
| DB | PostgreSQL 真事务与约束，项目专属容器，持久化 volume | SQLite 不能用作本案例权威库或并发测试替身 | 本机 Docker Desktop 或已有兼容 Docker 运行时；Linux PostgreSQL 镜像；实现时确定维护版本并锁 digest，不能用 latest |
| 测试 | pytest + pytest-django、真实 PG、Python Playwright、ruff | 单靠 Mock/截图不覆盖权限/事务/重启 | dev 锁含测试与浏览器工具；浏览器二进制路径仅项目 .cache/ms-playwright，安装不改全局 |
| 运行 | 本机开发 runserver；构建 smoke 用 Linux 容器内 gunicorn + WhiteNoise + collectstatic | Windows 便携离线包不适合真实多人系统 | Dockerfile 锁基础镜像；gunicorn/WhiteNoise进入runtime锁；生产反向代理/TLS后续审批，不自行部署 |

实现时检查 Python/Django/psycopg 支持矩阵，选可维护兼容组合并记录官方依据、实际版本与锁文件。不能为了版本未知无限安装或改栈。此处使用 Django 5.2 官方文档作为设计依据，不指定未来必须使用该版本，也不声称这是当前最新版本。smoke确定使用WhiteNoise：middleware紧跟SecurityMiddleware，STATIC_ROOT=项目staticfiles，CompressedManifestStaticFilesStorage，模板static tag，镜像collectstatic后实测CSS/JS HTTP200与样式；gunicorn和collectstatic本身不承担静态HTTP服务。[WhiteNoise官方Django配置](https://whitenoise.readthedocs.io/en/stable/django.html)支撑此方案，不使用CDN。

[Django transaction.atomic 官方文档](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)支持事务边界设计；[Django 认证文档](https://docs.djangoproject.com/en/5.2/topics/auth/default/)与[CSRF 文档](https://docs.djangoproject.com/en/5.2/howto/csrf/)支持同源会话方案；[PostgreSQL SQL Dump 文档](https://www.postgresql.org/docs/current/backup-dump.html)支持隔离 dump/restore 方案。版本、目标机和性能仍需实现阶段核实。

## 3. 目录与单一装配者
未来拟建目录：
```text
InventoryService/
  manage.py, pyproject.toml, requirements.txt, requirements-dev.txt
  compose.yaml, Dockerfile, .env.example, .gitignore, README.md
  config/{settings/{base,dev,test,smoke}.py,urls.py,wsgi.py}
  accounts/{models.py,services.py,api.py,views.py,migrations/}
  common/{errors.py,permissions.py,audit.py,models.py,migrations/}
  sample/{models.py,services.py,api.py,views.py,migrations/}
  health/{views.py,urls.py}
  templates/{base.html,accounts/,sample/,future.html}
  static/{css/tokens.css,css/app.css,js/sample.js}
  tests/{unit/,integration/,e2e/,conftest.py}
  scripts/{bootstrap.ps1,dev.ps1,verify.ps1,backup-restore.ps1}
  docs/{baseline.md,contracts.md,acceptance-goal0.md,operations-dev.md}
  validation/goal0/{round-001/,manifest.json,review.md}
  PROJECT_STATUS.md
```
config 根配置、urls 装配、compose、依赖锁、全部 models/apps/包初始化/migration/seed管理命令、状态文件由整合者独占。T-B01必须先建accounts/common/sample模型骨架与app装配，再迁移seed；T-B02只能实现service/API/view/权限错误审计辅助，排除模型/迁移/seed，模型变更回整合者处理。service 不依赖 template；view/API 共享 service、权限和 errors；DB 模型不读浏览器 store。
未来 inventory、requisitions 模块经 config/urls.py 单点注册，复用 accounts、common.audit、transaction service 与 base.html。新迁移增量，不能删重建 Goal 0 表。

## 4. UI、导航与可观察状态
视觉工程假设：背景 #F5F7FA，正文 #172B4D，主色 #1D4ED8，错误 #B91C1C；中文系统字体；正文14px、页标题22px、行高1.5；间距4/8/12/16/24px；侧栏208px、页头56px；焦点2px可见描边。实现时核对文字/控件对比度，不照搬行业主题。
菜单：物料台账（Goal1）、领用申请（Goal2）、经理审批（Goal2）、库存处理（Goal3）、审计（Goal3）、账号管理（Goal1管理员）、工程验证（Goal0 dev/test/smoke可见）。未来页统一“尚未实现 / 计划阶段”，无假数据、假成功或启用业务提交按钮。
登录页 username/password，失败提示不区分账号存在性；主框架显示用户名、部门、角色、退出。
工程验证页真实列表、条数同源、UUID/label/owner/department/time、新增弹窗。label 去空白1…100字符；确认期间禁用重提；取消不发送POST；成功读回更新列表，失败保留输入并显示错误，可安全重试同 request_id。空、加载、网络错、DB错、401会话过期和403无权均有可读态。
目标视口 1440×900、1280×720；菜单和提交/取消无需滚动到隐藏区域，文本长项换行。表格可以局部滚动但整页无横向溢出。Tab 顺序、Enter提交、Escape取消、弹窗焦点约束与恢复需实测；不要求无来源的驾驶舱/图表/双主题。

## 5. 身份权限与初始化
开发 seed 建两个虚构部门 A/B；员工 employee_a/employee_b、经理 manager_a、仓管 keeper_a、管理员 admin_dev 五账号。密码仅从本机项目 .env 的 DEV_SEED_PASSWORD 注入，hash 存库，禁止日志和截图显示；seed 只限 dev/test，不使用真实账号、默认生产口令或创建隐含超级管理员。
| 角色 | 工程样板创建 | 样板读取 | 未来业务 |
| --- | --- | --- | --- |
| 员工 / 仓管 | 自己，department 从服务端身份派生 | 自己 | 后续根据明确需求，不由样板推导跨部门权限 |
| 经理 | 自己 | 本部门 | Goal2本部门审批 |
| 系统管理员 | 自己 | 全部工程样板 | Goal1管理账号，不等于跨部门领用查看已获授权 |

列表过滤与详情检查都在服务端；伪造 owner/department字段400或403且无写入，不“先相信客户端再隐藏”。匿名API401、跨部门404不泄露资源、CSRF403；HTML匿名跳登录。
Django DB session；退出删除会话，禁用账号/过期后API401。生产需要HTTPS cookie Secure；本机HTTP dev允许Secure=false，HttpOnly与SameSite=Lax仍设置。JS读CSRF token，不持久化密码/token到localStorage。
会话超时时长为可撤销工程参数（开发默认30分钟），测试通过配置或时钟操控过期，不真实等待30分钟；生产时长另审批。

## 6. 数据、事务与环境隔离
实体：Department(UUID,name unique)、User扩展或profile(department,role,is_active)、SampleRecord(UUID,label,owner,department,request_id UUID,created_at)、AuditEvent(UUID,actor,action,resource_id,request_id,created_at,脱敏summary)；unique(owner,request_id)，FK规则明确且非本阶段删账号。
样板无业务审批状态；只有客户端 idle/submitting/success/error，服务端已提交记录唯一权威。事务内创建样板和成功审计；异常整体回滚。相同请求键+规范化label重放200原记录，不同label409 IDEMPOTENCY_CONFLICT；首次201。并发唯一键冲突后在事务外读取同记录，避免破坏事务继续查询。
UTC aware服务端时间，显示Asia/Shanghai；工程统计count由同权限过滤查询派生，不硬编码数字。
无 Mock 适配器、无SQLite fallback、无浏览器库存。UI取消未提交不产生审计；超时已可能提交时按同request_id重试或查读，取消UI等待不能宣称回滚服务端已提交事务。
.env 必填 APP_ENV、DJANGO_SECRET_KEY、DB_HOST/PORT/NAME/USER/PASSWORD、DEV_SEED_PASSWORD；模板使用说明字符串而非真实秘密，运行时缺必需项失败。dev DB inventory_factory_case_b_dev，test DB test_inventory_factory_case_b，restore DB inventory_factory_case_b_restore；loopback+项目compose名 factory-case-b；volume同名专属。程序启动验证库/host/env allowlist；测试账号仅授权隔离测试库。
迁移幂等；seed get-or-create不覆盖人工样板、修改密码需显式dev操作。不做UI重置；命令reset需要 dev/test、精确库名、项目容器标签和显式 confirmation 字串全部匹配，默认不执行，不能脚本down -v。
备份pg_dump dev→项目 backups/（忽略、权限受限）→隔离restore库；比对样板UUID/label、账号关联和审计计数，恢复完只清专属restore库可选且需校验；不恢复覆盖原库。生产保留/RPO/RTO/加密凭据为待确认，不造数字。

## 7. API契约
统一错误：{"error":{"code":"…","message":"可读说明","request_id":"…"}}，不返回traceback/DB密码。
GET /api/session：已登录用户部门角色200，未登录401。
POST /auth/login/、POST /auth/logout/：同源CSRF；HTML登录/退出配合API状态验证。
GET /api/engineering/records：权限过滤列表和count。
POST /api/engineering/records：只接受 label/request_id；201/200/400/401/403/409/503。
GET /api/engineering/records/{uuid}：200 / 404 / 401；可按本人request_id查询已提交结果。
GET /health/live：进程活200，不依赖DB；GET /health/ready：SELECT1及迁移检查成功200、DB故障503，连接超时有限（建议3秒）、HTTP故障预算5秒内返回；这两个数值是测试工程阈值不是生产SLA。
工程入口和写API仅 dev/test/smoke 显式启用，生产配置默认关闭并返回404；不提供业务偷跑开关。
事务内部审计失败应回滚样板，可在隔离测试中注入失败，不在正常运行暴露破坏端点。

## 8. 拟定运行接口与证据
以下命令均在未来目标目录，Coder须创建脚本后验证。脚本调用项目 .venv\Scripts\python.exe，失败非0且不吞错误；Linux容器使用 python。
| 顺序 | 拟建/执行命令 | 前提 / 成功结果 | 证据 |
| --- | --- | --- | --- |
| 1 | py --version；docker version；只读Git核验 | 工具已存在，目标安全，版本可用；缺失停止，不全局安装 | docs/baseline.md |
| 2 | powershell -NoProfile -File scripts/bootstrap.ps1 | 建专属venv、哈希锁安装、项目PG容器、校验env、migrate、seed；脚本可重复，0 | round-001/bootstrap.log |
| 3 | .venv\Scripts\python.exe -m ruff check .；… manage.py check；… makemigrations --check --dry-run | 0；迁移同步，不覆盖文件 | round-001/checks.log |
| 4 | .venv\Scripts\python.exe manage.py collectstatic --noinput；docker compose build app；docker compose --profile smoke up -d app | noDEBUG smoke依赖健康PG，静态本地，无真实部署 | round-001/build.log |
| 5 | powershell -NoProfile -File scripts/dev.ps1 start | 主应用127.0.0.1:8000；端口占用不得强杀；启动记录PID | round-001/run.log |
| 6 | powershell -NoProfile -File scripts/verify.ps1 -Round round-001 | 顺序单元→真PG集成→UI→故障/重启→备份演练→smoke；全部0；测试专库 | round-001/test*.log / report.xml |
| 7 | powershell -NoProfile -File scripts/backup-restore.ps1 -Environment dev | 校验专属库后dump/restore并比较，不覆盖原库，0 | round-001/backup.log |
| 8 | powershell -NoProfile -File scripts/dev.ps1 stop；docker compose stop | 只关本任务PID/项目容器，保留卷；0 | round-001/stop.log |

bootstrap 必须先建立/确认锁文件：选支持版本后用venv工具生成哈希锁，再用pip --require-hashes安装。初始化生成锁允许受控一次解析，不将尚无锁文件的首建说成已可复现。所有脚本先创建项目.cache/pip、.cache/tmp、.cache/ms-playwright，仅本进程/子进程设置PIP_CACHE_DIR、TMP/TEMP、PLAYWRIGHT_BROWSERS_PATH指向这些路径，退出恢复原值；不setx/不改系统环境。README列出每个路径/作用域、Docker项目专属托管缓存volume例外、运行/重建/测试/备份接口；工具仍写未授权路径则停报，不全局替装。T-B04 operation_artifact_write_set包含backups/和.cache/，源码仅tests/、证据仅validation新轮次；备份dump是本地敏感运行产物，不提交/外传。
故障测试只能stop项目db或app：每步保存记录UUID和DB计数，finally恢复自己停止的服务，保证bootstrap/测试清理不抹证据。应用重启 / DB重启与reset是不同操作。DB不可用导致session读失败也要503而不是假401或登录成功。

## 9. AC / 任务 / 证据
T-B00→T-B01→(T-B02,T-B03)→T-B04→T-B05；T-B06由后续独立Reviewer只读核对。单Coder只完成T-B00…05实现与自测，未提供独立Reviewer则停待外部验收且不得假称独立结论；不依赖已实现调度器。
AC-B01环境/构建；02布局/取消/键盘；03会话；04资源权限；05真实写事务/重放；06刷新关闭重启；07迁移seed守卫；08健康故障；09真实测试层级；10状态与指纹；11隔离恢复；12CSRF/cookie。
每项均在plan.md有Given/When/Then；T-B04需记录真实PG测试及UI行为，权限不可只测按钮，持久化不可只刷新内存。
截图：login、shell、sample-list、sample-create、permission-rejected、db-unavailable，各实际视口；文本适应性与取消另留trace。管理员/权限截图不能显示秘密。截图不能代替API/DB断言。
manifest记录R/AC、基线HEAD（无仓库则null）、非秘密源码SHA256清单、测试版本、命令、exit_code、时间时区、系统/浏览器/视口、实际结果、相对证据路径。证据目录轮次递增不覆历史。

## 10. 工程完整门槛与状态
14项覆盖：类型/栈/目录/UI/导航/认证授权/数据状态/真实后端区别/持久化初始化重置/配置构建运行/自动测试/项目状态/截图证据/AC门槛均明确。
Goal0完成须 AC-B01…12 全部真实验证，迁移与锁可重建，服务故障不假成功，账号权限由API可证，sample→audit同事务，恢复不覆盖其他库，两个视口可用。DB数据秘密不入证据，只脱敏关联与计数。
PROJECT_STATUS 标当前任务、输入版本、候选内容指纹、实际测试、失败次数、下一恢复动作、未测Linux真机和生产问题；验收表按AC记录实际而非计划。
只满足本地Linux容器验证时必须写“内网Linux真机未验证”；不声称正式发布。全部自测达标才写“Goal 0：已完成，待外部 Reviewer 验收”；外部结论未发生，完成后停止。

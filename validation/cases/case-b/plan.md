# 案例 B 需求与 Goal 计划
版本：case-b-plan-v1；日期：2026-10-08 Asia/Shanghai。
需求来源仅为同目录 input.md“已确认需求 / 尚未确定 / 本次输出授权”。本文是独立使用 requirement-planner 的文档产物，不代表开发或验收结果。

## 定位、事实与边界
澄明设备运营公司库存与领用管理系统：30 名内部员工多人协同，真实关系数据库持久化；开发机 Windows，未来内网 Linux 部署。目标业务闭环为“维护物料→提交领用→本部门审批→仓管出库→库存与审计一致”。

用户明确：批准不扣库存；出库才扣；不为负；重复请求不重复扣；并发结果一致；所有成功变更有审计；浏览器缓存不能作权威数据。
工程可撤销假设：Django 单体、PostgreSQL、同源模板 UI 与 JSON API、Linux本机smoke用gunicorn+WhiteNoise提供已collectstatic资源、本地开发账号、UTC 存储/Asia/Shanghai 显示。这些是本案例方案决策，不是用户指定版本或生产承诺。
仓库事实：本轮未访问 C:\FactoryCases\InventoryService，目录、HEAD、工具、容器运行时版本均未核实。未来实施必须先只读核验；存在未知旧工程时停止而非覆盖。
本轮范围：规划、骨架方案、提示词和任务交接设计实例。未来 Goal 0 范围：真实认证、最小工程样板权限、UI/API/DB、健康、迁移、测试、证据、开发备份恢复演练。
排除：本轮案例开发；Goal 0 的物料/申请/审批/出库业务；付费云、真实 SSO、短信邮件、支付、AI API、微服务调度、生产发布与容量承诺。

## 功能、阶段及可执行验收映射
下表全部为未来计划验证，尚未运行。验收值中界面 token 和样板字段属于工程假设。
| R-ID | 功能 / 确定性 | Goal | AC-ID：前置 → 动作 → 可观察结果 | 方法 / 证据 |
| --- | --- | --- | --- | --- |
| R-B001 | Windows 开发、Linux 可移植依赖；用户明确 | 0 | AC-B01：干净项目专属容器与 venv → 锁定安装、迁移、构建、启动 → 退出码 0，127.0.0.1:8000 可达，无全局安装；Linux compose smoke 可由本机 Linux 容器验证并标明非内网真机 | 命令日志、环境清单 |
| R-B002 | 登录主布局和菜单；用户明确 | 0 | AC-B02：1440×900 / 1280×720 → 键盘登录、切换所有菜单、打开工程样板新增/取消 → 无横向溢出和遮挡，焦点可见，未来业务入口明确“后续 Goal”，取消无请求/写入 | Playwright、两视口 PNG / trace |
| R-B003 | 真实账号认证与服务端资源权限；用户明确 | 0 | AC-B03：有效/错误/禁用账号 → 登录、退出、过期后 API 请求 → 成功建立服务端会话；失败无会话，未登录/退出/过期 API 401；密码不明文、日志无凭据 | API、DB 会话和日志检查 |
| R-B003 | 最小资源权限；工程样板规则为假设 | 0 | AC-B04：A/B 部门样板 → 员工读自己、经理读本部门、管理员读工程样板；资源越权直接 API → 403 或不泄露存在性的 404；伪造 owner/department 非法字段 → 400或403；无新增记录/审计；仓管本阶段无跨部门样板特权 | 真实 DB 集成、权限矩阵 |
| R-B004 | UI/API/DB 工程纵向样板；用户明确 | 0 | AC-B05：登录员工 → UI 填 label、确认并查询详情 → DB 生成 UUID，owner/department 服务端赋值，一条成功审计；空值 400 无写入；同 creator/request_id 同 payload 重放只一条记录/审计，不同 payload 409；两个同时相同请求也只一次成功变更 | UI、API、DB 事务 / 唯一性集成 |
| R-B004 | 持久化、刷新 / 重启；用户明确 | 0 | AC-B06：已提交样板 → 刷新、关浏览器重登录、重启应用服务 / DB 容器 → 同 UUID 和 label 保留；客户端超时不写假成功，按同 request_id 查回或安全重试 | UI / API 与 DB 重启证据 |
| R-B005 | 初始化迁移和虚构 seed；用户明确 | 0 | AC-B07：空专属 DB → 迁移两次、seed 两次 → 无待生成迁移、账号部门样板数量不重复，已新增样板不被 seed 覆盖；非 dev/test、陌生库 reset 请求 → 拒绝且不执行 DROP/清空 | 真实 PostgreSQL 集成、命令日志 |
| R-B006 | 不可用时明确错误；用户明确 | 0 | AC-B08：服务正常 / DB 停止 / API 停止 → liveness/readiness、样板读取/提交 → 正常 200；DB 不可用 readiness 503且短时返回可读 DB_UNAVAILABLE，liveness仍200；API 不可达显示连接失败；恢复后原记录可读，无 Mock 成功或缓存库存 | 故障注入日志 / UI / DB |
| R-B007 | 自动测试基础、证据和工程状态；工程设计 / Skill导出，非案例原文明确条款 | 0 | AC-B09：可重建隔离测试库 → 静态检查、单元、真实 DB API/事务、UI 全链路、无 DEBUG 的构建 smoke → 必需测试通过且不跳过，预期 400/401/403/404/409/503 明确与意外错误区分 | 日志、JUnit / pytest 报告、trace |
| R-B007 | 状态 / 截图 / 验收证据；工程设计 / Skill导出，非案例原文明确条款 | 0 | AC-B10：固定候选内容 → 每个 AC 记录实际步骤/结果/退出码/证据、指纹/环境/视口、失败历史 → PROJECT_STATUS 与验收矩阵一致；外部验收未发生；无 Git 写、部署或全局安装 | evidence manifest / 状态审查 |
| R-B005 | 开发备份恢复；用户明确 | 0 | AC-B11：有样板的专属 dev DB → pg_dump 到本项目忽略目录，再恢复到另一隔离库 → UUID、label、账号关联与审计计数一致；拒绝原库覆盖与生产地址；生产保留周期只列待确认 | 备份日志 / 校验清单，不提交数据 |
| R-B003 | 同源会话防伪 / 凭据保护；工程安全设计 | 0 | AC-B12：登录会话 → 去掉或伪造 CSRF 令牌提交 → 403且 DB 不变；合法令牌成功；cookie HttpOnly、SameSite=Lax；非开发 HTTPS cookie Secure；不使用浏览器持久凭据 | API / header / DB 检查 |
| R-B008 | 物料台账、入库基础；用户明确 | 1 | AC-B13：仓管创建物料与入库 → 物料编码唯一、数量正数、库存与入库流水/审计同事务，员工直接调用被拒；重复编码/非法数量无写入 | UI、API、DB；后续运行 |
| R-B009 | 员工领用申请；用户明确 | 2 | AC-B14：员工同部门 → 草稿提交、查看自己的申请 → 服务端标记 submitted、数量正数且关联有效物料，其他部门列表/详情不可读；提交不扣库存；取消编辑不写入 | UI、API、DB；后续运行 |
| R-B010 | 经理审批本部门；用户明确 | 2 | AC-B15：submitted → 本部门经理 approve/reject → approved/rejected 且审计一次，跨部门拒绝，终态不能重复审批，approved 后库存仍不变；代理未决定前不实现 | UI、API、DB；后续运行 |
| R-B011 | 仓管出库、库存不变量；用户明确 | 3 | AC-B16：approved 数量3、库存10 → 仓管出库 → 库存7，申请 fulfilled，流水/审计同事务，员工 / 未批申请拒绝；AC-B17：同幂等键重放 → 库存仍7、唯一流水；AC-B18：库存5、两 approved 各4并发 → 仅一成功、另409 STOCK_INSUFFICIENT，库存1；AC-B19：事务注入异常 → 库存/状态/流水/审计全部回滚 | 真 PostgreSQL 并发 / 回滚集成、UI；后续运行 |
| R-B012 | 管理员账号角色；用户明确 | 1 | AC-B20：管理员创建 / 禁用账号、改部门角色 → 服务端生效且审计记录；非管理员403；禁用会话失效；角色变更不依赖隐藏按钮 | API、UI、会话；后续运行 |
| R-B013 | 所有成功变更审计；用户明确 | 3 | AC-B21：执行已定义成功变更 → 同事务审计绑定 actor/action/resource/time/request_id；失败无成功审计；普通员工无法读审计或修改审计，脱敏 | DB、API；后续运行 |
| R-B014 | Linux 正式交付、生产身份与备份；部分待确认 | 4 | AC-B22：获批准身份/凭据/备份周期/容量指标与固定候选 → Linux 内网部署演练、TLS/备份恢复、批准容量测试 → 仅按已批准指标交付可回退包；未确认不部署或声称生产就绪 | Release 检查 / 真目标机，后续审批 |

## 阶段与冻结边界
| Goal | 进入依赖 | 范围、产物与增量入口 | 退出门槛 |
| --- | --- | --- | --- |
| 0 | 目标目录 / 工具只读核验；当前未来目录未知 | accounts/common/sample/health、布局和 API 契约、真实 PG、工程证据；业务菜单为显式占位无写接口 | AC-B01…12；自测后待外部 Reviewer，禁止自冻 |
| 1 | Goal 0 外部验收与后续明确授权 | inventory 模块物料 / 入库和 accounts 管理 UI；复用布局认证审计事务入口 | AC-B13、20 与 Goal 0 回归 |
| 2 | Goal 1 契约稳定 | requisitions 模块申请与本部门一次审批；不得代办 / 代理 | AC-B14、15；stock 不变断言 |
| 3 | Goal 2 approved 状态与库存基础稳定 | inventory 出库服务、幂等与锁 / 条件更新，同阶段交付全部库存不变量；audit 业务入口 | AC-B16…19、21；完整闭环回归 |
| 4 | 业务阶段验收及生产决定 | Linux 真实环境交付、身份策略、备份/容量/回退；独立发布审批 | AC-B22及批准发布门槛 |

未来仅在外部验收和显式 Git 授权后由 Git Agent 提交 / Tag / 冻结；本案例设计包 git_write=false，不能推导 Git 权限。

## 任务、依赖与并行
任务全部是未来设计，未派发。
| Task | 角色 | depends_on | 输入 → 输出 | write_set / 独占者 | AC |
| --- | --- | --- | --- | --- | --- |
| T-B00 | Coder / 整合者 | 无 | 本设计 → 目录工具基线记录、契约选择 | README.md, docs/baseline.md；根配置所有者 | 01 |
| T-B01 | Coder / 整合者 | T-B00 | 契约 → venv依赖、容器、模型与app骨架后迁移seed、运行脚本 | config/, requirements*.txt, compose.yaml, Dockerfile, manage.py, scripts/, accounts/common/sample的models.py/apps.py/包初始化/全部migrations/seed管理命令；模型独占；.venv/.cache为项目运行产物 | 01,07 |
| T-B02 | Coder / 服务端 | T-B01 | 模型契约 → 登录/API/权限/事务/健康 | accounts/common/sample服务API/views、common权限错误审计辅助、health/；排除models/apps/迁移/seed/模板静态，模型变更回整合者 | 03,04,05,06,08,12 |
| T-B03 | Coder / UI | T-B01 | 冻结路由字段 → 主布局 / 登录 / 样板 | templates/, static/；不得改根路由或服务端 | 02,05 |
| T-B04 | Tester | T-B02,T-B03 | 固定候选 → 测试/故障/重启/备份恢复实际结果 | tests/, validation/goal0/ 下新一轮目录；operation_artifact_write_set为backups/、.cache/，只允许专属测试/恢复库 | 01…09,11,12 |
| T-B05 | Orchestrator / 整合者 | T-B04 | 实际结果 → 状态与证据索引 | PROJECT_STATUS.md, docs/acceptance-goal0.md, validation/goal0/manifest.json | 10 |
| T-B06 | Reviewer | T-B05 | 固定候选全材料 → 独立问题报告 | validation/goal0/review.md；只读实现，不写结论为外部验收 | 01…12 |
| T-B10 | Coder | T-B06 外部验收另需授权 | 物料 / 入库业务 | inventory/；迁移注册仍单整合者 | 13 |
| T-B11 | Coder | T-B06 外部验收另需授权 | 管理账号 UI | accounts/admin-ui/, templates/accounts-admin/ | 20 |
| T-B20 | Coder | T-B10,T-B11 | 领用申请 | requisitions/requests/ | 14 |
| T-B21 | Coder | T-B20 | 一次经理审批 | requisitions/approvals/ | 15 |
| T-B30 | Coder | T-B21 | 出库与审计 | inventory/dispatch/, common/audit.py兼容增量, common/audit_views.py；不另建与audit.py冲突的同名package | 16…19,21 |
| T-B40 | Release Agent | T-B30 | 已批准环境与固定源码 → 发布材料 | release/, docs/operations/ | 22 |

T-B02 / T-B03 在 T-B01 完成并冻结接口后可并行；接口变更必须回整合者登记，不能抢改 config/urls.py。T-B10 / T-B11 可在接口和独立写集确定后并行，账号依赖由 T-B20 汇合。测试与只读审查可在固定候选上并行规划，但此串行样例便于首次闭环；任何修复都会产生新内容指纹，旧测试不能套用。
依赖顺序 00→01→(02,03)→04→05→06→(10,11)→20→21→30→40；无环。单Coder可完成T-B00…05实现与自测，T-B06必须后续独立Reviewer只读执行；未提供该角色时Coder停待外部验收，不能自行伪造独立审查结论。

## 重大待确认与风险
| Q-ID | 问题 / 建议 | blocks_tasks | 可以继续 |
| --- | --- | --- | --- |
| Q-B01 | 生产 SSO 或继续本地账号？建议先确认安全责任与接入范围，不接真实身份平台 | T-B40 | Goal 0 本地开发认证及后续本地业务 |
| Q-B02 | 跨部门代办 / 授权代理是否纳入范围？默认本次仅本人申请与本部门经理一次审批；任何代理需独立需求批准 | T-B21 中代理扩展（当前不纳入）；不阻塞既定单经理审批 | Goal 0、Goal 1、既定 Goal 2 |
| Q-B03 | 生产备份保留周期、RPO/RTO、容量和部署凭据是多少？无答复不能给 SLA / 上线承诺 | T-B40 | Goal 0 隔离开发备份演练、业务开发 |

Q-B02 不应阻塞整个 T-B21 的已确认审批实现；机器包将用独立候选业务任务 T-B22 表示代理扩展，状态 blocked_candidate，依赖 T-B21，AC 在获准后另行定义。
风险：并发必须使用 PG 真实事务；测试若 SQLite 会隐去差异。本机 Linux 容器不证明真实服务器运维可用。工程样板管理员全读仅适用于样板，不扩张员工领用部门边界。未来并发写同迁移注册 / 锁文件必须串行整合。pip/浏览器/测试需PIP_CACHE_DIR、TMP/TEMP、PLAYWRIGHT_BROWSERS_PATH仅当前脚本进程指向项目.cache对应目录，README明示，退出恢复；未授权路径写入则停报，Docker专属托管volume/cache例外必须限定项目。
禁止：静默 Mock fallback；为测通清其他库；把审批扣库；猜代理权限；生产一键清空；本轮创建工程；任何 Git 写 / 部署 / 全局安装。

## 交接状态
规划产物已形成，Goal 0 的工程细节可作为未来 Coder 明确任务；生产和代理候选仍待决定。task-packet.json 是接口设计实例，未运行调度器，业务测试全部未运行，外部 Reviewer 结论未发生。

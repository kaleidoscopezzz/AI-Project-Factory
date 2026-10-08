# 独立内部文档与行为检查

日期：2026-10-08（Asia/Shanghai）。性质：受限评估子 Agent 的内部检查；不是外部 Reviewer 验收，不构成验收通过。

## 范围与证据边界

- 检查本项目三个 `skills/*/SKILL.md`、各技能全部 `references/assets/agents`、`docs/MULTI_AGENT_ROADMAP.md`、`docs/USAGE.md`，及本项目案例输入与产物。
- 两案例 `input.md` 是唯一需求事实源；计划中的技术决策只按其来源、约束和自洽性检查，不预设技术栈答案。
- 依据 skill-creator 的职责边界、自包含、渐进读取、授权保持和独立前向验证原则检查。
- 未读取或修改 `C:\910Program`，未执行 Git 命令、安装、全局 Skills 操作、案例开发或业务测试；只写本文件。
- `docs/SOURCE_EXPERIENCE.md` 的来源声明已读，其参考源码与历史测试事实本次未独立重验；不得把本检查作为这些历史事实的新执行证据。

## 核心产物检查

| 检查 ID | 对象与可观察要求 | 内部结果 |
| --- | --- | --- |
| IR-CORE-001 | 三 Skill 的 YAML `name/description`，名称与目录一致，入口职责可区分 | 已人工核对；格式与角色描述一致，正式格式验证由本项目验证脚本另记 |
| IR-CORE-002 | Skill 使用资源均随自身目录提供，无必须安装另一个 Skill 的隐式前提 | 已核对；Planner、Scaffolder、Prompt Writer 均提供独立输入处理与本地相对资源 |
| IR-CORE-003 | 原始需求、事实、假设、阻塞分开；R/AC/Goal/Task 映射与依赖、写集要求明确 | 已核对；Planner 入口和模板均有对应要求 |
| IR-CORE-004 | 架构按项目类型选择，DEMO 与真实服务端/数据库分清，无行业或参考技术栈默认 | 已核对；架构参考提供多种场景，真实授权与持久化要求明确 |
| IR-CORE-005 | Goal 0 只建纵向基础样板，后续业务增量接入，既有项目不重建冻结基座 | 已核对；三个入口与模板的阶段边界一致 |
| IR-CORE-006 | 提示词 16 项有可填写位置，合理不适用、执行前基线核验、拟定命令/实测区别明确 | 已核对；14 个模板章节承载 16 项，不要求机械生成 16 个标题 |
| IR-CORE-007 | 正常/异常/授权/取消/刷新重启/持久化等行为验证按相关性覆盖；不以镜像文案检查冒充测试 | 已核对；行为检查与技术层级对应，有不得绕过失败断言要求 |
| IR-CORE-008 | 权限继承、禁止事项、有限返工、失败停止、外部验收与自测分离 | 已核对；未从模板推导额外 Git、发布或外部服务权限 |
| IR-CORE-009 | 多 Agent 文档明确未来方案，角色、任务包、冲突、候选指纹、恢复、预算与审批控制点可审查 | 已核对；未宣称调度器已实现，后续建设顺序与本轮范围分开 |
| IR-CORE-010 | 中文使用说明区分按文件读取与已安装发现，安装示例标未执行，未测平台/客户端发现如实说明 | 已核对；本轮使用与未来安装边界明确 |

截至核心检查，未发现必须修改的阻断性问题。以上是人工内容检查，不替代正式格式脚本、参考目录复核或外部验收。

## 两案例检查状态

已读取两案例 `input/plan/goal0-blueprint/goal0-prompt/task-packet/evaluation`。两条 Skill 文档链实际生成完毕；工程实施、业务测试、外部验收均未发生。

实际执行的检查只读取文档 JSON 和提示词，未执行业务：A 为 18 个 R、18 个 AC、11 个 Task；B 为 14 个 R、22 个 AC、14 个 Task（包括未获范围批准的代理候选）。两份提示词各包含全部 12 个 Goal 0 AC，没有 `{{` 未填写变量，packet 的 `git_write=false`、`head=null`。该检查仅是结构事实，不能证明工程运行。

## 已发现问题与迭代记录

| Issue | 严重度 | 原问题及定位 | 修正与复核状态 |
| --- | --- | --- | --- |
| IR-B-001 | P2 | B plan 的 R-B007 两行把测试/证据/状态写成 input 用户明确要求，实际属于工程细化 | 已见 plan 改为工程设计/Skill 导出，packet 对应 source_kind 同步；已复核 |
| IR-B-002 | P2 | B 的 T-B01 先迁移/seed，却只允许写 migrations，模型交给后置 T-B02 | 已见 plan/prompt/blueprint/packet 把模型/app/seed 骨架交 T-B01 独占，T-B02 排除；已复核 |
| IR-B-003 | P2 | B prompt 要求临时文件/缓存在目标根，却未约定 pip cache 与 TMP/TEMP；T-B04 备份会写未列明的 backups/ | 已见 plan/prompt/blueprint/packet 设置进程 PIP_CACHE_DIR、TMP/TEMP、PLAYWRIGHT_BROWSERS_PATH；每个运行脚本继承/设置且退出恢复，仍越界停报；packet 区分代码写集与 operation_artifact_write_set，覆盖 venv/cache/staticfiles/backups；已复核 |
| IR-B-004 | P2 | 主 Agent 发现在 B DEBUG=false gunicorn/collectstatic 没明确静态 HTTP 提供方 | 已见 WhiteNoise runtime 锁、middleware/storage/STATIC_ROOT/collectstatic 与 CSS/JS 实测门槛明确；已复核文档设计，未运行工程 |
| IR-B-005 | P2 | 主 Agent 发现在 B T-B06 要独立 Reviewer 与单 Coder 顺序完成表述冲突 | 已见 T-B00…05 可单 Coder 实施/自测，T-B06 由后续独立 Reviewer，未提供不伪造结论；已复核 |
| IR-A-001 | P2 | 主 Agent 发现在 A 手动 preview 4173 与 E2E webServer reuseExistingServer:false 撞端口 | 已见手动 smoke 后只停本任务 PID、确认端口释放，再由 Playwright 自行启停；已复核 |
| IR-A-002 | P2 | 主 Agent 发现在 A test:unit 未明确组件测试及 e2e 排除 | 已见 Vitest include unit/component、exclude e2e、jsdom/setup 在 prompt/blueprint 写明；已复核 |
| SELF-B-01 | P2 | B 作者自检发现后续 common/audit/ 与基础 common/audit.py 重名 | 已见 B plan T-B30 与 packet 改为 common/audit.py 兼容增量和 common/audit_views.py；已复核，发现来源为作者 evaluation |

三个 Skills 的窄修正已重读：Planner 检查步骤前提产物/写集，Scaffolder 检查模型→迁移→seed 及生产静态来源，Prompt Writer 检查可执行顺序与单 Coder 自测/独立审查角色区别。修正依据是文档行为检查中实际出现的问题；没有固化案例技术栈。

编号说明：IR-B-001…005 与 B evaluation 对应；IR-B-003 合并缓存与备份运行写集问题，避免同一问题在产物中编号冲突。父审查所发现的问题已明确注明来源，不冒称全为本评估 Agent 独立发现。

修正位置索引（相对于本项目）：

- IR-B-001：`validation/cases/case-b/plan.md` 的 R-B007 两行；`task-packet.json` 的 R-B007.source_kind。
- IR-B-002：B `plan.md` / `goal0-prompt.md` 的 T-B01/02；`goal0-blueprint.md`“目录与单一装配者”；`task-packet.json` 的 T-B01/02.write_set。
- IR-B-003：B `plan.md` T-B01/04 和风险；`goal0-prompt.md`“工程命令与测试执行”第 2 步、T-B04；`goal0-blueprint.md`“拟定运行接口与证据”；`task-packet.json` 的 policy.command_process_environment 和 operation_artifact_write_set。
- IR-B-004：B `plan.md` 工程假设；`goal0-blueprint.md` 技术选择；`goal0-prompt.md` 工程命令第 3 步，均明确 WhiteNoise。
- IR-B-005：B 三份文档的单 Coder/T-B06 说明；`task-packet.json` 的 T-B06.execution_contract。
- IR-A-001/002：`validation/cases/case-a/goal0-prompt.md` 第 8 节命令步骤 4、6、7；`goal0-blueprint.md` 的 test:unit / preview / test:e2e 契约。
- SELF-B-01：B `plan.md` 和 `task-packet.json` 的 T-B30。

## 案例行为与一致性检查

| 检查 ID | 案例 A | 案例 B |
| --- | --- | --- |
| IR-CASE-001 输入覆盖 | 填报/提交锁定/退回修改重提、审批意见、执行进度、统计/记录、两模拟角色、唯一编号、取消无改动、刷新持久、标准/退回重置、本地资源、两视口、无 Node/管理员的现场限制均映射到 R-A001…018 | 30 人多人、Windows 开发/Linux 部署、员工/经理/仓管/管理员、部门权限、审批不扣库、出库非负/幂等/并发、成功审计、真 DB/迁移/seed/备份、重启持久、无 Mock fallback、菜单/视口、费用及外部系统排除均映射到 R-B001…014 与 AC-B01…22 |
| IR-CASE-002 Goal 合理性 | 0 样板基座；1 申请审批退回闭环；2 执行/统计；Release 现场包装。业务歧义只阻塞对应业务，未把 preview 当现场无 Node 包 | 0 真 UI/API/DB 样板；1 物料/入库/账号；2 申请审批；3 出库全部库存不变量与审计；4 获批准生产交付。生产未知不阻塞基座，代理是范围外候选 |
| IR-CASE-003 架构选择 | 比较静态 SPA/IndexedDB 与本地 API/SQLite，依单机虚构断网选择前者，HashRouter 已明确；版本待实现核验 | 比较 Django 同源单体与 React/FastAPI，选前者；真实 PostgreSQL 不用 SQLite/浏览器缓存替代；Linux 容器 smoke 与目标真机分开 |
| IR-CASE-004 数据/身份边界 | 模拟身份持续标明；会话内存、运行数据 IndexedDB；immutable seed、snapshot、版本/epoch、确认重置与损坏恢复独立；故障注入明确，不冒称真实授权 | 服务端 session/hash/CSRF 与对象权限；样板管理员权限不外推业务；DB 原子样板/审计、唯一键重放/并发、超时同键查回、故障 503、隔离库和 dump 恢复约束明确 |
| IR-CASE-005 依赖与写集 | T-A001…006 串行、共享文件单一整合；后续 Task 不获当前执行权限。单 Coder 可完成实现及 Tester 自测职责，边界自检非独立 Review | 模型/app→迁移/seed→API 与 UI→测试→证据；模型/根配置由单一整合者；operation_artifact_write_set 区分运行输出；T-B06 后续独立 Reviewer，不依赖不存在的调度器 |
| IR-CASE-006 AC 一致 | 12 个 Goal 0 AC 在计划、方案、提示词与 packet 中保持相同 ID/结果语义；采购业务/Release AC 明确后续 | 12 个 Goal 0 AC 与后续 10 个业务/交付 AC 可追溯；资源拒绝 400/401/403/404、幂等 409、故障 503 的前置明确，无必须所有 HTTP 200 的矛盾 |
| IR-CASE-007 证据与真实性 | evaluation 仅主张实际文档生成/结构检查；无浏览器截图、Vitest、构建或业务通过结果；未来截图故障注入要标明 | evaluation 仅主张文档链、静态 QA 与设计官方依据；逐项列明 PG/API/UI/重启/备份/构建未运行；未称工程测试通过 |
| IR-CASE-008 禁止与失败停止 | 禁 Git/参考与工厂写入/全局配置/真实外部业务；未知旧工程/路径/工具/端口问题停报；两次修复/三轮验证；必需 AC 未运行不可完成 | 同样保持权限与预算，额外限制专属 dev/test/restore DB、生产/其他库拒绝、不强杀/不清库修测试；新增服务或生产决定待授权 |
| IR-CASE-009 内容污染 | 只有采购输入与必要工程细化，无参考行业模块移植；Windows/React/IndexedDB 仅本例 | 只有库存/领用/部门输入与工程细化，无参考行业或离线 DEMO 默认；Django/PostgreSQL 仅本例 |

## 两份完整提示词的 16 项定位

章节只是定位，检查对象是内容；不把 16 个标题当成功标准。

| 必要项 | A prompt 定位 | B prompt 定位 |
| --- | --- | --- |
| 背景 | 1 | 1 |
| 工作目录 | 2、3 | 2、3 |
| 环境/技术栈 | 2、8 | 2、10 |
| Git/Goal 基线 | 3 | 3 |
| 目标 | 1、11 | 1、4、12 |
| 功能实施步骤 | 4、6、9 | 5、7、8、9 |
| 页面交互 | 5 | 6 |
| 数据状态 | 6 | 7、8、9 |
| 允许修改 | 2、4、7 | 2、5、13 |
| 禁止修改 | 2、3、7 | 2、3、13 |
| 测试运行 | 8、9 | 10 |
| 截图/证据 | 9、10 | 11 |
| 完成标准 | 11 | 12 |
| 失败处理 | 12 | 12 |
| 最终报告 | 13 | 14 |
| 完成后停止 | 14 | 15 |

两份最终提示词都提供了具体路径、未知基线先核验、拟建命令接口、行为结果与证据、停止门槛，可在未来获准的目标项目中交给单 Coder 实施与自测。当前授权仍只允许工厂文档，提示词和 packet 都不是现在启动案例开发的授权。

## 检查限制

- 未实作任何案例；这里的“可执行性”是指文档动作、依赖、边界与接口可直接作为实施任务，不能证明拟建命令已经存在或工程实际可运行。
- 本 Agent 实际运行的文档快检与人工语义审查分开。案例 evaluation 中作者的 QA 命令由其记录，本 Agent 未重跑全部作者 QA；主 Agent 的最终格式/资源/反例检查另有报告。
- 没有独立重新核实官方安装发现路径、参考项目源码/历史验收、参考目录前后指纹；这些由主 Agent 的来源与只读复核证据支撑，并非本检查直接证据。
- 未覆盖所有一句话、招标、增量、Release 模式的实际使用；两个案例覆盖离线 DEMO 与真实服务端/数据库的主要分歧。

## 最终内部结论

主 Agent 已通知两案例作者完成且文件收口。对本次三个 Skills、自包含模板、中文说明、未来多 Agent 方案以及两案例文档行为验证的独立内部检查已完成。上表问题均已在最终产物中实际修正并复核；在本次检查范围内未发现残留的必须修正项。

该结论支持将交付物交给外部 Reviewer，不能替代外部验收、工程业务测试或参考目录复核，也不批准案例开发、Git 写入、冻结或发布。

## 外部验收状态

外部 Reviewer 验收：未发生。本文件只能作为其后续审查的输入。

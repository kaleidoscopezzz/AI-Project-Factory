# 案例 B 独立技能行为验证记录
日期：2026-10-08 Asia/Shanghai。执行角色：受限独立案例评估子Agent。
性质：文档生成/映射/可执行性检查；不是案例工程测试，不是外部Reviewer验收结论。

## 1. 实际过程和访问边界
唯一需求输入为本目录input.md，未借用案例A输出，也未查看C:\910Program或未来C:\FactoryCases\InventoryService。
顺序使用：
1. 读取skills/requirement-planner/SKILL.md、assets/requirement-plan.md、references/decomposition.md，输出plan.md。
2. 读取skills/goal0-scaffolder/SKILL.md、assets/goal0-blueprint.md、references/architecture.md，按已生成计划输出goal0-blueprint.md。
3. 读取skills/goal-prompt-writer/SKILL.md、assets/goal-development-prompt.md、assets/project-status.md、assets/acceptance-record.md、references/writing-guide.md，输出自包含goal0-prompt.md。
4. 从真实同一R/AC/Task映射生成task-packet.json，不生成运行调度程序。
5. 收到主Agent独立内部审查反馈后，修正生成材料中的具体执行缺口，保留本记录。使用项目既有验证器函数检查最终机器包与提示词映射。
本轮只编写本案例五项交付物，未运行任何案例浏览器/API/数据库/构建/备份命令，未安装依赖或全局Skill，未执行Git写/发布。项目验证器为工厂交付物静态QA，不是业务测试。

## 2. 决策质量与范围检查
| 项目 | 产物中的具体决策 | 本轮检查结果 |
| --- | --- | --- |
| Planner定位 | 30人多人真实内网Web；Windows开发与Linux部署区分 | 与input一致，未默认离线DEMO |
| Goal拆分 | 0基座；1物料/入库与账号；2领用/审批；3出库全部库存不变量；4批准后正式交付 | 批准不扣库、出库扣库及并发/重放同一阶段验收，未拆成假按钮完成 |
| 技术适配 | Django模板/API单体+PostgreSQL；React/FastAPI方案作为备选 | 真数据库与服务端对象授权；未复制Vue/Mock/localStorage/Windows便携包 |
| Goal0链路 | 工程样板登录→UI→API→事务写PG/audit→读回→重启 | 真实可实现基础；不实现库存业务，样板管理员权限不外推领用 |
| 对象授权 | 列表过滤+详情检查；员工本人、经理本部门；Django model权限不能替代 | 直接API测试在提示词明确，401/403/404按具体前置区分 |
| 故障/恢复 | DB不可用503、不Mock；超时同键查回；专属dump恢复另一库 | 初始化/重置/保留卷/恢复原数据区分，未授权生产动作拒绝 |
| 可执行提示词 | 完整目录、未知基线、拟建脚本、字段/API/status、顺序、测试/截图/最终报告/停止规则 | 最终无未填占位符；12项Goal0AC均能定位到行为和验证 |
| 歧义 | 生产SSO/备份容量仅阻塞T-B40；代理候选T-B22仅设计等待批准 | 不因生产问题阻塞Goal0；不擅自猜跨部门代理 |
| Git/费用权限 | 三项policy false，所有Git写禁止，生产/全局禁用 | 未将设计包当权限授权；未来案例需独立启动授权 |
| 业务污染 | 模块围绕物料、领用、库存、部门角色 | 无辽宁政法业务模块复制 |

## 3. 实际发现与修正
本次自检和主Agent内部只读审查发现生成材料中的问题；这些是可审查的真实发现，不能冒称Skill初稿完美。
| ID | 发现 | 已修正产物 / 处理 |
| --- | --- | --- |
| IR-B-001 P2 | Planner把自动测试/截图/状态标为案例用户明确，但input未逐条要求这些 | plan将R-B007改为工程设计/Skill导出；packet同样标source_kind；与原始用户业务需求区分 |
| IR-B-002 P2 | T-B01要求迁移/seed，却无models写权限；T-B02才拥有模型，顺序不可执行 | plan/blueprint/prompt/packet把models/apps/初始化/迁移/seed独占交T-B01；T-B02排除模型；实际映射自检确认 |
| IR-B-003 P2 | 路径边界要求项目内缓存，但pip/临时目录未配置；备份dump不在Tester写集 | 四产物明确进程PIP_CACHE_DIR/TMP/TEMP/PLAYWRIGHT_BROWSERS_PATH、退出恢复，README契约；T-B04新增backups/.cache运行产物写集，Docker例外限定项目 |
| IR-B-004 | DEBUG=false gunicorn并不会因为collectstatic就提供静态文件，smoke实现缺一环 | 选定WhiteNoise、runtime锁、middleware位置、STATIC_ROOT/storage/static tag、镜像收集与实际CSS/JS200；plan/blueprint/prompt同步 |
| IR-B-005 | “同一Coder可顺序完成”包含T-B06，可能把Coder自测冒充独立Reviewer | 三文档/packet明确单Coder只T-B00…05；T-B06须独立Reviewer，未提供停待外部验收，不依赖自动调度 |
| SELF-B-01 | Goal3拟用common/audit/可能与Goal0 common/audit.py模块重名 | plan/packet改为common/audit.py兼容增量和audit_views.py，无不必要重建 |

Skill可改进点：工作流已经要求事实区分、写集和依赖、运行契约，本次仍需逐行实审生成材料。建议将“初始化任务必须拥有模型/app/seed写集”“无DEBUG静态服务实际入口”“工具缓存/临时文件路径”“Coder与独立Reviewer不可同一执行声明”加入相应检查提醒。未擅自修改父任务Skills；是否采纳由主Agent处理。本次未发现必须停止整个案例规划的Skill结构缺失。

## 4. 实际静态QA与结果
使用工厂项目已存在的 .tools/validation-env/Scripts/python.exe；调用scripts.validate_delivery.check_packet和negative_checks；最终复查使用-B避免产生新pyc。所有检查仅读取本案例材料并在内存构造坏包，没有业务执行。
最终命令exit_code=0，输出：
- requirements=14、acceptance=22、tasks=14（包含一个未批准且无承诺AC的代理候选Planner任务）。
- Goal0AC数量12，所有ID在最终提示词出现：true。
- 最终提示词未填占位符检测：false。
- 6个坏包探针均被拒：重复Task、未知依赖、自循环、Git授权扩大、缺失AC映射、相对路径越界。
- T-B01拥有三个models路径：true；T-B02排除models：true。
- blocking_questions不阻塞任何Goal0任务：true。
这些结果是格式/一致性证据，不是自动语义证明。写集互斥、阶段恰当、身份/故障语义由上述人工文本审查支持；未来实现时仍须运行真实AC。

本案例未运行：登录浏览器、API权限、PG迁移/seed、事务/并发、故障/重启、备份/恢复、Linux构建、两视口截图。没有生成这些业务测试的通过次数、截图或数据库日志。skill官方frontmatter/resource完整检查由主Agent统一运行，不在本记录冒称本子Agent已运行。

## 5. 技术依据
仅为核实具体工程可行性，查阅[Django事务](https://docs.djangoproject.com/en/5.2/topics/db/transactions/)、[Django认证](https://docs.djangoproject.com/en/5.2/topics/auth/default/)、[Django CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/)、[PostgreSQL SQL Dump](https://www.postgresql.org/docs/current/backup-dump.html)、[WhiteNoise Django配置](https://whitenoise.readthedocs.io/en/stable/django.html)官方primary docs。它们支持设计，不证明未来目标工具存在、版本已经锁定或测试已运行。未追求最新版本，未假造历史原始提示词来源。

## 6. 输出与限制
产物：plan.md、goal0-blueprint.md、goal0-prompt.md、task-packet.json、evaluation.md。
未来目标目录基线仍未知；后续Coder必须先只读核验。生产身份、跨部门代理、保留周期、容量和凭据未定，不能承诺上线。
本例的技能文档链已实际生成并完成静态检查及问题修正，可供主Agent与外部Reviewer进一步检查。外部Reviewer验收未发生，本记录不宣布验收通过或案例工程完成。

# Goal 0 交付验证报告

日期：2026-10-08，Asia/Shanghai。性质：本轮交付自测与独立内部文档检查，外部 Reviewer 验收尚未发生。状态：**Goal 0：已完成，待外部 Reviewer 验收。**

## 验证方法与证据边界
先依据三个 Skills 的自包含入口及相关模板/参考，由两个受限独立评估 Agent 分别从虚构输入生成需求计划、工程方案、Coder提示词和设计任务包。父 Agent 核对输入→输出一致性，另做独立内部检查；机器 QA 检查格式、引用、ID映射、依赖与权限不变量。案例系统不开发，不执行拟定的 pnpm/Django/浏览器/API/DB 命令，不伪造截图或 0 错误。

真实执行的 QA 命令和结果保存到 `skill-checks.json`、`checks.json`；参考只读核查保存在 `reference/`。`.tools` 内 Python venv/PyYAML 只服务本项目 YAML 检查，不是付费外部服务或全局依赖。

## 检查分层
1. 官方格式：三个目录名称与 YAML name/description、Skill Creator validator；UI metadata 单独检查。
2. 可移植性：各 Skill 的资源链接全部在自身目录，不依赖工厂 docs、另一个 Skill 或参考仓库。
3. 文档行为：两种真实不同的架构决策、合理 Goal、逐点 AC、具体工程方案和可复制提示词。
4. 交接设计不变量：唯一ID、需求↔AC↔Task 覆盖、依赖无环、问题阻塞指向真实任务、相对写路径、未核验基线如实表达、Git/部署/全局安装禁权。
5. 检查器反例：重复任务、缺失依赖、环、越权Git、未知AC、路径逃逸必须被拒绝；只是设计包校验，不实现调度。
6. 只读保护：全目录路径/大小/mtime，除 node_modules 外 SHA-256，以及 HEAD/branch/refs/status 前后比较。

## 案例产物
| 案例 | 输入 | 生成输出 | 本轮验证状态 |
| --- | --- | --- | --- |
| A 政府采购离线 DEMO | cases/case-a/input.md | plan.md、goal0-blueprint.md、goal0-prompt.md、task-packet.json、evaluation.md | 文档行为与结构检查完成 |
| B 真实后端企业管理 | cases/case-b/input.md | 同样五项 | 文档行为与结构检查完成 |

两个案例逐项核对结果：

| 验证点 | 案例 A | 案例 B |
| --- | --- | --- |
| Planner 定位/边界/功能/阶段/逐点AC/依赖/并行/歧义/风险 | 18 R、18 AC、11 Task；Goal0→申请审批→执行统计→Release | 14 R、22 AC、14 Task；Goal0→物料入库账号→领用审批→出库全部不变量→批准后交付 |
| Goal0工程方案14项主题 | 布局、模拟身份、导航、IndexedDB状态与样板、初始化确认重置、Vitest/Playwright、状态证据门槛 | Django UI/API/PG样板、真实会话/对象授权/事务、迁移seed、健康、pytest/Playwright、隔离备份恢复 |
| 工程适配 | React/TypeScript/Vite/HashRouter、单机IndexedDB；前端身份只是模拟；便携包装后续 | Django/PostgreSQL/WhiteNoise、真数据库和服务端权限；Linux本机容器smoke与生产部署区分 |
| 提示词16项 | 12个Goal0 AC逐项操作、命令/证据/路径/未知基线/禁止项/有限失败/报告/待验收停止齐全 | 同样12个Goal0 AC；401/403/404/409/503区分，API/DB/重启恢复和两视口验证明确 |
| 未知规则和授权 | 审批层级/阈值/版本只阻塞业务，工程可独立实施；本轮不创建目标 | 生产身份/备份周期/容量与代理候选不偷实现、不阻塞基座；当前无部署/Git权 |
| 数据真实性与范围 | 全虚构演示，场景标签不冒充采购状态机；不开发完整业务 | 无Mock/SQLite/localStorage替真PG，样板不冒充库存业务；出库并发验收留Goal3 |
| 测试和完成门槛 | 真实UI/IndexedDB、取消全快照、存储失败/旧epoch、生产构建断外域、两视口 | 真实API/PG授权与事务、会话/CSRF、重放并发、故障/重启、隔离dump恢复、两视口 |
| 行业污染 | 无政法模块，无企业库存规则 | 无政法模块，无Windows离线便携前提 |
| 机器设计包检查 | ID双向映射、AC到Task、无环、写集路径、禁权、未知基线均满足；6坏包被拒 | 同样检查满足；另含模型/运行产物写集；6坏包被拒 |

Prompt Writer 的16项逐条定位表和两案例详审见 [独立内部检查](INDEPENDENT_REVIEW.md)。各项只在文档设计范围内核对；未来实现可行性还要由真正Coder按AC运行证明。

## 已完成检查
| 实际检查 | 结果 | 证据 |
| --- | --- | --- |
| skill-creator quick_validate.py（三目录） | 3/3，exit0，Skill is valid | checks.json中的official_output与validator路径/hash |
| 自包含资源/UI metadata/交付链接 | 8处Skill资源全部有效，UI3份合法，文档链接均有效 | checks.json，链接总数以机器记录为准 |
| 两设计包和提示词 | 32 R / 40 AC / 25 Task，Goal0各12 AC无遗漏；依赖无环、禁权、无占位符 | cases/*/task-packet.json、checks.json |
| 校验器反例 | 两案例各6，共12个坏包全部拒绝；只是文档QA | checks.json中的negative_probes |
| 独立内部文档审查 | 修正后未发现残留必须修正项；不是外部验收 | INDEPENDENT_REVIEW.md、cases/*/evaluation.md |
| 参考截图/发行哈希只读核对 | 11张PNG尺寸与索引一致，正式ZIP/sidecar/当前状态SHA一致 | reference/source-inspection.json |
| 参考项目不变检查 | 35,839文件清单/大小/mtime不变，除node_modules外SHA不变，HEAD/分支/refs/status不变 | reference/before.json、after.json |
| Git/全局安装 | 新目录未初始化仓库，Git写操作0；三个Skills未安装全局 | 本轮工具操作、PROJECT_STATUS；参考Git只读快照 |

正式ZIP核对SHA：`d92fa5bf324233ed6588605356c0008e0c1231ecf94b9af1b60c00a91c48e23b`。这只是现有发行物文件检查，未重构、重打包或重测参考项目。

真实执行的完整交付命令：`.tools/validation-env/Scripts/python.exe -X utf8 scripts/validate_delivery.py --official-validator C:/Users/44725/.codex/skills/.system/skill-creator/scripts/quick_validate.py`。首次在B的evaluation未齐时返回exit1及missing evaluation；补齐后exit0。旧检查结果保存check-runs，不把产物未齐的检查伪装成通过。最后检查的时间、Python/PyYAML/平台和候选文件SHA详见checks.json。

## 实际发现与改进闭环
| 问题 | 处理和复核 |
| --- | --- |
| A手动preview与Playwright争用4173 | 手动smoke后先停本任务PID，再让Playwright自己启停 |
| A单元/组件与E2E范围不清 | Vitest明确include unit/component、exclude e2e；组件环境写明 |
| A损坏恢复不能依赖损坏epoch | 单独recover token/generation契约、确认才恢复 |
| B自动测试/状态来源标注失真 | 标为工程设计/Skill导出，不冒充案例用户明确 |
| B模型→迁移seed顺序/写集错位 | 初始化任务拥有models/apps/迁移seed；后续service任务排除这些路径 |
| B DEBUG=false静态资源入口缺失 | 固定WhiteNoise配置和真实静态HTTP检查，不假设gunicorn自己提供 |
| 缓存/临时/备份运行写集遗漏 | 仅进程级项目缓存/TEMP、运行产物写集和Docker专属例外明确 |
| Coder自测与独立Reviewer混淆 | 单Coder可执行实现和自测；独立审查由另人/Agent，完成停待外部验收 |

已将“前提产物/写集检查、模型→迁移seed、相关静态资源来源、单Coder自测与独立审查区别”补进Skills工作流，两个案例按修订重新核对。具体Issue-ID及修正定位在内部报告；没有把未经运行的工程设计问题说成实测业务bug。

## 已知限制
- 未找到历史原始对话提示词，风格是基于成果与本次用户指令归纳。
- 只验证两类文档链；未穷尽所有行业、PRD/招标附件、CLI/移动任务或长期实际Coder使用。
- 本轮没有实现两个案例，没有跑它们的浏览器/API/DB/构建/备份测试或生成业务截图，所有案例命令与预期均是未来任务。
- 全局安装/自动发现未实测；可按路径显式使用，用户级安装仅给说明。当前官方与本会话旧目录差异已披露。
- 参考node_modules只比较size/mtime，不逐文件做字节哈希；不比较access time。参考历史测试未重跑，内部Reviewer未独立重验参考源码。
- 多Agent调度、自动返工恢复、Git/冻结/Release尚未实现。task-packet与路线只作设计，QA脚本不是调度程序。
- 未提供本轮精确Token计数，不捏造节约比例。已用按需源码阅读、单份模板、自包含资源和窄范围修正减少重复；预算节约不替代核心验收证据。

## Reviewer 阅读顺序
先读 AGENTS / PROJECT_STATUS，再读 docs/SOURCE_EXPERIENCE，之后逐个 Skill 与必要资源，分别从案例 input 核对 plan→blueprint→prompt→packet，最后检查 evaluation、checks、独立内部报告和 reference/after.json。重点核对实际结果与拟定命令的区分、权限与停止规则。

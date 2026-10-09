# AC-012 历史资料装配与派发前预检

本模块只验证资料来源与可读性，不替Tester/Reviewer判断质量。原TaskPacket/12项AC、TesterResult/ReviewerResult schema和当前测试证据校验不改。历史自测不能代替本轮测试，无法验证的引用不自动标通过。

## 当前策略：当前交付严格验证，三条归档限制披露

外部Reviewer已审阅上一轮依赖、报告和计划，用户明确批准收敛AC-012历史审计范围。AC-012主要审查当前交付说明、R/AC/Task映射、真实命令与结果、当前源码指纹、日志/截图/trace索引、操作范围和验收状态；每项passed仍需真实本轮证据。

仅以下三条已确认的非关键归档引用为warning/unverified且不自动阻塞：

| 原始父记录 | 不可核实的引用 |
| --- | --- |
| validation/history-20261009-095808-578/goal0/acceptance.md | 同归档PROJECT_STATUS.md |
| validation/history-20261009-095732-444/goal0/source-sha256.json | tests/goal0.test.mjs，原索引SHA dab1ed47… |
| validation/history-20261009-095808-578/goal0/source-sha256.json | tests/goal0.test.mjs，原索引SHA dab1ed47… |

factory/history.py中按父记录相对路径、原始父文件完整SHA、引用及原期待SHA固定范围。父记录本身仍是必需来源：缺失、篡改或伪造completion不能享受豁免。其他未知依赖、当前关键证据和当前结论实际依赖的关键历史来源仍严格拒绝；直接从当前资料引用缺失文件不能继承归档豁免。不得借用新字节、改旧索引或继续无必要文件搜索。

archive_warnings在预检、上下文清单、角色索引/输入及新质量完成记录中持久披露。Tester应在本轮AC-012审查证据及reason中说明三条追溯限制，Reviewer在reason/summary中披露。它们不是当前AC的unverified结论；不将非关键warning塞入limitations再放宽全部语义校验。任何真正缺失的当前/关键证据必须按原规则unverified/blocked，不能靠这一说明隐藏。内部Reviewer决定不是外部验收。

2026-10-09最终最小收口：外部Reviewer逐条认定第三次Tester的四条limitations是非阻塞范围披露。factory/quality.py只对固定TaskPacket指纹、候选指纹及这四条原文开放Tester语义校验；未知或改写的说明、其他任务/候选仍拒绝批准，不使用关键词猜测。原始limitations保留在结果及独立复核记录中，不删除、不修改历史payload。AC失败/unverified、issues、缺引用、哈希或路径错误、缺实际build/test/runtime/浏览器证据仍阻塞；Reviewer的结果规则不继承该例外。

这只是原结果的零模型重校验，不是旧失败账本恢复成功或Reviewer批准。rv-548ec488c49d缺少accepted output.json及Tester通过检查点、原预算到期、旧工厂哈希固定；不得写回通过状态、重置授权或更新旧哈希绕过守护。现有机制不能安全接续时停止，不为此增加调度器或第四次Tester。

## 依赖闭包

factory/history.py 是无执行副作用的依赖解析辅助函数，供既有QualityGate.history_plan/history_files使用。入口为完成清单固定的acceptance.md、session-environment.json、source-sha256.json，以及当前候选Markdown交付说明。追踪Markdown文件引用、历史目录中的验收索引、JSON path/SHA256记录和文件名→SHA256索引；记录父引用、原工作区相对路径、completion SHA、类别、验证结果。循环用访问集合终止，限制256节点及8MiB文本索引。

每个必要依赖须存在、属于原completion.workspace_manifest且字节匹配。旧索引指定SHA时，不能只因当前文件同名就使用；归档中的PROJECT_STATUS引用不得落到最新状态。目录命名空间、../、绝对路径、源/副本的symlink或junction均经现有路径守护。历史JSON中Windows相对分隔符仅归一化表示法，不允许驱动器/穿越。

明确写为“计划产物，未生成”的历史行记录为declared_not_generated，不补造文件、不充当通过证据；若物理文件存在却未被完成清单固定，则拒绝。运行目录描述（如var/demo/store.json）与证据索引的必要依赖区别处理。日志、源码、PNG/trace是文件叶子，不把程序输出中的URL/栈路径当成可访问依赖。复用已核实的有限引用解析，不扩展扫描语法或历史搜索；不能宣称通用自然语言依赖解析。无法确定的必要依赖放入unverified且ready=false；只有上表固定三条归档缺口分入archive_warnings。

## 分离的上下文

- context/history：只复制闭包中经验证的历史材料，保留原字节，单独固定source/path/SHA及依赖关系，不复制整个validation或加入业务候选指纹。
- context/delivery：原TaskPacket、包校验、completion、Coder结果的字节副本。核验来源及副本SHA；当前候选说明文件已在测试workspace并由候选清单固定，不能据其自报通过。
- context/run-records：派发前当前候选/包/轮次/独立身份快照，明确不是已完成Agent结果。检查日志与环境预检归本轮artifacts；Tester的新证据仍放workspace/validation或.quality-evidence。

history-manifest和角色evidence-index分别提供这些组，不在提示词内重复嵌入所有历史日志/源码/图像。context路径只读审查，不允许改写。全部context元数据不能单独证明本轮AC passed，仍须当前测试/审查证据；原逐AC、CLI事件、浏览器两视口及trace门槛保留。Full Access路径和文件属性没有OS隔离能力。

## 模型派发前

新轮在context/dependency-preflight.json持久保存必需依赖完整性、三条归档warnings、当前候选/TaskPacket、ready和已有调用计数。任一必要来源缺失/哈希不匹配则在角色登记前停止，新增模型0。复制后verify_context再次核验来源、全部副本、清单、预检、快照和候选/包关联；每次Tester/Reviewer调用前继续执行同一核验，不能以旧预检绿灯复用变动资料。

预检仅是调用的必要条件。资料ready不等于真实AC-012通过；不改写上一轮ready=false或任何失败结论。不可改旧账本哈希来迁移两个失败轮次。未来真实复验使用现有revalidate-goal2.ps1另建独立RunId，经用户新授权；失败过或工厂哈希过期的旧RunId不重放。

## 历史发现与本次处理

2026-10-09闭包验证了38份历史材料、16份当前候选引用，仍有3条unverified依赖：一次归档验收引用的同轮PROJECT_STATUS记录不可确认，以及两份旧源码索引的tests/goal0.test.mjs哈希dab1ed47…在原完成清单中没有匹配留存字节。它们不能用最新状态、当前测试c618…或失败轮存档a368…代替。

上一轮将三条引用均视为必要依赖，因此资料预检拒绝，其历史报告保留原字节。按本次明确决定，这三条现仅作为未恢复的非关键追溯限制披露；当前实际必需资料预检可以ready。没有恢复这些字节，不修改历史声明、completion或AC定义，不声称真实Tester/Reviewer成功。详细原路径与哈希仍可查上一轮ac012-fix报告。

确定性检查：原Goal1/Goal2、test_quality_evidence、test_revalidation及test_history_dependencies；不得把AgentDouble结果冒充真实Tester/Reviewer成功。

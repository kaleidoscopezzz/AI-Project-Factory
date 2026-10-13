# AI Project Factory 项目状态

更新时间：2026-10-13，Asia/Shanghai。

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Goal 0 | 开发经验提炼与核心 Skills 建设 | 已验收冻结 |
| Goal 1 | Planner→TaskPacket→Coder 自动交接与基础验证 | 已验收冻结 |
| Goal 2 | 独立 Tester/Reviewer、有限返工与恢复 | 有限范围外部批准，已验收封版 |
| APF Goal 3 | 同一软件项目的两阶段串行执行 | 受控双阶段真实交付已批准封版 |
| Goal 4 | 受控 Git Agent 与批准来源版本记录 | 已批准封版 |
| Goal 5 | Release Agent 与发行交付 | 外部限定范围审查通过，已限定范围封版 |

## 当前产品整合：统一开发入口已实现，APF 1.0.0 真实全链验收未完成

开发基线为 main `427b3feb28a055faac13fff5777f53ea36b80c05`；Goal 0～5 原批准范围不变。新增 `apf --build` / `--resume`，保留 CLI 0.1.0 的两行版本及仅规划入口。产品适配直接复用 Controller、Sequence、QualityGate、Git Agent 和 Release Agent；安装包含工厂模块与原样 Skill。每轮最多两个 Goal、一次实现返工、十次模型调用，单次至多600秒、整轮墙钟3600秒；Token无硬上限。默认不提交软件Git，需显式 `--allow-local-git`，不自动Push。

已运行完整确定性回归387/387（585.192秒），恢复补充后定向94/94（109.234秒）；资料装配兼容初测97项有1项旧历史数量失败，收紧适用范围后最终98/98（202.737秒），另恢复兼容68/68（144.290秒）。新增产品/引用测试共31项，不将复测相加冒充独立测试数。最终安装后的版本、帮助、权限拒绝、工厂/Skill加载、Fake双阶段路径和完成恢复7项检查通过；原规划命令用原生Fake Codex真实生成三份UTF-8文件。Fake不等于真实模型质量批准，真实发行兼容性由既有Release Agent本地脚本测试独立覆盖。

本次唯一新待办场景调用真实Planner 1次和Goal0 Coder 1次。形成合法双阶段规划、独立Goal0 TaskPacket及源码；主控build/test均退出0，首次HTTP启动通过。Coder自测含实际Edge截图与Trace，不能替代独立Tester。材料装配因文档标签被误当缺失路径而阻塞：局部修复后34份实际依赖路径/SHA齐备，原失败质量账本未改，新零派发上下文保留来源与原预算，不冒称测试通过。

新上下文实际build/test继续退出0，但默认启动因遗留 `data/store.lock` 被拒绝，确认当前候选无法可信完成重复启动验证。独立Tester、Reviewer、CoderRepair均新增0次；软件Goal0未获正式质量批准，Goal1未执行，本次未生成合法发行ZIP。另发现原Planner运行参数/包布局不符合Release接口，现已在未来Coder派发前检查原有发行契约，并强化Planner技术参数说明；不重写本次原始计划、任务包或业务源码制造通过。

**本阶段是经过确定性验证的产品整合实现，不是APF 1.0.0正式发布或真实E2E通过。** 后续仍需修复软件锁生命周期，在新授权的有界真实验收中证明完整开发→独立质量批准→ZIP→解压业务运行链。真实自动返工闭环、换机体验和任意多Goal无人值守仍未验证；Full Access无OS隔离，Token无硬上限。使用见 [产品入口](docs/PRODUCT_USAGE.md)。下方历史记录保持其当时事实。

## 历史：CLI 0.1.0 接入主线时的产品整合记录

本轮以 main 文档提交 `11397200cb9bc7c4d63204508a0ade210488d7ee` 为基线，整合已提交 CLI 分支 `feat/cli-0.1.0` 的 `e38f432c520664cea97fb3c413dbd6e92c06f833`。使用普通 Merge，未以旧版本覆盖 Controller、QualityGate、Sequence、Git Agent 或 Release Agent。CLI Worktree 的原有未跟踪规划和证据保留，Goal 0～5 批准 Tag 不移动。

主线可在独立 Python 虚拟环境安装 `apf`，支持离线 `--version`（严格两行）和 `--help`，以及通过本机已安装且登录的 Codex 执行 `--prompt-generate`、可选 `--out`。提示词生成复用三个冻结 Skill 的完整原文，生成 UTF-8 的 requirements.md、goals.md、goal0-prompt.md 及私有运行记录；不会启动业务 Coder/Tester/Reviewer 或进入 Goal 3～5 的执行链。小范围兼容修改增加模型派发前的登录态检查，不读取认证文件或索取额外 API Key。

Windows / Python 3.14.6 独立环境真实安装成功，激活 PowerShell 后 Get-Command 找到该环境的 console script。已安装命令在非源码目录执行版本、帮助和两次原生 Fake Codex 规划，验证默认目录、中文 --out、UTF-8、文件覆盖保护、无 Codex/未登录/非法目录错误，以及 wheel 和源目录两个 Skill 来源的逐文件哈希。实际本机 Codex 0.162.0-alpha.17.2 只做版本、帮助、features 和登录态检查，未执行真实规划。

CLI 专项 47/47（17.177 秒）；包含 Goal 0～5 兼容功能的完整确定性回归 365/365（692.502 秒），失败、初始化错误、跳过均 0，保留既有 ResourceWarning 原始日志。新增真实 Planner/Coder/Tester/Reviewer/CoderRepair 模型调用全部 0；Fake 不等于真实模型规划验收。

**CLI 0.1.0 的提示词生成功能已接入主线，但 APF 1.0.0 的完整一句话自动开发、测试、版本管理与发行入口尚待最终产品化整合。** 新项目根 AGENTS.md 强制交付、详细需求忠实度验证、真实自动返工、任意多 Goal 无人值守、多模型/多 Agent 自由编排和 GUI 等明确延期。本轮不发布 APF 1.0.0、不新增批准 Tag，不修改历史阶段性质。安装与使用见 [CLI 文档](docs/CLI_USAGE.md)；原 PowerShell 开发入口继续有效。以下封版和开发记录保持其当时事实。

## 历史：Goal 5 封版文档同步时的状态

Goal 5 已完成外部限定范围审查并由用户完成源码封版。只读核验 main、HEAD、origin/main 和远端 main 均为 `3e02835593dc860618208fb69297d295648db693`；annotated Tag `goal-5-approved` 对象为 `3018b9b392e534d9d062ab213f735511606a3c03`，本地及远端一致，解引用至同一提交。本次后续文档提交不移动任何批准 Tag。

原始 Goal 0～5 六个研发里程碑已完成核心开发。Goal 2 保留有限范围批准；Goal 3 保留受控软件 Goal 0→Goal 1 双阶段批准；Goal 4 限于明确授权的本地 Git 版本；Goal 5 限于已批准候选的本地构建、ZIP 内容检查、独立解压启动与来源绑定交付记录。不得把历史未验证能力追溯改写成通过。

真实待办软件 Goal 1 已发行含 9 个文件的本地 ZIP，原包 SHA-256 为 `4bd82c79f9880ef6e3bada3c1a758f9a2691995aea9d92fee621a0d554559651`。解压后实际验证新增、编辑、完成状态、查询、删除和重启持久化。Windows 发行验证使用 Node.js 26.3.0；外部独立审查额外使用 Node.js 22.16.0 / Linux 验证核心服务，不代表完整跨平台发行链路。包仍依赖 Node.js，不是免安装 EXE；历史包保存在本地，未声称 GitHub 提供公开发布附件。使用方法见 [Goal 5 本地发行](docs/GOAL5_USAGE.md)。

APF 1.0.0 尚未正式发布，仍需 CLI 整合、统一用户入口和最终端到端体验验收。CLI 0.1.0 独立分支尚未合并 main，建议 Goal 6 产品化阶段尚未正式立项。AGENTS.md 强制生成、详细需求忠实度验证、真实自动返工、多模型和多 Agent 自由编排均为未来计划。Full Access 无 OS 隔离、Token 无硬上限、三条非关键历史引用 warning/unverified 等限制继续披露。自动 GitHub Push、云部署、通用 EXE 和安装器不属于当前能力。

本轮只同步公开文档，核对既有事实，不运行新的业务模型 Agent、构建或测试。下方开发记录正文保留原貌；其中“待审”“尚未开始”及旧 main 仅表示当时状态，不作为当前进度判断。

## 历史：Goal 5 开发完成时的待审记录

用户已批准 Goal 0～4；只读核验 `goal-4-approved` 为 annotated Tag，解引用至 `6e16dba7fd15bfb517c381b6e0eb152392aa2487`。本轮开发基线为 main `7a7705c672a04b9710cef136c48514f1c5927661`。下方原有章节保留当时表述，包括 Goal 4 开发期的待审状态，不代表重新打开已封版阶段。

新增确定性 Release Agent、Controller 阶段后接口、PowerShell 入口及中文说明；复用 Sequence 正式回执和 Git Agent 的只读真实质量来源校验，不重新派发模型。原待办软件 Goal 1 已批准候选在独立副本中真实构建和测试，发行 ZIP 在全新目录解压并通过包内启动脚本运行。真实检查覆盖界面资源、新增、查询、编辑、完成状态、重启持久化和删除；检查结束终止本轮进程树，并只读确认端口关闭。默认不上传、不修改 Git。

发行包为需要 Node.js 的 Windows 本机便携 ZIP，9 个文件、8,687 字节；不内置运行环境，不是单文件 EXE。实际验证环境 Node.js v26.3.0、Windows 11；说明要求 Node.js 22 或更高版本加入 PATH，其他 Node 版本未逐一验证。用户发行文件没有本机绝对路径、凭证或内部账本；构建专用测试脚本及浏览器日志不进入发行包。可选 Git Commit 仅读取验证，真实待办候选未建软件 Git 版本，记录明确为 null。

完整回归 316/316（434.355 秒，原 295 项兼容测试及当时 21 项发行测试）；补充可选 Git 来源边界后的最终定向回归 23/23（11.935 秒），合计 318 个不同测试，失败、初始化错误和跳过均 0。保留既有 ResourceWarning 原始输出。批准业务配方 build/test 真实退出均为 0，业务/Edge 检查脚本 33 条结果记录均 passed，其中包含阶段验收和证据记录，不折算为 33 个独立业务测试。

首次配置预检发现构建专用测试有本机工具引用；保持其字节且仅作为私有构建输入。随后一次真实构建副本漏列 package.json 导致测试最终退出 1，失败目录、日志和临时产物完整保留；补齐获批构建输入后新配置发行成功。没有修改原业务代码或旧批准记录，没有隐式重试失败发行。相同成功配置重放返回 already_released，不重建、不再次启动软件。

原项目、Skills 和既有改动共 1,085 份文件在状态更新前逐份复核不变；本轮仅另行增量更新本状态文件。主仓库 HEAD、批准 Tag、暂存区未变，不执行 Git 写操作；参考项目和 CLI Worktree 不访问、不修改。新增 Planner/Coder/Tester/Reviewer/CoderRepair 模型调用全部 0。

限制：首版仅支持明确批准的直接 Node/Python 脚本和回环 HTTP 检查；无自动依赖安装、运行环境捆绑、安装器、签名、远端 Release、Push 或部署。当前用户执行无 OS 隔离，敏感扫描为保守启发式；Token 无硬上限、真实自动返工未验证等原限制保留。使用说明见 [Goal 5 本地发行](docs/GOAL5_USAGE.md)。不创建 Goal 5 批准 Tag，等待外部审查。

## 历史：Goal 3 封版后的项目状态

用户已完成 Goal 3 正式封版与 GitHub 推送。Goal 3 封版基线为 `437a84b2e497b0020f0495a16c9f557351488856`，本次文档更新前 main、HEAD、origin/main 与远端 main 已核验一致；annotated tag `goal-3-approved` 对象 `dea42ac0c0dd562ce04a4d4fbcd353407f539dfa` 解引用至该提交。以下历史章节保留开发当时状态，不作为当前是否封版的判断依据。文档更新提交将继续在该批准提交之后推进 main，批准 Tag 不移动。

| APF 阶段 | 外部批准性质 |
| --- | --- |
| Goal 0 / Goal 1 | 已批准封版 |
| Goal 2 | 有限范围外部批准；不追溯宣称当时完成真实 Reviewer 或自动返工闭环 |
| Goal 3 | 受控双阶段真实交付批准；待办软件 Goal 0、Goal 1 均有真实独立质量批准 |

Goal 3 复用原规划并以不同 TaskPacket、新候选完成软件 Goal 1 的编辑、完成状态、筛选与旧数据兼容；真实 Coder、Tester、只读 Reviewer 执行，阶段回执保存来源与证据，完成续跑不重复派发。封版前确定性回归 260/260；文档维护只核对现有记录，不重新执行真实 Agent 或业务 E2E。公开范围摘要见 [已验证能力](docs/VERIFIED_CAPABILITIES.md)。

仍未验证真实 CoderRepair→再次 Tester/Reviewer 闭环；任意数量 Goal 无人干预执行、自动后续任务生成、自动 Git/发行和普通用户零配置入口尚未完成。Full Access 无 OS 隔离、Token 无硬上限，三条非关键历史归档引用仍 warning/unverified。Goal 3 批准不消除这些限制，也不重新打开 Goal 2。

当前建设阶段为 Goal 4，Goal 5 职能保持原路线图；建议 Goal 6 为产品化与一键体验，未作为原始路线图已批准阶段。独立 CLI 0.1.0 未合并 main。未来新项目根 AGENTS.md 强制生成/验收规范未实施，历史批准不追溯失效。

## 历史：Goal 4 开发完成时的待审记录

基于已批准 Goal 3 主线添加 `factory/git_agent.py`、Controller 的阶段后接口及 `scripts/git-stage.ps1`。默认只读；显式项目策略授权初始化/本地提交，复用正式 Sequence 回执、候选与 TaskPacket 指纹、真实 Tester/Reviewer 批准来源。明确交付文件逐份暂存，Git 树字节与批准清单一致，版本记录保存实际 Commit、阶段、授权和批准 SHA；未改变原质量状态机或旧账本。

验证：原有 260 项兼容回归通过。初次完整回归 288/288（含当时 28 项 Git 测试，443.433 秒）；最终 Git 定向回归 34/34（37.346 秒），另有真实 Git 与两阶段 Sequence 串联测试 1/1（9.832 秒），共 295 个不同测试通过，失败/初始化错误/跳过均 0，原始日志保留 ResourceWarning。真实 git.exe 仅作用于新隔离测试仓库，验证初始化、既有仓库读取、实际 Commit/内容、重复请求、无变更、拒绝与错误保全、提交后中断恢复；PowerShell 正式入口只读检查通过。

质量输入为明确标记的契约夹具，Git 操作集成测试替换质量来源验证；生产来源校验拒绝 AgentDouble。另只读确认现有真实待办软件 Goal 1 批准来源可识别，未在历史业务目录执行 Git 写入，未新增真实开发 Agent 调用。不能把本轮 Git 集成测试写成新一轮真实软件质量验收。

本轮主仓库 HEAD 保持文档维护基线 `cdb4fbc9cd7d587d9b0f1f1f874162db354caa4d`；既有 Goal 0～3 Tag 不移动，原有未提交改动不收口。没有主仓库 Git 写操作。新测试仓库原件保留在验证区，局部忽略规则只排除新增临时仓库，源码、日志和结果摘要不排除。

仍未实现外部验收自动化、自动 Tag/冻结、远端创建/Push 和 Goal 5 发行；均需要独立范围与授权。Git 操作入口是显式阶段后调用，不代表任意多阶段无人干预交付。敏感检查为保守启发式，不保证识别所有秘密；同用户并发或恶意篡改不具备 OS 防护。既有 Full Access 无 OS 隔离、Token 无硬上限和真实自动返工未验证限制保留。使用方法见 [Goal 4 本地 Git](docs/GOAL4_USAGE.md)。Goal 4 尚未外部批准，不创建批准 Tag。

以下是历史事实的公开保留版：本机绝对路径、原始线程/运行标识及私人运行位置用通用说明替代，失败次数、结论、验证性质与已知限制保留。原始历史证据与账本本次不修改。

## 历史：软件 Goal 1 内部质量批准，等待 APF 外部封版

当前 main、HEAD、origin/main 与远端 main 均为 2755392535b02cc92d34f18f14f23be327b46748，属于用户提交的 Goal 3 WIP；Goal 2 批准 Tag 对象仍为 2fd33d9d0527f27034072124bb3e89356a6c461c，解引用至 551107e1041ce55570a9ec0fd396d55666ec0156。没有本轮 Git 写入。

复用 <已归档项目或执行ID> 及原 Planner 的 AC-101..104，经现有 Sequence 在已批准 Goal 0 工程上完成编辑、完成状态、三类筛选和旧数据兼容。独立 Goal 1 TaskPacket 指纹 2a62575bf78da0360efe32d12c437376fa9bcde2004742b03bc7d3b5e10a148d；新业务候选 209fc3ca875363d86a5a37e651cfbefe55f6c1e120adf06cbb4d3df9e21527a9。原 Goal 0 包、批准快照及历史未覆盖。

本轮真实调用 Planner 0、Coder 1、CoderRepair 0、Tester 1、只读 Reviewer 1。Tester 原始四项正式 AC passed，独立构建、业务及 Edge 双视口证据有效；Reviewer 原始 decision=approved。原 Reviewer 另列一项非正式 AC-012 补充交付审查，完整保留在来源绑定的范围复核记录中，正式 AC 视图为原规划四项；没有新 Tester/Reviewer 调用或人工改写原始 JSON。宿主输入后缀与源码引用校验问题经局部修复后，现有 QualityGate 和 Sequence 生成正式阶段回执，89 份完成引用验证通过；已完成续跑新增模型调用 0。

最终确定性回归 260/260（253.378 秒），失败/初始化错误/跳过均 0，原始日志保留 ResourceWarning 说明。阶段来源为 <该轮历史验证归档> 与原项目 control/sequence/goal1-completion.json。交付说明、真实用量、回归与保护结果统一见同目录 FINAL_REPORT.md；旧准备失败、质量失败账本及首次 Coder 自测失败均保留。本轮没有软件 Goal 2 执行。

真实 Coder 自动返工模型闭环仍未验证。Full Access 无 OS 工作区隔离，Token 无硬上限；移动验收为已安装 Edge 的视口模拟。两阶段真实接续成立，尚不代表任意数量 Goal 从一句话全自动完成、发行交付或 APF Goal 3 外部批准。

## 历史基线：Goal 2 已由用户手动完成有限范围封版

2026-10-09用户亲自完成并核验Git收口及GitHub推送。只读核对main/HEAD/本地与远端main为551107e1041ce55570a9ec0fd396d55666ec0156；annotated tag goal-2-approved对象2fd33d9d0527f27034072124bb3e89356a6c461c，解引用至同一Commit，本地与远端对象一致。Goal0/Goal1既有Tag不变。暂存区空；原图书state/events/quality与探针遗留属于已核对的历史文件，不自动清理或重提交。

批准性质是有限范围外部批准，已经封版；真实Tester与第三次12项AC/27条引用的确定性重校验、Windows 194项回归及外部静态审查已有依据。真实独立Reviewer批准和自动返工模型闭环仍未验证，Full Access无OS隔离、Token无硬上限、三条历史warning/unverified继续披露，但不据此重开Goal2验收。本轮不修复、重验或提交Goal2。

APF自身Goal3与生成软件的Goal0/Goal1不同。本轮采用用户批准的两阶段串行第一增量，保留旧路线图的依赖/整合方向，复用现有Controller/TaskPacket/QualityGate；不开发并发DAG、Git/发行或通用审计平台。新真实模型调用未授权，只执行本地确定性夹具。历史段落均保留原貌。

## 历史：APF Goal 3 两阶段串行第一增量已停止，待外部审查

新增开发API prepare_goal_sequence/run_goal_sequence，复用现有Controller与QualityGate。完整原始需求/计划保留，调用者先确认软件Goal1独立提示词、AC/运行契约；软件Goal0质量门槛通过后才建立独立Goal1任务包1.1、state/events与质量记录，在同一workspace增量开发。旧包1.0及单任务入口保持兼容，已登记串行项目禁止从旧Auto入口重跑Goal0。没有新增正式CLI参数或修改根README。

本轮确定性结果212/212：原Goal1 41、Goal2兼容62、证据18、复验执行器32、历史27、语义14，以及新增两阶段18。明确标记AgentDouble的项目p-49486fcfac43完成软件Goal0→Goal1，保留基础源码、使用独立Goal1 AC/提示词/TaskPacket及现有质量门槛。完成阶段续跑、完成检查点到游标间的中断恢复没有重复派发；缺入口条件/有效包、错误依赖、篡改、跨workspace、删除前序源码、越出写集及质量失败均拒绝或停止。未知部分调用中断仍停止等待人工，不开发新恢复执行器或隐式重试。

Planner/Coder/Tester/Reviewer本轮新增真实调用均0，未运行真实业务E2E或浏览器。确定性通过不等于真实Reviewer批准或完整软件交付；真实自动返工仍未验证。本增量固定两个软件Goal，后续阶段提示词与范围需要调用者明确确认，自动后续规划/任意Goal/并发/Git/Release未实现，APF Goal3整体未宣布完成。

新增factory/sequence.py、tests/test_sequence.py、docs/GOAL3_INCREMENT.md及Goal3测试目录忽略规则；最小修改controller.py/contracts.py与当前状态。Goal2质量实现、历史报告/账本、原图书源码、冻结Skills与历史Tag保持不变；不访问<项目目录或受保护目录>，无Git写入。当前基线仍551107e1041ce55570a9ec0fd396d55666ec0156/goal-2-approved，暂存区空。证据见<该轮历史验证归档>。

下一次真实验证需另获授权：新非UI小项目，Planner最多1，两个阶段Coder/Tester/只读Reviewer各最多1，共最多7；每调用最多600秒、无Retry/NoAutoRepair，任一质量门槛未通过停止。仅为计划，不执行。Full Access无OS隔离、Token无硬上限继续披露。完成第一增量后停止，等待外部ChatGPT Reviewer审查，不自行Git封版。

## 历史：Goal 2 2026-10-09 有限范围收口，停止开发

用户已决定停止反复真实验证和恢复机制扩张；外部ChatGPT Reviewer同意按有限范围进入最终代码与证据审查。现有Tester、Reviewer、DefectPacket、有限返工、证据校验和恢复实现全部保留，本轮不修改实现、不新增测试/质量协议/审计工具、不尝试接续第三次失败账本。

真实Tester已经执行。第三次原始结果的12项AC、27条证据引用已通过整改后的确定性零模型重校验；原四条limitations及三条非关键历史归档warning继续如实披露。194项确定性回归记录已核对，本轮没有重新运行回归、业务E2E或浏览器。

真实独立Reviewer尚未执行，真实自动返工闭环未验证；不把这些实现或替身回归写成真实质量闭环通过。Full Access没有OS级工作区隔离，Token没有硬上限。旧执行失败状态、三次Tester原始结果、state/events/quality与历史证据保持原字节，独立新复核不覆盖旧判断。

本轮只更新当前状态并整理精简外部Reviewer ZIP，包含Goal2新增/修改源码（含未跟踪文件）、相对Goal1的差异、194项原始日志、原Tester与零模型复核、必要业务/浏览器证据、保护结果及限制。收口材料位于<该轮历史验证归档>。Goal0/Goal1、原业务源码、参考项目和历史Tag不变；无Git写入，不开始Goal3。

**Goal 2 核心实现完成，有限范围外部验收待审查。** 该状态不代表内部Reviewer批准、完整真实闭环或外部验收通过。生成验收包后停止，等待外部ChatGPT Reviewer审查。

## 历史：Goal 2 2026-10-09 最终最小语义收口已停止

外部ChatGPT Reviewer已审阅第三次真实验证及遗留清单，认定原四条limitations均为非阻塞范围说明。本轮只修改factory/quality.py的Tester结果语义：精确绑定原TaskPacket、当前候选指纹和四条原文；其他未知limitations、AC未通过、issues、缺证据或必要检查缺失仍阻塞。结果schema、12项AC和全部原始结果/证据未修改。

独立零模型复核通过：原始Tester结果、候选16文件、TaskPacket、12份复用来源及全部本轮证据哈希有效；12项AC/27条引用通过完整现有校验器，四条limitations与三条历史warning完整披露。新判断单独保存于<该轮历史验证归档>，不写回旧state/events/quality，也不把历史失败改为通过。

实际确定性回归194/194：原Goal1 41、Goal2 62、证据18、复验执行器32、历史依赖27，新增语义14。没有重新运行业务E2E/浏览器，Planner/Coder/Tester/Reviewer新增真实调用全部0。

现有机制不能安全接续Reviewer：旧调用failed，缺accepted output.json且round.tester为空；原1800秒预算已到期，准备账本的工厂哈希也与本轮获准修改不同。恢复只接受完整已接收检查点，不能通过新判断伪造旧检查点、重置计时或改旧守护哈希。按用户条件授权停止，Reviewer未启动，未创建新执行器或第四次Tester。独立复核不等于真实Reviewer决定或Goal2外部验收。

本轮报告<该轮历史验证归档>。原三次失败、冻结44文件、原图书项目、参考项目与Git基线保护检查通过；无Git写入。未满足Reviewer approved条件，不生成成功验收ZIP，不标记开发完成。真实自动返工仍未验证，Full Access无OS隔离，Token无硬上限。

**Goal 2：开发中，待真实验证；已停止，等待人工决定及外部Reviewer审查。**

## 历史：Goal 2 2026-10-09 最终真实收口验证已停止

用户明确授权新独立RunId <已归档项目或执行ID>，仅Tester最多1、合法通过后只读Reviewer最多1，Planner/Coder/返工0，NoAutoRepair/无Retry。12份来源、当前候选/原包、3条warning分类、冻结守护、CLI/Node/Edge预检有效；复用既有180/180回归记录，没有新增功能或改协议/schema/状态机。

官方入口退出1：Tester真实调用1，CLI退出0、未超时、524.192秒，线程<已归档独立调用ID>。12项AC均自报passed且27条路径/SHA有效，真实业务5/5、双视口PNG及Trace有新证据；但顶层limitations含4条范围/执行说明，与既有passed不得含limitations规则冲突，主控正确拒绝。三条历史warning已在AC-012披露，并非本次阻塞；没有发现新的失败业务断言，不代表无缺陷或质量通过。Reviewer0、返工0，不启动第四次Tester。

实际usage input 429059（cached 376576）、output 8826、reasoning output 493为CLI字段子项，不重复计数。原两次失败、本次原始payload/失败状态均保存，未删limitations、改结果或放宽校验器。guard复核冻结、原业务、旧账本、参考、Git基线无变化，暂存区空。本轮只增加独立上下文/报告及本文状态，无Git写操作。

报告<该轮历史验证归档>，遗留清单FINAL_REMAINING_ISSUES.md。原始执行在<该轮历史验证归档>；被拒绝结果没有accepted output.json，报告副本仅原样提取。未生成通过验收ZIP，未标开发完成。自动返工未真实验证，Full Access无OS隔离、无Token硬上限。

**Goal 2：开发中，待真实验证；本轮已停止，等待人工决定。** 不自动重试、继续整改/审计、开始Goal3或Git封版。

## 历史：Goal 2 2026-10-09 AC-012策略收敛

外部Reviewer审阅上一轮依赖及报告后，用户明确决定：当前有效交付与关键来源严格验证；仅已确认的三条非关键归档引用以warning/unverified披露，不自动阻塞质量门槛。原12项AC、结果schema和当前测试证据校验不变。必需文件缺失、哈希错误、篡改或候选/任务包变化仍须拒绝。

现有factory/history.py仅按固定父路径、原始父SHA、引用与期待SHA识别3条限制，不增加历史搜索或调度器。当前资料预检ready=true，3条归档引用仍unverified；未恢复/伪造文件、未借用新版哈希、未改旧索引。增加原完成清单根目录交付文档缺失的拒绝。两次真实Tester失败、旧state/events/quality及历史ready=false保留原字节，不替AC-012判passed。

最终确定性回归Goal1 41/41、Goal2 62/62、证据18/18、复验执行器32/32、历史专项27/27，共180项通过。替身验证3条限制不阻碍进入Tester，故意无输出仍失败且Reviewer不启动；关键证据缺失/篡改、伪造SHA、扩大归档豁免、未验证AC冒充passed仍拒绝。中间失败日志保留，修正后全套重跑通过。

真实Planner/Coder/Tester/Reviewer调用均0，无新业务E2E/浏览器运行/Git写操作。报告 <该轮历史验证归档>，原41+62最终回归 <该轮历史验证归档>。Full Access无OS工作区隔离，无Token硬上限，自动返工未真实验证。新真实复验须用现有执行器另建RunId并取得新授权；CLI/环境预检及真实质量决定本轮未运行。

**Goal 2：开发中，待真实验证。** 完成策略整改与确定性验证后停止，等待外部审阅及新的真实调用授权。

## 历史：Goal 2 2026-10-09 AC-012历史依赖整改

本轮仅修复历史装配及模型派发前资料完整性预检，真实Planner/Coder/Tester/Reviewer均0，无业务E2E或浏览器新运行。原TaskPacket/AC及结果schema不改；现有QualityGate仍承担唯一质量状态机。新增factory/history.py依赖解析辅助、tests/test_history_dependencies.py，增量修改factory/quality.py的history/context/索引与预检；交付记录、派发前快照、本轮日志和历史材料分类引用，context元数据不能单独证明本轮AC通过。

完整依赖检查超出事后11份抽查：验证38份历史资料、16份当前候选引用及116条来源边，记录6项历史明确“计划产物未生成”。仍有3条unverified必要依赖：一次归档验收的同轮PROJECT_STATUS无法确认；两份旧源码索引引用tests/goal0.test.mjs的dab1ed47…哈希，在原完成清单中没有匹配字节。不得以最新状态、当前c618…测试或失败轮a368…存档补证。实际history_files预检已拒绝且未初始化Agent，未创建新的可执行复验上下文、未重放两个失败轮次。

38份必要历史字节在本轮非执行审查preview内逐份复制并验证来源/completion/副本SHA，覆盖原11份原件，不复制整个validation。原两次失败与旧state/events/quality/RunId不改变。最终确定性回归：Goal1 41/41、Goal2 62/62、证据18/18、复验执行器32/32、新依赖20/20，共173项通过；合法夹具不代表真实资料齐备或真实AC通过。报告<该轮历史验证归档>；原41+62最终日志<该轮历史验证归档>。详细依赖、哈希、unverified、预检拒绝和保护记录保存本轮目录。

**Goal 2：开发中，待真实验证。** 未授权/未调用真实Agent，无Git写操作。实际资料尚不具备下一次模型调用条件；等待外部Reviewer审查来源缺口和新的处理授权，不提前完成或Git封版。

## 历史：Goal 2 2026-10-09 一次独立真实复验已停止

本次用户明确授权 goal2-revalidation-approved-01 / <已归档项目或执行ID>。来源12份、候选16文件、原完成记录、CLI与冻结基线预核验通过后，官方入口仅执行1次，无Retry、无返工；原图书项目及首轮失败账本不变，新进度和证据仅在独立上下文/新报告目录保存。

独立Tester真实调用1次，thread <已归档独立调用ID>，Full Access，CLI退出0、无超时、331.012秒，实际usage输入260304（cached input222592）、输出5796（reasoning337为输出子集）。结构化与证据校验合法，结果blocked：AC-001至AC-011自报passed且每项引用路径/SHA有效，AC-012 unverified。历史验收文档引用的构建/测试/失败轮等资料未提供到受控历史上下文，不能核验完整性；事后只读抽查11份原件存在且匹配原完成哈希，不据此补改Tester结果或宣布通过。

主控构建/测试退出0，Tester独立业务测试5/5，Edge双视口PNG与trace、刷新/持久化/进程重启/故障503有本轮实际证据。主控接收blocked后停止、退出1，总运行414.585秒；Reviewer0、Planner0、初始Coder0、返工0，内部Reviewer决定未发生。仍未验证真实独立Reviewer通过或自动返工，不能宣称Goal2成功质量闭环或外部验收。报告 <该轮历史验证归档>；12项证据审核、usage、来源、截图/trace索引与守护结果保存同目录。

原项目238非缓存文件、此前39历史报告、冻结44文件、参考35839文件及19历史探针无异常；Git main/Goal1仍adf6800、Goal0仍11aa80e，暂存区为空，无Git写操作。Full Access无OS工作区隔离，无Token硬上限。Tester一次额度已耗用，Reviewer进入条件不满足，不执行新的调用。

**Goal 2：开发中，待真实验证。** 本次已停止，等待外部ChatGPT Reviewer审查blocked原因与后续范围，不开始Goal3。

## 历史：Goal 2 2026-10-09 独立复验执行器准备

用户本轮仅授权最小独立质量复验入口和确定性验证，未授权真实 Planner/Coder/Tester/Reviewer。新增 factory/revalidation.py、scripts/revalidate-goal2.ps1 和 tests/test_revalidation.py；复用现有 QualityGate 状态机，只增加来源/原项目锁/独立身份/单次派发和预算守护。原 state/events、首次 Tester 失败和旧 quality 账本保持不变；没有更新旧账本的工厂哈希。原完成来源及元数据哈希经历史容器验证，新控制副本分别记录来源与 SHA256。

准备与真实执行分离；Prepare 不初始化模型，Execute 必须另获本次明确授权。有效预算强制 Planner/Coder/返工0、Tester最多1、合法通过后只读Reviewer最多1、NoAutoRepair、无Retry，每Agent最多600秒，总墙钟1800秒且恢复不重置。Full Access仍无OS工作区隔离，无Token硬上限。当前实现和新回归报告保存于 <该轮历史验证归档>，使用说明 docs/GOAL2_REVALIDATION.md；本轮没有新的真实模型或业务E2E，不能把确定性通过称为真实验收。

最终确定性回归原Goal1 41/41、既有Goal2 62/62、证据专项18/18、独立执行器32/32，共153项通过；原41+62日志在 <该轮历史验证归档>，其余两组及原历史隔离检查在本轮报告目录。首次数值未运行的语法检查失败日志保留，修正后30项首验及新增两项最终32项日志均保留。冻结44文件、原项目238非缓存文件、先前39报告文件、参考35839文件及19历史探针无差异；当前暂存区为空，Git基线未变。

**Goal 2：开发中，待真实验证。** 完成准备后停止，等待用户明确批准一次真实Tester/Reviewer复验。

## 历史：Goal 2 2026-10-09 首轮 Tester 失败专项整改

本轮用户只授权诊断和最小整改，真实 Planner/Coder/Tester/Reviewer 新增调用均0，不运行业务E2E、不修改冻结Skills/Goal1入口/原图书源码及历史证据、不进行Git写操作。查明：CLI最终消息与原result/execution完全一致，9项AC在Agent原始输出中就缺逐项evidence；提示词仅明确checks证据而未明确每项AC绑定，schema允许空数组供unverified使用，语义校验正确拒绝。不能从这一次输出证明模型内部遗漏的心理原因。

AC-012所需原 `workspace/validation/goal0/acceptance.md`、`session-environment.json` 存在且SHA与原完成记录有效；副本按GENERATED_ROOTS排除validation、没有提供独立历史上下文。三份补充历史资料（含source-sha256.json）现在只在新轮次context/history复制、哈希绑定和只读属性保护，不加入候选业务指纹；历史属性/事后守护不是Full Access的OS隔离。

最小改动仅 `factory/quality.py`、新 `tests/test_quality_evidence.py`、`docs/GOAL2_USAGE.md` 和本文状态。提示词明确每项AC格式、unverified规则、受控文件索引、runtime及browser证据放置；保留严格语义拒绝，不补填原结果，不允许历史绿灯单独证明当前通过。基础检查重复信息用摘要和索引代替，12项AC及候选指纹保持原文；输入上下文字节减少，新增规则使总提示词略增，未声称Token实耗下降或硬上限。

最终回归：原Goal1 41/41、既有Goal2 62/62、新证据夹具18/18，共121项通过（全部Agent控制为确定性替身，不能冒充真实质量成功）。原始failed TesterResult重放仍报“AC 无证据”；正确引用、历史资料缺失/篡改、候选变化及越界/伪造拒绝均有回归。报告 `<该轮历史验证归档>`，最终原41+62回归 `<该轮历史验证归档>`。首轮全部失败日志/历史usage及原工程无变；守护复核冻结44文件、参考35839文件和Git main/Tag基线通过，暂存区为空。

旧quality账本绑定旧工厂哈希，原失败状态不改写。新复验须另行批准、先创建保留旧记录的独立质量控制上下文，不能直接Retry绕过守护；本轮只形成方案 `NEXT_REAL_VALIDATION_PLAN.md`，未实现或运行该准备执行器。建议Tester最多1、通过后只读Reviewer最多1，每Agent600秒，Planner/Coder/返工0，无Retry；权限不扩大，预算剩余不能当授权。

**Goal 2：开发中，待真实验证。** 本轮停止，未经新的明确授权不调用真实Agent，不宣布完成，不进入Git或Goal3。

## 历史：Goal 2 2026-10-09 一次已授权真实验证结果

用户明确授权依照原 REAL_VALIDATION_PLAN 执行一次既有图书候选的真实质量验证，显式 Full Access / NoAutoRepair，无 Retry。原任务完成记录、TaskPacket、候选和已提交阶段材料校验通过；CheckCli 与固定 Node/Edge 环境预检通过。原 Planner/Coder 完成记录直接复用，没有新规划或开发调用。

官方入口只运行一次，退出 1，耗时 339.938 秒。独立 Tester 调用 1 次，thread `<已归档独立调用ID>`，进程退出 0、无超时、耗时 270.570 秒；实际 usage 为 input 257575（其中 cached input 220672）、output 4435（reasoning output 212，按 CLI 原字段记录）。Reviewer 0 次、初始 Coder 0 次、返工 Coder 0 次、Planner 0 次，质量轮次 1。CLI 同一次调用内有 4 条网络重连错误事件，未追加 APF 调用或重试。

副本主控构建/测试退出 0，真实业务测试 5/5，Edge 交互、刷新/服务重启、故障分类、两视口 PNG 和 trace 有实际新证据；Tester 又在副本证据目录内重跑未修改源码的构建/5 项测试及补充浏览器检查。以上局部成功不等于质量链路通过。

Tester 原始结构化结论为 failed：AC-001 至 AC-011 自报 passed，AC-012 failed（测试副本缺失文档引用的 acceptance.md 和 session-environment.json）。两份文件实际存在于原工作区；副本生成排除了 validation/，没有提供这些历史文档。另有 9 项 AC 的逐项 evidence 为空，主控以“AC 无证据”拒绝该结果，没有接收 Tester 检查点，没有调用 Reviewer、修复或第二轮。原始日志/结果均保留，不将退出 0 或测试 5/5 写成验收通过。

报告：`<该轮历史验证归档>`，同目录 RESULTS、acceptance-audit、guard-final、quality-evidence-index 和最终哈希清单。44 个冻结文件、原项目 146 个非缓存文件（只允许 control/state.json 与 events.jsonl 本轮进度变化）、19 个历史探针及参考项目 35839 文件按既定覆盖无异常；Git main/HEAD/Goal0/Goal1 Tag 未变、暂存区为空、未执行 Git 写操作。有限守护不能证明 Full Access 的操作系统级隔离或宿主全域安全。

**Goal 2：开发中，最小真实验证未通过，未完成。** 本次授权已用完 Tester 的一次调用，Reviewer 条件不满足；未使用的 Reviewer 预算不允许绕过门槛继续执行。已停止，等待外部 ChatGPT Reviewer 审查失败证据和后续整改范围。真实 Reviewer/自动返工及新的成功质量 E2E 仍未验证，不代表外部批准或 Git 冻结。

## 历史：Goal 2 2026-10-09 实施与真实验证授权前节点

以下保留本次授权之前的实现和确定性回归阶段记录；其中“待授权”“真实调用为零”等仅描述当时状态，当前结果以上节为准。

当前冻结基线：main / `adf680014853618a5f512aae08a47ee55c5dd64c` / annotated `goal-1-approved`；Goal0仍为11aa80e / goal-0-approved。Goal1 Git收口已完成，下面“准备冻结”的描述保留为收口前历史。本Goal2开发禁止Git写操作。

已在现有主控增量加入QualityGate：独立Tester候选副本、只读Reviewer、Tester/Reviewer/DefectPacket契约、稳定源码与证据指纹、按缺陷分类的两次返工/三轮验证、分角色调用/时长硬预算、持久调用登记与中断检查点恢复。默认权限不放宽，FullAccess/CodexPath/CheckCli保持；NoAutoRepair可限制本次只验收不派发返工Coder。内部approved只覆盖当前TaskPacket，不代表APF外部验收、Git冻结或发行。

最终原41/41项回归、新增62/62项Goal2测试通过，证据 `<该轮历史验证归档>`。全部使用明确AgentDouble验证业务/模型控制逻辑；可信本地超时、脱敏、进程身份和junction拒绝用例包含真实本机进程/文件操作。历史失败记录保留，最新最终回归结果以阶段REPORT链接为准。没有调用真实Planner/Coder/Tester/Reviewer，没有新业务E2E或大型浏览器验收。

真实Tester/Reviewer调用与真实自动返工均未验证；不能把确定性回归标为真实质量链路完成。最小真实方案在 `<该轮历史验证归档>`：复用p-dc1e9d42b5ae原规划及任务包，最多Tester1+Reviewer1、每次600秒，NoAutoRepair阻止任何返工Coder；需用户另行批准本次FullAccess。原工作区不重建，证据写入新增质量目录，失败即停且不Retry。

限制：FullAccess无OS工作区隔离；无Token硬上限，真实usage缺失标unknown；新技术栈/缺依赖需blocked；证据哈希及CLI工具事件不能独自证明语义充分；Coder部分执行中断/重大歧义需要人工审查，不自动重放可能有副作用的操作；不支持全部后续业务Goal、多任务DAG、Git/Release。冻结文件/原图书交付/参考项目及Git基线按本阶段守护检查复核，不将有限检查声称宿主全域安全证明。

**Goal 2：实现与确定性回归已推进，待真实验证授权，尚未完成。** 按原任务第八、十节要求，在该授权节点暂停；最终还需真实独立Tester/Reviewer证据与外部ChatGPT验收。

## Goal 1 当前授权与基线（历史）
用户已授权 Goal 1 实施。执行前只读核验：main / `11aa80e1dc345d63f9b325d14227b078c0f924bb`，`goal-0-approved` 解引用到同一 Commit，工作区干净。下方 Goal 0 的“尚无仓库”“等待手动冻结”“自动交接尚未实现”等文字保留为当时的历史记录，不代表当前阶段。

本阶段只建设 Planner→TaskPacket→Coder→基础验证→结果回收。冻结 Skills、历史案例和报告保持原样；新验证写入 `validation/goal1/`，生成工程写入 `projects/`。开发期间禁止 Git 写操作；以下用户另行批准的最终收口仅授权当前 Goal 1 的提交、annotated tag 与 main/Tag push，不授权重写历史或下一阶段。

## Goal 1：外部验收批准与 Git 收口

结论来源：用户本轮转述外部 ChatGPT Reviewer 第二轮验收正式结论 **Goal 1 — REVIEWER APPROVED**。批准范围为 Planner→TaskPacket→Coder 自动交接、基础验证、失败恢复，以及新需求 Full Access 与 CodexPath 入口整改；不将该通知扩大为完整软件开发工厂的最终验收。

真实 Planner/Coder 分阶段执行并恢复成功：原独立 Planner 规划与任务包自动交接给真实 Coder，失败记录保留；随后复用规划/包进行一次经明确授权的 Full Access 恢复，Coder 与主控真实构建/业务/浏览器验证成功。真实业务测试5/5、此前主控回归31/31；整改后主控回归41/41（含明确标记的AgentDouble，原31覆盖中1项按新要求更新）。已完成任务恢复复用结果、调用数保持3，无重复规划/开发。

新需求 `-Request ... -Mode Auto -FullAccess` 目前经过替身控制测试，尚未进行全新任务真实E2E。Planner保持只读、Coder/检查只在调用者显式选择后使用当前用户权限。独立Windows PowerShell移除Codex PATH后，`-CheckCli -CodexPath` 真实确认文件及codex-cli 0.162.0-alpha.2版本，退出0；该检查没有验证新任务模型执行、登录或业务验收。

Full Access 无操作系统级工作区隔离，指定workspace和指纹复核不是OS安全保证；Token尚无硬上限，现有硬限制为调用数、超时及有限重试。原Windows受限令牌管道EPERM、Chrome/Edge IPC失败、本轮前503分类失败及恢复记录均保留，不篡改历史结果。未实施完整Tester/Reviewer/Git/Release自动化，未开始Goal2。

提交前已复核：main/HEAD/goal-0-approved仍为11aa80e1dc345d63f9b325d14227b078c0f924bb，批准整改版本22文件哈希一致；44份冻结文件及参考项目35839文件在既定覆盖内无差异，相关源码与证据没有未知变化。Goal1源码、文档、必要原始日志/规划/截图/trace按明确文件清单纳入；测试工作区、.factory-tmp、运行数据var、构建缓存、运行锁、凭据和私人配置不纳入。

本次仅增加Git元数据规则：projects/.gitignore排除临时运行目录和锁；.gitattributes对Goal1路径关闭文本换行转换，保持批准证据字节哈希，不改变Goal0文件或全局配置。旧manifest中当前源码/状态字节哈希属于各次历史候选，本次状态收口另有前后记录，不回写旧哈希。提交前清单与复核见 `<该轮历史验证归档>`。

用户授权提交说明 `feat(apf): approve goal 1 planner-coder orchestration`、annotated tag `goal-1-approved`，推送已有GitHub origin的main及该Tag。本文随批准提交冻结；实际commit/Tag/远程一致性以收口后的Git记录和最终报告为准，不提前伪造推送结果。禁止force push、改动Goal0 Tag或继续开发。

## Goal 1：2026-10-09 外部 Reviewer 最小整改（历史：验收批准前）

用户转述外部静态审查结论：原真实链路已有成功证据，但暂不批准Git封版。仅整改新需求显式FullAccess入口及普通PowerShell的CLI路径，不扩展Goal2。

新入口支持 `-Request ... -Mode Auto -FullAccess`：调用者显式选择并打印权限范围，Planner保持read-only；新需求正常规划/校验/组包，TaskPacket验证及所选模式预检通过后才启动Coder。默认仍受限，不能从桌面权限、全局配置或旧任务状态自动升级。新任务创建Goal0工程，重试才限制为修复现有失败；预算/归档/恢复和独立工作目录规则保留，FullAccess不构成OS隔离。

新增 `-CodexPath`（显式绝对exe路径优先、不回退）和 `-CheckCli`（只检查文件及10秒内版本，不创建任务/登录/调用Agent）；没有硬编码Desktop版本目录。独立Windows PowerShell移除Codex PATH后，实际显式路径检查退出0，版本codex-cli 0.162.0-alpha.2；未修改全局PATH、权限、配置或安装工具。

41项回归通过，报告 `<该轮历史验证归档>`。原31项覆盖保留，旧“禁止新FullAccess任务”测试按新授权范围改为拒绝FullAccess Plan，另新增10项；新需求Planner→TaskPacket→预检→Coder完成及默认模式用明确标记AgentDouble验证，不能当作新增真实E2E。原完整业务/浏览器成功记录仅为上一版历史。本轮真实Planner/Coder调用均0、无E2E/浏览器重跑，未变更原图书项目与历史证据。新入口真实复验需要另行授权，本轮不执行。

整改材料位于 `<该轮历史验证归档>`；使用说明 `docs/GOAL1_USAGE.md` 已修正矛盾，旧失败说明标为历史。现阶段仅表示最小整改与限定验证完成，等待外部Reviewer复审，不自行验收或Git封版。

## Goal 1：2026-10-09 执行策略调整（历史：本轮整改前）

用户将当前产品范围收敛为个人 Windows 电脑与 Codex，并明确原受限沙箱修复不再是前置条件；下方沙箱修复路线保留为历史，不再作为当前必做工作。启动链诊断时适配器显式使用 workspace-write/unelevated，未继承桌面 Full Access。说明具体范围和风险后，用户明确回复“同意本次启用并复验一次”，授权记录见本次专项目录 `authorization.json`。

已完成启动链核对与可信原生环境探针：非受限令牌下 Node 管道子进程、Windows 命名管道读写和 Chrome/Edge 空白页均成功；Node→Playwright→已安装 Edge 固定 DOM 检查退出0，显式保留浏览器自身沙箱。另确认现有测试默认 Playwright Chromium 文件不存在，候选最小修复是使用已验证的 msedge channel。这些均为环境诊断，不是业务验收。

诊断及授权前方案：`<该轮历史验证归档>`。新增显式 `-FullAccess` 参数，仅接受已有包 Auto Retry；默认模式不变，不修改全局配置或提权。Full Access 下工作目录只是任务约束，不是 OS 隔离边界，不能报告越界拒绝验证通过。控制记录在重试前复制归档，修改已有源码可以接受，但仍须主控真实检查；31项回归通过，报告 `<该轮历史验证归档>`（包含替身，不是E2E）。

原 TaskPacket 重新校验通过，规划与控制记录、既有源码、44份冻结文件及参考项目35839文件在初始探针前后既定覆盖无差异，参考 Git 无差异；证据 `guard-after-probes.json`。HEAD/main/goal-0-approved仍为11aa80e，无Git写命令。历史专项报告记录的其他漂移事实原样保留。

授权后的同模式 Node/Edge 固定页面预检通过，启动唯一一次真实 Coder（总调用第3次），不重新运行 Planner。实际启动参数保存为 `control/coder-03.launch.json`，900秒上限，模式 danger-full-access；CLI曾出现模型连接超时并在同一调用内重连，最终完成。以下为回收后的最终状态；下方旧环境阻塞段落仍为历史事实。

本次真实 E2E 成功1条：自动复用已验证的TaskPacket与原7734字符Goal0提示词，Coder线程 `<已归档独立调用ID>` 实际修复现有测试入口（msedge、chromiumSandbox=true）及预期故障503分类。首次完整测试4/5失败记录已归档，修复后Coder完整自测5/5；主控独立build=0、test=0（5通过、0失败、0跳过），HTTP200/预期内容匹配、服务停止。真实浏览器验证交互、持久化/重启、故障和离线请求，并保存1440×900、390×844 PNG及trace，已检查截图及ZIP完整性。没有用HTTP200或替身替代浏览器验收。生成项目仅完成规划的Goal0，不是全部图书业务完成。

主控恢复命令退出0、复用已完成结果，调用数保持3，重试1，无重复规划/开发。原规划、包与提示词哈希不变；30份旧control文件已复制归档并核对哈希，旧workspace证据和本次失败轮记录均保留。最终守护复核通过：44份冻结文件、参考项目35839文件及参考Git无差异（node_modules按大小/mtime，其余SHA）；workspace AGENTS.md未变。Full Access无OS越界阻止能力，有限指纹及可见日志不能证明整个电脑零越界或零敏感数据读取。未执行Git写命令；HEAD/main/goal-0-approved仍为11aa80e，不能据此声称宿主所有.git缓存文件零变化。

本阶段新增Planner0、Coder1；Coder耗时276.844秒，CLI input=297757、cached_input=258560、output=5413（reasoning148是输出子集，不再相加）。主控build/test分别0.153/6.469秒。原调用/时间/重试上限保留，Token用量有真实记录但无Token硬上限；主会话Token未取得。本次FullAccess参数仅接受已有包的Auto Retry，新需求仍默认受限模式，后续执行需按次明确授权，不声称所有新需求都能无介入完成。

最终报告：`<该轮历史验证归档>`；机器结果及证据哈希见`RESULTS.json`、`evidence-manifest.json`、`guard-final.json`。Goal 1：已完成，待外部 Reviewer 验收。停止，不进入Goal2，不自行验收/提交/Tag/Push。

## Goal 1：2026-10-09 环境专项诊断（历史）

已复用现有报告、日志、Planner 四份产物、TaskPacket 和工程；未重新规划，未调用 Planner/Coder，未进行正式端到端重试。新报告与原始诊断记录：`<该轮历史验证归档>`。下方“实际进展与阻塞”保留上轮事实。

当前可验证原因范围：Codex CLI 0.162.0-alpha.2 的 unelevated 受限令牌下，Node v26.3.0 本身及继承/忽略/文件输出子进程均成功，管道输出子进程 EPERM；Win32 命名管道服务端能创建，读连接成功、写连接错误5。换 cwd/TEMP、去掉桌面包环境变量均无改善。Chrome/Edge 能创建进程，但新 workspace 私有用户目录下仍在 Mojo/Crashpad IPC 访问拒绝处失败。尚未确定具体 CLI 缺陷或已修复版本，不能把业务代码标为错误来源。

继续专项诊断：成功读取默认管道DACL，确认完整权限给当前用户而该用户SID不在受限SID列表，Everyone仅可读；libuv写端、WRITE_DAC及Chrome Mojo精确访问掩码均被拒绝。匹配libuv 1.52.1和Chrome154.0.8037.98源码，确认该权限机制与失败一致。TokenDefaultDacl与默认管道DACL不同，materialized helper与当前CLI SHA一致；没有实施加用户SID、改ACL或DLL注入等未经边界验证的权限补丁。新增原始证据pipe-acl-followup.json、pipe-access-followup.json和runtime-source-inventory.json；原失败证据未覆盖。

最小适配修复：Windows Node 管道预检在现有包验证后、重试计费和 Agent 派发前执行；失败明确留证并停止。边界探针文件改为每次独立路径。一次真实预检仍失败，不进入正式 E2E。另修复运行锁追加问题：首次无Retry恢复令controller.lock增加一个ASCII“0”字节（0x30），保留实际变化；最终27项主控回归通过（含显式 AgentDouble，不是业务工程成功）。26项通过、锁修正初版27项中2个错误、最终27项通过的报告均保留。没有解决底层 IPC 权限，没有放宽沙箱、变更 Windows 安全设置或全局配置、安装 WSL/Docker/VM。

实际恢复保持“已失败”，历史 Agent 调用2、重试0；不带 Retry 的恢复返回退出1且未调用 Agent。TaskPacket、规划、旧控制记录和工程源码保留，剩余一次 Coder 重试未消耗。8个被测冻结/外部文件或目录拒绝写访问，探针未修改这些对象；不能把有限路径检查等同完整宿主安全审计。

完整性证据见专项目录guard-final.json：44份冻结文件、原源码及历史报告、参考项目35839文件的既定覆盖无差异；control只存在上述运行锁差异，修复锁后的再次无Retry恢复没有继续改变锁内容；原state/events、规划和包未变。跨中断点的工厂.git由235文件到272文件（38个objects新增、1个codex/turn-diffs引用文件消失），用户config SHA也变化，最终guard仍为false。没有执行Git写命令或编辑全局config，变化来源未独立确认；不声称.git、control或全局config绝对零写入。只读确认HEAD/Tag/main仍为11aa80e基线；发现漂移后停止进一步执行，仅收口报告，等待外部Reviewer及用户决定。

当前构建/业务测试仅保留上轮 build=0、test=1、HTTP200 的历史事实，本轮未运行业务测试或取得浏览器验收截图。Goal 1 保持“开发中，环境受阻，未完成”。下一步需用户选择管理员协助修复官方 elevated 环境，或授权受控 WSL2 环境建设；任何替代执行器都须重新验证权限与浏览器能力。停止，等待外部 Reviewer；不自行验收或 Git 收口。

## Goal 1 实际进展与阻塞（历史）
主控、PowerShell入口、独立CLI执行适配、TaskPacket 1.0验证、状态/日志/查询/有限恢复、Plan与Auto分支已实现。最终25项异常/恢复测试通过，报告 `<该轮历史验证归档>`；Agent替身只用于这些确定性测试。

真实案例 `projects/<已归档项目或执行ID>/`：Planner与Coder两个不同CLI thread实际执行，自动交接完整任务包和7734字符Goal0提示词；Planner四份产物、12项AC和无环依赖已验证。Coder实际创建工程代码并如实返回失败。主控独立诊断：构建退出0、测试退出1（Node spawn EPERM）、健康HTTP 200、临时服务已停止。没有成功的端到端链路，没有真实浏览器截图或完整AC通过结论，不宣布Goal1完成。

阻塞：本机Codex CLI 0.162.0-alpha.2的elevated沙箱初始化失败；unelevated沙箱可拒绝control越界写入，但Node子进程EPERM、Chrome/Edge IPC拒绝访问，桌面兼容设置也未解决。保留受限沙箱，不降级完全访问、不修改全局配置、不安装其他服务。不消耗剩余一次Coder重试去重复已确认的环境失败。

恢复点：真实任务保持“已失败”；规划可复用。需先在另行授权范围内修复/验证受限执行环境，再以 `scripts/factory.ps1 -ProjectId <已归档项目或执行ID> -Mode Auto -Retry` 使用剩余1次重试；不得把未完成工程或缺失截图当作通过。完整说明见 `docs/GOAL1_USAGE.md`，验证报告见 `<该轮历史验证归档>`。停止，等待用户决定阻塞处理；不进入Goal2或Git收口。

Goal1结束只读复核：44份受保护冻结文件无内容变化，参考项目35839文件的路径/大小/mtime一致、除node_modules外SHA一致，参考Git无差异；工厂.git 96文件内容亦无差异（该.git快照在Planner启动后、Coder启动前采集）。证据见 `<该轮历史验证归档>`、`factory-git-after.json`。不据此声称Codex宿主运行缓存绝对零写入。

## Goal 0 历史：当前任务
三个 Skills、五份权威模板、中文使用说明及架构路线已完成。两个独立案例均生成输入→计划→骨架方案→可执行提示词→设计任务包→评估记录，完整交付检查通过；独立内部审查发现的问题均已修正并复核。依据用户本轮明确通知，外部 Reviewer 已验收通过，Goal 0 状态更新为“已验收冻结”。当前无开发任务，等待用户手动 Git 冻结。

## Goal 0 历史：外部验收收口
结论来源：用户于本轮提供的“AI Project Factory — Goal 0 外部验收收口”通知；外部 Reviewer 结论为“Goal 0：验收通过”。

用户通知的检查范围：三个核心 Skills 实际内容、Skill 内部资源引用、两个不同类型案例、需求/验收标准/Goal/任务映射、两案例各12项 Goal0验收标准覆盖、开发提示词可执行性与约束、任务依赖无环、已提供文件与验证记录的内容哈希。

该结论不代表两个案例已实际开发、多 Agent 调度已实现或全局 Skills 安装已验证；不声称外部 Reviewer 重跑了未提供的全部验证脚本。

本轮仅更新本状态并补建根目录缺失的 `.gitignore`，不修改 Skills、案例、验证报告或参考项目，不删除文件，不执行 Git 写操作。下方历史验证结果与已知限制保留。验收前 checks.json 的文件哈希仍为当时候选记录；本次状态更新及新增 .gitignore 是收口变更，不重写历史哈希或把它们冒充本轮新验证。

## Goal 0 历史：授权与基线
本轮只写 `<项目目录或受保护目录>`。不安装全局 Skills、不开发两个案例系统、不执行 Git 写操作、不发布。新目录最初为空，当前未初始化 Git 仓库；只读 rev-parse 确认无仓库，不能称“Git工作区干净”或提供虚构 Commit。

参考项目 `<项目目录或受保护目录>`：只读确认 HEAD `a0f0bf30d74834b7374817d0f3f977cba16d885b` / `final-release-metadata-approved`，分支 `release-metadata-final-fix`，初始工作区干净；业务冻结 `a8dbb4a / acceptance-v2-task-state-fix-approved`。初始全文件只读快照位于 validation/reference/before.json，结束时复核。

## Goal 0 历史：已运行验证
- 使用本机 skill-creator/quick_validate.py，三个 Skills 均返回 `Skill is valid!`。
- `scripts/validate_delivery.py`：三个 Skills frontmatter/UI metadata、8 处自包含资源链接与交付文档链接通过；案例 A 18 R / 18 AC / 11 Task、案例 B 14 R / 22 AC / 14 Task，各12项 Goal0 AC 均入提示词，映射完整、依赖无环、禁权一致、无未填提示词变量，结果 validation/checks.json。两案例各6个无效任务包探针被拒，共12个。
- `scripts/inspect_reference_evidence.py`：11 张历史截图 PNG 尺寸及当前正式 ZIP SHA 与外部校验一致，结果 validation/reference/source-inspection.json。这不是重测参考业务。
- 仅项目内 `.tools/validation-env` 安装 PyYAML 6.0.3 用于检查；未安装全局依赖。Skills 运行不需要这一验证环境。
- `scripts/reference_guard.py after`：35,839文件路径/大小/mtime与Git状态无差异，除node_modules外SHA-256亦无差异；证据validation/reference/after.json。参考项目未修改，Git写操作未执行。
- 独立内部审查见 validation/INDEPENDENT_REVIEW.md；不是外部验收。修正包括任务前提与写集、事实来源、静态服务、缓存/备份写集、测试端口与自检角色，记录在两案例evaluation及验证报告。
- 首次完整QA时案例B评估记录尚未生成，检查明确返回未完成；补齐后完整通过。先前机器结果保存在 validation/check-runs/，未冒充全程一次通过。

## Goal 0 历史：证据和限制
经验来源 docs/SOURCE_EXPERIENCE.md；历史原始提示词未找到，只依据可核实成果及用户本次指令归纳。没有重新运行参考工程或两个案例业务系统，不能给它们新的运行通过结论。

官方用户级安装说明已核对，当前文档为 `.agents/skills`，本会话旧目录 `.codex/skills` 差异已如实说明；本轮未测试全局发现。

## Goal 0 历史：恢复点与下一动作
Goal 0 已获外部验收通过，候选内容指纹与逐文件SHA在validation/checks.json，保留为验收前历史记录。下一动作由用户手动执行 Git 冻结；本代理不初始化仓库、不提交、不打Tag、不进行Git冻结。没有新的授权不开始下一阶段或自动交接程序。

## Goal 0 历史：未来工作
参见 docs/MULTI_AGENT_ROADMAP.md。任何 Planner→Coder 自动交接程序、Agent执行、Git/发布能力均未实现；下一阶段需要新的任务授权。

**Goal 0：已验收冻结。** 完成后停止，等待用户手动 Git 冻结。

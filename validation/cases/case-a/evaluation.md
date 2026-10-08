# 案例 A 独立前向使用记录

日期：2026-10-08，Asia/Shanghai。性质：独立生成者按已写 Skill 的文档行为验证与输出自检，不是业务测试、自测工程通过、外部 Reviewer 验收或调度器执行。

## 实际过程与产物

1. 读取唯一需求输入 input.md，顺序读取 requirement-planner、goal0-scaffolder、goal-prompt-writer 的 SKILL.md，以及它们的 assets 模板和 references。没有读取参考项目、企业案例或历史项目业务源码；未读取/创建未来目标目录。
2. 使用 Planner 产出 plan.md：提取 18 个需求与 18 个 AC，Goal 0 12 项、Goal 1 3 项、Goal 2 2 项、Release 1 项；11 个 Task、5 个问题。已确认事实、工程假设和业务待确认分开。
3. 使用 Scaffolder 比较静态 SPA + IndexedDB 和本地 API + SQLite；按单机虚构断网需求选择前者，保留真实生产授权排除项。产出 goal0-blueprint.md，覆盖 14 项基础主题，并明确开发/运行/发行依赖差异。
4. 使用 Prompt Writer 生成 goal0-prompt.md：固定 React/TypeScript/Vite/HashRouter，包含目录和基线核验、具体 Task、UI/数据/身份/失败规则、12 个 AC 逐项执行、拟定脚本、证据、有限返工、最终报告和完成停止。最终提示词无需用户填空，未来 Coder 仍须核实目录/环境事实，不能伪造 HEAD。
5. 生成 task-packet.json：schema 1.0，明确 design_only；需求/AC/Task/依赖、禁止操作、两次/三轮预算、未核验目标基线和业务阻塞项。它只作为未来接口实例，不运行调度。
6. 实际执行 PowerShell 文档结构检查（读取 JSON、ID 映射、Goal 0 AC 出现、占位符扫描）与文件 SHA-256 读取。首次结果：18 requirements、18 acceptance、11 tasks、unmapped=0、Goal0 missing in prompt=0、template placeholder=false、git_write=false、head=null。该结果只证明文档结构，不证明业务正确或实际命令可运行。
7. 接到跨案例独立审查指出“步骤前提产物/写集、Coder 自检不得冒称独立 Review”的反馈后，读取 Skills 中相关窄修正，复核本案例：本例没有服务端模型/迁移/seed 顺序问题；数据类型与 seed 同属 T-A003，前于样板 UI T-A004。补全 T-A002 根配置、本地缓存和资产写集；把 T-A006 依赖外部审查改为自测结果、外部审查后续进行，显式允许单个 Coder 顺序完成实现与 Tester 职责。
8. 完成上述必要修正后再次实际执行文档检查，exit 0：18 需求、18 AC、11 Task；未映射 0、Goal 0 提示词缺失 AC 0、模板占位符 false。拓扑排序实际解析为 T-A001→002→003→004→005→006→101→102→103→104→201，无环或缺失依赖；六个案例文件齐全。仍仅为结构/文档证据，不是工程测试。

## 六项案例判断

| 项目 | 本次可核对结果 | 限制 |
| --- | --- | --- |
| Planner 合理拆分 | 工程样板先行，完整申请审批/退回作为 Goal 1，执行与统计 Goal 2，正式包装 Release；每条需求有 AC | 审批层级/阈值/版本仍待用户，不算已确认业务 |
| Goal 0 方案 | 布局、模拟身份、数据 adapter、样板、刷新、确认重置、错误、测试与证据齐全 | 只是方案，未创建工程 |
| Prompt 可执行性 | 具体入口/接口、拟定命令、运行前提、全部 AC 与证据/停止规则自包含 | 未实现脚本，因此不声称命令已经可运行 |
| 适配工程选择 | 单机虚构可采用 IndexedDB，无真实后台；比较了服务端方案但按当前需求不采用 | IndexedDB 与现场包装还需未来实测 |
| 测试完成标准 | 取消全快照不变、真实存储 refresh、身份拒绝、写失败、schema恢复、epoch竞争、两视口生产构建外域阻断 | 本轮没有运行浏览器、Vitest、构建或业务 |
| 行业内容污染 | 输出只有采购输入中的业务任务；未引入政法或企业库存模块，React/IndexedDB/Windows 仅本例选择 | 不是法律/合规方案 |

## 发现的问题及必要修正

- 初稿把正常 reset 与损坏恢复共用 expectedEpoch，但损坏记录可能不能解析 epoch；增加独立 recoverScenario + generation 绑定 recoveryToken，确认前不覆盖数据，阻断旧 pending 写入。这是输出设计质量修正，并非实测 bug。
- 项目内安装默认可能写 npm/Playwright/临时缓存到目标外；提示词固定仅命令进程的项目内 NPM_CONFIG_CACHE、PLAYWRIGHT_BROWSERS_PATH、TMP/TEMP，不修改用户/系统配置，仍越界则停止。避免“允许安装”与“唯一写目录”冲突。
- 外部 Reviewer 不应成为单个 Coder 完成自测的未提供运行依赖；初稿措辞在 T-A006/AC-A012 存在混淆，已明确 Coder 只自检，外部独立结论另行进行。
- Blueprint 的路由选择文字曾容许 HashRouter 或其他方案，最终 prompt 已唯一固定 HashRouter；不让 Coder 猜。
- 后续任务写集不自动授予当前权限；packet 对 Goal1/2/Release 标 future_goal_not_authorized_now，现场包仍需另授权。审批和版本问题只阻塞业务 Task，Goal0 可独立完成。
- 主 Agent 阅读最终 prompt 发现手动 preview 占用 4173 后 E2E webServer（reuseExistingServer:false）也要启动同端口；已把步骤改为手动 smoke 结束先停止本任务 preview PID 并确认释放，再由 Playwright 自行启停。不是实际服务运行发现，也没有强杀进程。
- 同一轮文档审查发现 test:unit 配置边界未精确约定；已明确 Vitest include tests/unit 和 tests/component、exclude tests/e2e，并给组件环境 jsdom/setup，避免漏跑组件或误执行 Playwright。该修正是提示词约束，不代表已配置或执行套件。

本轮未发现必须改写三个 Skill 的全局格式问题；跨案例反馈的步骤/独立审查检查已由主 Agent 纳入 Skill，本例按修正要求复核。可用性判断来自“实际读取 Skill 并生成可审查完整链路”，并不等于已测其所有输入类型。

## 当前证据范围与结论边界

实际证据仅为本目录输入、计划、方案、提示词、任务包和本文，及主 Agent 后续保存的交付结构检查报告。没有浏览器截图、数据库记录、系统测试日志或真实开发结果。未执行任何 Git 命令/写操作，未安装任何依赖，未触及参考目录，不创建 C:\FactoryCases\ProcurementDemo。

状态：案例 A 文档行为验证已生成并完成输出自检，待主 Agent 交付检查及外部 Reviewer；不作验收通过结论。

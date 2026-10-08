# 参考项目经验与证据来源

分析日期：2026-10-08，Asia/Shanghai。参考目录 `C:\910Program` 严格只读；本轮未启动其服务、运行其安装/构建/测试或解压发行包。下面的通过数量是历史文件记载，本轮只核对记录、实现和存在性，不把历史结果说成本轮重测结果。

## 1. 基线和阶段方法
只读 `git log --oneline --decorate`、`git tag --list`、`git show` 核实：

| 阶段 | Commit / Tag | 可提炼经验 |
| --- | --- | --- |
| Goal 0 | d3e7ba9 / goal-0-approved | 先建可运行统一基座，业务入口占位，纵向样板验证共享状态与交互 |
| Goal 1 | aa5a97a / goal-1-approved | 在基座上交付第一业务闭环并回归基础能力 |
| Goal 2 | d50a759 / goal-2-approved | 保留前阶段业务，按模块增量装配，扩展存储校验和场景 |
| Goal 3 | b02fbc4 / goal-3-approved | 后续业务延续同一契约；受保护文件哈希核对 |
| 最终业务 | a8dbb4a / acceptance-v2-task-state-fix-approved | 验收反馈定向修复、可演示运行状态、刷新恢复和 Reset 清理 |
| 最终交付 | a0f0bf3 / final-release-metadata-approved | 业务与发行元数据分开核对，当前版本与历史记录分开 |

实际 HEAD 完整值：`a0f0bf30d74834b7374817d0f3f977cba16d885b`。实际分支 `release-metadata-final-fix`，初始只读 status 干净。最终业务完整 SHA 在 PROJECT_STATUS 记为 `a8dbb4a1bdee99d6a6ad37cba51db13fa3794107`。验收结论来自该项目既有状态与用户提供的冻结说明，工厂不重开其验收。

注意 `git show goal-0-approved:PROJECT_STATUS.md` 内容仍为当时“已完成，待验收”，而当前状态记录已验收冻结。Tag 与当前权威状态共同说明历史演进，不能只取旧文档中的“当前”字段当最新状态。

## 2. 逐项来源→提炼→适用边界
| 来源（相对参考目录） | 本轮检查内容 | 可复用规则 | 不可推广的个案 |
| --- | --- | --- | --- |
| PROJECT_STATUS.md | 历史阶段、当前任务无、后续验收修复、业务与发行基线 | 当前状态优先、历史保留、外部验收与自测区分 | 辽宁模块名称及已通过结论不属于工厂 |
| goal-0-approved 历史目录、package.json、PROJECT_STATUS.md | 基础目录、依赖脚本、范围和后续接口 | 骨架先跑通，后续增量开发；命令必须真实存在 | Vue/Pinia/Element Plus/pnpm 等仅为当时选型 |
| docs/GOAL_0_CHECKLIST.md | 要求→实现位置→验证映射 | 每个功能可追溯、有对应测试 | 三系统、深浅主题并非通用必选 |
| docs/VALIDATION.md | 历史 10 项双视口基础测试、运行环境、警告和限制 | 不混淆格式/类型/行为检查，不宣称没执行的 lint | 当时工具版本、测试数量不作新项目要求 |
| docs/GOAL_0_VISUAL_EVIDENCE.md、docs/screenshots/goal-0/evidence.json | 11 张实际视口截图、交互链路及索引 | 截图附视口、路线、动作，不能压缩长图伪装首屏 | 1920/1366 仅特定演示目标 |
| tests/foundation.spec.ts、playwright.config.ts | UI交互、刷新、隔离复位、取消、外部请求与错误监听 | 用真实用户链路验证状态不变量，隔离测试上下文 | 前端测试不能证明真实后端授权 |
| goal-0-approved:src/stores/demo.ts、src/utils/storage.ts | 模板 clone、运行状态、派生指标、持久化异常 | 状态同源，部分损坏隔离恢复，存储失败显式提示 | localStorage 只适合这里的单机演示状态 |
| goal-0-approved:src/stores/auth.ts | 模拟身份及记住登录 | 明示身份真实性和权限边界 | 浏览器记住 admin 不等于生产认证 |
| docs/GOAL_1_VALIDATION.md | 30/30 历史总回归；初次 28/30 及等待路由修正 | 保留失败原因，不靠改业务绕测试失败 | 特定案件和流程业务不复制 |
| docs/GOAL_2_VALIDATION.md | 54 项历史总回归、26 张截图、旧阶段保护 | 增量变更必须验证契约兼容 | 文书/模型/线索不是所有项目的模块 |
| docs/GOAL_3_VALIDATION.md | 历史 88/88，51 个前阶段文件哈希保护 | 明确写集、单一装配点和证据保护 | 地图、网格及风险语义不迁移 |
| src/systems/supervision/store.ts（仅运行/恢复片段）、docs/ACCEPTANCE_V2_TASK_STATE_FIX_VALIDATION.md 与状态摘要 | executionWindow、同 runId 恢复、运行锁定、销毁/重置防旧异步写回 | 异步有开始/终态/恢复/取消，不预置永久运行假象 | 4 秒窗口仅现场DEMO展示，不当真实调度 SLA |
| packaging/README.md、docs/FINAL_RELEASE_METADATA_VALIDATION.md | 冻结业务与运行依赖隔离，来源/许可/哈希，独立解压 smoke；旧包 78 个业务文件一致的历史报告 | 元数据不替代内容一致性，未测设备明确记录；ZIP 自身哈希置包外 | Windows Portable、Node24.19、CMD 编码只用于对应交付形态 |

`PROJECT_RULES.md` 和 `DEMO_DATA_RULES.md` 用于核对虚构数据、模块边界及演示实现限制；不是工厂业务规范的直接副本。没有一次性读取所有源码；仅为验证状态、身份和工程基础读上述局部文件及历史对象。

## 3. 提示词风格提炼
参考仓库可核实工程与成果，不含已确认的历史原始对话提示词。本轮未访问 ChatGPT 历史对话，未找到原文。因此 goal-prompt-writer 是“成果证据 + 本次用户详细指令”的归纳版本，不能保证逐字复现历史提示词。

提炼出的稳定写法：背景和基线先行；范围内/外清楚；编号动作具体到页面/API/数据变化；取消、禁用、错误、刷新恢复明确；允许和禁止按路径及操作约束；测试、截图、实际报告闭合；失败次数有限；自测完成后停止待外部验收。

本次用户指令本身提供了详尽风格样本：16 个提示词考虑项、严格只读参考、禁 Git 写入、证据与最终报告顺序、完成后停止。将这些结构转为模板，而非把当前禁 Git 或参考业务误当永久规则。

## 4. 只读审计证据
`validation/reference/before.json` 在初始只读勘察后、开始核心产物建设前采集；`after.json` 在交付自检末采集。覆盖参考项目全部文件路径、大小和修改时间；除 node_modules 外全部文件（含 `.git`、缓存、截图和发行物）另做 SHA-256。HEAD、分支、refs、只读工作区状态同时比对。不比较访问时间；node_modules 字节未逐一哈希，报告不夸大这一限制。

`validation/reference/source-inspection.json` 记录截图尺寸/证据路径核对和正式 ZIP/外部校验文件的只读哈希核验。本轮不声称重新构建或执行了参考项目的 180 项测试。

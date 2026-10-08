# AI Project Factory 工作约束

## 当前范围
Goal 0 仅建设三个 Codex Skills、复用模板、案例验证及未来自动化方案。不得开发案例业务系统，不得把方案称为已实现的调度器。

## 文件和 Git 边界
- 唯一写入目录：`C:\AI-Project-Factory`。本轮不安装全局 Skills。
- `C:\910Program` 严格只读，包括源码、证据、依赖、发行物和 `.git`；不得运行参考项目构建、测试、格式化、安装或服务。
- 本轮禁止一切 Git 写操作，包括 init/add/commit/tag/push/branch/switch/reset/restore/clean。只读检查使用 `git --no-optional-locks`，不得将这些限制当成未来所有项目的永久约束。
- 不覆盖历史证据；新验证写入本项目 `validation/`。如发现参考目录变化或路径越界，立即停止相关操作并报告。

## 内容与状态
- 经验必须有源文件或历史基线支撑；历史原始提示词未找到时如实说明。
- 技术栈按项目选择；辽宁业务、Vue、Mock、localStorage、Windows 离线运行均非通用默认。
- 需求、验收、任务、测试、证据采用稳定 ID；标明事实、推断、假设、待确认。
- 区分计划中的测试、实际运行结果、外部 Reviewer 结论；不伪造截图、测试或验收。
- Skills 使用标准 YAML name/description frontmatter，支持资源随各自目录独立安装。
- 验证须覆盖离线 DEMO 和真实服务端/数据库两个案例，保存输入、计划、骨架方案、可执行提示词及审查结果。
- 复杂 Skills 可依 skill-creator 的独立前向验证建议使用受限评估子 Agent；只评估本项目交付物，不触及参考项目或全局安装。

## 完成门槛
三 Skills 的格式与资源引用检查通过，两个案例行为验证完整，中文使用说明和状态齐全，参考项目只读复核无变化。最终只标记“Goal 0：已完成，待外部 Reviewer 验收”，随后停止。不得自行验收、提交、打 Tag 或冻结。

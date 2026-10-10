# 有限独立质量复验机制

这是已实现的特定来源复验入口，不是通用任务平台或新用户快速开始。Goal 2 已有限范围封版，无须为文档更新重跑；正常使用入口见 [快速开始](GOAL1_USAGE.md)。

`scripts/revalidate-goal2.ps1` 复用 `factory/revalidation.py` 和 QualityGate；默认路径针对既有图书案例，Goal 3 有单独有限适配。来源、项目身份和历史守护都有约束，不能用于任意项目或把示例 ID 替换后就认为可运行。不存在旧授权自动续用或通用失败重开额度功能。

## 准备、执行与证据

Prepare 在原项目锁下验证原规划/任务包/完成记录、Coder 结果、候选及历史来源，建立独立账本并保存来源及副本 SHA。原 state/events、失败质量记录和旧哈希不修改；候选源码与历史上下文分离。来源不齐或身份变化在派发前停止，模型调用为 0。

执行需当前有效的显式授权、全新合法身份、已验证的可信 CLI 与 Full Access 选择。该字段记录授权，不能自身充当用户许可。Tester 与工程检查使用当前用户权限，Reviewer 为独立只读；无 OS 隔离，无 Token 硬上限。

既有独立入口固定 Planner/初始 Coder/返工 0、Tester/Reviewer 各最多 1、无 Retry/自动返工，每 Agent 至多 600秒，整体墙钟至多 1800秒，并取原任务更严格预算。Tester 合法通过后才可调用 Reviewer；blocked、非法、超时或真实失败均保存并停止。

新上下文通过 prepared/receipt/source 记录绑定来源、任务包、阶段、候选和必要证据；工厂身份变化不能手改旧账本来放行。完成检查点、原始输出及其文件哈希可被重新核验，零模型复核不构成新的真实 Tester 调用。已终结或额度已用的上下文不能重复派发。

## 维护者零模型入口

从仓库根目录运行帮助或特定确定性测试：

```powershell
python -B -m factory.revalidation --help
python -B -m unittest tests.test_revalidation -v
```

帮助不调用模型；测试使用夹具，不是新真实 E2E。公开文档不提供依赖私人历史目录的复制执行命令；实际使用需要按特定来源约束审查上下文。Goal 3 适配见 [说明](GOAL3_QUALITY_REVALIDATION.md)。

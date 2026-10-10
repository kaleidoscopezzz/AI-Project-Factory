# APF Goal 3：受控两阶段串行执行

**已批准封版，Tag：`goal-3-approved`。** 批准范围是同一待办软件从已批准 Goal 0 到 Goal 1 的真实增量开发、独立测试、只读审查与阶段记录。它不是任意多 Goal、并发 DAG 或发行交付器。案例及限定范围见 [能力说明](VERIFIED_CAPABILITIES.md)。

APF Goal 3 是工厂里程碑；下面的 Goal 0/Goal 1 指生成软件的两个实施阶段。Goal 2 已有限范围封版，不再重开其验收。

## 现有开发 API

1. `Controller.create` / `run(..., mode="Plan")` 保存原始需求、完整 Goal/Task/AC 规划和软件 Goal 0 TaskPacket。
2. 调用者确认 Goal 1 独立 `goal1_spec` 和 `approval_id`；提示词、checks、runtime 与 AC/写集必须匹配原规划，重大问题未确认时拒绝。
3. `prepare_goal_sequence` 只验证登记，不调用模型；默认 `allow_repair=False`、无 Retry。可显式选择既有有限返工能力，不代表真实闭环已验证。
4. `run_goal_sequence` 复用 Controller 和 QualityGate；只有前阶段合法通过，才建立下一阶段独立任务包，在同一 workspace 增量开发。
5. 已在独立上下文取得真实 Goal 0 批准时，可使用 `adopt_goal0_approval` 验证并保存来源绑定快照，不修改原 blocked/failed 账本。

以下是参数形状示意，不是可直接执行的零配置入口。各变量必须来自已确认需求和真实环境；执行 `Plan` 及阶段链会调用模型：

```python
from factory.controller import Controller

planner = Controller(full_access=False, codex_path=trusted_cli)
pid = planner.create(request, timeout=600,
                     coder_execution_intent="danger-full-access")
planner.run(pid, mode="Plan")

runner = Controller(full_access=True, codex_path=trusted_cli)
spec = {
    "goal": "Goal 1",
    "prompt_md": reviewed_incremental_prompt,
    "checks": reviewed_build_test_argv,
    "runtime": reviewed_local_runtime_assertion,
    "blocking_questions": [],
}
runner.prepare_goal_sequence(pid, spec, approval_id="explicit-scope-approval")
runner.run_goal_sequence(pid, through="Goal 0")
runner.run_goal_sequence(pid)
```

权限意向只是规划记录。Planner/Reviewer 本次实际执行仍只读；未来 Coder 的 Full Access 必须由调用者在 Auto 执行时再次明确选择且与意向一致，不允许静默升级。`approval_id` 是范围确认字段，不是签名或自动获取用户许可。

## 独立记录与接续

| 位置（相对软件项目） | 用途 |
| --- | --- |
| `control/` | 原需求、Planner、Goal 0 包及历史记录 |
| `control/sequence/` | 计划、游标、前序快照及两阶段完成回执 |
| `control/goals/goal-1/` | 独立 TaskPacket、状态、Coder 与质量记录 |
| `workspace/` | 原工程上的增量业务源码 |

旧 TaskPacket 1.0 与单任务入口保留；阶段包 1.1 增加前序引用，不能把 Goal 0 AC 和提示词冒充 Goal 1。完成结果绑定候选、任务包和必要证据；前序快照保留当时身份，当前最后阶段必须匹配当前源码。

已登记 Sequence 的项目禁止使用旧 Auto 入口重跑 Goal 0。完成且合法的阶段会复用，不重复派发；未完成调用、缺检查点、权限/来源变化和真实质量失败停止，不自动修改旧账本。有限的零模型来源复核只处理已证实的格式或工具恢复情况，不能重新发放调用额度、忽略未知问题或伪造 Reviewer 批准。

## 实际验证与边界

待办案例的软件 Goal 0、Goal 1 均已取得真实独立质量批准。Goal 1 使用原规划的四项 AC、新任务包及新候选；Coder、Tester、只读 Reviewer 各真实调用一次，没有新 Planner 或真实 CoderRepair。完成续跑没有重复调用，最终确定性回归 260/260。

当前没有正式两阶段 PowerShell 参数；单阶段启动见 [快速开始](GOAL1_USAGE.md)。阶段提示词仍由调用者准备，任意数量 Goal、自动后续规划、真实返工闭环与产品化一键入口未实现或未验证。Full Access 无 OS 隔离，Token 无硬上限。不得将本次受控案例写成从一次请求自动交付任意软件。

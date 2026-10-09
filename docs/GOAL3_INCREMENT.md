# APF Goal 3 第一增量：软件项目两阶段串行

这是APF自身Goal3的开发API增量。它执行生成软件的Goal0→Goal1，两个概念不同；不是完整工厂、并发DAG或交付发行器。Goal2已有限范围外部批准并封版，不再重开其真实验收。

旧路线图的Goal3包含Reviewer、依赖、锁及整合回归；本轮复用已在Goal2实现的QualityGate，只落实串行依赖第一步。未来并发、全局调度、Git/Release不在范围。

## 受控工作流程

1. 使用现有Controller.create及Plan，保留原始需求、完整Goal/Task/AC计划和软件Goal0的1.0 TaskPacket。
2. 调用者审阅软件Goal1范围并提供明确approval_id及独立goal1_spec。它包含goal、prompt_md、checks、runtime、blocking_questions。prompt必须明确workspace、Goal1、增量边界、全部本阶段AC-ID、测试/验收/报告/停止规则；AC定义和任务写集来自原完整计划，重大问题未确认时拒绝。
3. prepare_goal_sequence只验证和登记，不调用模型。配置只允许Goal0→Goal1，无Retry、NoAutoRepair；它不生成新的业务规划。
4. run_goal_sequence运行前序Coder及现有Tester/Reviewer。只有QualityGate合法通过，才保存固定阶段完成记录并建立Goal1独立控制目录和任务包。
5. Goal1使用同一workspace，增量修改原计划的Goal1任务写集；本增量禁止删除前序有效源码、改AGENTS或清空重建。复用原Controller执行Coder、基础检查及QualityGate，独立记录thread/usage/退出状态/候选和证据。失败或未确认问题停止，不进入下一阶段，不自动返工。

只有本次Controller创建的阶段授权workspace可登记；旧AGENTS仅允许Goal0的工程会被拒绝，本轮不改旧项目授权或图书业务源码。复杂跨阶段依赖、删除/迁移源码及已登记阶段重规划需另外明确范围，不能通过改账本绕过。

## 开发API示意（本轮没有真实执行）

~~~python
from factory.controller import Controller

planner = Controller(full_access=False, codex_path=trusted_cli)
pid = planner.create(request, timeout=600,
                     coder_execution_intent="danger-full-access")
planner.run(pid, mode="Plan")  # 只读Planner；真实调用必须另获授权
c = Controller(full_access=True, codex_path=trusted_cli)  # Auto仍须本次显式选择
spec = {
    "goal": "Goal 1",
    "prompt_md": reviewed_incremental_prompt,
    "checks": reviewed_build_test_argv,
    "runtime": reviewed_local_runtime_assertion,
    "blocking_questions": [],
}
c.prepare_goal_sequence(pid, spec, approval_id="explicit-human-scope-approval")
c.run_goal_sequence(pid, through="Goal 0")  # 可选择先停在前序完成点
c.run_goal_sequence(pid)                   # 复用前序完成记录，继续Goal1
~~~

approval_id记录调用者明确范围确认，不是自动生成的用户批准或身份签名。FullAccess只由Controller/执行器调用者显式选择；Planner/Reviewer保持只读，工作目录和源码指纹不是OS隔离。未指定时沿用受限模式，预检失败停止，不自动放宽。

create的coder_execution_intent仅记录后续Coder/工程检查意向，可取workspace-write或danger-full-access，不启用任何执行权限。默认按调用者本次full_access选择记录；Plan要预先记载未来FullAccess时，应保持Controller(full_access=False)，仅显式传入意向。原Plan/CLI禁止FullAccess执行的规则不变，本增量没有增加正式CLI参数。Auto派发前必须与规划意向一致，且执行器权限必须与调用者当前显式选择一致；不一致立即停止，不能仅凭state意向自动提权。旧记录没有该字段时保持兼容且不迁移，但执行仍受当前显式选择约束；原blocked项目不改写、不解除阻塞。

本轮不新增正式PowerShell参数或更新根README；旧单任务CLI不自动转入多Goal。登记sequence之后，旧Auto入口会明确拒绝回到Goal0执行，避免Goal1增量后使旧记录变为失败。开发API读取control/sequence/state.json查看完整游标，原Status仍展示旧单任务状态。

## 目录与契约

- control/：原Planner产物、软件Goal0包及Coder/质量记录；Goal1不覆盖这些已完成记录。
- control/sequence/：调用者批准的Goal1说明、固定配置、阶段游标及goal0-completion.json、goal1-completion.json完成引用。
- control/goals/goal-1/：独立state/events、TaskPacket、提示词、包校验、增量前候选、Coder和quality/记录。
- workspace/：共享业务源码，不重复创建第二个软件项目。

旧TaskPacket1.0校验与入口兼容。增量TaskPacket1.1只增加predecessor引用，明确Goal1、独立task_id/input指纹、Goal1 AC、提示词、运行契约、六份固定产物及单Coder预算。原需求、项目类型/技术、workspace和禁止范围共用；不能以改个Goal名称沿用Goal0 AC或提示词。前序完成引用、完整规划副本和输入/产物SHA必须验证。

阶段完成记录只引用现有QualityGate的真实结果、候选和必要证据哈希，不另作质量决定。完成顺序与原计划依赖一致；不能让Goal0任务依赖后续Goal1，也不能依赖本轮未执行的Goal2。

## 恢复与停止

完成阶段重新核验固定控制/质量/证据引用，不再调用其Planner/Coder/Tester/Reviewer。后续增量合法改变共享源码时，前序记录仍表示其当时固定候选；当前最后阶段必须与当前候选一致。

质量通过后、串行游标更新前中断，可以凭现有合法检查点补存完成引用，不重派Agent。质量阶段中断继续采用原QualityGate恢复规则；未知/缺失检查点、未完成Coder、残缺阶段准备或源变化停止等待人工，不新增隐式Retry/恢复执行器。已完成记录被篡改不能借重跑修复。

原项目运行锁覆盖整个串行调用，单阶段复用原锁/状态机。证据被修改、缺AC/任务包、候选不匹配、跨workspace、计划/批准输入变化或必要质量门槛未通过时，拒绝派发或停止。没有回滚、自动删文件、Git或发布行为。

每阶段最多一个初始Coder；顺序中的Planner只在首次Plan调用一次，既有质量门槛提供独立Tester/Reviewer。NoAutoRepair及无Retry使本两阶段正常总调用最多7次（Planner1+每阶段Coder/Tester/Reviewer各1），失败不隐式补充次数。按create(timeout=600)配置时每模型调用最多600秒；工程检查沿用180秒/HTTP30秒，没有新的Token硬上限或整个开发API墙钟看门狗。无法取得usage时保留unknown。

## 本轮验证性质

tests/test_sequence.py使用明确标记的AgentDouble及小型源码夹具；每阶段通过是控制逻辑验证，不是新的真实业务测试、浏览器验收或模型Reviewer批准。兼容性回归不改变Goal2的既有批准性质。

真实执行的下一步需另行授权新项目范围、FullAccess和调用预算。为遵守本轮不访问参考项目，测试使用独立Controller root，没有参考inventory文件；现有QualityGate在真实仓库root的参考守护仍存在，本轮未调用。若后续真实验证继续禁止参考访问，应使用明确指定的独立root及必要工厂资源副本，不把它当OS隔离。

自动生成后续Goal提示词、任意数量Goal、并发依赖图、自动审批和全自动软件交付尚未实现。完成第一增量后停止，等待外部Reviewer审查，不宣布APF Goal3完成或Git封版。

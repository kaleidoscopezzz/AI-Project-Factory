# Goal 1 本地工厂使用说明

在项目根目录用 PowerShell 运行，Python 3.11+ 和已登录的 Codex CLI 必须可通过 PATH 调用。当前实测环境见 `validation/goal1/environment.json`；无需安装全局 Skills、依赖服务或配置 API Key。本机 Codex CLI 为 alpha 版本，跨版本应重新核对 `codex exec --help` 和 `codex sandbox --help`。

## 一句话入口

```powershell
.\scripts\factory.ps1 -Request "帮我开发一个离线图书借阅管理演示系统，要有图书列表、借阅状态、简单搜索，界面专业，以后方便增加更多功能。" -Mode Auto
```

`Plan` 只调用 Planner 并保存完整规划和经校验的任务包，不启动 Coder：

```powershell
.\scripts\factory.ps1 -Request "帮我规划一个离线设备管理演示系统" -Mode Plan
```

入口打印项目 ID、当前角色/状态和产物路径。`projects/<id>/workspace/` 是工程目录，`control/` 是主控拥有的规划、日志、任务包和状态目录。Planner 使用项目自带三个冻结 Skills 的原文、模板和参考资源；Coder 只收到已校验任务包及完整开发提示词，不需要人工复制。

## 查询与恢复

将示例 ID 替换为入口返回的实际 ID：

```powershell
.\scripts\factory.ps1 -ProjectId p-0123456789ab -Status
.\scripts\factory.ps1 -ProjectId p-0123456789ab -Mode Auto
.\scripts\factory.ps1 -ProjectId p-0123456789ab -Mode Auto -Retry
```

第二条可把 Plan 结果交给 Coder；复用已有规划，不重复调用 Planner。运行失败或中断的任务默认保持失败，不自动重跑；第三条显式允许一次重试。已完成任务先核对源码内容指纹，内容未变时直接返回已保存结果；内容变化时失效，不能沿用成功标记。文件锁防止同一任务并发运行，进程退出后操作系统释放锁。

重大歧义进入“等待用户确认”，不启动依赖操作；查看 `questions.json` 或 `coder-questions.json`，补充完整需求后提交新任务。本版没有自动审批、答案合并或任意状态编辑入口。请勿编辑 `state.json`、`task-packet.json` 以绕过校验。

退出码：0＝Plan 产物已验证或 Auto 基础验证完成；1＝拒绝/失败；2＝等待用户确认。Plan 的 0 不代表工程已开发。Ctrl+C 会停止当前受控 Agent 进程树并记录失败；电脑断电后下一次恢复会把遗留执行中状态标为中断失败，显式 Retry 后才继续。

## 预算和停止

默认每项目最多 3 次 Agent 调用（正常 Planner 1 + Coder 1，余量供一次显式重试），显式重试最多 1 次；单 Agent 默认 900 秒，可用 `-TimeoutSeconds` 设置 1–1800 秒。主控 build/test 各 180 秒，本地 HTTP 启动 30 秒；主控基础验证仅一轮。本版本不做自动返工循环，Coder 自测修复限同问题 2 次、总验证 3 轮，由提示词约束；Agent 内部细分工具次数/Token 无强制上限。总进程超时和主控调用上限可强制执行。

事件保存真实 CLI thread ID、exit code、耗时和 `turn.completed.usage`；没有可靠 usage 时保留 null，不推算费用。首次验证发现 WebSocket 超时，CLI 自身转为 HTTPS；本版本不允许覆盖内置 OpenAI provider，诊断中的该配置尝试被 CLI 拒绝并保留失败证据。适配器使用原服务商和用户已选模型，CLI 内部传输重试受单调用总超时限制；不更换模型服务商、不修改用户配置。

## 本次明确授权的 Full Access 恢复

2026-10-09 用户将 APF 收敛为个人 Windows 与 Codex，并明确确认现有 `p-dc1e9d42b5ae` 一次 Full Access Coder/工程验证。下方旧“绝不使用 danger-full-access”、受限环境修复路线保留为历史，不代表本次策略。默认仍受限；不继承桌面权限、不改全局配置。

只有本次明确授权才可运行：

```powershell
.\scripts\factory.ps1 -ProjectId p-dc1e9d42b5ae -Mode Auto -Retry -FullAccess
```

参数仅接受已有任务包的 Auto Retry；拒绝新需求或重新规划，先校验原包和规划。所选模式的固定 Node 管道与 Playwright/Edge 空白页预检通过后才计费重试。派生 Coder 显式 `-s danger-full-access`；主控工程验证采用当前账户原生子进程，工作目录和临时缓存放在项目内，不提权。Full Access 没有 OS 文件越界阻止能力；`execution-policy-03.json` 如实标记，不执行越界写拒绝探针冒充安全通过。浏览器自身 sandbox 保留。

运行前控制文件复制到 `control/attempts/<attempt>-<id>/before/` 并保存哈希（运行锁不复制）；不会删除旧证据。最新结果仍在既有路径，独立 Agent 的 input/launch/log/result 则按调用编号保存。重试源码只改已有文件也可验收，但必须有实际源码变化，且主控仍实际运行原 build/test/HTTP 契约。

原预算保持3次总调用、1次重试、900秒 Coder 和180秒单项检查；不增加 Planner 调用。CLI usage 记录实际 Token；只有调用/时间硬上限，细分 Token 没有硬计数上限。超出本次授权需重新由用户决定，参数本身不能代替授权。环境预检不等于真实 E2E。

## Windows 环境预检与当前恢复限制（历史）

2026-10-09 专项诊断见 `validation/goal1/environment-repair-20261009T010203/REPORT.md`。Node 本身与不使用管道的子进程可以运行；管道子进程 EPERM。Win32 命名管道读连接成功、写连接拒绝访问；Chrome/Edge 启动后在 Mojo/Crashpad IPC 处失败。换 cwd/TEMP 或移除桌面包环境变量没有解决 Node 问题。当前没有通过的安全工程执行方式，Goal 1 仍未完成。

Auto 对 Windows Node/npm 任务增加受限环境预检：只执行固定的 Node→Node `--version` 管道探针，不运行生成源码、不改变权限。已有任务先验证包及规划哈希，预检通过且文件写边界探针通过后才消耗显式重试预算。预检失败保存新的 `environment-preflight-<id>.json/log.jsonl`，保留失败状态和调用余量；不能把预检成功理解为浏览器验收通过。非 Windows 或非 Node/npm 任务不适用这个专项预检，仍需原有边界与真实工程验证。

边界探针与 `sandbox-verification-<id>.json` 采用独立文件名，保留早期同名历史记录。已有工程的正式重试仍须先保全原 Coder/运行/检查记录：本次没有进入正式重试，也没有重写原 `coder-result.json` 或规划文件。

运行锁仅在空文件时初始化，重开已有锁不追加或截断内容。并发竞争仍由操作系统字节锁拒绝；不要在锁持有期间通过另一句柄读取被锁定字节。最终27项回归验证预算保护、锁的并发拒绝和已有锁内容保留；中间失败记录同样留存。

需要再次诊断时，以下命令仅创建新的诊断目录；不会调用 Planner/Coder，也不会运行生成的业务源码：

```powershell
python -B scripts\diagnose_goal1_environment.py
```

诊断收集退出 0 只表示证据收集完成，必须逐项检查 `diagnostics.json`、预检和报告；不能解释为环境或 Goal 1 通过。不要直接在宿主机运行生成项目测试以绕过沙箱。当前任务保持原恢复点，待获授权的环境修复通过 Node、浏览器和写入边界验证后，才可使用剩余一次 `-Retry`。

后续可由用户/管理员修复官方 elevated 初始化，或明确授权安装 WSL2 并建设受限 Linux 验证适配器；具体操作、边界验证与代价见专项报告。本轮未安装或升级工具、未修改用户全局配置及 Windows 安全设置。

跨中断点比对另发现工厂Git的Codex turn-diffs命名空间/对象变化与用户config SHA漂移，来源尚未独立确认；当前HEAD/冻结Tag未变。Agent没有执行Git写命令或编辑config，但不能将这一事实解释为所有宿主进程均零写入。最终守护检查保留false，不重建基线掩盖变化；恢复前应核对这些漂移。详情见专项报告及guard-final.json。

## 验证与查看证据

```powershell
python -B -m tests.test_factory
```

此命令将异常测试结果写入 `validation/goal1/exception-tests-<runid>.json/txt`，保留每轮历史。测试替身用于确定性异常测试，不能作为真实 E2E 成功证据。真实记录必须有不同的 Planner/Coder CLI thread ID、自动 handoff 指纹、工程创建前后清单、主控 build/test/HTTP 检查和 `completion.json`。

`control/plan.md`、`goals.md`、`goal0-blueprint.md`、`goal0-prompt.md` 是四份 Planner 产物；`task-packet.json` 和 `packet-validation.json` 是派发依据；`coder-result.json` 为 Coder 回收结果；`basic-checks.json`、`runtime-check.json` 和对应日志为主控复核。生成工程自己的 README 说明具体启动命令与下一阶段扩展点。主控结束时停止临时 HTTP 服务，不留下后台演示服务。

## 边界与限制

主控只接受随机生成 ID、规范项目路径和 argv 数组；拒绝 `..`、绝对文件路径、symlink/junction、篡改包与产物。新项目不初始化 Git。冻结工厂 Skills 和旧案例不修改，参考项目只读。

Planner 用 read-only，Coder 和基础检查用 workspace-write Windows 受限令牌沙箱；每次派发前真实探针要求写入同项目 control 被拒。较强 elevated 沙箱在本机初始化失败，因此使用官方提供的 unelevated 模式，绝不使用 danger-full-access。该模式网络约束较弱、可读取部分本机文件，不是恶意代码或多租户安全产品；提示词中的禁止读取凭据不构成保密边界。Codex 本身可能维护用户目录内认证缓存、运行日志或沙箱状态，`--ephemeral` 不等于绝对零宿主写入；本工厂不主动编辑全局配置或安装全局依赖。

首版 Auto 基础验证支持 Node、Python 和固定 npm run scripts 的本地 HTTP 工程。不是任意技术栈的全自动交付器。移动/桌面或其他栈需扩展受控验证适配器，不能跳过不支持的门槛宣布成功。UI 行为和截图由 Coder 自测并保存；主控执行这些测试接口并独立检查 HTTP，不能代替外部 Reviewer。测试不等于业务完工或外部验收。

没有 Git Agent、Release Agent、独立生产 Tester/Reviewer、云发布、多个 Coder 并行或完整自动审批；只实施当前 Goal。外部 Reviewer 通过且收到专门 Git 收口授权之前，禁止 Git 写操作。

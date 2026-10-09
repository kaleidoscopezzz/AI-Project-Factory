# Goal 1 本地工厂使用说明

在项目根目录用 PowerShell 运行，Python 3.11+ 必须可通过 PATH 调用。Codex CLI 需已登录；可以从 PATH 查找，也可用 `-CodexPath` 显式指定 Desktop 内的原生可执行文件，不依赖桌面注入 PATH。无需安装全局 Skills、依赖服务或配置 API Key。本机 CLI 为 alpha 版本，跨版本需重新核对本机帮助。

## 普通 PowerShell 指定 Codex CLI

先查找已安装 Desktop 中的候选文件（目录布局可能随应用版本变化；此命令只列文件，不安装或升级）：

```powershell
Get-ChildItem -LiteralPath "$env:LOCALAPPDATA\OpenAI\Codex\bin" -Filter codex.exe -Recurse -File |
    Select-Object -ExpandProperty FullName
```

选择可信的当前安装文件，把完整路径赋给变量；不把某个版本目录写死在工厂代码中。如果上述目录不存在，从本机 Desktop 安装位置找到实际 `codex.exe`，不要猜测或静默改用别的程序：

```powershell
$cli = '替换为实际 codex.exe 的绝对路径'
.\scripts\factory.ps1 -CheckCli -CodexPath $cli
```

`CheckCli` 只确认文件存在、执行 `--version`（10秒上限）并输出路径和 `codex-cli` 版本；不检查登录、不创建任务、不调用模型或浏览器。显式路径优先于 PATH；错误/不存在的显式路径、脚本文件、无效版本或超时会停止，不回退到其他 CLI。不修改全局 PATH/配置/Windows权限。应用更新后旧文件若失效，重新选择并检查路径。普通 PowerShell 去掉 Codex PATH 后的本机验证见 `validation/goal1/reviewer-fixes-20261009T103057/standalone-powershell-cli-check.json`。

## 一句话入口

```powershell
.\scripts\factory.ps1 -Request "帮我开发一个离线图书借阅管理演示系统，要有图书列表、借阅状态、简单搜索，界面专业，以后方便增加更多功能。" -Mode Auto
```

调用者明确授权本次 Coder/工程检查使用 Full Access 时，可以直接提交新需求：

```powershell
.\scripts\factory.ps1 -Request "开发一个离线图书管理 Demo" -Mode Auto -FullAccess -CodexPath $cli
```

CLI 已在 PATH 中时可以省略 `-CodexPath`，对应 `-Request ... -Mode Auto -FullAccess`。`-FullAccess` 本身是调用者对本次运行的显式权限选择；入口会打印权限说明，不从桌面会话、任务旧状态或全局设置自动放宽。Planner 始终只读；新需求依次执行 Planner→规划校验→生成并验证TaskPacket→所选模式预检→Coder→独立工程检查。Coder与工程检查仅在明确选择后使用当前用户权限、不提权；工作目录不是OS访问边界。未指定时继续受限模式，受限环境失败会停止，不能自动切换。

本轮新入口仅用明确标记的 AgentDouble 验证控制逻辑；没有新增真实 Planner/Coder/E2E 或浏览器验收。真实执行仍需另行授权，不能将41项回归当成新入口真实E2E成功。

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

## 当前 Full Access 与恢复规则

2026-10-09 用户将 APF 收敛为个人 Windows 与 Codex。现已支持新需求 Auto、已规划任务 Auto 及失败任务 Auto Retry 的显式 `-FullAccess`；Plan保持只读，不接受该参数。每次运行仍须调用者明确指定，不沿用历史 Full Access 授权。下面沙箱失败章节是历史。

已有任务可以按其状态恢复，失败任务仍需 `-Retry`；以下只是调用形式示例，已完成的历史任务会复用结果，不再次开发：

```powershell
.\scripts\factory.ps1 -ProjectId p-dc1e9d42b5ae -Mode Auto -Retry -FullAccess
```

已有包先校验身份/路径/预算/规划哈希并复用，不重复Planner。新需求先正常规划和组包，校验失败或重大歧义不派发Coder。Windows Node/npm任务在Coder调用前执行固定Node管道预检；FullAccess模式同时执行Playwright/已安装Edge固定页面预检，已有失败任务预检通过后才扣重试。派生Coder显式 `-s danger-full-access`；检查用当前账户原生子进程，TMP/TEMP/cache在项目内。FullAccess无OS文件越界阻止能力，策略记录如实标记，不执行越界写拒绝探针冒充通过。浏览器自身sandbox保留。

重试前控制文件复制到 `control/attempts/<attempt>-<id>/before/` 并保存哈希（运行锁不复制）；不会删除旧证据。最新结果仍在既有路径，独立Agent的input/launch/log/result按调用编号保存。新任务要求真实工程，重试只改已有源码也可接受；两者都必须有实际源码变化和原build/test/HTTP验证。

预算保持3次总调用、1次显式重试、默认900秒每Agent和180秒单项检查；新任务通常Planner1+Coder1，恢复已有包不重复Planner。CLI usage记录实际Token，细分Token没有硬上限。调用者应只对已获授权的需求指定FullAccess，参数不扩展业务、冻结目录、Git或发布权限。环境预检不等于真实E2E。

## Windows 环境预检与当前恢复限制（历史）

以下整节记录旧受限环境阶段的失败和当时处理路线，不能当作当前执行规则。原沙箱底层问题未修复；用户后来单独授权的FullAccess真实复验已成功，新入口修正则仅做替身控制测试。

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

Planner始终read-only。默认Coder及工程检查使用workspace-write/unelevated，并要求写边界探针通过；环境失败会停止，不能静默放宽。仅调用者显式选择FullAccess后使用danger-full-access/当前用户原生检查，不再要求OS越界拒绝，也不假称有隔离。两种模式都不构成恶意代码或多租户安全产品；提示词禁读凭据不构成保密边界。Codex可能维护认证缓存/运行日志，`--ephemeral`不代表绝对零宿主写入；工厂不主动编辑全局配置、安装依赖或改变Windows权限。

首版 Auto 基础验证支持 Node、Python 和固定 npm run scripts 的本地 HTTP 工程。不是任意技术栈的全自动交付器。移动/桌面或其他栈需扩展受控验证适配器，不能跳过不支持的门槛宣布成功。UI 行为和截图由 Coder 自测并保存；主控执行这些测试接口并独立检查 HTTP，不能代替外部 Reviewer。测试不等于业务完工或外部验收。

没有 Git Agent、Release Agent、独立生产 Tester/Reviewer、云发布、多个 Coder 并行或完整自动审批；只实施当前 Goal。外部 Reviewer 通过且收到专门 Git 收口授权之前，禁止 Git 写操作。

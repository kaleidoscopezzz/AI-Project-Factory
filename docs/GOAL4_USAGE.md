# Goal 4：生成软件的受控本地 Git 版本

本轮实现项目级授权、本地仓库检查、正式阶段批准校验、明确文件暂存、真实 Commit 与版本记录。Git Agent 不调用模型，不推送、不打 Tag、不进行外部验收或发行。APF Goal 4 尚待外部审查；软件内部质量批准与 APF 里程碑封版是两种不同结论。

## 操作入口

在仓库根目录执行，使用已经完成软件阶段的项目 ID。需要 Python 和本机 Git；无需为 Git Agent 重新调用 Planner、Coder、Tester 或 Reviewer。

```powershell
$ProjectId = '<合法项目ID>'
$RepoRoot = (Get-Location).Path
$RuntimeRoot = $RepoRoot # 使用其他合法运行根目录时由调用者显式指定
.\scripts\git-stage.ps1 -ProjectId $ProjectId -RuntimeRoot $RuntimeRoot
```

未指定写操作时，只读检查该软件 workspace 的自身仓库、分支、HEAD、变更清单与暂存路径。即使 workspace 位于 APF 仓库之内，也不会向上采用 APF 的 `.git`。外部 worktree、共享 Git 目录、符号链接、junction、外部对象库和自定义过滤器被拒绝。

## 一次项目级授权

默认没有本地提交权限。由用户或已获授权的主控提供明确策略；这不是模型产物，也不能由 TaskPacket 自动推导。

```powershell
$PolicyPath = Join-Path $RuntimeRoot "projects/$ProjectId/control/git-policy-input.json"
$Policy = @{
    version = 1
    project_id = $ProjectId
    authorization_id = 'my-local-git-approval'
    allow_init = $true
    allow_local_commit = $true
    branch = 'main'
}
[IO.File]::WriteAllText($PolicyPath, ($Policy | ConvertTo-Json), [Text.UTF8Encoding]::new($false))
.\scripts\git-stage.ps1 -ProjectId $ProjectId -RuntimeRoot $RuntimeRoot -PolicyFile $PolicyPath
.\scripts\git-stage.ps1 -ProjectId $ProjectId -RuntimeRoot $RuntimeRoot -CommitGoal 'Goal 0'
```

`allow_init` 只允许在该软件 workspace 建立仓库；已有仓库可以设为 false。`allow_local_commit` 只允许已取得正式阶段批准的本地版本；不授予 Push、Tag、切换分支或清理历史权限。首次仓库没有 Git 身份时，明确返回 blocked，用户自行配置该软件仓库身份后再决定继续。工具不虚构作者，不修改系统或全局配置。

已有 Sequence 的正式回执必须绑定同一候选和任务包，且其 Tester passed、独立只读 Reviewer approved 的实际 CLI 与证据来源合法。只包含 passed/approved 字样或 AgentDouble 回执不能作为生产业务批准。后续软件 Goal 1 使用它自己的回执：

```powershell
.\scripts\git-stage.ps1 -ProjectId $ProjectId -RuntimeRoot $RuntimeRoot -CommitGoal 'Goal 1'
```

也可在现有主控中调用 `Controller.inspect_project_git(project_id)`、`configure_project_git(project_id, policy)`、`version_approved_stage(project_id, goal)`。这是一项显式的阶段后操作，不改变 Sequence 的原有执行或质量状态机。

## 文件范围与版本来源

提交清单来自批准回执的候选文件 SHA-256，不采用 `git add .` 或 `git add -A`。源码、配置、测试和项目说明保留；`.git` 不属于业务指纹。生成目录、运行缓存和工厂控制账本不进入版本；测试证据由原批准回执引用，在控制目录保存，不把大体量 Agent 日志塞进软件 Commit。

待提交文件检查敏感文件名、凭据格式及个人环境路径；可疑内容拒绝并保留原件，不能代替人工对所有秘密类型的判断。单文件最多 20 MiB，总源码最多 50 MiB，超出时停止说明。未知工作区改动、已有暂存内容、分支不符、忽略规则导致交付文件不能暂存、属性改变批准字节均停止。不会 reset、clean、restore 或删除用户文件。

Git 命令使用有限超时，清除继承的仓库/索引重定向；禁用系统 Git 配置、自动换行转换、hooks、签名和 fsmonitor，保留用户/软件仓库的作者配置。用户或仓库配置的外部 filter 拒绝执行。Git 树中每份实际文件字节必须与批准清单完全相同，Commit 前后都核验；不以命令退出 0 代替内容验证。

`control/git/` 保存项目策略、请求意向、追加事件及 `goal0-version.json` / `goal1-version.json`。版本记录含真实 Commit SHA、分支、阶段、候选和 TaskPacket 指纹、批准来源与 SHA、授权 ID、交付清单。批准文件、旧质量账本不改写；Git 操作失败不撤销真实质量结论。

## 重复和失败

同一阶段已记录且真实 Git 内容、批准来源和历史关系仍一致时，返回 `already_versioned`。工作区与已有 HEAD 完全一致时记录 `no_changes`，不创建空 Commit。Commit 成功但记录写入中断时，只能根据原请求、父提交、提交说明和完整树内容恢复 `recovered`，不重复提交。

Git 失败可留下本次已暂存文件，必须如实报告现场；不会偷偷清理暂存区。未知中断、记录或身份变化、安全检查失败时 blocked，由用户判断后续操作。此增量没有自动重试。

## 验证和未覆盖范围

本轮在全新隔离测试仓库使用真实 Git 验证初始化、提交、内容、重复请求、无变更与异常路径。质量输入使用明确标记的契约夹具，Git 操作测试中替换质量来源检查；没有新的真实业务 Agent 调用。另对现有真实待办软件 Goal 1 批准来源做只读验证，没有在历史软件中初始化或提交。

Git 策略和项目锁都是应用控制，不是 OS 隔离，也不防御同用户恶意修改整个可信账本。外部验收自动化、Tag/冻结、远端仓库、Push、发布打包未实现或不在本轮范围内，需要独立授权。既有 Full Access 无 OS 隔离和 Token 无硬上限的限制继续保留。

# Goal 1 外部 Reviewer 最小整改：待复审

2026-10-09，Asia/Shanghai。依据用户转述的外部静态审查，仅修复两个阻塞项。旧真实成功证据保留，本轮不宣称新入口真实 E2E 已通过，不批准或执行 Git 封版。

## 1. 修改文件与关键差异

六个既有文件已修改；本目录及新的回归结果为新增验证材料，未覆盖旧证据。逐项差异见 changes.patch，修改前副本在 source-before/。

| 文件 | 变化 |
| --- | --- |
| factory/controller.py | 显式 Full Access 允许新需求 Auto 与已有任务 Auto，不再要求已有包或 Retry；新需求仍完整规划/验证/组包/预检后派发Coder。保存调用者选择、不从旧状态继承。Planner提示明确当前执行策略，新任务要求实现工程，重试才限制为修复失败。增加CodexPath与CheckCli，按需初始化执行器。 |
| factory/executor.py | 增加 resolve_codex；显式绝对exe路径优先，错误不回退；文件存在并在10秒内返回有效codex-cli版本才使用。原Planner read-only、Coder显式模式和工程检查分支保留，不硬编码版本目录。 |
| scripts/factory.ps1 | 增加 -CodexPath、-CheckCli 并按argv转交主控。原 -Request/-Mode/-FullAccess 入口可用于新需求。 |
| tests/test_factory.py | 原31项覆盖保留，旧“拒绝新FullAccess”测试更新为拒绝FullAccess Plan；新增10项控制流程、默认权限、实际适配器角色参数、显式CLI路径、无效版本/超时与CheckCli测试。 |
| docs/GOAL1_USAGE.md | 增加显式路径检查、新需求FullAccess与恢复说明，矛盾旧说明改正或明确标为历史。 |
| PROJECT_STATUS.md | 记录外部静态审查及本轮限定整改/验证，状态为最小整改完成待复审；原成功、失败及限制保留为历史。 |

默认不选择FullAccess时仍使用受限模式，失败不自动升级；Planner始终read-only。FullAccess只让本次Coder与工程检查采用当前用户权限，不提权、不修改全局配置。工作目录是任务契约，不是OS隔离。预算、预检、任务包指纹、失败状态、归档、重试限制与独立workspace均保留。

## 2. 回归结果

实际执行 `python -B -m tests.test_factory`：41项通过、0失败、0错误，耗时4.545秒。原31项中30项未变，1项按新的授权范围更新；新增10项。详细映射见 control-flow-double-results.json；原31项结果未改写。

新报告 `validation/goal1/exception-tests-ce98c8a0d8.json`，原始输出同名txt，夹具位于test-workspaces/ce98c8a0d8。测试包含明确标记的AgentDouble/FlowDouble；其completed只是控制夹具状态，不是业务、构建、浏览器或模型成功。

实际适配器参数测试拦截进程执行，分别检查Planner read-only及默认Coder workspace-write/显式Coder danger-full-access。显式CLI路径测试模拟PATH无CLI，且校验不调用PATH回退；不存在路径、无效版本、超时均拒绝。CheckCli测试确保不创建Controller/任务。

## 3. 新需求 Full Access 控制入口

Python入口按等价命令参数 `--request "开发一个离线图书管理 Demo" --mode Auto --full-access --codex-path ...` 测试，PowerShell脚本保留现有FullAccess转发并新增CodexPath转发。

AgentDouble验证：新需求→Planner→完整规划校验→TaskPacket生成和指纹校验→所选模式预检→Coder→主控检查/结果保存，夹具调用顺序Planner、Coder，重试0、共2次替身调用。预检失败夹具只有Planner，Coder未调用、重试0；未指定FullAccess夹具保持默认受限选择。实际记录和任务包路径见control-flow-double-results.json。

以上只验证控制流程。未启动真实Planner/Coder；未启动新的完整E2E或浏览器预检/验收，不能用41项替身回归替代真实验证。

## 4. 独立 PowerShell 的 CLI 路径

实现优先显式路径、否则PATH查找。不自动扫描选择某个版本，不硬编码应用版本目录，不安装/升级CLI。调用者从实际Desktop安装位置选择可信原生exe，指定绝对路径；应用更新后重新检查即可。

普通Windows PowerShell实测：C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe，NoProfile/NonInteractive；仅在子进程环境移除Codex所在目录和桌面CODEX变量，保留Python和系统命令。Get-Command确认codex.exe不可见，然后实际调用factory.ps1 -CheckCli -CodexPath；退出0，输出codex-cli 0.162.0-alpha.2。实际选中的版本目录仅在验证日志中记录，未进入生产代码。

CheckCli只运行本机--version，不检查登录、读取用户配置或创建任务/调用模型；本轮未设置ExecutionPolicy、修改全局PATH/配置或Windows权限。stdout/stderr及所选路径见standalone-powershell-cli-check.json。

使用方式（以下开发命令仅文档示例，本轮未运行）：

```powershell
$cli = '替换为已安装 codex.exe 的绝对路径'
.\scripts\factory.ps1 -CheckCli -CodexPath $cli
.\scripts\factory.ps1 -Request "开发一个离线图书管理 Demo" -Mode Auto -FullAccess -CodexPath $cli
```

## 5. 完整性、限制与停止点

guard-after.json复核通过：44份冻结文件（含三个Skills）、原图书项目146份非缓存文件及参考项目35839文件无差异；参考Git无差异。参考覆盖为全部路径/大小/mtime及node_modules以外SHA，不能宣称完整宿主审计。HEAD/main/goal-0-approved仍为11aa80e1dc345d63f9b325d14227b078c0f924bb，无Git写命令。

本轮真实Planner0、Coder0、E2E0、浏览器测试0，仅41项主控回归及一个本机CLI路径/版本检查。新的一句话FullAccess完整真实链路需要用户另行授权和预算，本轮不执行。原沙箱IPC问题、Token没有硬上限、固定本机Playwright/Edge依赖与FullAccess没有OS隔离的限制仍存在。版本识别是运行检查，不是可执行文件签名或任意程序安全审计。

旧成功报告、证据manifest和外部ZIP都没有重写；其中源码/状态哈希代表整改前版本，当前变更由本目录changes.patch及新evidence-manifest.json表达。没有修改Goal0、旧图书业务工程、参考项目或系统设置，没有进入Goal2。

机器结果见RESULTS.json，当前Git只读记录见git-readonly.json。最小整改已完成，停止等待外部Reviewer复审；不得自行验收、Git封版或启动新的真实测试。

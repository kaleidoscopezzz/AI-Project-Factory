# Windows 快速开始与主线入口

从仓库根目录执行以下示例。CLI 0.1.0 已整合 `main`，可在独立虚拟环境安装并使用 `apf --version`、`--help` 和 `--prompt-generate`，见 [CLI 安装与使用](CLI_USAGE.md)。规划命令只生成文件；新 `apf --build` 接通受控双阶段开发与本地发行，详见 [产品入口](PRODUCT_USAGE.md)。以下原有 PowerShell 开发与恢复入口继续有效，最新验证与批准范围见 [项目状态](../PROJECT_STATUS.md)。

## 环境准备

- Windows 11、PowerShell、Python 3.11+，`python` 可通过 PATH 调用。
- 已安装且登录的可信 Codex CLI；APF 不安装或升级它，也不配置凭证。
- 工厂核心使用 Python 标准库。生成软件的 Node、数据库、Edge/Playwright 等依赖按项目选择，不能把工厂可启动等同于这些环境齐备。
- 当前部分浏览器配置、参考资料守护和复验适配具有原开发环境依赖，换机完整 E2E 尚未验证。不要通过关闭安全机制来掩盖预检失败。

```powershell
git clone https://github.com/kaleidoscopezzz/AI-Project-Factory.git
Set-Location AI-Project-Factory
python --version
```

已有源码时直接进入仓库根目录，不重复克隆。不要求安装全局 Skills；工厂读取仓库中的三个 Skills。

## 普通 PowerShell 指定 CLI

优先选择本机已经安装、可信的原生可执行文件，避免依赖 Desktop 会话注入的 PATH：

```powershell
$cli = Read-Host '请输入已安装且可信的 codex.exe 路径'
.\scripts\factory.ps1 -CheckCli -CodexPath $cli
```

显式路径优先于 PATH；错误路径、非原生程序、无效版本或超时会停止，不回退到另一个程序。检查只执行版本读取，不调用模型、不检查登录、不启动浏览器，也不验证数字签名。应用更新后应重新检查，不能硬编码版本目录。若 CLI 已在 PATH，可省略 `-CodexPath`。

## 当前单阶段入口

只规划、不运行 Coder：

```powershell
.\scripts\factory.ps1 -Request "规划一个离线设备管理演示系统" -Mode Plan -CodexPath $cli -TimeoutSeconds 600
```

规划并开发，包含独立质量检查，发现缺陷即停止、不自动返工：

```powershell
.\scripts\factory.ps1 -Request "开发一个 Windows 本机离线待办工具，先实现新增、查看、删除和本地持久化" -Mode Auto -QualityGate -NoAutoRepair -FullAccess -CodexPath $cli -TimeoutSeconds 600
```

这些命令会消耗真实模型 Token。`Auto` 默认只执行软件 Goal 0，完整规划中的后续阶段不会自动执行。省略 `-QualityGate` 时只有 Coder 与基础工程检查，不能称作独立质量验收。

`-FullAccess` 必须由调用者本次显式选择；Planner/Reviewer 始终只读，Coder/Tester 与工程检查在明确选择后使用当前用户权限，不提权。工作目录不是 OS 边界。默认受限模式预检失败不会静默升级。`Plan` 不接受 `-FullAccess`；规划未来 Coder 的权限意向需要现有 Python 开发 API，意向本身不授予执行权限，实际 Auto 必须再次显式选择且匹配。

新需求 Full Access PowerShell 入口经过确定性控制验证；待办项目真实双阶段接续使用开发 API。两者的验证范围不能混为一谈。

## 查询、接续与重试

```powershell
$projectId = Read-Host '请输入先前返回的项目 ID'
.\scripts\factory.ps1 -ProjectId $projectId -Status
.\scripts\factory.ps1 -ProjectId $projectId -Mode Auto -CodexPath $cli
```

Status 不调用 Agent。第二条复用已有合法规划，实际权限必须与规划意向一致；如规划为 Full Access，调用者需明确加 `-FullAccess`。已登记 Sequence 的项目必须走阶段开发 API，不能用旧 Auto 入口重跑前序。

失败不会自动重试。确需重试且原授权/预算/守护仍有效时，旧单阶段入口支持显式 `-Retry`；它不是任意终结账本的恢复按钮。先检查失败原因和剩余额度，不能改写 state 或任务包绕过守护。

数据位于 `projects/<项目ID>/workspace/`，控制记录位于同项目 `control/`。请保留失败日志；不要把控制文件、凭证或原始私人日志随公开文档提交。

退出码 0 表示对应 Plan 或执行阶段通过；1 表示拒绝/失败；2 表示等待用户确认。Plan 返回 0 不代表软件已开发，基础检查通过不代表 Reviewer 批准。

## 开发 APF 与验证说明

```powershell
python -B -m factory.controller --help
python -B -m unittest discover -s tests -p 'test_*.py'
```

回归使用明确标记的 AgentDouble 和可信本地进程夹具，不派发真实业务 Agent；不等同于真实 E2E。Goal 3 封版时保存的确定性结果为 260/260，本次文档维护不重跑昂贵业务测试。

原阶段默认调用/重试与质量阶段预算见 [质量验证说明](GOAL2_USAGE.md)。示例选择 600 秒单次上限；现有默认配置可能不同。没有 Token 硬上限，超时不等于 Token 限额。

同一软件的受控 Goal 0→Goal 1 使用 [阶段 API](GOAL3_INCREMENT.md)，目前需要确认下一阶段提示词、范围与权限。普通用户零配置入口属于未来工作，不属于当前主线安装能力。

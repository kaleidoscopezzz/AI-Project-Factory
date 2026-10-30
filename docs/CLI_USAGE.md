# AI Project Factory CLI 0.1.0（Windows）

CLI 0.1.0 已整合主线，复用三个冻结 Codex Skills。`--prompt-generate` 只生成规划文件；
新增 `--build` 通过原 Controller、Sequence 和 QualityGate 执行受控双阶段开发，再由
Release Agent 交付本地 ZIP。安装包包含工厂模块与原样 Skill，内部版本仍为 0.1.0。
APF 1.0.0 尚未正式发布；真实与确定性验证范围见 [项目状态](../PROJECT_STATUS.md)。

```powershell
apf --build "开发一个支持新增、完成和删除的本地待办事项软件" --out ".\my-todo" --full-access
apf --resume ".\my-todo" --full-access
```

这两个入口消耗真实模型额度，具有有界 Goal/时间/返工限制，不是无限自动开发。
默认不提交软件 Git、不 Push；本地版本另需 `--allow-local-git`。
详细环境、权限、发行及恢复规则见 [产品使用说明](PRODUCT_USAGE.md)。以下规划命令兼容原行为。

最新待办案例复用已批准 Goal 0 与 Goal 1 真实返工候选，已取得独立 Tester **8/8 AC**
通过和只读 Reviewer **approved**，并生成新的本地 ZIP。包内启动、全部核心操作及重启
持久化已在独立解压目录验证；运行需要 Node.js 26.x（验证版本 26.3.0），不是独立 EXE。
这是明确授权后的分阶段续跑实证，不是一次命令不中断完成任意项目的证明。
`--resume` 不会续期过期预算、追加已耗尽角色额度或静默接受变化的工厂检查点。
已完成阶段和候选继续复用，旧超时/失败与预算不改写；当前尚未创建 APF 1.0.0 正式版本。

## 安装

需要 Python 3.11 或更新版本（本轮在 Windows / Python 3.14.6 验证）。运行依赖仅标准库；
安装构建使用 setuptools。建议在仓库内创建独立环境，无须管理员权限或全局安装 Skills：

```powershell
# 在已克隆的主项目仓库根目录执行。
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\Activate.ps1
apf --version
apf --help
```

若 PowerShell 阻止 Activate.ps1，可仅在当前终端加入环境的命令目录：

```powershell
$env:PATH = (Join-Path (Get-Location) '.venv\Scripts') + ';' + $env:PATH
apf --version
```

不需要改变全局执行策略。关闭终端后重新激活或重新设置 PATH。也可直接运行
`.\.venv\Scripts\apf.exe`。`Get-Command apf` 应指向本次环境，避免命中其他同名程序。

标准 console script 入口由安装器生成。可发行 wheel：

```powershell
python -m pip wheel . --no-deps --wheel-dir .\dist
# 将 wheel 带到目标 Windows 设备，然后在其 Python 环境安装：
python -m pip install .\dist\ai_project_factory_cli-0.1.0-py3-none-any.whl
```

wheel 内含三个完整冻结 Skill 资源的原样快照；目标设备不需要源码仓库。
离线安装 wheel 不调用模型、不下载 Codex、不需要网络；构建 wheel 首次可能需要获取 setuptools。

## 离线元信息

```powershell
apf --version
```

标准输出精确两行，退出码 0：

```text
AI Project Factory 0.1.0
Wit beyond measure is man's greatest treasure
```

`--version` 和 `--help` 不检查 Codex、不读取 Skills、不调用模型。

## 生成规划

以下命令会使用真实模型额度，请由用户手动授权/执行。开发测试没有运行这些真实调用。

```powershell
apf --prompt-generate "我想开发一个图书馆管理系统"
apf --prompt-generate "我想开发一个图书馆管理系统" --out ".\library-plan"
$cli = Read-Host '请输入已安装且可信的 codex.exe 路径'
apf --prompt-generate "我想开发一个图书馆管理系统" --out ".\中文计划" --codex-path $cli
```

未指定 `--out` 时，输出位于当前目录 `apf-plan-YYYYMMDD-HHMMSS`；同秒已存在则用
`-02`、`-03` 等序号。显式目录可含空格和中文。所有文档为 UTF-8、无 BOM。

输出：

```text
library-plan/
  requirements.md     # 需求整理、来源/假设/约束、R/AC/Goal行为映射
  goals.md            # 整个软件开发阶段、进入/退出、依赖、任务及写集
  goal0-prompt.md     # Goal 0提示词 + 完整工程方案，可一并复制给Codex
  planning-run.json  # 调用次数、Codex版本/参数、资源与输出哈希、规划状态
  apf-diagnostic-*.jsonl  # 仅保留安全事件类型和耗时；成功与失败均留存
```

只有结构、覆盖和依赖校验全部通过才写入这四个文件。任一目标文件存在即失败，
没有 `--force`，不静默覆盖；不相关的现有文件不修改。写入失败回滚本次创建的文件。
失败不发布四个规划文件，但一旦进入 Planner 准备阶段，会保留本次 `apf-diagnostic-*.jsonl`
诊断日志。临时资源由本地代码创建并在本次调用结束后清理。

仅一句话通常不足以确定业务工程目录、当前基线、业务权限和重大规则。Skills 要求如实
记录这些缺口；此时输出“草案，不可派发”与阻塞项，仍提供完整可审查计划。
补齐阻塞并人工确认后再交付 Codex，保存规划本身不授权业务开发。

## Codex 定位与权限

1. 显式 `--codex-path` 优先；无效则报错，不回退。
2. PATH 上 `codex`。Windows 原生 exe 直接执行；标准 npm `.cmd/.ps1` 包装器仅用于
   定位旁边 `@openai` 包内唯一原生 `codex.exe`，APF 不通过 shell 执行包装器。
3. `%LOCALAPPDATA%\OpenAI\Codex\bin\*\codex.exe` Desktop CLI，多个版本选修改时间最新者。

Desktop Store 或其他未知安装布局不猜测，使用显式路径。没有开发者用户名或私人路径硬编码。
可用 `Get-Command codex -All` 查来源；APF 不会自动下载 Codex，沿用当前用户已登录认证。

生成前实际运行离线 `codex --version`、`codex --help`、`codex exec --help`、
`codex features list`，然后执行 `codex login status` 确认当前登录态；不读取认证文件内容，
不保存登录命令的原始输出。未登录、版本不兼容或缺少必要隔离开关时在模型调用前停止，
不降级。分支开发资料检查版本为 `codex-cli 0.162.0-alpha.2`；本轮主线整合另外检查本机
CLI 元信息与登录态，其他版本仍须通过同样运行时检查，不宣称全部兼容。登录态退出码
依据 [官方 CLI 命令参考](https://learn.chatgpt.com/docs/developer-commands?surface=cli)。

唯一模型命令为 `codex --no-daemon --ask-for-approval never exec ... -`，需求通过 UTF-8
标准输入传入。固定设置 `--sandbox read-only`、`--ignore-user-config`、`--ignore-rules`、
`--ephemeral`、`--skip-git-repo-check`、`--json`、`--color never`、`--output-schema`。
Windows 指定 `windows.sandbox="unelevated"`；禁用 shell_tool、unified_exec、multi_agent、
multi_agent_v2、plugins、apps、hooks、memories、skill_mcp_dependency_install 和 web_search。
不从桌面会话继承工具管道、会话或权限环境变量；保留 `CODEX_HOME` 以沿用本地登录。
用户 config 仅提取 `model`；不导入其权限、MCP、hooks 或 provider。自定义 model_provider
本版明确拒绝，不偷偷切换提供方。受管理设备的额外策略仍可能使 Codex 拒绝运行。

Planner 只返回文本，不被授予输出目录写权限。完整资源已在输入里，所以无需 shell。
APF 标准库代码负责生成临时输入/Schema、校验 JSONL 和最终结构、写入文件。
默认超时 600 秒，可用 `--timeout 1..3600` 调整；失败不自动重试，最多一次 Planner 调用。
Ctrl+C 或超时终止本次拥有的子进程树；不强杀其他用户进程。

## 实时进度与网络异常

Planner 的 stdout JSONL 在子进程运行期间逐行读取、解析；stderr 同时排空且不转发原始诊断。
交互 PowerShell 终端在 stderr 显示单行 Spinner、已运行时间和当前阶段，每0.1秒刷新。
即使没有新事件，也持续显示最近可确认的状态，不将安静期间猜作连接成功或模型完成。
重定向/非交互终端改用换行文本日志：阶段变化时立即记录，同阶段每10秒记录存活状态，
没有光标控制或颜色序列。stdout继续提供输出目录和最终生成摘要，`--version`仍精确两行。

阶段根据真实JSONL事件显示：会话启动、回合启动等待输出、模型输出、连接异常/重试、
回合报告完成等待进程退出。只识别到重试但没有网络证据时显示“Codex报告重试”；
未知error显示“Codex报告异常”，不猜具体原因。只有收到后续模型输出事件才显示输出恢复。
模型隐藏思考、完整原始事件、错误原文、认证信息和需求正文不出现在进度日志中。

普通 `error` 是告警，不单凭它判定失败，也不立即宣称成功。接受结果必须同时满足：
进程退出码0、唯一 `turn.completed`、没有 `turn.failed`、有效最终JSON，以及原有规划
结构/ID/依赖/Goal 0范围校验通过。`turn.failed`、非零退出码、超时、输入传输失败、
非法结果仍拒绝发布。结构校验和文件写入状态由APF自身的实际操作更新，完成字样仅在成功后显示。
`planning-run.json`记录 `observed_codex_error_events` 计数和诊断日志文件名，不保存错误原文。

### 诊断日志（成功、失败都会留存）

每次进入 Planner 准备阶段时在 `--out` 目录独占创建
`apf-diagnostic-UTC时间戳-随机值.jsonl`；终端输出完整位置。文件逐事件刷新，
即使失败也不会清除。日志仅含相对耗时、事件类型、item 类型、
运行成功/失败与本地异常类名，不保存模型正文、隐藏思考、stderr 原文、
请求正文、凭据或 JSONL 原始消息。日志最多记录 10000 条事件，超限记录截断标记。

已知禁止工具类型（如 `command_execution`、`file_change`、`mcp_tool_call`、
`web_search`）仍被拒绝。`error` 类型 item 仅作为被动诊断事件，
不得单凭它判定最终失败；接受条件不变。其他未知 item 类型单独报
“协议兼容性未确认”，记录类型后拒绝，不自动放宽执行权限。

PowerShell 查看最近一次日志：

```powershell
Get-ChildItem .\library-plan\apf-diagnostic-*.jsonl |
  Sort-Object LastWriteTime -Descending | Select-Object -First 1 | Get-Content
```


重试状态表示Codex在本次调用内报告重试；APF不会自动重新启动整个Planner或增加调用次数。
以下仅为模拟网络恢复日志示例（非交互 stderr），不是一次真实模型生成记录：

```text
[APF 00:00] Codex 会话已启动，等待回合事件
[APF 00:00] 规划回合已启动，等待模型输出
[APF 00:00] 连接异常；Codex 正在重试，尚未确认恢复
[APF 00:00] 模型输出已恢复，执行中
[APF 00:00] 回合报告完成，等待进程退出
[APF 00:00] 结构校验中
[APF 00:00] 结构校验通过，准备写入文件
[APF 00:00] 文件写入中
[APF 00:00] 文件写入完成
```

## Skills 发现与复用

每个 Skill 的发现顺序：`--skills-dir` 指定目录（若提供则只查此处）、当前目录 `skills/`、源码相邻 `skills/`、
`$HOME\.agents\skills`、`$CODEX_HOME\skills`（默认 `$HOME\.codex\skills`）、wheel 内资源。
源码安装优先仓库权威原文；用户级安装没有被修改。检查 name/description frontmatter、
本地 Markdown 资源引用和链接边界；缺失或损坏停止，不借模板冒充规划。

全部资源原样复制到本次临时工作目录 `.agents/skills/<name>` 并逐文件核对哈希，
同时完整 SKILL.md、模板、references 作为指令内容传入。提示词显式使用
`$requirement-planner` → `$goal0-scaffolder` → `$goal-prompt-writer`，限定本次副本。
职责依次为需求/整个Goals、Goal 0工程方案、Goal 0开发提示词；三者协调在一个规划回合完成。
这些是 Codex 指令资源，不是导入的Python函数。输入契约只规定传输和结构，未改冻结Skills。

Codex 的本地 `.agents/skills` 发现与 `$skill` 调用见
[官方 Skills 文档](https://learn.chatgpt.com/docs/build-skills)；结构化输出与当前登录复用见
[官方非交互执行文档](https://learn.chatgpt.com/docs/non-interactive-mode)。
`planning-run.json` 保存源路径和每个资源哈希；`skills_used` 是模型自述，不能当独立复用证明。
该运行记录含本机路径，应作为私有材料保存，公开分享前检查并脱敏，不自动加入 Git。

结构校验检查必需章节、内容长度、占位符、稳定ID、AC覆盖、有序无环依赖、Goal 0的
R/AC/Task引用和退出边界。Goals和提示词前面的Goal 0范围由同一结构字段渲染。
这些检查不能证明自然语言所有语义完全一致，真实规划质量须人工审查。

## 常见错误与退出码

| 情况 | 处理 |
| --- | --- |
| `apf` 无法识别 | 激活环境/在当前PATH加入Scripts；用 `Get-Command apf` 检查 |
| 找不到Codex | 安装并登录现有Codex，配置PATH或传入原生exe路径；APF不代安装 |
| 尚未登录、网络/额度问题 | 自行执行 `codex login status`，必要时 `codex login`；不填写新API Key |
| Codex不兼容 | 检查实际help和features，用户自行更新已安装CLI；不回退完全访问 |
| Skill缺资源 | 检查三个完整目录，或用 `--skills-dir` 指定；不全局安装 |
| 已存在输出文件 | 改用新 `--out`，手工检查旧结果；没有自动覆盖选项 |
| 空需求、目录不可写 | 提供需求，选择可写目录；在模型调用前停止 |
| 模型失败/非法JSON/不完整结构 | 非零退出，拒绝发布；用户检查后自行决定是否重试 |
| 草案不可派发 | 查看blockers，补齐业务目录、基线、重大规则及授权，再人工确认 |

成功为0；生成/配置/文件/模型失败为1；参数用法错误为2；Ctrl+C为130。
不读取认证文件内容，不在报告打印凭据或模型原始错误日志。

## 确定性测试和真实质量测试

```powershell
python -m unittest tests.test_apf_cli tests.test_apf_progress -v
```

使用手写fixture和Python假Codex子进程，明确为模拟结果，绝不调用真实模型。
本轮整合使用真实安装的 console script 和确定性 Fake Codex 检查文件生成；不是一次真实
模型规划验收。最小后续授权是用户手动执行一次上述图书馆命令到全新目录：
最多一次Planner模型调用、只读、无其他角色、无自动重试，人工检查三个文档与三个Skill职责、
范围一致性和中文可读性。失败时停止，新增调用需用户另行决定。

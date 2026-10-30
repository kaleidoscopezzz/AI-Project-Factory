# AI Project Factory 1.0.0

APF 本体的首个正式版本：面向个人 Windows + 已登录 Codex CLI 的受控软件开发工厂。
验证范围为小型本地待办软件的 **Goal 0 → Goal 1 两阶段生成、独立质量验收与 ZIP 交付**，包含明确授权的接续过程。

## Windows 安装

需要 Windows 11、PowerShell、Python 3.11+（安装验证使用 3.14.6）、Git，以及已安装并登录的可信 Codex CLI。
本轮生成软件使用 Node.js 26.x（验证版本 26.3.0）；Web 验收还需要 Edge 和可用的 Playwright 工具环境，APF 不自动安装这些运行依赖。

推荐从本 Release 的源码 Tag 安装：

```powershell
git clone --branch v1.0.0 --depth 1 https://github.com/kaleidoscopezzz/AI-Project-Factory.git
Set-Location AI-Project-Factory
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\apf.exe --version
.\.venv\Scripts\apf.exe --help
```

也可下载本 Release 的 `ai_project_factory_cli-1.0.0-py3-none-any.whl` 和 `SHA256SUMS.txt`，核验 SHA-256 后安装：

```powershell
.\.venv\Scripts\python.exe -m pip install --no-deps .\ai_project_factory_cli-1.0.0-py3-none-any.whl
```

APF wheel 包含 CLI、工厂模块和三个原样冻结 Skills；没有捆绑 Codex、Node.js、Edge 或模型凭据，不要求额外 API Key。
`apf --version` 精确输出：

```text
AI Project Factory 1.0.0
Wit beyond measure is man's greatest treasure
```

## 使用

在安装目录执行（输出目录必须不存在）：

```powershell
.\.venv\Scripts\apf.exe --build "开发一个支持新增、查看、编辑、完成和删除的本地待办事项软件" --out ".\my-todo" --full-access
```

`--prompt-generate` 保留仅规划行为。`--build` 复用 Planner、TaskPacket、Coder、Tester、独立只读 Reviewer、阶段回执与 Release Agent，质量批准后才创建本地软件 ZIP。
可显式加 `--allow-local-git` 允许获批软件阶段的本地版本管理，默认不写软件 Git，绝不自动 Push。

生成软件的 ZIP 需要相应运行环境；在新的可写目录解包后，按包内说明运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1 -Port 3000
```

打开 `http://127.0.0.1:3000`。当前进程的 ExecutionPolicy 参数不修改系统策略。

## 已验证能力

- 同一软件的受控两阶段真实规划、增量编码和前序批准接续。
- 修复后 Goal 1 独立 Tester 八项 AC 全 passed，独立只读 Reviewer approved，正式阶段回执与候选来源一致。
- 新软件 ZIP 的独立解包、包内启动、新增/查看/编辑/完成/删除及重启持久化验证通过。
- 授权本地 Git 版本管理、来源绑定与本地发行；失败记录、预算和昂贵调用复用受到保护。
- 本次发布只运行安装、版本、帮助及针对性确定性测试，复用已有真实验收，没有重新调用业务 Agent。

## 范围与限制

- 仅验证上述 Windows / Node.js 小型项目与两阶段受控接续；不是任意多 Goal 无人值守开发的保证。
- 真实返工产物已通过独立复验/批准，但同一轮自动触发返工的完整真实闭环尚未验证。
- Full Access 是当前用户权限，没有 OS 级工作区隔离；Reviewer 保持只读。单次模型最多600秒、普通整轮最多3600秒，Token没有硬上限。
- 换机完整开发 E2E、复杂需求忠实度、多模型自由编排、GUI、云部署、通用EXE及安装器不在本版本验证范围。
- 示例 Todo ZIP 是生成软件的验证成果，**不是 APF 本体安装包**，本 Release 不将其作为 APF 安装资产。
- `--version`/`--help` 离线，不启动模型；`--build` 和 `--prompt-generate` 使用登录账户并消耗模型额度。

安装详情见 [CLI 使用说明](https://github.com/kaleidoscopezzz/AI-Project-Factory/blob/v1.0.0/docs/CLI_USAGE.md)，执行边界见 [产品说明](https://github.com/kaleidoscopezzz/AI-Project-Factory/blob/v1.0.0/docs/PRODUCT_USAGE.md)。

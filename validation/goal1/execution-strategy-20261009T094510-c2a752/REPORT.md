# Goal 1 执行策略诊断与待授权运行方案

日期：2026-10-09。状态：环境探针通过，派生 Coder Full Access 尚未启用，等待用户确认。本报告不是业务验收通过结论。

## 已核实的启动链

`scripts/factory.ps1` → Python `factory.controller` → `factory.executor.CodexExecutor` → Codex CLI 0.162.0-alpha.2。

当前适配器清除父会话权限上下文；派生 CLI 显式使用 `--ignore-user-config`，Planner 为 `-s read-only`，Coder 为 `-s workspace-write`。构建、测试和服务被包装为 `codex sandbox -P :workspace -c windows.sandbox="unelevated"`。因此桌面主会话 Full Access 没有传递为派生 Coder 的执行策略。只读取全局配置的模式字段，没有读取认证内容或修改全局配置。证据：`launch-chain.json`。

## 本次实际环境验证

仅执行现有可信环境探针和固定内容 Playwright 探针，没有运行生成业务工程，没有调用 Planner/Coder。

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| 当前账户原生令牌 | 非 restricted、非 AppContainer | native-probe.json |
| Windows 命名管道读写、libuv 与 Mojo 请求访问掩码 | 错误码均为 0 | native-probe.json |
| Node 管道子进程 | 退出 0，无 EPERM | native-probe.json |
| Chrome、Edge 固定空白页 | 均退出 0 | native-probe.json |
| Node → Playwright → 已安装 Edge | 退出 0，固定 DOM 校验通过，3.119 秒 | playwright-edge-probe.json |
| Chromium 自身沙箱 | Edge 探针显式 chromiumSandbox=true | playwright-edge-probe.cjs |
| Playwright 默认 Chromium 文件 | 不存在 | playwright-edge-probe.json |

现有受限令牌的管道访问拒绝诊断仍保存在 `../environment-repair-20261009T010203/`。本次对照支持权限模式是既有 EPERM/IPC 的原因范围，没有证明某一 Codex 内部缺陷已修复。Playwright 默认浏览器缺失是另一个独立问题，可复用已安装 Edge，避免下载或安装全局浏览器。正式派生 CLI 在 Full Access 下的工具执行尚未验证。

## 具体候选执行方案（尚未启用）

1. 添加仅本次运行显式选择的 Full Access 参数，默认仍沿用原模式；不从全局配置或桌面环境隐式推导。不修改全局设置、不提权为管理员。
2. 只对既有项目 `p-dc1e9d42b5ae` 的 Coder 使用 `-a never exec --ignore-user-config -s danger-full-access -C C:\AI-Project-Factory\projects\p-dc1e9d42b5ae\workspace`；其他现有 CLI 限制、日志与超时保留。Planner 不重新执行。
3. 经确认后，构建、业务测试、服务与浏览器验证由当前账户原生子进程执行，不再用受限令牌包装。采用相同工作目录、项目内 TMP/TEMP/cache、输出脱敏、进程超时与自有进程树清理。浏览器继续启用自身 Chromium 沙箱。
4. 在模型调用前，用所选模式重新做固定环境预检，未通过不消耗 Coder 重试。原越界拒绝探针在 Full Access 下不能充当安全隔离通过证据；不得把无 OS 隔离包装成有隔离。检查路径契约及前后文件指纹属于检测措施。
5. 复用原 Planner 四份规划、TaskPacket、Goal 0 提示词和源码。原任务包 SHA-256 为 `edb6c6afa62657c5dc2d899e4774bed1855b5e4dd5b9689ca67ac746207c8ad2`，仍需执行原校验。保留原始证据，重试前归档可能被最新结果替代的控制记录。
6. Coder 仅修复已定位的浏览器入口及复验实际发现的必要问题，不重新生成工程。主控在修复现有源码的情况下应检查源码实际变化，不能要求通过无用新文件冒充开发。最小适配改动先执行主控回归。
7. 一次真实 Coder 调用，上限 900 秒，使用原剩余一次重试；每项主控检查上限 180 秒，正式验收一轮。失败停止留证，不新建项目或再次规划。不提高原调用预算。模型 Token 数由 CLI usage 实际记录；耗时/调用上限不是严格 Token 硬上限。
8. 实际运行构建、业务测试和浏览器测试，保存截图与 trace；HTTP 200 不替代浏览器验收。仍需核对冻结 Skills、参考项目、规划和任务包未变，并如实记录 Full Access 没有 OS 越界阻止能力。

## 权限范围与风险：需本次明确确认

Full Access 使派生 Coder 及生成工程执行进程具有当前 Windows 用户可用的文件、进程和网络权限；`-C` 指定工作目录不是操作系统访问边界。它不会自动获得管理员权限，但可访问工作目录以外当前用户原本可访问的路径。无需逐命令审批的模式意味着错误代码可能误写其他文件或访问不相关数据。

不修改 Skills/参考项目/其他工程、不读取无关凭据、不执行 Git 写操作、不改系统配置等仍为明确任务约束；工作目录校验、环境清理、日志脱敏、前后哈希、预算与超时降低误用风险，但不能防止全部越界或证明未读取其他文件。不能宣称该方案保留了原 OS 文件隔离。浏览器自身沙箱只约束浏览器，不能隔离 Coder 或 Node。

按照用户本次指令第二部分第 5 条，必须先说明上述范围，再由用户确认本次运行是否启用。当前未启用、未提交权限更宽的模型任务。

## 当前状态与恢复点

Goal 0 仍已验收冻结；Goal 1 仍为“开发中，环境受阻，未完成”。原任务仍已失败，历史 Agent 调用 2、重试 0；本阶段新增 Planner 调用 0、Coder 调用 0，新增模型 Token 0（不包含主会话对话用量，该用量未取得）。业务构建、业务测试、浏览器验收与正式 E2E 本阶段均未运行。

用户确认后才实施并启用上述最小适配、预检及一次真实复验；拒绝或未确认则停止于诊断结果。旧专项报告和完整性漂移记录原样保留，不以新的快照抹去历史。

官方说明：[Codex 权限模式](https://learn.chatgpt.com/docs/agent-approvals-security)、[Codex 命令参数](https://learn.chatgpt.com/docs/developer-commands)、[Playwright 已安装浏览器 channel](https://playwright.dev/docs/browsers)。实际参数与启动结果以本地 CLI 帮助、适配器和上述探针日志为准。

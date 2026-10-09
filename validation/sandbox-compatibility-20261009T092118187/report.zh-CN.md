# Windows Codex 最小沙箱兼容性检查

检查 ID：SBX-COMPAT-20261009。日期：2026-10-09，Asia/Shanghai。

## 结论

本会话实际有效策略为 `danger-full-access`（未启用执行沙箱），approval_policy 为 `never`。无法确认本会话已启用 MXC，因此按用户指定条件停止，不运行 Goal 1 Node 命名管道或 Chrome/Edge IPC 探针。本轮未切换权限模式。

该结论依据本会话 rollout 的实际 turn_context（2026-10-09T01:18:01.278Z），并与执行环境提供的有效权限元数据一致；并非仅依据 config.toml。当前命令不能归类为 MXC、elevated 或 unelevated 沙箱内的执行。

## 版本和系统事实

- Codex Desktop 安装包版本：26.1002.7124.0（Get-AppxPackage）。
- 后端：codex-cli 0.162.0-alpha.2（运行中后端路径执行 --version；session_meta 同样记录该版本）。
- Windows 11 家庭版 中文版，10.0.26200，Build 26200，64 位。
- 本会话 ID：01a11e3c-d319-7ed0-bfd7-d67196ce3458。

## 配置与诊断事实

config.toml 中 sandbox_mode = danger-full-access，windows.sandbox = elevated。MXC 相关布尔开关的原始键和值已白名单提取到 diagnostics.json 的 mxc_feature_settings。windows.sandbox 和功能开关属于配置意图，不能覆盖本会话的实际策略证据。

观察到 codex-windows-sandbox-service.exe（PID 14632），但没有本会话命令经由 MXC 启动的证据；服务存在不能证明 MXC 已启用。其可执行路径在普通 CIM 查询中为空，本轮未为此提权。

沙箱日志 2026-10-09 09:10:22—09:10:36（北京时间）记录运行时 node_repl.exe 访问验证失败：`open ACL target for root-only update: 另一个程序正在使用此文件，进程无法访问。 (os error 32)`。setup_error.json 为 `helper_unknown_error` / `setup refresh had errors`。这是本会话开始前的诊断错误，未证明其导致当前有效策略；本轮没有执行初始化或修复，也没有调整 ACL。

## 探针结果

| ID | 探针 | 实际结果 |
| --- | --- | --- |
| SBX-P01 | exec_command 启动 powershell.exe，无配置文件，输出固定标记后 exit 0 | 成功，输出 APF_SANDBOX_MINIMAL_START_OK，exit_code 0；未记录启动错误 |
| SBX-P02 | Goal 1 Node 命名管道 | 未运行：未确认 MXC 启用 |
| SBX-P03 | Goal 1 Chrome IPC | 未运行：未确认 MXC 启用 |
| SBX-P04 | Goal 1 Edge IPC | 未运行：未确认 MXC 启用 |

SBX-P01 只证明当前有效权限下能启动最小命令，不能用于认定 MXC IPC 兼容性。

## 证据

- `diagnostics.json`：系统、版本、白名单配置、会话策略、进程摘要、带源路径和行号的诊断错误摘录。
- `minimal-start.json`：实际工具结果、命令、退出码及执行参数。
- 源会话日志：`C:\Users\44725\.codex\sessions\2026\10\09\rollout-2026-10-09T09-17-45-01a11e3c-d319-7ed0-bfd7-d67196ce3458.jsonl`。
- 源诊断：`C:\Users\44725\.codex\.sandbox\sandbox.2026-10-09.log`、`C:\Users\44725\.codex\.sandbox\setup_error.json`。
- 官方术语参考：https://learn.chatgpt.com/docs/config-file/config-basic?translationFallback=zh-Hans 。官方文档只用于解释配置，不用于认定本机运行实现。

仅向本次 validation 目录写入证据；未调用 Planner、Coder 或子 Agent，未执行 E2E，未修改 APF 业务代码、Skills、Git、Windows 权限或全局配置，未安装软件，未读取凭证文件，未操作 C:\910Program。本报告不是 Goal 0/Goal 1 验收或冻结结论。

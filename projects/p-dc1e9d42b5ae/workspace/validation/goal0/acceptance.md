# Goal 0 自测验收记录

性质：Coder 自测；2026-10-09 本机实际执行。外部 Reviewer 身份、来源、时间、结论均未发生。最终源码候选见 source-sha256.json；执行配置见 session-environment.json。

|R|AC|Task|输入与预期|实际结果|方法/命令/退出码与证据|状态|
|---|---|---|---|---|---|---|
|R-001|AC-001|T-001|构建、回环服务、health、dist 资源|构建成功；健康字段准确；真实浏览器加载 CSS/JS|node scripts/build.mjs=0，node scripts/test.mjs=0；build.log、test.log、requests.json、runtime-restart.log|通过|
|R-002|AC-002|T-003|三条稳定 ID、书名作者、刷新|UI 三条与 seed 对比通过，刷新后保持|完整测试=0；test.log、browser-trace.zip|通过|
|R-003|AC-003|T-003|两可借一借出，汇总一致，无状态 API|领域/UI 3/2/1 通过，状态 PATCH 404|完整测试=0；test.log、behavior.log、desktop-1440x900.png|通过|
|R-004|AC-004|T-003|片段/空白/大小写、空态清空、记录不变|全部搜索断言及文件比对通过|完整测试=0；test.log、browser-trace.zip|通过|
|R-005|AC-005|T-003|双视口、键盘、焦点、对比度、截图|无横向溢出，可达，Enter/Esc 成功；7 组颜色均 >=4.5；截图已查看|完整测试=0；contrast.json、desktop-1440x900.png、mobile-390x844.png、browser-trace.zip|通过|
|R-006|AC-006|T-002|UI 确认、刷新、进程重启、revision|UI 写入后实际服务进程重启，值保留，UI/API/文件 revision=1|完整测试=0；runtime-restart.log、browser-trace.zip|通过|
|R-007|AC-007|T-002|取消无写入、空白/121 码点拒绝|文件含元数据不变，UI 不开确认框，API 400|完整测试=0；test.log、behavior.log、browser-trace.zip|通过|
|R-007|AC-008|T-002|延迟禁用、重复点击、幂等、旧版本|PATCH 一次；相同 operationId revision 仅加一；409 不变|完整测试=0；requests.json、test.log、browser-trace.zip|通过|
|R-008|AC-009|T-002|失败保留草稿/文件，损坏/schema 拒绝和恢复|503 保留原文件；损坏不覆盖；恢复读取成功|完整测试=0；browser-errors.json、test.log、browser-trace.zip|通过|
|R-001|AC-010|T-004|阻外域后列表/搜索/保存/刷新|外域尝试 0，意外 HTTP/请求/控制台错误 0；预期故障 503 单独登记|完整测试=0；requests.json、browser-errors.json、browser-trace.zip|通过|
|R-009|AC-011|T-003|虚构 DEMO 文案、非回环拒绝、Origin 拒绝|UI 文案通过；非回环子进程退出 1（预期）；Origin 403 且文件不变|完整测试=0；test.log、behavior.log、desktop-1440x900.png|通过|
|R-010|AC-012|T-005|文档、矩阵、实际数量、指纹、日志/PNG/trace|本记录及状态/中文说明齐全；历史失败保留；无保护范围访问/Git 写入|文件核对及 Coder 操作记录；source-sha256.json、session-environment.json、PROJECT_STATUS.md|通过|

汇总：AC 通过 12、失败 0、跳过 0；最终 Node 测试 5、通过 5、失败/取消/跳过 0。最终构建和完整测试退出码均 0。固定 Node spawnSync 管道输出 42、退出 0。健康与运行验证包含在完整测试中，并真实运行 scripts/serve.mjs --host 127.0.0.1 --port <隔离端口> 重启服务，runtime-restart.log 记录端口 63882。

历史失败不删除：

- validation/history-20261009-095732-444/goal0/build.log：旧环境首次构建失败。
- validation/history-20261009-095732-444/goal0/test.log：旧环境 spawn EPERM，主体未运行。
- validation/history-20261009-095732-444/PROJECT_STATUS.md：旧阶段阻塞状态与证据缺口。
- validation/history-20261009-095808-578/goal0/test.log：本次首次全量 4 通过/1 失败，503 控制台消息分类错误。
- validation/history-20261009-095808-578/goal0/browser-trace.zip：本次失败轮真实 trace。
- validation/history-20261009-095808-578/goal0/desktop-1440x900.png、validation/history-20261009-095808-578/goal0/mobile-390x844.png：失败轮原始截图。
- validation/history-20261009-095808-578/goal0.test.mjs：失败轮测试源码。

本次两次修复、两轮完整自测；仅改变启动选项和预期 503 分类，不跳过业务断言。预期 400/403/404/409/503 已真实验证；浏览器一次预期 PATCH 503 和对应控制台消息在 browser-errors.json 精确登记，意外错误数组为空。

最终证据索引（以下均已存在）：build.log、test.log、runtime-restart.log、desktop-1440x900.png（初始列表，1440×900）、mobile-390x844.png（工程验证区域，390×844，未裁剪）、browser-trace.zip（搜索、取消、确认、保存、刷新、重启及失败链路）、requests.json、browser-errors.json、behavior.log、contrast.json、source-sha256.json、session-environment.json。本目录旧 build-recheck.log、runtime.log、runtime-http.log 属于历史，不作为本轮成功证据。

事实：未调用 Agent，无 Git 命令/安装/发布；未访问保护目录。未运行：其他浏览器/平台、Python、生产认证及参考目录哈希复核。外部验收未发生；仅标记“Goal 0：已完成，待外部 Reviewer 验收”。

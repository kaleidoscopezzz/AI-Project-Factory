# Goal 0 自测验收记录

性质：Coder 自测，非独立审查。外部 Reviewer：未发生。日期为环境提供的 2026-10-09；没有伪造精确执行时间。输入指纹见 PROJECT_STATUS.md。

| R | AC | Task | 输入与预期 | 实际结果 | 方法/证据 | 状态 |
|---|---|---|---|---|---|---|
|R-001|AC-001|T-001|构建、127.0.0.1:4173、健康和 dist 资源成功|构建复核 0，HTTP 200，浏览器资源验证未运行|build.log、build-recheck.log、runtime-http.log|部分验证|
|R-002|AC-002|T-003|三条稳定 ID、书名作者，刷新不变|API 三条正确；UI/刷新未运行|runtime-http.log；tests/goal0.test.mjs 为计划|部分验证|
|R-003|AC-003|T-003|两可借一借出，计数一致，无状态修改|API 计数 3/2/1；领域/UI/接口拒绝测试未运行|runtime-http.log；源码|部分验证|
|R-004|AC-004|T-003|片段、修剪、大小写、空态、清空不变|计划已编码，测试主体未运行|test.log|受阻|
|R-005|AC-005|T-003|两视口、键盘、对比度、原始 PNG|未运行，无 PNG，未作人工截图审查|test.log|受阻|
|R-006|AC-006|T-002|UI 保存、刷新、进程重启、revision 一致|未运行；不得将初始文件读取冒充保存|test.log|受阻|
|R-007|AC-007|T-002|取消不变、空白/超限 UI 与 API 拒绝|未运行|test.log|受阻|
|R-007|AC-008|T-002|延迟禁用、重复点击、operationId、旧版本|未运行|test.log|受阻|
|R-008|AC-009|T-002|写失败、草稿保留、损坏/schema 失败、恢复|未运行|test.log|受阻|
|R-001|AC-010|T-004|断外域真实浏览器全链路、无意外错误|未运行，无请求日志/trace，不声称零错误|test.log|受阻|
|R-009|AC-011|T-003|DEMO 文案、非回环失败、Origin 拒绝|文案和实现存在；行为测试未运行|源码；test.log|受阻|
|R-010|AC-012|T-005|文档、矩阵、实际数量、指纹、PNG/trace 索引|文档和已有证据齐全，PNG/trace 未生成，门槛未满足|本目录与 PROJECT_STATUS.md|部分完成|

完整 AC 通过 0、受阻/未完整验证 12；不以部分结果计作通过。Node 报告文件级测试 1、通过 0、失败 1、跳过 0；5 个计划测试主体未运行。

实际命令：node --version（0）；node scripts/build.mjs（1）；node scripts/test.mjs（1）；修复后 node scripts/build.mjs（0）；node scripts/serve.mjs --host 127.0.0.1 --port 4173（实际启动，工具会话停止后 1）；node --input-type=module 的原生 fetch 检查（0，五条 HTTP）。各检查未达到 180 秒超时。

首个构建候选未在修改前生成源码指纹，这是证据缺口；保留了原始失败日志，最终候选有 SHA-256。不得用最终指纹冒充初始候选。修复仅改 scripts/build.mjs；测试受阻结论及实际 HTTP 检查都对应最终候选。

证据索引：

- build.log：首次构建失败，stdout/stderr 为 undefined；Node spawnSync 错误未被旧脚本有效打印，根因由测试相同 spawn EPERM 及构建去除 spawn 后成功推断。
- build-recheck.log：唯一构建修复复核成功。
- test.log：真实测试启动失败堆栈及数量。
- runtime.log：启动与停止记录。
- runtime-http.log：实际健康、资源及三条记录响应。
- source-sha256.json：最终候选 src/scripts/tests/data 文件内容指纹。
- desktop-1440x900.png、mobile-390x844.png、browser-trace.zip、requests.json、behavior.log、contrast.json：计划产物，未生成。

没有执行 API 拒绝测试，因此预期 400/403/404/409/503 不能登记为实测成功。未访问参考项目，未作参考项目哈希复核；所有 Git 写操作为零。

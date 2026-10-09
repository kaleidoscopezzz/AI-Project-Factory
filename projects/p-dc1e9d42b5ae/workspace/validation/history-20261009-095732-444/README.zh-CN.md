# 阅间：离线图书借阅演示

Goal 0 工程草案已实现，但自测受环境阻塞，尚未完成，外部 Reviewer 验收未发生。

本工程使用 Node 原生 HTTP、HTML/CSS/JavaScript 与隔离 JSON 文件，无外部运行依赖。三条虚构图书支持列表、只读借阅状态和书名/作者搜索；仅 B-001 工程备注提供确认后保存。没有借出/归还、读者、真实认证或生产授权功能。

在本 workspace 执行：

```powershell
node scripts/build.mjs
node scripts/serve.mjs --host 127.0.0.1 --port 4173
# 浏览器打开 http://127.0.0.1:4173
node scripts/test.mjs
```

服务只接受 127.0.0.1。静态资源来自 dist；首次运行从不可变 data/seed.json 初始化 var/demo/store.json。已有文件损坏或 schema 不识别时明确失败，不覆盖文件。可用 DEMO_DATA_DIR 指定 workspace 内独立目录。没有一键清空入口。

模块入口：src/contracts 定义提交校验与错误；src/domain 定义搜索和汇总；src/adapters 实现串行文件写入、revision 与 operationId；src/server 装配 HTTP；src/web 实现界面。后续可在这些入口增量扩展，本次没有实施下一 Goal。

测试使用用户指定的只读 Playwright 模块，不安装或下载浏览器。当前沙箱拒绝 Node 子进程（spawn EPERM），node:test 的隔离进程未启动，真实浏览器、重启和截图测试尚未执行。测试代码存在不等于已验证。详见 PROJECT_STATUS.md 和 validation/goal0/acceptance.md。

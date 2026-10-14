# 一句话开发与本地发行（产品整合入口）

在已安装 `apf` 的 Windows PowerShell 中执行：

```powershell
apf --build "开发一个支持新增、完成和删除的本地待办事项软件" --out ".\my-todo" --full-access
```

这会调用真实模型并消耗额度。需要 Python 3.11+、已登录的可信 Codex CLI、Git、相应的
Node.js 或 Python 运行环境，以及 UI 验收所需的 Edge 和已安装 Playwright。
默认发现本机 Codex；可用 `--codex-path <可信codex.exe>` 显式指定，失败不回退。
Playwright 优先使用已有 Codex 依赖；其他安装位置可设置 `APF_PLAYWRIGHT_PATH` 为其包目录。
APF 不下载浏览器，不安装全局依赖，也不索取 API Key。

`--full-access` 是明确的本次工程执行授权：Coder、Tester、构建/运行检查使用当前 Windows
用户的文件、进程及网络权限，没有 OS 级工作区隔离。Planner 和独立 Reviewer 始终只读。
省略该选项会在派发模型前停止，不从桌面应用继承执行权限。

## 两个命令的区别

| 命令 | 输出和行为 |
| --- | --- |
| `--prompt-generate "需求"` | 一次只读规划，生成 requirements.md、goals.md、goal0-prompt.md；不开发或发行 |
| `--build "需求" --full-access` | 一次结构化规划，生成正式 TaskPackets，执行两个软件 Goal，独立测试/审查后发行 |
| `--resume ".\my-todo" --full-access` | 在原账本、来源和预算内恢复；不隐式重试失败模型，不修改需求 |

`--build` 没有从自由格式 Markdown 猜测任务包。它复用 Controller 的规划契约，要求同一次
Planner 响应提供完整计划、独立 Goal 1 实施契约和明确发行文件清单，再经过原有校验器。
三个冻结 Skills 以完整原文和模板参与规划。旧规划命令行为不变。

## 已支持的范围与预算

- 最多两个顺序软件 Goal：Goal 0 建立可运行基础，Goal 1 完成独立增量任务；原始需求及完整规划保留。
- Node/Python 标准库回环 HTTP 项目；每阶段一条直接脚本 build 和 test，不自动安装运行依赖。
- 运行脚本接受 `--host 127.0.0.1 --port {port} --data-dir var`；包内保留获批脚本的原相对路径。规划不满足原发行接口时，在Coder派发前停止并保留完整原响应。
- 超过两个 Goal、必须额外安装环境、重大业务歧义或不支持的发行类型会停止，不能静默丢需求。
- 整轮最多 Planner 1、初始 Coder 2、CoderRepair 1、Tester 3、Reviewer 3；额外质量调用仅用于返工后复验。
- 默认每次模型最多 600 秒，整轮墙钟 3600 秒；`--timeout` 可缩短单次预算，恢复不能扩大预算。
- 自动 Retry 为 0；一次有真实实现缺陷依据的返工由原 QualityGate 执行。业务失败或证据不可信不能被格式修正掩盖。
- Token 没有可靠硬上限；保存 CLI 实际提供的 usage，没有费用硬限制。

模型正在执行时被中断，且无法确认最终检查点的，不会自动重派。已完成且来源有效的阶段
会跳过昂贵调用；工厂代码、候选或证据变化会停止。恢复参数需保留原来的 Git 授权和超时。
整轮墙钟从创建运行时起计算，暂停时间也计入；过期后不得通过 resume 获得新额度。

Node 运行检查现在通过私有标准输入管道请求应用已有的 SIGINT 清理处理，再在有限等待后
强制结束本次启动的进程树。发行解压检查的 PowerShell → Node 启动链也使用同一请求机制。
此机制不修改用户的系统设置、不提供 OS 隔离，也不能代替应用自身的异常退出恢复设计。
辅助启动失败的非零退出码保持原值，不会因关闭处理改成成功。

## 输出与运行

输出目录必须不存在，不覆盖已有文件。运行信息包括：

```text
<输出目录>/
  .apf/run.json                         整轮身份、共享预算、实际调用与状态
  .apf/product-plan.json                完整原始产品规划
  .apf/projects/<项目ID>/workspace/      增量演进的软件工程
  .apf/projects/<项目ID>/control/        原 Controller / Sequence / QualityGate 记录
  .apf/releases/<项目ID>/<发行ID>/       ZIP、独立解压验证与来源记录
  BUILD_RESULT.json                     成功时的交付摘要
  RUN.md                                成功时的运行说明
```

控制记录含本机路径及私人执行日志，**不要把整个输出目录上传公开仓库**。
发行 ZIP 使用明确清单，只包含运行文件与发行说明；凭据、缓存和内部账本不进入包。
只有 Tester 合法通过、独立 Reviewer approved、正式阶段回执校验通过后才能发行。
Release Agent 在独立副本构建，检查 ZIP 文件及 SHA-256，在全新目录解压并实际启动。
当前 `http-health` 配方验证启动和健康响应；`offline-todo` 配方另验证实际增删改、完成及重启持久化。
不要把仅健康响应的验证称为完整交付业务操作验证。

成功输出包路径、运行前提、启动命令、验证状态、来源与 SHA-256。先将 ZIP 解压到新的
可写目录，再在解压目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1 -Port 3000
```

打开 `http://127.0.0.1:3000`。仍需安装包注明的 Node/Python；它不是独立 EXE 或安装器。
ExecutionPolicy Bypass 仅针对这个 PowerShell 进程，不改变系统策略。

## 可选的本地 Git

```powershell
apf --build "开发一个本地待办工具" --out ".\my-todo" --full-access --allow-local-git
```

此选项只授权最终已批准软件阶段的本地初始化/Commit。复用 Git Agent 的文件范围、敏感
内容检查和批准绑定，不逐文件重复询问，也不 Push、不 Tag、不创建远端仓库。
需要现有可用 Git 身份；APF 不代填个人身份或修改全局配置。Git 失败不抹掉质量批准，
保留原因并停止后续发行。已有用户改动不清理、不重置。

## 验证范围

产品整合的确定性测试覆盖双阶段全链控制、拒绝不发行、共享调用限额、有限返工、完成
恢复及输出保护。Fake 发行仅用于控制逻辑，不能代替真实模型或实际软件 ZIP 验收。
真实新需求的验收结果以 [项目状态](../PROJECT_STATUS.md) 的当前产品记录为准。
已有 Goal 0～5 案例不充作本次新命令的真实成功案例。

本次新需求完成真实 Planner 与 Goal 0 Coder，独立质量 Agent 尚未派发。锁问题已在独立
修复副本中完成正常停止、异常终止恢复、持久化及并发保护检查。副本使用 Node.js 26.3.0
自带 SQLite 的 OS 文件锁作为互斥器，业务数据仍为原 JSON；没有删除原候选的空锁或数据。
该副本拥有新的候选指纹，尚未获得质量批准，不能沿用旧指纹发行。

原规划中的标题编辑和删除属于尚未执行的 Goal 1，本轮不授权新增全量 Coder，故停止模型
派发。原运行的墙钟预算已经结束，工厂代码检查点也不匹配当前修复代码；不能通过修改旧
账本或直接重跑 `--resume` 绕过。接下来需要明确授权尚未执行的增量开发，并在保留原始
规划/Coder 来源的正式接续机制中验证新候选；目前尚不是只差发布按钮。

本轮未新增 Planner/Coder/Tester/Reviewer 调用，未获新的质量批准、未生成发行 ZIP。
因此不能把此命令描述为已经通过 APF 1.0.0 真实全链验收。

APF 1.0.0 尚未正式发布。任意规模/任意 Goal 无人值守、真实自动返工通用保证、换机完整
体验、强制 AGENTS.md、详细需求忠实度专项、多模型、GUI、云发布和安装器仍未交付。

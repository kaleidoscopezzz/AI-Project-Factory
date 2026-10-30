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

### 显式授权的成果接续

维护者可使用现有 `factory.product.ProductRun.handoff` 为已完成一次 Planner 和软件 Goal 0
Coder、尚未调用质量 Agent 的停止运行建立独立接续。它需要新的授权标识和显式 Full Access
选择，不会修改旧预算、代码检查点、失败账本或真实模型结果，也不会复制质量批准。

接续绑定原始执行文件、TaskPacket、候选、Skill/工厂快照和来源 SHA。必要的路径/运行参数
适配及经授权的源码修复会形成新的任务包指纹和候选，并执行实际基础检查。原 AC 和任务
范围保留；Tester/Reviewer 必须重新检查新候选。同一授权只能绑定一个运行，原来源变化
会停止派发，不能通过更换输出目录刷新同一授权。

当前接续上限是 Planner 0、Goal 0 全量 Coder 0、Goal 1 Coder 1、CoderRepair 1、Tester 3、
Reviewer 3；单次至多 600 秒，新授权窗口 3600 秒，Token 无硬上限。创建完合法接续后，
继续使用既有入口，不需要手工改内部 JSON：

```powershell
apf --resume ".\my-todo-continued" --full-access
```

这不是普通 `--resume` 的自动续期，也不支持无限链式接续或任意历史状态迁移。

如果软件 Goal 0 已取得真实 Tester/Reviewer 批准、Goal 1 尚未批准且候选仍与前序批准一致，
维护者可在新的明确授权下调用 `ProductRun.continue_goal1`。它核验正式阶段回执、质量结果、
原 TaskPacket 及完整规划，复制工作区并只重定位执行路径；旧批准和失败账本保持原字节。
批准回执继续保留原 TaskPacket 身份，新执行包与来源的路径重定位关系另行验证。

该入口只分配 Goal 1 Coder 1、CoderRepair 1、Tester 2、Reviewer 2；所有 Planner 和
Goal 0 Agent 均为 0。第二次质量调用只用于真实返工后的复验，每次最多 600 秒，独立授权
窗口 3600 秒，无 Token 硬上限。它不会自动更新过期预算，重复授权标识会被拒绝。

创建上下文时实际装配最终 Coder 输入，绑定经核验的前序批准路径、SHA、时间、候选和
质量结论，说明工作区中旧“待验收”自测文档的历史性质。实际派发输入必须与预检一致，
不一致则零模型停止。接续使用既有 `apf --resume`，不会重跑已批准的 Goal 0。


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

本次新需求已复用真实 Planner 和 Goal 0 Coder，通过上述授权接续将锁修复纳入新候选。
Node.js 26.3.0 自带 SQLite 只提供 OS 文件互斥，业务数据仍为 JSON；原空锁和原数据不删除。
运行参数和包入口按现有 Release 契约重新绑定，AC 与业务范围不变，旧检查点和预算不改写。
软件 Goal 0 的 12 项 AC 已通过真实 Tester 和独立只读 Reviewer，并有正式阶段回执。

此前 Goal 1 Coder 因缺少明确的前序正式批准而在编码前停止，原 failed 结果保留。
随后在新的有限授权下，`ProductRun.continue_goal1` 已建立独立执行包、来源绑定、预算和
检查点。正式批准路径、原始 SHA、时间及候选进入最终提示词，并解释旧自测文档的历史
性质；实际派发输入与零模型预检一致。重定位只改变执行路径，不修改原 AC 或批准原件。

历史：此前接续的 Coder 曾被平台额度限制拒绝，原始失败及其调用额度完整保留。

最新明确授权下，Goal 1 Coder 已保存编辑、删除、UI、测试和文档，但 600 秒内未返回
完整回合。`ProductRun.accept_saved_delivery()` 仅接受具有真实交付声明、原清单 SHA、
实际源码增量和独立基础检查的单次超时产物，记录 interrupted_with_verified_delivery；
原失败调用、计数、时间和输出不改写。没有保存声明、文件篡改或权限不符时拒绝接收。
这不是新模型调用，不替代独立 Tester/Reviewer，也不会刷新整轮预算。

真实 Tester 7/8 项 AC passed，独立深目录副本测试发现 SQLite 锁数据库的 Windows
长路径缺陷。一次真实 CoderRepair 仅修复路径转换，自测 build/test 通过。旧文档中的
修复前源码引用只绑定受控原轮次快照 SHA，标记为历史资料；当前候选及未来测试仍使用
新指纹。修复后的材料预检已通过，失败轮次、原始 Tester 输出和准备失败目录都保留。
`ProductRun.recover_repaired_preparation()` 只适用于已有合法返工且新候选未派发的材料
准备失败；保留原账本副本、新代码检查点和原时限，不产生质量批准或新的模型额度。

历史续跑窗口曾不足以完成独立复验和审查，原过期账本保持原样。2026-10-30 新授权下，
`ProductRun.open_quality_window()` 在同一 runtime 中建立独立预算/结果文件和质量上下文，
继续调用既有 Sequence、QualityGate 与 Release Agent。Planner/初始 Coder 的预算为 0；
默认只需 Tester 1、Reviewer 1，只有真实缺陷才能使用一次返工及对应复验，不自动续期。
不得用普通 `--resume` 绕过授权或覆盖旧账本。

### 最新真实发行验收（2026-10-30）

本轮真实 Tester 八项 AC 全部 passed，独立只读 Reviewer approved。上一轮的实际返工
候选未改动，取得正式 Goal 1 阶段回执后才发行。新增 Planner/Coder/CoderRepair 均为 0；
旧 Coder 超时和首次 Tester 失败保持原样。深层辅助测试夹具路径问题以同 SHA 的较短
独立副本复测解决，保留失败日志，没有修改源码/断言或忽略当前 AC。

新 ZIP：12 个文件、10,563 字节；SHA-256：
`f127b3d16cd0307e89deba52bfbcd7f2eace7969547e94c5d0e6aafac1d29b91`。
在原开发/runtime 之外全新解包，包内 Windows PowerShell 启动脚本及新增、查看、编辑、
完成、删除、重启持久化验证通过。它依赖 Node.js 26.x（本轮 26.3.0），不包含运行环境。
本地验证 ZIP 没有作为 GitHub Release 附件公开；不要将历史 Goal 5 ZIP 当作这份新包。

用户取得 ZIP 后，解压到新的可写目录，在解压目录执行：

```powershell
node --version
powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1 -Port 3000
```

打开 `http://127.0.0.1:3000`；按 Ctrl+C 停止，数据保存在解压目录的 `var`。端口占用可改
`-Port 3001`。ExecutionPolicy 仅作用于当前 PowerShell 进程，不修改系统策略。

当前案例已完成真实双阶段接续到 ZIP 的验收；分阶段新授权不等于完全无人值守的单次
输入闭环。真实返工候选的复验/批准已成立，同一轮自动触发返工全过程仍未真实验证。

APF 1.0.0 尚未正式发布。任意规模/任意 Goal 无人值守、真实自动返工通用保证、换机完整
体验、强制 AGENTS.md、详细需求忠实度专项、多模型、GUI、云发布和安装器仍未交付。

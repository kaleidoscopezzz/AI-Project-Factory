# Goal 5：本地软件发行

Release Agent 将已获得真实质量批准的软件阶段，转换为经过构建、解压和运行检查的本地便携 ZIP。入口为 `scripts/release-stage.ps1`，Python API 为 `Controller.release_approved_stage(project_id, goal, config)`。没有模型调用、Git 写操作或远端上传。

**Goal 5 已限定范围封版**，批准 Tag 为 `goal-5-approved`。范围是已批准候选的本地构建、ZIP 检查、独立解压运行和来源绑定交付记录，不代表 APF 1.0.0 已发布或任意技术栈均可自动发行。

## 输入与授权

先完成现有 Sequence 的正式阶段批准。工具复用 Git Agent 的只读批准验证，核对阶段回执、TaskPacket、候选文件和独立真实 Tester/Reviewer 来源；它不会重新启动质量 Agent，也不要求候选已有 Git 仓库。当前共享验证器要求 Git 命令已安装。存在本地版本记录时校验其 Commit 树与批准候选一致，否则版本字段明确为空。

配置是调用者明确提供的 JSON，不从候选自动发现或执行任意构建命令。字段如下：

| 字段 | 用途 |
| --- | --- |
| `version` | 固定为 `1` |
| `project_id`、`goal` | 已批准软件项目与 `Goal 0` / `Goal 1` 阶段 |
| `authorization_id` | 非空的本次本地发行授权标识 |
| `name` | 简短的小写英文、数字及连字符包名 |
| `source_files` | 从批准候选中选择的完整构建输入清单，逐份验证 SHA-256 |
| `package_files` | 实际交付文件清单；只允许选定源码及 `dist/`、`build/` 产物 |
| `runtime_requirement` | 公开运行前提；不得包含本机路径或私人信息 |
| `timeout_seconds` | 每条工程命令与每次启动等待的上限，1～180 秒 |
| `smoke` | 通用 `http-health`，或当前待办软件的 `offline-todo` 检查 |

构建、测试及启动配方直接来自正式 TaskPacket；发行配置不能替换命令。第一版支持直接执行 Node/Python 脚本的回环 HTTP 软件，暂不支持任意 shell 命令、自动安装依赖、桌面 EXE 转换或 npm 生命周期。启动必须明确绑定 `127.0.0.1` 并接受受控端口。

候选中的测试脚本可能引用已安装的本地测试工具。这些文件可以作为经哈希验证的**构建专用输入**，不会修改其字节；包含私人路径的文件不能进入公开发行包。凭证、内部账本、缓存和运行数据均不能交付。

## 执行

在仓库根目录打开 PowerShell，设置自己的项目 ID、运行根目录及已准备的配置文件：

```powershell
# $ProjectId 和 $RuntimeRoot 指向已有的正式批准项目。
# release-config.json 由调用者按上表明确配置。
.\scripts\release-stage.ps1 -ProjectId $ProjectId -Goal 'Goal 1' `
    -RuntimeRoot $RuntimeRoot -ConfigFile .\release-config.json

# 预检 ready 后，显式开始本地发行。
.\scripts\release-stage.ps1 -ProjectId $ProjectId -Goal 'Goal 1' `
    -RuntimeRoot $RuntimeRoot -ConfigFile .\release-config.json -Execute
```

默认只做输入预检。`-Execute` 才会复制构建输入，执行批准配方并生成发行包。配置授权标识是调用者意图记录，不是操作系统级隔离或凭证认证。

## 产物与使用

输出位于运行根目录的 `releases/<project-id>/<release-id>/`，成功结果含 ZIP、`release-record.json`、配置、真实命令 stdout/stderr、退出码、运行检查及哈希索引。ZIP 内只放明确清单、`START.ps1`、中文 `README.txt` 和 `RELEASE_SOURCE.json`，不带工厂内部日志或旧验收材料。

将 ZIP 解压到**新的可写目录**，在解压目录运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1 -Port 3000
```

打开 `http://127.0.0.1:3000`；端口占用可改成 3001；Ctrl+C 停止。执行策略参数只作用于这一次 PowerShell 进程，不修改系统设置。待办软件需要已加入 PATH 的 Node.js 22 或更高版本，不内置 Node，也无第三方 npm 依赖。数据保存于解压目录的 `var/`；一个数据目录只运行一个服务。

工具实际执行 ZIP CRC、清单和 SHA-256 验证，拒绝路径穿越、链接和覆盖已有解压目录；随后从包内启动脚本启动服务。待办配置额外检查界面/静态资源、新增、编辑、完成状态、查询、重启持久化及删除。检查结束只终止本轮拥有的进程树；记录受控清理的退出码，不能将它冒称为程序自然退出成功。

## 已验证发行实例

原待办软件 Goal 1 的发行 ZIP 含 9 个文件，8,687 字节；原包 SHA-256 为 `4bd82c79f9880ef6e3bada3c1a758f9a2691995aea9d92fee621a0d554559651`。Windows 发行验证使用 Node.js 26.3.0，已从新解压目录实际检查新增、编辑、完成状态、查询、删除和重启持久化。外部独立审查另使用 Node.js 22.16.0 在 Linux 验证核心服务，不等于 Linux 下 Windows 启动脚本或完整发行链路均已验证。

历史发行包只保存在本地验证资料中，本文不提供 GitHub 发布附件下载。包需要已安装的 Node.js，不是免安装 EXE；公开软件发行、运行环境捆绑和安装器尚未提供。

## 重复、失败与限制

相同阶段、候选、批准来源及发行配置得到稳定 Release ID。再次请求会校验现有包和日志后返回 `already_released`。失败或中断目录保留，不隐式重试；没有通过解压运行验证的 ZIP 保留 `.partial` 名称，不生成成功交付记录。发行失败不修改原阶段批准、原候选或 Git 历史。

每文件限制 20 MiB、总交付限制 50 MiB。运行检查使用当前用户权限，工作目录不是 OS 沙箱；同用户恶意并发无法由这些应用检查隔离。敏感信息扫描是保守启发式，不能保证识别所有秘密。首版为本机便携交付，不提供安装器、代码签名、远端 Release、Push、部署、上传或跨机器完整兼容保证。自动返工真实模型闭环与任意多 Goal 无人值守能力不因本功能而获得验证。

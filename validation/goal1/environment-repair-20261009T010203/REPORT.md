# Goal 1 环境专项诊断与有限复验

日期：2026-10-09，Asia/Shanghai；从夜间中断点于上午继续。项目：`C:\AI-Project-Factory`。

结论：已定位受限令牌下的管道写连接拒绝访问，并完成失败预检与预算保护的最小修复；底层 Windows IPC 环境未修复。一次真实适配器预检失败，未进入正式端到端复验。**Goal 1：开发中，环境受阻，未完成。** 本报告待外部 Reviewer 检查，不自行宣布验收。

本次复用 `projects/p-dc1e9d42b5ae/`，没有新建业务项目或重新规划。此前 `validation/goal1/REPORT.md`、控制日志、失败记录和规划保持原样；本目录是独立增量证据。诊断脚本的退出0只表示收集完成，不表示环境通过。

## 1. Node EPERM：事实与原因范围

当前 Node：`C:\Program Files\nodejs\node.exe`，v26.3.0。Codex CLI：0.162.0-alpha.2，路径见 `cli-metadata.json`。探针使用现有适配器的 `codex sandbox -c windows.sandbox="unelevated" -P :workspace -C <原workspace> -- ...`，未切换 full access、未关闭私有桌面。

| 独立探针 | 本轮真实结果 |
| --- | --- |
| 宿主固定 `node --version`，不加载项目代码 | 退出0 |
| 受限令牌中 `cmd /d /c ver` | 退出0 |
| Python→Python普通子进程，捕获输出 | 退出0 |
| 受限令牌中 `node --version` | 退出0 |
| Node→Node，stdio=inherit / ignore / 文件句柄 | 三者均退出0 |
| Node→Node，stdio=pipe | EPERM，status=null |
| 相同管道探针，cwd分别为原workspace、私有TEMP、私有诊断目录 | 三者均EPERM |
| Node localhost TCP 服务与客户端 | 退出0，返回ok |
| Win32默认命名管道服务端创建 | 成功 |
| 同一受限令牌，命名管道客户端读连接 | 成功 |
| 新管道客户端写连接 / 读写连接 | 两者均拒绝访问，Win32错误5 |
| 仅移除继承的CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY，保持原沙箱 | Node管道仍EPERM，Win32连接仍错误5 |

证据：`diagnostics.json`、`restricted-probe.json/log.jsonl`、`pipe-boundary-detail.json`、`without-package-context.json`、`native-inventory.json`。GetTokenInformation实际观察到 `is_restricted=true`、四个restricting SID、`is_app_container=0`。未请求调整令牌、提权或修改对象ACL。

上轮 `scripts/test.mjs` 的外层stdio=inherit可启动 Node 测试运行器；运行器内部创建带管道的测试进程时触发EPERM。当前三类无管道启动成功，排除了“所有子进程均被禁止”或“Node可执行文件无法访问”的解释；变更cwd/TEMP未改善，文件输出可写，说明这三个位置的工作/临时目录不是本次最小复现的触发因素。

进一步只读核查从中断处继续，新增 `pipe-acl-followup.json`、`pipe-access-followup.json`。最初GetSecurityInfo查询返回87的记录原样保留；改用GetKernelObjectSecurity后成功读取实际管道描述符，没有修改它。管道DACL给SYSTEM、管理员和当前用户完整权限，Everyone/Anonymous仅文件读权限；restricting SID列表有workspace相关SID、登录SID与Everyone，**不包含这个管道owner的当前用户SID**。写/读写、读+WRITE_DAC、libuv写端、与Chromium Mojo相同访问掩码的客户端连接全部返回错误5，普通读连接成功。

这将本次最小复现的原因明确到：**默认管道DACL没有给限制SID所需的写/WRITE_DAC权限，受限令牌访问检查拒绝了客户端端点**。与实际Node启动矩阵及浏览器Mojo失败行相互印证；仍未通过系统调用跟踪直接记录Node的每次API调用，也未定位到具体CLI修复版本或所有机器的行为。

本机Node报告libuv 1.52.1；对应上游源码的uv__create_pipe_pair先以默认描述符创建命名管道，再以包含WRITE_DAC的权限打开客户端；ERROR_ACCESS_DENIED明确映射UV_EPERM。[libuv 1.52.1 管道实现](https://raw.githubusercontent.com/libuv/libuv/v1.52.1/src/win/pipe.c)，[错误映射](https://raw.githubusercontent.com/libuv/libuv/v1.52.1/src/win/error.c)。这是源代码机制核对，未重新编译或替换Node。

受限进程TokenDefaultDacl已经给登录SID GENERIC_ALL、OWNER_RIGHTS READ_CONTROL，实际命名管道DACL却采用另一套默认权限。因此仅调整TokenDefaultDacl没有证据能改变该管道默认描述符，不实施这种补丁。向限制列表加入当前用户SID则可能同时放宽该用户拥有的文件访问，不能作为保留原文件边界的快捷修复；未修改令牌、ACL或注入DLL。

`runtime-source-inventory.json`确认materialized codex.exe与实际CLI二进制SHA一致，排除本次使用旧命令runner文件的解释；较旧helper没有执行或替换。存量elevated setup marker版本5、创建于2026-06-10，仅反映历史初始化，不能直接认定它就是setup refresh失败的原因。没有跨版本或管理员初始化复验。

## 2. 浏览器 IPC：独立失败证据

直接在同一受限workspace启动已安装Chrome/Edge，访问固定 `about:blank`；用户数据及崩溃目录分别指向新建 `.factory-tmp/environment-probe-857cd684aa/chrome`、`edge`。保留Chromium自身沙箱，不使用 `--no-sandbox`，不加载业务源码。

| 浏览器 | 进程创建 | 退出码 | 时间 | 关键stderr |
| --- | --- | --- | --- | --- |
| Chrome | 成功，PID23740 | 4294930433 | 0.104秒 | Crashpad CreateFile 0x5；Mojo platform_channel FATAL 0x5 |
| Edge | 成功，PID14084 | 2147483651 | 7.082秒 | Crashpad / Mojo FATAL 0x5；缓存、Network目录授权亦报拒绝访问 |

本轮Chrome结果为明确失败退出，上轮Chrome超时记录保留，不改写。用户数据父目录已在workspace成功创建，仍存在浏览器内部网络子进程的目录授权失败，不能宣称全部profile权限正常。主故障发生在IPC，业务页面尚未打开；不能据此判业务代码错误。与Win32管道写拒绝的共同权限机制是有证据支持的推断，尚无完整系统调用跟踪。

原始stderr均在 `diagnostics.json`。诊断结束后按本次独有profile路径筛选浏览器进程，结果为空，见 `remaining-probe-processes.json`；未按进程名批量结束用户浏览器。没有业务浏览器测试通过、截图或trace。

继续核查得到本机Chrome 154.0.8037.98、Edge 154.0.4258.62。与Chrome版本匹配的Mojo源码先用默认描述符CreateNamedPipeW，再用 `(FILE_GENERIC_READ | FILE_GENERIC_WRITE) & ~FILE_APPEND_DATA` 打开客户端，并检查端点有效性；本次相同掩码0x0012019B的只读权限探针返回错误5，见 `pipe-access-followup.json`。[Chromium 154.0.8037.98 平台通道实现](https://raw.githubusercontent.com/chromium/chromium/154.0.8037.98/mojo/public/cpp/platform/platform_channel.cc)。这支持Chrome Mojo与Node共享同一类管道权限阻塞；未获取Edge定制源码或完整Crashpad调用跟踪，Crashpad具体失败链保留为日志证据范围。

## 3. 采用的最小修复与有限复验

修复执行适配/主控的失败处理，不修改生成工程、冻结Skills或规划：

1. `CodexExecutor.preflight` 为 Windows Node/npm 任务运行固定Node管道探针，仍走原unelevated workspace沙箱；20秒外层超时、5秒子进程超时，真实退出码与超时决定结果。
2. 已有TaskPacket/规划先校验，预检与原写边界探针成功后，才扣除显式重试预算并派发Coder。预检失败不会绕过失败状态或转full access。
3. 预检、写边界探针、sandbox-verification采用独立随机文件名，保留早期历史文件。
4. 增加主控异常回归：环境失败不调用Planner/Coder、不消耗已有任务重试、保留规划和探针记录。
5. 完整性检查发现既有 `a+b` 锁文件打开方式每次恢复都追加一个ASCII“0”字节（0x30）；改用独占创建/读写重开，仅空文件初始化，不截断既有锁。第一次修正读取锁定字节导致并发测试错误，已改为查询文件大小；中间失败日志保留，最终并发与锁内容回归通过。

一次实际适配器预检：退出1、0.155秒、`passed=false`，Node报告EPERM。见 `environment-preflight-8cb87b68c6a7.json/log.jsonl`、`minimal-verification.json`。这验证了**检测失败并停止的修复**，没有验证环境已经可用。该记录由执行时版本产生，后续仅澄清错误消息措辞，没有再次执行Node预检。

依用户限定，最小环境验证未通过，因此正式E2E复验0次，Coder重试0次。没有通过调试选项/关闭浏览器沙箱/文件输出替换完整测试来规避必需验收。

## 4. 权限边界

保持原受限令牌、workspace范围和私有桌面。没有安装/升级WSL、Docker、VM或工具；没有编辑全局配置、Windows安全设置、目录/管道ACL、令牌默认DACL；没有将生成源码交给宿主full access执行器。本轮主控回归用审阅过的固定Python夹具，明确标注AgentDouble，不运行真实Coder生成的业务源码。

Win32探针仅请求现有对象写访问，再关闭句柄；不截断、不写内容、不创建外部标记。以下8个对象均返回错误5：control目录、原state.json、工厂skills目录、goal-prompt-writer/SKILL.md、工厂.git目录、工厂AGENTS.md、参考目录、参考PROJECT_STATUS.md。实际workspace私有诊断目录及文件可写。见 `pipe-boundary-detail.json`。

这些结果仅证明所测对象，不证明所有宿主对象、注册表和网络都完全隔离。OpenAI Docs将unelevated定义为受限令牌加文件ACL、较弱网络隔离；它不是恶意代码多租户隔离。官方elevated采用低权限独立用户等更强边界，但需要管理员批准的初始化。[OpenAI Docs：Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)。

## 5. 本轮文件变化

修改：`factory/executor.py`、`factory/controller.py`、`tests/test_factory.py`、`docs/GOAL1_USAGE.md`、`PROJECT_STATUS.md`。

新增：`factory/windows_probe.py`、`scripts/diagnose_goal1_environment.py`；本目录诊断/快照/报告；本轮三次主控回归报告及隔离测试夹具（见第8项）；原工程`.factory-tmp/`中的私有探针文件/profile（忽略的运行数据，不删除）。运行数据变化：第一次无Retry恢复令 `control/controller.lock` 追加一个ASCII“0”字节（0x30），未截断或恢复锁内容，修正后的再次恢复不再改变其字节。

未修改三个Skills、Goal0案例/报告、原项目源码、原control规划与日志、参考项目。最终差异与覆盖范围见 `guard-final.json`、`file-changes.json`。保留既有Goal1未提交成果，不覆盖它们以恢复所谓干净工作区。首次检查因运行锁变化返回false，原记录保留在 `guard-after.json`、`guard-first-check.json`。最终检查仍为false：除了运行锁外，还发现跨中断点的工厂Git目录和用户配置漂移，详见第10、15项；不把受保护业务文件通过等同整个守护检查通过。

## 6. 已有规划和任务包复用

原ID：p-dc1e9d42b5ae。原TaskPacket校验仍有效，指纹 `edb6c6afa62657c5dc2d899e4774bed1855b5e4dd5b9689ca67ac746207c8ad2`。四份规划产物、planner-result、提示词、预算、身份及验收映射全部按现有 `validate_packet` / `validate_plan` 验证，未改包/状态绕过校验。新预检接收这个原包；未创建替代规划。

## 7. Coder结果

本轮没有调用Coder；上轮真实Coder创建代码但失败的事实保留。当前无法验证Coder完成所有必要工程操作，不能报告成功。剩余一次重试未消耗。

## 8. 构建与测试

原业务工程：本轮未执行build/test；上轮独立结果build退出0、test退出1、health HTTP200，来源原REPORT及控制日志。HTTP200没有替代完整测试。

本轮主控适配回归共三次，均保留独立报告：初次26/26通过（f366a1347d，3.169秒）；锁修正初版27项出现2个错误（b8a8939a2b，3.135秒）；最终27/27通过（a9e1c5c82e，3.181秒）。最终证据：`../exception-tests-a9e1c5c82e.json/txt`。后两轮仅因新锁修正及实际失败而复测，未增加Node/浏览器环境复验或Agent调用。明确使用AgentDouble；超时/脱敏测试为固定本地真实子进程。这不是27条真实Agent链路或业务AC通过。

## 9. 浏览器验收

Chrome/Edge独立环境启动探针失败；业务UI浏览器验收未执行，没有截图/trace。不能报告12项工程AC通过。

## 10. 沙箱越界与完整性

8个所测对象写访问均被拒；未在参考/冻结目录创建探针文件。`before.json`与`guard-final.json`独立比对：44份冻结文件、原工程非临时文件、全部已有Goal1历史证据，以及参考目录35839文件/只读Git信息无差异。control仅运行锁出现可解释的一字节追加，状态、规划、日志、包等证据字节不变。

跨中断点出现另外两类变化，必须单列：工厂.git从235文件到272文件，新增38个objects、原 `refs/codex/turn-diffs/captures/1791478557135/0a857a75-d30e-41fa-98b8-6d1a00123f98/base` 消失；用户config SHA变化。夜间首次guard中的这两项相同，而上午续作最终guard不同。路径与应用turn capture命名空间一致，但不能仅凭路径确认写入者。本Agent未调用Git写命令、未编辑全局config，未回滚/清理这些变化；不能声称.git或config整体未变化，最终guard保留 `passed=false`。

只读核对当前所选model、approval、sandbox_mode、windows.sandbox仍与先前观察一致，私有桌面无显式覆盖；实际所有Node/管道诊断显式使用unelevated及:workspace，并取得相同的受限SID列表。配置的宿主danger-full-access不是生成项目的执行策略，没有据此运行不可信源码。详细观察在 `external-drift-observation.json`，仅记录白名单字段、未读取凭据；完整漂移内容与来源尚未确认。发现漂移后暂停进一步运行测试/Agent，仅收口报告。

参考node_modules仅路径/大小/mtime覆盖，其他文件SHA覆盖；不比较访问时间，不把它称为所有依赖内容哈希。有限路径权限检查也不是完整宿主安全审计。

## 11. 真实端到端

本轮正式尝试0、成功0；历史真实尝试1、成功0。没有completion.json。环境门槛失败后停止，不浪费剩余Agent预算。

## 12. 自动恢复与持久化

实际执行不带Retry的既有任务恢复：退出1、仍“已失败”、Agent调用2、retries0，见 `recovery-no-retry.json`。修复运行锁后一次同样无Retry的恢复仍退出1，锁字节不再变化，见 `recovery-after-lock-fix.json`。没有再次调用Planner，原state/events与规划指纹保持。新预检/诊断日志真实落盘；主控回归验证环境拒绝后失败状态与error持久化、原规划保留。故障注入只作为回归，不冒充真实断电恢复。

| 用户要求的独立验证项 | 本轮结论 |
| --- | --- |
| 1. 规划安全复用 | 校验通过；哈希比对另存 |
| 2. TaskPacket有效 | 实际校验通过 |
| 3. Coder在隔离workspace执行 | 本轮未派发，不能新增通过结论 |
| 4. Coder必要工程操作 | 未完成；Node管道阻塞 |
| 5. 基础构建及工程测试通过 | 本轮未复验；历史完整测试失败 |
| 6. 必需浏览器验收 | 未通过，环境探针失败 |
| 7. 冻结目录防越界 | 8个对象拒绝写；完整性比对另存，有限覆盖 |
| 8. 失败不标成功 | 真实预检失败、恢复仍失败；回归亦通过 |
| 9. 状态/日志持久保存 | 新日志可读取、原状态保存；回归通过 |
| 10. 恢复不重跑规划 | 实际无Retry恢复调用数不变；回归验证显式Retry预检拒绝 |

## 13. 调用、时间与Token

本轮真实Planner0、Coder0、正式E2E0；新增角色执行时间0秒、新增Planner/Coder模型调用Token0。独立诊断脚本14.347秒（含初始快照/原生信息采集），实际预检0.155秒，三轮主控回归合计9.485秒；不是整轮对话耗时，这些范围有独立原始计时。父会话总Token与总耗时未通过产品接口提供，保持未知，不推算账单。见 `metrics.json`、`session.json`与各原始结果。

用户要求继续后，仅追加两次有新增信息目的的只读管道探针（0.400秒、0.338秒），分别取得DACL和TokenDefaultDacl/精确Mojo访问掩码；不重跑完整Node矩阵、浏览器、Planner/Coder或正式E2E。锁复核只做无Retry恢复。上述探针退出0仅表示收集完成，客户端连接仍然失败。

上轮主链2次调用、耗时1244.812秒、输入247901/缓存208000/输出25418保持历史，不算成本轮消耗；没有读取认证文件或获取密钥。

## 14. Goal状态

Goal0：已验收冻结。Goal1：**开发中，环境受阻，未完成**。根PROJECT_STATUS已同步本轮诊断和限制；不标记待验收完成，更不标外部验收通过。

## 15. Git

HEAD及 `goal-0-approved^{commit}` 均保持 `11aa80e1dc345d63f9b325d14227b078c0f924bb`；main，见 `git-baseline-resumed.txt`、`git-branch-resumed.txt`。本Agent只运行只读命令并使用 `--no-optional-locks`；未执行commit/tag/push/reset/restore/clean或其他Git写命令。工厂.git有第10项记录的跨恢复变化，来源未独立确认，因此不能承诺所有进程都没有Git目录写入。未尝试删除/恢复应用记录。

工作区保留之前未提交Goal1成果及本轮增量：M PROJECT_STATUS.md，docs/GOAL1_TASK_PACKET.md、GOAL1_USAGE.md、factory/、projects/、scripts/diagnose_goal1_environment.py、factory.ps1、goal1_guard.py、tests/、validation/goal1/为未跟踪。最新实际输出 `git-status-resumed.txt`；只读diff --check退出0。git diff --stat不包含未跟踪新增内容。

## 16. 剩余阻塞与待用户决定

现有Windows环境仍不能完成所需Node管道和Chrome/Edge IPC；没有找到已验证且不降级权限的完整执行方式。

还需用户/外部Reviewer确认跨中断点的config/Git元数据变化来源与可接受的宿主行为。保留原证据，不用新的基线掩盖漂移；本Agent不会自行更改应用设置、config或Codex refs消除报告差异。

| 可选方案 | 用户操作与代价 | 再次执行前的必要验证 |
| --- | --- | --- |
| 管理员修复官方elevated初始化（优先评估） | 本机既有setup_error为helper_unknown_error / setup refresh had errors，仅存量证据，未重跑UAC初始化。用户/IT需查看官方初始化诊断并确认本地用户/组、文件边界、防火墙和登录权限设置；管理员动作须另行授权，可能受组织策略限制 | 同样Node管道、浏览器about:blank、文件写边界、清理/退出检测全部通过；不能预先保证elevated能解决 |
| 用户授权受控WSL2 Linux执行 | 原生wsl --list --verbose退出1，明确“未安装”。需用户安装/批准WSL2及Linux发行版，可能重启；准备Linux Node/Python/Codex与浏览器依赖，增加存储和适配成本，无需本阶段付费服务 | 不是裸wsl执行生成代码。Linux Codex沙箱、固定workspace、冻结资源只读、网络/凭据/Windows互操作边界、返回产物路径和进程清理必须实际验证；适配路径及健康检查后才允许正式复验 |
| Agent写代码与独立验证分离 | 现有主控已经分开派发和独立验证；换执行器仍需受限后端。单独分层不修复本机IPC，无安全验证环境时不能执行源码 | 新执行器必须先证明权限边界；不允许宿主full access作为捷径 |

官方WSL2是原生两种沙箱不适用时的可选路线；当前Linux沙箱使用bubblewrap、WSL1不再支持。[OpenAI Docs：WSL](https://learn.chatgpt.com/docs/windows/wsl)。本轮没有安装WSL/Docker/VM或替代调度器，也没有下载/切换Node/CLI版本；不声称某个未测升级版本已经修复。

后续顺序：用户选择并授权环境修复→先通过独立Node/浏览器/边界最小验证→归档保全原Coder/检查记录→使用原包及剩余一次Coder显式Retry进行一次正式E2E→任一必需项失败立即停止并留证。不把当前预检修复冒充环境修复；不重建规划或无限尝试。

停止，等待外部 Reviewer；系统环境变更与Git收口仍需后续明确授权。

"""Real Codex CLI adapter; argv/stdin only, bounded owned process trees."""
import json
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import tomllib
import uuid
import base64
from pathlib import Path
from .contracts import FactoryError

def playwright_path():
    """Use an installed dependency; never download or install a browser."""
    paths = []
    if os.environ.get('APF_PLAYWRIGHT_PATH'):
        paths.append(Path(os.environ['APF_PLAYWRIGHT_PATH']))
    paths += [Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright',
              Path.cwd()/'node_modules/playwright']
    for path in paths:
        if (path/'package.json').is_file(): return str(path.resolve())
    raise FactoryError('未找到已安装Playwright；可用APF_PLAYWRIGHT_PATH指定其目录，不自动安装')

def redact(text):
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----','[REDACTED PRIVATE KEY]',text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]{8,}', '[REDACTED KEY]',text)
    text = re.sub(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+','[REDACTED JWT]',text)
    text = re.sub(r'(?i)(Bearer\s+)[A-Za-z0-9_.-]+',r'\1[REDACTED]',text)
    text = re.sub(r'(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|client[_-]?secret)[\"\x27]?\s*[=:]\s*[\"\x27]?)[^\s\"\x27,}]+',r'\1[REDACTED]',text)
    return text

def clean_env(cwd):
    inherited_context = {'CODEX_APP_TOOLS_PIPE_PATH','CODEX_SESSION_ID','CODEX_THREAD_ID','CODEX_PERMISSION_PROFILE',
                         'CODEX_TASK_WORKSPACE_VERIFYING_IDENTITY','CODEX_INTERNAL_ORIGINATOR_OVERRIDE'}
    env = {k:v for k,v in os.environ.items() if k not in inherited_context and not re.search(r'(?i)(token|secret|password|api_key)',k)}
    env['PYTHONIOENCODING']='utf-8'
    env['PYTHONDONTWRITEBYTECODE']='1'
    temp = Path(cwd)/'.factory-tmp'
    temp.mkdir(exist_ok=True)
    env['TMP']=env['TEMP']=str(temp)
    env['npm_config_cache']=str(temp/'npm-cache')
    env['GIT_OPTIONAL_LOCKS']='0'
    return env

def kill_tree(process):
    # Only a still-live process created by this invocation is targeted.
    if process.poll() is None:
        if os.name == 'nt':
            subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            import signal
            os.killpg(process.pid,signal.SIGKILL)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

# Trusted preload for APF-owned Node runtime checks, not Agent/model processes.
# Closing the verifier's pipe requests the application's existing SIGINT cleanup
# on Windows too. Applications without such a handler still hit the bounded,
# owned-process fallback; no exit status is manufactured by the preload.
NODE_STOP_IMPORT = 'data:text/javascript;base64,' + base64.b64encode(
    b"process.stdin.resume();process.stdin.unref?.();process.stdin.once('end',()=>{"
    b"if(process.listenerCount('SIGINT'))process.emit('SIGINT');});"
).decode('ascii')

def runtime_launch(argv):
    node = Path(argv[0]).name.lower() in ('node','node.exe')
    return ([argv[0], '--import='+NODE_STOP_IMPORT, *argv[1:]] if node else list(argv)), node

def stop_runtime(process, graceful=False, timeout=5):
    """Bounded cleanup of precisely the runtime process owned by this call."""
    forced=False
    if process.poll() is None and graceful and process.stdin:
        try:process.stdin.close()
        except (OSError,ValueError):pass
        try:process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:pass
    if process.poll() is None:
        forced=True;kill_tree(process)
    return {'graceful_requested':graceful, 'forced':forced,
            'exit_code':process.returncode, 'process_stopped':process.poll() is not None}

def process_identity(pid):
    """Read a specific handle identity; never kill an unowned/reused PID."""
    if os.name!='nt':
        try:
            fields=Path(f'/proc/{pid}/stat').read_text().split()
            return {'live':fields[2]!='Z','creation':fields[21]}
        except FileNotFoundError:return {'live':False,'creation':None}
    import ctypes
    from ctypes import wintypes
    api=ctypes.WinDLL('kernel32',use_last_error=True)
    api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];api.OpenProcess.restype=wintypes.HANDLE
    api.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
    api.GetProcessTimes.argtypes=[wintypes.HANDLE,*([ctypes.POINTER(wintypes.FILETIME)]*4)]
    api.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=api.OpenProcess(0x1000,False,pid)
    if not handle:
        if ctypes.get_last_error()==87:return {'live':False,'creation':None}
        raise FactoryError('无法只读确认指定Agent进程是否存活，禁止重复调用')
    try:
        code=wintypes.DWORD();times=[wintypes.FILETIME() for _ in range(4)]
        if not api.GetExitCodeProcess(handle,ctypes.byref(code)) or not api.GetProcessTimes(handle,*(ctypes.byref(t) for t in times)):
            raise FactoryError('无法读取指定Agent进程身份')
        return {'live':code.value==259,'creation':str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)}
    finally:api.CloseHandle(handle)

def popen(argv,cwd,env=None):
    return subprocess.Popen(argv,cwd=cwd,env=env or clean_env(cwd),stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                            text=True,encoding='utf-8',errors='replace',creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
                            start_new_session=os.name!='nt')

def bounded(argv,cwd,timeout,stdin='',log=None,callback=None):
    started = time.monotonic()
    process = popen(argv,cwd)
    messages = queue.Queue()
    def reader(stream,kind):
        private_key=False
        for line in stream:
            if '-----BEGIN ' in line and 'PRIVATE KEY-----' in line:
                private_key='-----END ' not in line
                messages.put((kind,'[REDACTED PRIVATE KEY]\n'))
                continue
            if private_key:
                if '-----END ' in line and 'PRIVATE KEY-----' in line:
                    private_key=False
                continue
            messages.put((kind,redact(line)))
        messages.put((kind,None))
    threads = [threading.Thread(target=reader,args=(process.stdout,'stdout'),daemon=True),threading.Thread(target=reader,args=(process.stderr,'stderr'),daemon=True)]
    for t in threads:
        t.start()
    output = {'stdout':[],'stderr':[]}
    timed_out, closed = False,set()
    stream = Path(log).open('w',encoding='utf-8') if log else None
    try:
        if callback:callback('process_started',str(process.pid))
        process.stdin.write(stdin)
        process.stdin.close()
        while len(closed)<2:
            if time.monotonic()-started > timeout:
                timed_out=True
                kill_tree(process)
                break
            try:
                kind,line=messages.get(timeout=0.2)
            except queue.Empty:
                if callback:
                    callback('heartbeat','')
                continue
            if line is None:
                closed.add(kind)
                continue
            output[kind].append(line)
            if stream:
                stream.write(json.dumps({'stream':kind,'text':line},ensure_ascii=False)+'\n')
                stream.flush()
            if callback:
                callback(kind,line)
        process.wait(timeout=10)
    except BaseException:
        kill_tree(process)
        raise
    finally:
        if stream:
            stream.close()
    return {'exit_code':process.returncode,'timed_out':timed_out,'elapsed_seconds':round(time.monotonic()-started,3),
            'stdout':''.join(output['stdout']),'stderr':''.join(output['stderr'])}

def resolve_codex(codex_path=None):
    """Explicit path wins; never fall back after a bad caller-supplied path."""
    candidate=codex_path if codex_path is not None else (shutil.which('codex.exe') or shutil.which('codex'))
    if not candidate:
        raise FactoryError('未找到 Codex CLI；请用 -CodexPath 指定 Desktop 内 codex.exe 的绝对路径')
    path=Path(candidate)
    if not path.is_absolute() or not path.is_file():
        raise FactoryError('Codex CLI 路径必须是实际存在的可执行文件绝对路径')
    if os.name=='nt' and path.suffix.lower()!='.exe':
        raise FactoryError('Windows 请指定原生 codex.exe，不接受脚本或命令字符串')
    try:
        result=subprocess.run([str(path),'--version'],capture_output=True,text=True,encoding='utf-8',errors='replace',
                              timeout=10,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except (OSError,subprocess.TimeoutExpired) as e:
        raise FactoryError('Codex CLI 版本检查无法执行或超过10秒；请检查指定文件') from e
    version=result.stdout.strip()
    if result.returncode or not re.fullmatch(r'codex-cli\s+\S+',version):
        raise FactoryError('指定程序没有返回有效 codex-cli 版本；停止，不回退到其他路径')
    return str(path.resolve()),version

class CodexExecutor:
    def __init__(self,full_access=False,codex_path=None):
        # Explicit per-run choice; never inherit desktop/user-config permissions.
        self.full_access = full_access
        self.exe,self.version = resolve_codex(codex_path)
        config = Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'config.toml'
        self.model = None
        if config.exists():
            self.model = tomllib.loads(config.read_text(encoding='utf-8')).get('model')
        auth = subprocess.run([self.exe,'login','status'],capture_output=True,encoding='utf-8')
        if auth.returncode:
            raise FactoryError('Codex CLI 尚无可用登录；请自行登录后重试，不读取或索取凭据')

    def sandbox_argv(self,argv,cwd):
        executable = shutil.which(argv[0]+('.cmd' if os.name=='nt' and argv[0]=='npm' else ''))
        if not executable:
            raise FactoryError('验证工具不可用：'+argv[0])
        if os.name=='nt' and argv[0]=='npm':
            # npm.cmd is only reached with fixed run/build/test/dev/start tokens.
            executable = shutil.which('cmd.exe')
            argv = [executable,'/d','/c','npm.cmd',*argv[1:]]
        else:
            argv = [executable,*argv[1:]]
        if self.full_access:
            return argv
        return [self.exe,'sandbox','-c','windows.sandbox="unelevated"','-P',':workspace','-C',str(cwd),'--',*argv]

    def probe(self,cwd,control):
        if self.full_access:
            # Do not write outside cwd or misrepresent Full Access as isolation.
            return {'mode':'danger-full-access','os_write_boundary_enforced':False,
                    'outside_write_denial_test_run':False,'workspace':str(Path(cwd).resolve()),
                    'authorization':'explicit per-run --full-access; current user, no elevation',
                    'scope':'path contract only; current-user filesystem/process/network permissions'}
        # A new evidence path for every probe: retain earlier failed attempts.
        stem = 'sandbox-probe-'+uuid.uuid4().hex[:12]
        script = Path(control)/(stem+'.py')
        target = Path(control)/(stem+'-escape-marker')
        script.write_text('from pathlib import Path\nimport sys\ntry:\n Path(sys.argv[1]).write_text("boundary failed")\nexcept PermissionError:\n print("outside-write-denied")\nelse:\n raise SystemExit("outside-write-allowed")\n',encoding='utf-8')
        result = bounded(self.sandbox_argv(['python',str(script),str(target)],cwd),cwd,30,log=Path(control)/(stem+'.log.jsonl'))
        result.pop('stderr',None)
        if result['exit_code'] or result['timed_out'] or target.exists() or 'outside-write-denied' not in result['stdout']:
            raise FactoryError('受限沙箱未通过项目外写入拒绝探针；停止，不降级完全访问')
        return result

    def preflight(self,packet,cwd,control):
        """Fail before spending an Agent retry on broken Node pipe transport.

        This tests a trusted literal command in the SAME execution mode. It is not
        a business test or a browser acceptance test, and never grants access.
        """
        commands = [c['argv'] for c in packet['checks']] + [packet['runtime']['argv']]
        if os.name != 'nt' or not any(c[0] in ('node','npm') for c in commands):
            return {'applicable':False,'reason':'Windows Node pipe preflight only'}
        script = ('const {spawnSync}=require("node:child_process");'
                  'const r=spawnSync(process.execPath,["--version"],{encoding:"utf8",timeout:5000});'
                  'console.log(JSON.stringify({status:r.status,error:r.error?.code,stdout:r.stdout}));'
                  'process.exit(r.error?1:(r.status??1));')
        stem = 'environment-preflight-'+uuid.uuid4().hex[:12]
        result = bounded(self.sandbox_argv(['node','-e',script],cwd),cwd,20,
                         log=Path(control)/(stem+'.log.jsonl'))
        result.update({'kind':'trusted Windows Node piped child preflight',
                       'sandbox':'danger-full-access / native current-user' if self.full_access else 'unelevated / :workspace / default private desktop',
                       'business_tests_run':False,'browser_acceptance_run':False,
                       'passed':result['exit_code']==0 and not result['timed_out']})
        if self.full_access and result['passed']:
            # Fixed content only. Reuse installed Edge; no generated app loaded.
            browser_script = ('const {chromium}=require('+json.dumps(playwright_path())+');'
                '(async()=>{let b;try{b=await chromium.launch({channel:"msedge",headless:true,chromiumSandbox:true,timeout:12000});'
                'const p=await b.newPage();await p.goto("about:blank");await p.setContent("<p id=probe>APF_ENV_PROBE</p>");'
                'if(await p.locator("#probe").textContent()!=="APF_ENV_PROBE")throw Error("DOM mismatch");'
                'console.log(JSON.stringify({passed:true,channel:"msedge",chromiumSandbox:true,version:b.version()}));'
                '}finally{if(b)await b.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1});')
            browser = bounded(self.sandbox_argv(['node','-e',browser_script],cwd),cwd,25,
                              log=Path(control)/(stem+'-browser.log.jsonl'))
            result['browser_environment_probe']=browser
            result['passed']=browser['exit_code']==0 and not browser['timed_out']
        path = Path(control)/(stem+'.json')
        path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if not result['passed']:
            raise FactoryError('所选执行环境预检失败（Node 管道或浏览器）；停止 Coder 派发。证据：'+str(path))
        return result

    def run(self,role,prompt,cwd,control,attempt,schema,timeout):
        schema_path = Path(control)/(role.lower()+'-schema.json')
        schema_path.write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
        args = [self.exe,'--no-daemon','-a','never','exec','--ignore-user-config','--ignore-rules','--ephemeral',
                '--skip-git-repo-check','--json','--color','never','-s','read-only' if role in ('Planner','Reviewer') else ('danger-full-access' if self.full_access else 'workspace-write'),
                '-C',str(cwd),'--output-schema',str(schema_path),'-c','windows.sandbox="unelevated"']
        for feature in ('multi_agent','memories','plugins','apps','hooks'):
            args += ['--disable',feature]
        args += ['--enable','skip_host_skill_discovery']
        if self.model:
            args += ['-c','model='+json.dumps(self.model)]
        args += ['-']
        path = Path(control)/f'{role.lower()}-{attempt:02d}'
        path.with_suffix('.input.md').write_text(redact(prompt),encoding='utf-8')
        path.with_suffix('.launch.json').write_text(json.dumps({'argv':args,'cwd':str(cwd),
            'timeout_seconds':timeout,'desktop_permission_inherited':False,
            'os_write_boundary_enforced':role in ('Planner','Reviewer') or not self.full_access},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        events, last = [],[time.monotonic()]
        def on_line(kind,line):
            if kind=='process_started':
                path.with_suffix('.process.json').write_text(json.dumps({'pid':int(line),**process_identity(int(line)),
                    'workspace':str(cwd),'argv_sha256':__import__('hashlib').sha256(json.dumps(args).encode()).hexdigest()},ensure_ascii=False),encoding='utf-8')
            if kind=='stdout':
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
            if time.monotonic()-last[0]>=25:
                print(f'[{role}] 执行中，事件 {len(events)}；日志 {path.name}',flush=True)
                last[0]=time.monotonic()
        result = bounded(args,cwd,timeout,prompt,log=path.with_suffix('.log.jsonl'),callback=on_line)
        messages = [e['item']['text'] for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='agent_message']
        completed = [e for e in events if e.get('type')=='turn.completed']
        result = {k:result[k] for k in ('exit_code','timed_out','elapsed_seconds')}
        result.update({'role':role,'version':self.version,'thread_ids':[e['thread_id'] for e in events if e.get('type')=='thread.started'],
                       'execution_mode':'read-only' if role in ('Planner','Reviewer') else ('danger-full-access' if self.full_access else 'workspace-write'),
                       'usage':[e.get('usage') for e in completed],'event_count':len(events),'turn_completed':bool(completed),
                       'error_events':[e for e in events if e.get('type') in ('turn.failed','error')], 'input_sha256':__import__('hashlib').sha256(prompt.encode()).hexdigest()})
        result['command_executions']=[{k:e['item'].get(k) for k in ('command','exit_code','status')}
            for e in events if e.get('type')=='item.completed' and e.get('item',{}).get('type')=='command_execution']
        result['output']=None
        if messages:
            try:
                result['output']=json.loads(messages[-1])
            except json.JSONDecodeError:
                pass
        path.with_suffix('.result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        return result

    def check(self,argv,cwd,control,index,timeout=180):
        return bounded(self.sandbox_argv(argv,cwd),cwd,timeout,log=Path(control)/f'check-{index}.log.jsonl')

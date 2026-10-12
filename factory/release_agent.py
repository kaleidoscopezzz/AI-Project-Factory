"""Approved Sequence stage -> verified local portable ZIP. No models or Git writes.

First increment supports explicit Node/Python script recipes and loopback HTTP
services. Work directories are application boundaries, not OS isolation.
"""
import argparse
import os
import platform
import re
import shutil
import socket
import stat
import subprocess
import time
import urllib.request
import uuid
import zipfile
from pathlib import Path

from .controller import Controller, ROOT, load, save, locked
from .contracts import FactoryError, digest, file_hash, relative_file, safe_path, command_check
from .executor import clean_env, kill_tree, redact
from .git_agent import GitAgent, sensitive, MAX_FILE_BYTES, MAX_TOTAL_BYTES
from .quality import candidate, GENERATED_ROOTS, GENERATED_ANY

FIELDS={'version','project_id','goal','authorization_id','name','source_files','package_files',
        'runtime_requirement','timeout_seconds','smoke'}
RESERVED={'START.ps1','README.txt','RELEASE_SOURCE.json'}


def public_text(text):
    if not isinstance(text,str) or not text.strip() or len(text)>1000:
        raise FactoryError('发行说明必须是简洁非空文字')
    sensitive('release-note.txt',text.encode('utf-8'))
    if re.search(r'(?i)(?<![a-z])[a-z]:[\\/]|[\w.+-]+@[\w.-]+\.[a-z]{2,}',text):
        raise FactoryError('公开发行说明不得含本机绝对路径或个人邮箱')
    return text


def file_name(name, root):
    path=relative_file(name,root)
    parts=Path(name).parts
    if (name!=Path(name).as_posix() or any(p.endswith(('.', ' ')) or
        re.fullmatch(r'(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?',p) or
        any(ord(c)<32 for c in p) for p in parts)):
        raise FactoryError('发行文件名不适合Windows安全解压')
    if parts[0] in GENERATED_ROOTS-{'dist','build'} or any(p in GENERATED_ANY for p in parts):
        raise FactoryError('缓存、运行数据和内部证据不进入发行清单')
    return path


def checked_data(name,path,*,public=True):
    data=path.read_bytes()
    if len(data)>MAX_FILE_BYTES:raise FactoryError('发行文件超过20MiB限制')
    text=data.decode('utf-8',errors='replace')
    if public:
        sensitive(name,data)
    else:
        # Approved build-only test scripts can refer to the local test runtime.
        # They are never silently rewritten or shipped. Still reject credentials
        # and sensitive filenames, including tokens appearing inside a path.
        if redact(text)!=text:raise FactoryError('构建输入疑似包含凭据：'+name)
        check=re.sub(r'(?i)[A-Z]:[\\/](?:Users|Documents and Settings)[\\/][^/\\\s\x22\x27]+[\\/]',
                     '<build-only-user-root>/',text)
        check=re.sub(r'/home/[^/\s]+/','<build-only-user-root>/',check)
        sensitive(name,check.encode('utf8'))
    # Deliverables never contain machine-specific absolute paths, even outside Users.
    if public and re.search(r'(?i)(?<![a-z])[a-z]:[\\/]',text):
        raise FactoryError('发行文件含本机绝对路径：'+name)
    return data


def unpack_checked(archive,target,expected):
    """Validate the complete archive before creating an exclusive new destination."""
    if target.exists():raise FactoryError('解压目录已存在；禁止覆盖用户文件')
    entries=[];seen=set();total=0
    with zipfile.ZipFile(archive) as z:
        for info in z.infolist():
            name=info.filename;file_name(name,target)
            if name.casefold() in seen or info.is_dir() or info.flag_bits&1:
                raise FactoryError('ZIP含重复/目录/加密条目')
            seen.add(name.casefold())
            mode=info.external_attr>>16
            if stat.S_IFMT(mode) not in (0,stat.S_IFREG):raise FactoryError('ZIP含不安全链接或特殊文件')
            total+=info.file_size
            if info.file_size>MAX_FILE_BYTES or total>MAX_TOTAL_BYTES:raise FactoryError('ZIP解压体积超限')
            data=z.read(info)
            if name not in expected or digest(data)!=expected[name]:raise FactoryError('ZIP交付清单/哈希不匹配')
            sensitive(name,data)  # CRC was checked by ZipFile.read.
            entries.append((name,data))
    if {n for n,_ in entries}!=set(expected):raise FactoryError('ZIP缺少交付文件')
    target.mkdir(parents=True,exist_ok=False)
    for name,data in entries:
        p=file_name(name,target);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
    return {name:file_hash(file_name(name,target)) for name in expected}


class ReleaseAgent:
    def __init__(self,controller,project_id):
        self.c=controller;self.project_id=project_id
        self.project,self.control,self.workspace,_=controller.locate(project_id)
        self.output=safe_path(controller.root/'releases'/project_id,controller.root)

    def _input(self,goal,config):
        if (not isinstance(config,dict) or set(config)!=FIELDS or config['version']!=1 or
            config['project_id']!=self.project_id or config['goal']!=goal or
            not isinstance(config['authorization_id'],str) or
            not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',config['authorization_id']) or
            not isinstance(config['name'],str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,59}',config['name']) or
            type(config['timeout_seconds']) is not int or not 1<=config['timeout_seconds']<=180 or
            config['smoke'] not in ('http-health','offline-todo')):
            raise FactoryError('发行配置/授权无效；默认不会运行构建或发行')
        public_text(config['runtime_requirement'])
        # Reuse Goal 4's read-only Sequence + real quality provenance verifier.
        verifier=GitAgent(self.c,self.project_id)
        receipt,approval=verifier._approval(goal)
        packet_paths=[n for n in receipt['files'] if n.endswith('/task-packet.json')]
        packets=[load(relative_file(n,self.project)) for n in packet_paths]
        packets=[p for p in packets if digest(p)==receipt['packet_fingerprint']]
        if not packets:raise FactoryError('批准来源没有对应TaskPacket')
        packet=packets[0]
        for key in ('source_files','package_files'):
            names=config[key]
            if (not isinstance(names,list) or not names or any(not isinstance(n,str) for n in names)
                or len({n.casefold() for n in names})!=len(names) or any(n.casefold() in {r.casefold() for r in RESERVED} for n in names)):
                raise FactoryError('发行清单为空、重复或占用发行工具保留名')
            for n in names:file_name(n,self.workspace)
        if not set(config['source_files'])<=set(receipt['candidate']['files']):
            raise FactoryError('构建来源必须全部属于已批准候选')
        total=0
        for n in config['source_files']:
            data=checked_data(n,relative_file(n,self.workspace),public=False);total+=len(data)
            if digest(data)!=receipt['candidate']['files'][n]:raise FactoryError('构建来源哈希变化')
        if total>MAX_TOTAL_BYTES:raise FactoryError('构建来源体积超限')
        for n in config['package_files']:
            if n not in config['source_files'] and Path(n).parts[0] not in ('dist','build'):
                raise FactoryError('仅允许选定源码或构建目录产物进入ZIP')
        checks=packet['checks'];runtime=packet['runtime']
        if {v['purpose'] for v in checks}!={'build','test'}:raise FactoryError('缺少获批的构建/测试配方')
        for argv in [v['argv'] for v in checks]+[runtime['argv']]:
            command_check(argv,argv is runtime['argv'])
            if argv[0] not in ('node','python') or argv[1] not in config['source_files']:
                raise FactoryError('首版发行仅执行获批的直接Node/Python脚本，不安装依赖')
        argv=runtime['argv']
        if ('--host' not in argv or argv[argv.index('--host')+1]!='127.0.0.1' or
            '--port' not in argv or argv[argv.index('--port')+1]!='{port}' or
            argv[1] not in config['package_files']):
            raise FactoryError('发行启动必须包含已打包脚本、回环地址及受控端口')
        if not runtime['path'].startswith('/') or runtime['path'].startswith('//') or not runtime['expected_text']:
            raise FactoryError('运行健康断言无效')
        executables={}
        for name in {v['argv'][0] for v in checks}|{argv[0]}:
            path=shutil.which(name)
            if not path:raise FactoryError('缺少已安装运行环境：'+name+'；不会自动下载安装')
            version=subprocess.run([path,'--version'],capture_output=True,timeout=10)
            if version.returncode:raise FactoryError('运行环境版本检查失败')
            executables[name]={'path':path,'version':public_text(version.stdout.decode().strip() or version.stderr.decode().strip())}
        optional=None
        version_file=self.control/'git'/('goal0-version.json' if goal=='Goal 0' else 'goal1-version.json')
        if version_file.exists():
            safe_path(version_file,self.control)
            version=load(version_file)
            if not verifier._repository():raise FactoryError('已有Git版本记录没有项目自身仓库；拒绝发现父仓库')
            if (version.get('candidate_fingerprint')!=receipt['candidate']['fingerprint'] or
                version.get('approval')!=approval or version.get('packet_fingerprint')!=receipt['packet_fingerprint'] or
                verifier._tree(version['commit'])!=receipt['candidate']['files']):
                raise FactoryError('已有Git版本与发行来源不一致')
            optional=version['commit']
        return receipt,approval,packet,executables,optional

    def preflight(self,goal,config):
        with locked(self.control):
            receipt,approval,packet,exe,commit=self._input(goal,config)
            return {'status':'ready','project_id':self.project_id,'goal':goal,'approval':approval,
                    'candidate_fingerprint':receipt['candidate']['fingerprint'],
                    'packet_fingerprint':receipt['packet_fingerprint'],'checks':packet['checks'],
                    'runtime':packet['runtime'],'versions':{n:v['version'] for n,v in exe.items()},'git_commit':commit}

    def _env(self,cwd):
        env=clean_env(cwd)
        for n in ('NODE_OPTIONS','NODE_PATH','PYTHONPATH','PYTHONHOME','PYTHONSTARTUP'):
            env.pop(n,None)
        return env

    def _spawn(self,argv,cwd,out,err):
        return subprocess.Popen(argv,cwd=cwd,env=self._env(cwd),stdin=subprocess.DEVNULL,
            stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0,
            start_new_session=os.name!='nt')

    def _command(self,argv,cwd,folder,label,exe,timeout):
        start=time.monotonic();timed_out=False
        out_path=folder/(label+'-stdout.log');err_path=folder/(label+'-stderr.log')
        with out_path.open('wb') as out,err_path.open('wb') as err:
            p=self._spawn([exe[argv[0]]['path'],*argv[1:]],cwd,out,err)
            try:p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out=True;kill_tree(p)
            finally:
                if p.poll() is None:kill_tree(p)
        # Raw local command evidence is retained with secret values redacted.
        for path in (out_path,err_path):path.write_text(redact(path.read_text(encoding='utf-8',errors='replace')),encoding='utf-8')
        result={'argv':argv,'exit_code':p.returncode,'timed_out':timed_out,'seconds':round(time.monotonic()-start,3),
                'stdout':out_path.name,'stderr':err_path.name}
        save(folder/(label+'-result.json'),result)
        if timed_out:raise FactoryError(label+'超时；已终止本轮拥有的进程树')
        if p.returncode:raise FactoryError(label+'真实退出非零：'+str(p.returncode))
        return result

    def _launcher(self,runtime):
        def quote(s):return "'"+s.replace("'","''")+"'"
        values=', '.join('$Port.ToString()' if s=='{port}' else quote(s) for s in runtime['argv'][1:])
        return ("param([ValidateRange(1,65535)][int]$Port = 3000)\n$ErrorActionPreference = 'Stop'\n"
                "Push-Location $PSScriptRoot\ntry {\n"
                "    if (-not (Get-Command "+runtime['argv'][0]+" -ErrorAction SilentlyContinue)) { throw 'Required runtime is not installed. Read README.txt.' }\n"
                "    Write-Host \"Open http://127.0.0.1:$Port ; press Ctrl+C to stop.\"\n"
                "    $runtimeArgs = @("+values+")\n    & "+runtime['argv'][0]+" @runtimeArgs\n"
                "    $runtimeExitCode = $LASTEXITCODE\n} finally { Pop-Location }\nexit $runtimeExitCode\n")

    def _request(self,base,path,method='GET',body=None):
        import json
        data=json.dumps(body).encode() if body is not None else None
        req=urllib.request.Request(base+path,data=data,method=method,headers={'Content-Type':'application/json'})
        # Never send loopback checks through inherited HTTP proxies.
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=3) as response:
            return response.status,response.read().decode('utf-8')

    def _smoke(self,folder,runtime,config,exe):
        import json
        start=time.monotonic();checks=[];procs=[]
        powershell=shutil.which('powershell.exe') if os.name=='nt' else None
        if os.name=='nt' and not powershell:raise FactoryError('Windows PowerShell不可用，无法验证交付启动脚本')
        with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        base='http://127.0.0.1:'+str(port)
        def run_once(index,assertions):
            out_path=folder/('runtime-'+str(index)+'-stdout.log');err_path=folder/('runtime-'+str(index)+'-stderr.log')
            with out_path.open('wb') as out,err_path.open('wb') as err:
                argv=([powershell,'-NoProfile','-ExecutionPolicy','Bypass','-File','START.ps1','-Port',str(port)] if powershell
                      else [exe[runtime['argv'][0]]['path'],*[s.replace('{port}',str(port)) for s in runtime['argv'][1:]]])
                p=self._spawn(argv,folder/'unpacked',out,err)
                try:
                    deadline=time.monotonic()+config['timeout_seconds']
                    while True:
                        if p.poll() is not None:raise FactoryError('发行启动进程提前退出：'+str(p.returncode))
                        try:
                            code,text=self._request(base,runtime['path'])
                            if code==200 and runtime['expected_text'] in text:break
                        except (OSError,ValueError):pass
                        if time.monotonic()>deadline:raise FactoryError('发行包健康检查超时')
                        time.sleep(.1)
                    checks.append({'check':'health','http_status':code,'expected_text':runtime['expected_text'],'phase':index})
                    assertions(base)
                    if p.poll() is not None:raise FactoryError('实际运行检查过程中服务异常退出')
                finally:
                    kill_tree(p)
                    procs.append({'phase':index,'pid':p.pid,'exit_code_after_cleanup':p.returncode,
                                  'stop_reason':'owned process tree terminated by verifier','still_running':p.poll() is None})
            for path in (out_path,err_path):path.write_text(redact(path.read_text(encoding='utf8',errors='replace')),encoding='utf8')
        remembered={}
        def require(ok,message):
            if not ok:raise FactoryError(message)
        def initial(base):
            if config['smoke']!='offline-todo':return
            code,html=self._request(base,'/');require(code==200 and '<html' in html.lower(),'发行界面不可访问')
            for path in ('/app.js','/style.css'):
                code,text=self._request(base,path);require(code==200 and bool(text),'发行静态资源缺失')
            checks.append({'check':'served interface and static assets','passed':True})
            code,text=self._request(base,'/api/todos','POST',{'title':'发行解压运行验证'})
            item=json.loads(text);require(code==201 and item['title']=='发行解压运行验证','发行包新增待办失败')
            remembered['id']=item['id']
            code,text=self._request(base,'/api/todos/'+item['id'],'PATCH',{'title':'编辑后持久化','completed':True})
            updated=json.loads(text);require(code==200 and updated['title']=='编辑后持久化' and updated['completed'] is True,'发行包编辑/完成状态失败')
            code,text=self._request(base,'/api/todos');require(code==200 and any(i['id']==item['id'] for i in json.loads(text)['items']),'发行包待办查询失败')
            checks.append({'check':'add / edit / complete / list','passed':True})
        def restarted(base):
            code,text=self._request(base,'/api/todos');items=json.loads(text)['items']
            require(code==200 and any(i['id']==remembered['id'] and i['title']=='编辑后持久化' and i['completed'] for i in items),'发行包重启后持久化失败')
            code,_=self._request(base,'/api/todos/'+remembered['id'],'DELETE');require(code==204,'发行包删除失败')
            code,text=self._request(base,'/api/todos');require(code==200 and not any(i['id']==remembered['id'] for i in json.loads(text)['items']),'发行包删除后查询失败')
            checks.append({'check':'restart persistence / delete','passed':True})
        try:
            run_once(1,initial)
            if config['smoke']=='offline-todo':run_once(2,restarted)
        finally:
            for path in folder.glob('runtime-*-*.log'):
                path.write_text(redact(path.read_text(encoding='utf8',errors='replace')),encoding='utf8')
            save(folder/'runtime-result.json',{'checks':checks,'processes':procs,'seconds':round(time.monotonic()-start,3),
                 'launch':'START.ps1 on Windows; direct script on non-Windows test fixture'})
        return load(folder/'runtime-result.json')

    def release(self,goal,config):
        folder=None;created=False
        with locked(self.control):
            try:
                receipt,approval,packet,exe,commit=self._input(goal,config)
                binding={'project_id':self.project_id,'goal':goal,'approval':approval,
                         'candidate_fingerprint':receipt['candidate']['fingerprint'],
                         'packet_fingerprint':receipt['packet_fingerprint'],'config_fingerprint':digest(config),'git_commit':commit}
                key=digest(binding);release_id='rel-'+key[:20];folder=safe_path(self.output/release_id,self.output)
                if folder.exists():
                    for p in folder.rglob('*'):safe_path(p,folder)
                    state=load(folder/'state.json')
                    if state.get('status')!='verified' or state.get('key')!=key:
                        raise FactoryError('已有失败/中断发行保留；不会隐式重试或把临时产物视作成功')
                    record=load(folder/'release-record.json')
                    if state['record_sha256']!=file_hash(folder/'release-record.json') or record['binding']!=binding:
                        raise FactoryError('已有发行记录身份/哈希变化')
                    for n,h in record['evidence'].items():
                        if file_hash(relative_file(n,folder))!=h:raise FactoryError('已有发行产物/日志哈希变化')
                    # Read the actual ZIP again, including CRC and file manifest.
                    with zipfile.ZipFile(folder/record['package']['name']) as z:
                        if len(z.infolist())!=len(record['files']) or {i.filename for i in z.infolist()}!=set(record['files']):
                            raise FactoryError('发行ZIP清单变化')
                        for n,h in record['files'].items():
                            if digest(z.read(n))!=h:raise FactoryError('发行ZIP文件变化')
                    return {'status':'already_released','release_id':release_id,'record':str(folder/'release-record.json'),'package':str(folder/record['package']['name'])}
                folder.mkdir(parents=True,exist_ok=False)
                created=True
                save(folder/'state.json',{'status':'running','key':key,'release_id':release_id})
                save(folder/'config.json',config)
                work=folder/'build-workspace';work.mkdir()
                for n in config['source_files']:
                    src=relative_file(n,self.workspace);target=file_name(n,work)
                    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
                    if file_hash(target)!=receipt['candidate']['files'][n]:raise FactoryError('构建副本哈希错误')
                results=[self._command(c['argv'],work,folder,c['purpose']+'-'+str(i),exe,config['timeout_seconds']) for i,c in enumerate(packet['checks'])]
                for n in config['source_files']:
                    if file_hash(file_name(n,work))!=receipt['candidate']['files'][n]:raise FactoryError('构建/测试修改了批准源码副本')
                staging=folder/'package-content';staging.mkdir()
                total=0
                for n in config['package_files']:
                    src=file_name(n,work);data=checked_data(n,src);total+=len(data)
                    if total>MAX_TOTAL_BYTES:raise FactoryError('发行包超过50MiB限制')
                    dest=file_name(n,staging);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
                (staging/'START.ps1').write_text(self._launcher(packet['runtime']),encoding='utf-8-sig')
                guide=('# 本机便携软件 — '+config['name']+'\n\n运行前提：'+config['runtime_requirement']+'\n'
                       '发行包不内置运行环境，不自动安装依赖。解压到新的可写目录后，在该目录打开 PowerShell：\n\n'
                       'powershell -NoProfile -ExecutionPolicy Bypass -File .\\START.ps1 -Port 3000\n\n'
                       '打开 http://127.0.0.1:3000 。端口占用可换成 3001；按 Ctrl+C 停止。\n'
                       'ExecutionPolicy Bypass 仅作用于本次 PowerShell 进程，不修改系统策略。\n'
                       '不要在 ZIP 内直接运行。数据保留在解压目录；单个数据目录请只运行一个服务。\n'
                       '本发行只验证本机回环运行，不包含公网部署、代码签名或安装器。\n'
                       '授权运行使用当前用户权限，不构成操作系统级工作区隔离。\n')
                public_text('运行前提：'+config['runtime_requirement'])
                (staging/'README.txt').write_text(guide,encoding='utf-8-sig')
                save(staging/'RELEASE_SOURCE.json',{'release_id':release_id,**binding,'runtime_requirement':config['runtime_requirement'],
                                                  'runtime_versions':{n:v['version'] for n,v in exe.items()}})
                packaged={}
                for p in sorted(staging.rglob('*')):
                    safe_path(p,staging)
                    if p.is_file():
                        n=p.relative_to(staging).as_posix();packaged[n]=digest(checked_data(n,p))
                package_name=config['name']+'-'+release_id+'.zip'
                archive=folder/(package_name+'.partial')
                with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
                    for n in packaged:z.write(file_name(n,staging),n)
                extracted=unpack_checked(archive,folder/'unpacked',packaged)
                if extracted!=packaged:raise FactoryError('解压副本哈希不一致')
                runtime=self._smoke(folder,packet['runtime'],config,exe)
                if any(p['still_running'] for p in runtime['processes']):raise FactoryError('发行检查进程未停止')
                for n,h in packaged.items():
                    if file_hash(file_name(n,folder/'unpacked'))!=h:raise FactoryError('运行检查改变了发行程序文件')
                # Check approved source and all provenance again before publishing locally.
                if candidate(self.workspace)!=receipt['candidate']:raise FactoryError('原候选在发行期间变化')
                again=GitAgent(self.c,self.project_id)._approval(goal)
                if again!=(receipt,approval):raise FactoryError('原批准来源在发行期间变化')
                archive.rename(folder/package_name)
                evidence={p.name:file_hash(p) for p in folder.iterdir() if p.is_file() and p.name!='state.json'}
                record={'version':1,'status':'verified','release_id':release_id,'binding':binding,'files':packaged,
                        'package':{'name':package_name,'bytes':(folder/package_name).stat().st_size,'sha256':file_hash(folder/package_name)},
                        'checks':results,'runtime':runtime,'evidence':evidence,'runtime_requirement':config['runtime_requirement'],
                        'versions':{n:v['version'] for n,v in exe.items()},
                        'platform':{'system':platform.system(),'version':platform.version(),'machine':platform.machine()},
                        'completed_at':time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                        'location':str(folder.relative_to(self.c.root)),'limitations':['Runtime not bundled; Windows loopback validation only.',
                        'No installer, code signing, remote release, upload, or deployment.','Current-user execution is not OS isolation.']}
                save(folder/'release-record.json',record)
                save(folder/'state.json',{'status':'verified','key':key,'release_id':release_id,'record_sha256':file_hash(folder/'release-record.json')})
                return {'status':'released','release_id':release_id,'record':str(folder/'release-record.json'),'package':str(folder/package_name)}
            except (FactoryError,OSError,ValueError,KeyError,IndexError,AssertionError,subprocess.SubprocessError,zipfile.BadZipFile) as e:
                message=redact(str(e)) or '实际运行行为断言失败'
                if created and folder is not None and folder.exists() and (folder/'state.json').exists():
                    # Never alter an existing verified/interrupted record on a repeat request.
                    state=load(folder/'state.json')
                    if state.get('status')=='running' and 'key' in locals() and not (folder/'release-record.json').exists():
                        save(folder/'failure.json',{'status':'failed','message':message,'at':time.time()})
                        save(folder/'state.json',{**state,'status':'failed'})
                return {'status':'blocked','message':message,'project_id':self.project_id,'goal':goal,
                        'diagnostics':str(folder) if folder is not None else None}


def main():
    parser=argparse.ArgumentParser(description='Approved stage -> verified local portable ZIP; no upload/model/Git writes')
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--project-id',required=True)
    parser.add_argument('--goal',required=True,choices=('Goal 0','Goal 1'))
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    try:
        c=Controller(args.root);config=load(args.config)
        agent=ReleaseAgent(c,args.project_id)
        result=agent.release(args.goal,config) if args.execute else agent.preflight(args.goal,config)
        import json
        print(json.dumps(result,ensure_ascii=False,indent=2))
        return 0 if result['status'] in ('ready','released','already_released') else 1
    except (FactoryError,OSError,ValueError,KeyError) as e:
        print(redact(str(e)));return 1


if __name__=='__main__':raise SystemExit(main())

"""Single-TaskPacket quality loop. No Git, release, or parallel scheduling.

Tester runs an expendable source copy; only CoderRepair may change the original.
Evidence is hashed, bound to a candidate, and rechecked on every recovery.
Full Access is a caller choice, not an OS workspace boundary.
"""
import json
import os
import re
import shutil
import time
import threading
import subprocess
import stat
import copy
from contextlib import contextmanager
from pathlib import Path
from .contracts import (FactoryError, digest, file_hash, safe_path, relative_file,
                        validate_packet, CODER_SCHEMA, schema_check)
from .quality_contracts import BUDGET, TESTER_SCHEMA, REVIEWER_SCHEMA, DEFECT_SCHEMA, validate_schema
from .executor import CodexExecutor, redact, process_identity
from .history import history_dependencies

# Only well-known generated directories are excluded. Arbitrary source extensions
# are never excluded; tests, configs, lockfiles, docs and AGENTS.md are included.
GENERATED_ROOTS = {'validation','dist','build','var','.quality-evidence','.factory-tmp'}
GENERATED_ANY = {'node_modules','__pycache__','.pytest_cache','.cache'}
RUNNING = {'Tester执行中','Reviewer审查中','Coder返工中'}

# External Reviewer classified these exact disclosures for this verified
# TaskPacket/candidate only. Unknown limitations and other contexts fail closed.
REVIEWED_SCOPE_PACKET='edb6c6afa62657c5dc2d899e4774bed1855b5e4dd5b9689ca67ac746207c8ad2'
REVIEWED_SCOPE_CANDIDATE='d4faabda3eeaeff1a70c25acf2bd0d9af1f37f961c6b45a747c607155e00dc4a'
REVIEWED_TESTER_DISCLOSURES=(
    '实际执行环境为Windows本机Edge；其他浏览器及平台未运行。',
    '为避免覆盖固定路径证据，原文件按字节复制到execution_workspace内新证据子目录执行；源码及断言哈希一致。',
    'Full Access不提供OS隔离；历史操作范围陈述属于文档审查，本轮操作范围依据实际CLI工具事件。',
    '本结论属于独立Tester；外部Reviewer验收、发布或冻结未发生。',
)

@contextmanager
def stage_deadline(control,seconds=BUDGET['stage_timeout_seconds'],enabled=True):
    """Hard CLI-worker wall limit, including disk IO; targets only this PID tree.

    Direct library callers retain per-call budgets. The official Windows CLI
    owns its Python worker and may terminate that worker and its descendants.
    """
    done=threading.Event()
    def expired():
        if done.is_set():return
        marker=Path(control)/f'quality-stage-timeout-{time.time_ns()}.json'
        try:
            marker.write_text(json.dumps({'status':'质量门槛失败','reason':'quality CLI stage wall budget exhausted',
                'pid':os.getpid(),'seconds':seconds,'at':time.time(),'scope':'owned CLI worker process tree only'},ensure_ascii=False),encoding='utf-8')
        finally:
            try:
                if os.name=='nt':
                    taskkill=str(Path(os.environ['SystemRoot'])/'System32/taskkill.exe')
                    subprocess.run([taskkill,'/PID',str(os.getpid()),'/T','/F'],capture_output=True,timeout=5)
            finally:os._exit(124)
    timer=threading.Timer(seconds,expired);timer.daemon=True
    if enabled:timer.start()
    try:yield
    finally:
        done.set();timer.cancel()

def candidate(workspace):
    workspace=safe_path(workspace,workspace,exact=True)
    files={}
    for p in sorted(workspace.rglob('*')):
        # Even links inside excluded directories are rejected rather than followed.
        safe_path(p,workspace)
        parts=p.relative_to(workspace).parts
        if parts[0] in GENERATED_ROOTS or any(x in GENERATED_ANY for x in parts):
            continue
        if p.is_file():
            if p.name=='.env' or p.name.startswith('.env.') or p.suffix.lower() in {'.pem','.pfx','.p12','.key'}:
                raise FactoryError('候选包含凭据文件；不能派发质量 Agent')
            files[p.relative_to(workspace).as_posix()]=file_hash(p)
    if not files:
        raise FactoryError('候选源码为空')
    return {'fingerprint':digest(files),'files':files}

def changed(before,after):
    return {p:{'before':before.get(p),'after':after.get(p)} for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)}

def protected_factory(root):
    files={}
    for directory in ('skills','templates','docs','factory','scripts','tests','validation'):
        folder=root/directory
        if folder.exists():
            for parent,dirs,names in os.walk(folder,followlinks=False):
                for name in dirs:safe_path(Path(parent)/name,root)
                dirs[:]=[d for d in dirs if d not in {'__pycache__','test-workspaces'} and not (Path(parent)==root/'validation' and d=='goal2')]
                for name in names:
                    p=safe_path(Path(parent)/name,root)
                    files[p.relative_to(root).as_posix()]=file_hash(p)
    for name in ('AGENTS.md','README.md','.gitignore','.gitattributes'):
        p=root/name
        if p.is_file():files[name]=file_hash(p)
    return files

def reference_snapshot(root):
    # Test roots do not contain this APF reference inventory. No reference access
    # is performed for fixtures; real APF uses the same read-only historical guard.
    if not (root/'validation/reference/before.json').is_file():return None
    from scripts.reference_guard import inventory
    snapshot=inventory()
    return {'files_fingerprint':digest(snapshot['files']),
            'git':{k:snapshot[k] for k in ('head','branch','status','refs')},'coverage':snapshot['coverage']}

def ui_required(packet):
    text=' '.join(a['method']+' '+a['criterion'] for a in packet['acceptance'])+' '+packet['project_type']+' '+packet['technology']+' '+packet['original_request']
    return bool(re.search(r'Playwright|浏览器|截图|viewport|前端|网页|界面|页面|桌面|\b(?:web|html|css|react|vue|frontend|ui|gui)\b',text,re.I))


def recovered_tester_event(execution, log_path, round_root):
    """Finite, evidence-based reclassification; never mutates the real result.

    Only the known hash-enumeration ParserError is supported. A successful
    command, its enumerated file hashes, and every AC/check remain mandatory.
    The caller still runs result() on the derived view with the real execution.
    """
    raw=execution.get('output');validate_schema(raw,TESTER_SCHEMA)
    if (execution.get('exit_code')!=0 or execution.get('timed_out') or not execution.get('turn_completed')
        or not execution.get('thread_ids') or execution.get('execution_mode')!='danger-full-access'
        or raw['status']!='passed' or raw['limitations'] or len(raw['issues'])!=1
        or any(a['result']!='passed' for a in raw['acceptance'])
        or any(c['result']!='passed' or c['exit_code']!=0 for c in raw['checks'])):
        raise FactoryError('不能将未解决质量问题归类为已恢复工具事件')
    issue=raw['issues'][0]
    if (issue['id']!='TESTER-TOOL-001' or issue['ac_ids'] or issue['category']!='test'
        or issue['severity']!='minor' or issue['expected']!='输出证据 SHA256 清单。'
        or issue['reproduce']!=['PowerShell 将 foreach 语句直接接到 ConvertTo-Json 管道。']
        or len(issue['evidence'])!=1):
        raise FactoryError('未知 issue 不得自动转为已解决')
    events=[]
    for line in log_path.read_text(encoding='utf-8').splitlines():
        wrapper=json.loads(line)
        if wrapper.get('stream')!='stdout':continue
        try:event=json.loads(wrapper['text'])
        except (ValueError,KeyError):continue
        if event.get('type')=='item.completed' and event.get('item',{}).get('type')=='command_execution':
            events.append(event['item'])
    failed=[(i,e) for i,e in enumerate(events) if e.get('exit_code')!=0]
    if len(failed)!=1:raise FactoryError('存在其他未恢复命令失败')
    index,bad=failed[0];text=bad.get('aggregated_output','');command=bad.get('command','')
    if (bad.get('exit_code')!=1 or 'ParserError' not in text or 'An empty pipe element is not allowed' not in text
        or 'foreach($p in $paths)' not in command or 'Get-FileHash' not in command or 'ConvertTo-Json' not in command):
        raise FactoryError('原命令并非已知辅助枚举解析错误')
    good=[e for e in events[index+1:] if e.get('exit_code')==0 and e.get('status')=='completed'
          and '$out=foreach($p in $paths)' in e.get('command','')
          and '$out | ConvertTo-Json' in e.get('command','') and 'Candidate changed' in e.get('command','')]
    if len(good)!=1:raise FactoryError('缺少唯一的已完成修正命令')
    corrected=good[0];enumerated=json.loads(corrected['aggregated_output'])
    if not isinstance(enumerated,list) or len({e['path'] for e in enumerated})!=len(enumerated):
        raise FactoryError('修正命令哈希输出非法')
    hashes={e['path']:e['sha256'] for e in enumerated}
    required=[*issue['evidence'],*[e for a in raw['acceptance'] for e in a['evidence']],
              *[e for c in raw['checks'] for e in c['evidence']]]
    for e in required:
        p=relative_file(e['path'],round_root)
        if hashes.get(e['path'])!=e['sha256'] or not p.is_file() or file_hash(p)!=e['sha256']:
            raise FactoryError('修正命令没有完整核验当前关键证据')
    for name,h in hashes.items():
        if not name.startswith('workspace/validation/') or file_hash(relative_file(name,round_root))!=h:
            raise FactoryError('辅助枚举路径或哈希不可信')
    record=json.loads(relative_file(issue['evidence'][0]['path'],round_root).read_text(encoding='utf-8-sig'))
    if record.get('kind')!='evidence hash enumeration' or record.get('exit_code')!=1 or 'ParserError' not in record.get('error',''):
        raise FactoryError('第一次失败事实缺失')
    summaries=execution.get('command_executions',[])
    for item in (bad,corrected):
        if not any(e.get('command')==item['command'] and e.get('exit_code')==item['exit_code'] and e.get('status')==item['status'] for e in summaries):
            raise FactoryError('CLI 原始日志与执行汇总不一致')
    derived=copy.deepcopy(raw);derived['issues']=[]
    proof={'classification':'recovered auxiliary tool event; not an unresolved software defect',
           'original_issue':copy.deepcopy(issue),'failed_command':bad,'corrected_command':corrected,
           'enumerated_hashes':enumerated,'source_result_fingerprint':digest(raw),
           'derived_result_fingerprint':digest(derived),'new_Tester_calls':0}
    return derived,proof

class QualityGate:
    def __init__(self,controller,project,control,workspace,state,retry=False,allow_repair=True):
        from .controller import load, save
        self.load,self.save=load,save
        self.c=controller;self.project=project;self.control=control;self.workspace=workspace;self.state=state;self.retry=retry
        self.allow_repair=allow_repair
        self.folder=safe_path(control/'quality',control);self.folder.mkdir(exist_ok=True)
        self.path=self.folder/'state.json'
        self.packet=load(control/'task-packet.json');validate_packet(self.packet,self.c.root,state)
        self.q=load(self.path) if self.path.exists() else {
            'version':'2.0','packet_fingerprint':digest(self.packet),'budget':dict(BUDGET),
            'round':1,'calls':[],'rounds':[],'repairs':[],'issue_attempts':{},'status':'待质量验证','error':None,
            'protected_factory':protected_factory(self.c.root),'protected_reference':reference_snapshot(self.c.root),
            'initial_control_manifest':{p.name:file_hash(p) for p in control.iterdir() if p.is_file() and p.name not in {'state.json','events.jsonl','controller.lock'}}}
        if self.q['version']!='2.0' or self.q['packet_fingerprint']!=digest(self.packet) or self.q['budget']!=BUDGET:
            raise FactoryError('质量执行协议/任务包/预算不匹配')
        self.save(self.path,self.q)

    def checkpoint(self):
        self.save(self.path,self.q)
        self.state['quality']={'version':'2.0','status':self.q['status'],'calls':len(self.q['calls']),
            'role_calls':{role:sum(c['role']==role for c in self.q['calls']) for role in ('Tester','Reviewer','CoderRepair')},
            'rounds':len(self.q['rounds']),'repair_attempts':sum(self.q['issue_attempts'].values()),
            'valid_repairs':sum(r['valid_repair'] for r in self.q['repairs']),
            'result_path':str(self.path),'budget':self.q['budget']}
        self.save(self.control/'state.json',self.state)

    def status(self,status,detail):
        self.q['status']=status;self.q['error']=None if status=='质量门槛通过' else self.q.get('error')
        self.checkpoint();self.c.transition(self.state,self.control,status,detail)

    def stop(self,message,wait=False):
        self.q['error']=redact(message);self.state['error']=self.q['error']
        self.status('等待用户确认' if wait else '质量门槛失败',self.q['error'])
        return self.state

    def guard(self):
        validate_packet(self.load(self.control/'task-packet.json'),self.c.root,self.state)
        for p,h in self.state['skill_hashes'].items():
            if file_hash(safe_path(self.c.root/p,self.c.root))!=h:
                raise FactoryError('冻结 Skill 发生变化；停止')
        if protected_factory(self.c.root)!=self.q['protected_factory']:raise FactoryError('冻结文件或工厂源码/配置发生变化，停止质量执行')
        if self.q['protected_reference'] is not None and reference_snapshot(self.c.root)!=self.q['protected_reference']:
            raise FactoryError('参考项目发生异常变化，停止质量执行')
        for name,h in self.q['initial_control_manifest'].items():
            path=relative_file(name,self.control)
            if not path.is_file() or file_hash(path)!=h:raise FactoryError('历史控制证据变化：'+name)

    def evidence(self,entry,round_root):
        path=relative_file(entry['path'],round_root)
        # Results cannot reference arbitrary copied source as proof of execution.
        rel=path.relative_to(round_root).as_posix()
        if rel.startswith(('context/history/','context/delivery/','context/run-records/')):
            rows=[r for r in self.q['rounds'] if relative_file(r['path'],self.folder)==round_root]
            if len(rows)!=1:raise FactoryError('历史证据没有对应候选轮次')
            self.verify_context(rows[0])
            ctx=rows[0]['context']
            allowed={e['path']:e['sha256'] for e in ctx['history']+ctx.get('delivery',[])+ctx.get('run_records',[])}
            if allowed.get(rel)!=entry['sha256']:raise FactoryError('历史证据不在受控清单')
        elif rel=='context/reviewer-evidence-index.json' or rel.startswith('context/tester-reuse/'):
            rows=[r for r in self.q['rounds'] if relative_file(r['path'],self.folder)==round_root]
            if len(rows)!=1 or not rows[0].get('tester_derivation'):raise FactoryError('没有受控的本次复核来源')
            row=rows[0];self.verify_context(row)
            allowed={e['path']:e['sha256'] for e in row['context']['indices'] if e['path']=='context/reviewer-evidence-index.json'}
            binding_path=relative_file(row['tester_derivation']['path'],self.folder)
            if file_hash(binding_path)!=row['tester_derivation']['sha256']:raise FactoryError('工具恢复来源绑定变化')
            binding=self.load(binding_path)
            allowed.update({binding[k]['path']:binding[k]['sha256'] for k in ('execution','log','raw_result','proof')})
            if allowed.get(rel)!=entry['sha256']:raise FactoryError('复核引用不在受控清单')
        elif not (rel.startswith('workspace/validation/') or rel.startswith('workspace/.quality-evidence/') or rel.startswith('checks/')):
            raise FactoryError('证据不在授权的测试/证据目录')
        if not path.is_file() or file_hash(path)!=entry['sha256']:
            raise FactoryError('证据不存在或哈希不匹配：'+entry['path'])
        return path

    def result(self,value,role,round_row,execution=None):
        schema=TESTER_SCHEMA if role=='Tester' else REVIEWER_SCHEMA
        validate_schema(value,schema)
        if role=='Tester' and round_row.get('tester_derivation'):
            binding=self.load(relative_file(round_row['tester_derivation']['path'],self.folder))
            if file_hash(relative_file(round_row['tester_derivation']['path'],self.folder))!=round_row['tester_derivation']['sha256']:
                raise FactoryError('派生复核绑定被篡改')
            root=relative_file(round_row['path'],self.folder)
            for e in (binding['execution'],binding['log'],binding['raw_result'],binding['proof']):
                if file_hash(relative_file(e['path'],root))!=e['sha256']:raise FactoryError('真实 Tester 来源副本变化')
            raw_execution=self.load(relative_file(binding['execution']['path'],root))
            if self.load(relative_file(binding['raw_result']['path'],root))!=raw_execution:
                raise FactoryError('真实原始结果与执行记录不一致')
            derived,proof=recovered_tester_event(raw_execution,relative_file(binding['log']['path'],root),root)
            if value!=derived or self.load(relative_file(binding['proof']['path'],root))!=proof:
                raise FactoryError('派生结论不能由原始证据重算')
            if execution is not None and execution!=raw_execution:raise FactoryError('派生执行来源不一致')
            execution=raw_execution
        if value['candidate_fingerprint']!=round_row['candidate']['fingerprint']:
            raise FactoryError('Agent 结果不属于当前候选')
        acs={a['id'] for a in self.packet['acceptance']}
        if len(value['acceptance'])!=len(acs) or {a['id'] for a in value['acceptance']}!=acs:
            raise FactoryError('质量结果遗漏或重复 AC')
        root=relative_file(round_row['path'],self.folder)
        for ac in value['acceptance']:
            if not ac['reason'].strip():raise FactoryError('AC 缺少判断理由')
            if ac['result']!='unverified' and not ac['evidence']:raise FactoryError('AC 无证据')
            if ac['result']=='passed' and all(e['path'].startswith('context/') for e in ac['evidence']):
                # Reviewer is read-only: its current CLI inspection + bound
                # current index/recovery sources can prove the delivery AC.
                # Tester and historical-only claims retain the original rule.
                current_review=(role=='Reviewer' and ac['id']=='AC-012' and round_row.get('tester_derivation')
                                and any(e['path']=='context/reviewer-evidence-index.json' for e in ac['evidence']))
                if not current_review:raise FactoryError('历史记录不能单独证明当前 AC 通过；需要本轮审查/测试证据')
            for e in ac['evidence']:self.evidence(e,root)
        if candidate(self.workspace)!=round_row['candidate']:
            raise FactoryError('候选源码已变化；旧证据失效')
        self.verify_context(round_row)
        ids=set()
        for issue in value['issues']:
            if not issue['id'].strip() or issue['id'] in ids:raise FactoryError('Issue ID 缺失或重复')
            ids.add(issue['id'])
            if not issue['ac_ids'] or not set(issue['ac_ids'])<=acs or not issue['reproduce'] or not issue['expected'].strip() or not issue['actual'].strip() or not issue['evidence']:
                raise FactoryError('缺陷无法复现/关联 AC/证据')
            for e in issue['evidence']:self.evidence(e,root)
        approved=value.get('status')=='passed' if role=='Tester' else value['decision']=='approved'
        if (value.get('status')=='blocked' or value.get('decision')=='blocked') and not (value['limitations'] or value['issues']):
            raise FactoryError('blocked缺少具体原因')
        scoped=(role=='Tester' and digest(self.packet)==REVIEWED_SCOPE_PACKET
                and value['candidate_fingerprint']==REVIEWED_SCOPE_CANDIDATE)
        blocking_limitations=[s for s in value['limitations'] if not scoped or s not in REVIEWED_TESTER_DISCLOSURES]
        if approved and (value['issues'] or blocking_limitations or any(a['result']!='passed' for a in value['acceptance'])):
            raise FactoryError('不能批准未验证/有缺陷/有限制的候选')
        if role=='Tester':
            for check in value['checks']:
                if not set(check['ac_ids'])<=acs or not check['evidence']:raise FactoryError('检查缺少关联/证据')
                for e in check['evidence']:self.evidence(e,root)
                if check['result']=='passed' and check['exit_code']!=0:raise FactoryError('非零退出不能标通过')
            if approved:
                if execution is None:
                    entry=round_row.get('tester_execution')
                    if not entry:raise FactoryError('Tester 缺少独立CLI执行证据')
                    path=relative_file(entry['path'],self.folder)
                    if file_hash(path)!=entry['sha256']:raise FactoryError('Tester CLI执行记录被篡改')
                    execution=self.load(path)
                commands=execution.get('command_executions',[])
                for item in self.packet['checks']:
                    if not any(c['kind']==item['purpose'] and c['argv']==item['argv'] and c['result']=='passed' and c['exit_code']==0 for c in value['checks']):
                        raise FactoryError('Tester 未实际覆盖任务包 build/test')
                    def invoked(command):
                        # CLI tool events, not model prose. Accommodate quoted
                        # Windows/PowerShell tokens without accepting mere file reads.
                        text=re.sub(r'["\x27]','',command.get('command') or '').replace('\\','/')
                        return command.get('exit_code')==0 and command.get('status')=='completed' and all(
                            re.search(r'(?<![\w./-])'+re.escape(arg)+r'(?![\w./-])',text) for arg in item['argv'])
                    if not any(invoked(c) for c in commands):raise FactoryError('Tester 未记录独立执行 build/test 的CLI工具事件')
                if not any(c['kind']=='runtime' and c['result']=='passed' for c in value['checks']):raise FactoryError('Tester 缺少实际运行检查')
                if not round_row['basic']['passed']:raise FactoryError('独立基础检查失败，Tester 不得通过')
                if ui_required(self.packet):
                    checks=[c for c in value['checks'] if c['kind']=='browser' and c['result']=='passed']
                    if not checks:raise FactoryError('UI 不能以 HTTP 或静态页面替代浏览器验收')
                    paths=[self.evidence(e,root) for c in checks for e in c['evidence']]
                    import zipfile,struct
                    images=[];traces=[]
                    for p in paths:
                        if p.suffix.lower()=='.png':
                            b=p.read_bytes()
                            if b[:8]!=b'\x89PNG\r\n\x1a\n' or len(b)<33:raise FactoryError('截图格式无效')
                            images.append(struct.unpack('>II',b[16:24]))
                        if p.suffix.lower()=='.zip':
                            with zipfile.ZipFile(p) as z:
                                if z.testzip() is not None or not any(n.endswith('.trace') for n in z.namelist()):raise FactoryError('浏览器 trace 无效')
                            traces.append(p)
                    if len(set(images))<2 or not traces:raise FactoryError('缺少两种视口截图或真实 trace')
        if role=='Reviewer' and approved:
            if not round_row.get('tester') or round_row['tester']['status']!='passed':raise FactoryError('Reviewer 无通过的 Tester 证据')
            if execution is None:
                entry=round_row.get('reviewer_execution')
                if not entry:raise FactoryError('Reviewer 缺少独立源码审查执行证据')
                path=relative_file(entry['path'],self.folder)
                if file_hash(path)!=entry['sha256']:raise FactoryError('Reviewer CLI执行记录被篡改')
                execution=self.load(path)
            source_names=[p for p in round_row['candidate']['files'] if Path(p).suffix.lower() in {'.js','.mjs','.ts','.py','.html','.css','.jsx','.tsx','.vue','.svelte'}]
            inspected=False
            for cmd in execution.get('command_executions',[]):
                text=(cmd.get('command') or '').replace('\\','/')
                if cmd.get('exit_code')==0 and cmd.get('status')=='completed' and re.search(r'Get-Content|\b(?:cat|type|rg)\b',text,re.I):
                    if any(p in text or ('/' in p and re.search(r'\b'+re.escape(p.split('/')[0])+r'\b',text)) for p in source_names):inspected=True
            if not inspected:raise FactoryError('Reviewer只自报approved，未记录实际源码审查工具执行')
        return value

    def call(self,role,prompt,cwd,round_row,schema):
        self.guard()
        self.verify_context(round_row)
        # A finished result is a durable checkpoint, not merely a status string.
        input_hash=digest(prompt.encode());key=role+':'+input_hash
        for rec in self.q['calls']:
            if rec['key']==key and rec['status']=='finished':
                out=relative_file(rec['output_path'],self.folder)
                if not out.is_file() or file_hash(out)!=rec['output_sha256']:raise FactoryError('持久化 Agent 结果被篡改')
                return self.load(out)
        caps=self.q['budget'];records=self.q['calls']
        count=sum(rec['role']==role for rec in records)
        if count>=caps[role] or len(records)>=caps['max_calls']:raise FactoryError('质量 Agent 调用预算耗尽')
        spent=sum(rec.get('elapsed_seconds',caps['timeout_seconds']) for rec in records)
        if spent>=caps['max_agent_seconds']:raise FactoryError('质量阶段时长预算耗尽')
        timeout=min(caps['timeout_seconds'],caps['max_agent_seconds']-spent,self.state['budget']['agent_timeout_seconds'])
        number=len(records)+1
        folder=self.folder/'calls'/f'{number:02d}-{role.lower()}'
        folder.mkdir(parents=True,exist_ok=False)
        rec={'role':role,'key':key,'number':number,'status':'running','candidate_fingerprint':round_row['candidate']['fingerprint'],
             'input_sha256':input_hash,'started_at':time.time(),'timeout_seconds':timeout,'path':folder.relative_to(self.folder).as_posix()}
        records.append(rec);self.checkpoint()
        self.status({'Tester':'Tester执行中','Reviewer':'Reviewer审查中','CoderRepair':'Coder返工中'}[role],'独立 '+role+' 调用已登记')
        protected={p.name:file_hash(p) for p in self.control.iterdir() if p.is_file() and p.name not in {'state.json','events.jsonl','controller.lock'}}
        factory_status=self.c.root/'PROJECT_STATUS.md'
        status_before=file_hash(factory_status) if factory_status.is_file() else None
        before=candidate(self.workspace);copy_before=candidate(cwd)
        try:
            actual_role='Coder' if role=='CoderRepair' else role
            result=self.c.executor.run(actual_role,prompt,cwd,folder,number,schema,timeout)
            self.save(folder/'execution.json',result)
            rec.update({k:v for k,v in result.items() if k!='output'})
            rec['role']=role;rec['usage']=result.get('usage') or 'unknown'
            if result.get('input_sha256')!=input_hash:raise FactoryError('Agent输入哈希不匹配')
            after=candidate(self.workspace);copy_after=candidate(cwd)
            provenance={'before':before,'after':after,'changes':changed(before['files'],after['files']),
                        'execution_copy_changes':changed(copy_before['files'],copy_after['files'])}
            self.save(folder/'provenance.json',provenance)
            self.guard()
            if (file_hash(factory_status) if factory_status.is_file() else None)!=status_before:raise FactoryError('Agent越权修改工厂项目状态')
            if any(not (self.control/p).is_file() or file_hash(self.control/p)!=h for p,h in protected.items()):raise FactoryError('Agent 修改主控历史证据')
            if before['files'].get('AGENTS.md')!=after['files'].get('AGENTS.md'):raise FactoryError('Agent 修改受保护 AGENTS.md')
            if role!='CoderRepair' and (before!=after or copy_before!=copy_after):raise FactoryError(role+' 越权修改源码或测试断言')
            if result.get('timed_out') or result.get('exit_code')!=0 or not result.get('turn_completed') or result.get('output') is None:
                raise FactoryError(role+' 超时/失败/结构化输出缺失')
            threads=result.get('thread_ids',[])
            prior={t for old in records[:-1] for t in old.get('thread_ids',[])} | {t for old in self.state['calls'] for t in old.get('thread_ids',[])}
            for saved in self.q['rounds']:
                if saved.get('tester_derivation'):
                    prior.update(self.load(relative_file(saved['tester_execution']['path'],self.folder)).get('thread_ids',[]))
            if not threads or prior.intersection(threads):raise FactoryError('Agent thread 缺失或与其他调用复用')
            value=result['output']
            if role!='CoderRepair':self.result(value,role,round_row,result)
            else:schema_check(value,CODER_SCHEMA)
            if role=='Tester':
                round_row['tester_execution']={'path':(folder/'execution.json').relative_to(self.folder).as_posix(),'sha256':file_hash(folder/'execution.json')}
            if role=='Reviewer':
                round_row['reviewer_execution']={'path':(folder/'execution.json').relative_to(self.folder).as_posix(),'sha256':file_hash(folder/'execution.json')}
            self.save(folder/'output.json',value)
            rec['output_path']=(folder/'output.json').relative_to(self.folder).as_posix();rec['output_sha256']=file_hash(folder/'output.json')
            rec['provenance_path']=(folder/'provenance.json').relative_to(self.folder).as_posix();rec['provenance_sha256']=file_hash(folder/'provenance.json')
            rec['status']='finished';self.checkpoint()
            return value
        except BaseException:
            rec['status']='interrupted' if 'execution_mode' not in rec and 'exit_code' not in rec else 'failed'
            rec.setdefault('elapsed_seconds',timeout);self.checkpoint();raise

    def history_plan(self):
        """Evidence closure only. Ready never means AC-012 passed."""
        completion=self.control/'completion.json'
        return history_dependencies(self.workspace,self.load(completion) if completion.is_file() else {},candidate(self.workspace),self.load,
                                    required_history=getattr(self,'state',{}).get('independent_revalidation',{}).get('required_history',[]))

    def history_files(self):
        plan=self.history_plan()
        if not plan['ready']:
            raise FactoryError('历史资料缺失/哈希不匹配/依赖未验证；新增模型调用为0：'+json.dumps(plan['unverified'],ensure_ascii=False))
        return {n['source']:n['sha256'] for n in plan['files'] if n['kind']=='history'}

    def attach_context(self,row):
        root=relative_file(row['path'],self.folder)
        folder=root/'context';folder.mkdir(exist_ok=False)
        history=[]
        plan=self.history_plan()
        preflight={'scope':'dependency completeness only, not AC-012 approval',
                   'candidate_fingerprint':row['candidate']['fingerprint'],'packet_fingerprint':digest(self.packet),
                   'dependencies':plan,'ready':plan['ready'],'registered_quality_calls':len(self.q['calls'])}
        self.save(folder/'dependency-preflight.json',preflight)
        if not plan['ready']:self.history_files()  # fail before any role registration
        for path,h in ((n['source'],n['sha256']) for n in plan['files'] if n['kind']=='history'):
            target=relative_file('history/'+path,folder);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(relative_file(path,self.workspace),target)
            if file_hash(target)!=h:raise FactoryError('历史资料副本哈希不匹配')
            # Windows read-only file attribute is a convenience, not an ACL or
            # an OS boundary against a Full Access process clearing the flag.
            target.chmod(stat.S_IREAD)
            history.append({'path':target.relative_to(root).as_posix(),'sha256':h,'source':path,
                            'purpose':'historical Coder documentation; not current pass evidence'})
        delivery=[]
        for name in ('task-packet.json','packet-validation.json','completion.json','coder-result.json'):
            source=relative_file(name,self.control)
            if not source.is_file():raise FactoryError('交付记录缺失：'+name)
            h=file_hash(source);target=folder/'delivery'/name;target.parent.mkdir(exist_ok=True)
            shutil.copy2(source,target)
            if file_hash(source)!=h or file_hash(target)!=h:raise FactoryError('交付记录复制来源哈希变化')
            delivery.append({'source':name,'path':target.relative_to(root).as_posix(),'sha256':h,
                             'purpose':'original completed delivery metadata; not current test proof'})
        records=folder/'run-records';records.mkdir()
        snapshot={'candidate_fingerprint':row['candidate']['fingerprint'],'packet_fingerprint':digest(self.packet),
                  'round':row['number'],'quality_status':self.q['status'],
                  'independent_revalidation':self.state.get('independent_revalidation'),
                  'nature':'current execution snapshot before role dispatch; not a completed Agent result'}
        self.save(records/'before-dispatch.json',snapshot)
        run_records=[{'path':'context/run-records/before-dispatch.json','sha256':file_hash(records/'before-dispatch.json'),'purpose':snapshot['nature']}]
        data={'candidate_fingerprint':row['candidate']['fingerprint'],'packet_fingerprint':digest(self.packet),
              'history':history,'delivery':delivery,'run_records':run_records,'dependencies':plan,'indices':[]}
        data['preflight']={'path':'context/dependency-preflight.json','sha256':file_hash(folder/'dependency-preflight.json')}
        self.save(folder/'history-manifest.json',data)
        row['context']={**data,'manifest_path':'context/history-manifest.json',
                        'manifest_sha256':file_hash(folder/'history-manifest.json')}

    def verify_context(self,row):
        plan=self.history_plan();expected=self.history_files();context=row.get('context')
        if not context:
            if expected:raise FactoryError('缺少绑定当前候选的历史证据上下文')
            return
        if context['candidate_fingerprint']!=row['candidate']['fingerprint'] or context['packet_fingerprint']!=digest(self.packet):
            raise FactoryError('证据上下文候选/任务包指纹不匹配')
        root=relative_file(row['path'],self.folder)
        if {e['source']:e['sha256'] for e in context['history']}!=expected:
            raise FactoryError('历史证据清单不完整或已变化')
        if any(e['path']!='context/history/'+e['source'] for e in context['history']):
            raise FactoryError('历史来源与副本命名空间不匹配')
        if context.get('dependencies')!=plan:raise FactoryError('历史依赖关系/当前交付来源变化')
        if {e['source'] for e in context.get('delivery',[])}!={'task-packet.json','packet-validation.json','completion.json','coder-result.json'}:
            raise FactoryError('交付记录上下文不完整')
        for entry in context['delivery']:
            if entry['path']!='context/delivery/'+entry['source']:raise FactoryError('交付来源与副本命名空间不匹配')
            if file_hash(relative_file(entry['source'],self.control))!=entry['sha256']:raise FactoryError('交付记录来源哈希变化')
        if context['manifest_path']!='context/history-manifest.json' or [e['path'] for e in context['run_records']]!=['context/run-records/before-dispatch.json']:
            raise FactoryError('证据上下文清单/快照路径非法')
        if context['preflight']['path']!='context/dependency-preflight.json':raise FactoryError('依赖预检记录路径非法')
        for entry in [{'path':context['manifest_path'],'sha256':context['manifest_sha256']},context['preflight'],*context['indices'],*context['history'],*context['delivery'],*context['run_records']]:
            path=relative_file(entry['path'],root)
            if not path.is_file() or file_hash(path)!=entry['sha256']:
                raise FactoryError('受控证据上下文缺失或被篡改：'+entry['path'])
        snapshot=self.load(root/'context/run-records/before-dispatch.json')
        if snapshot['candidate_fingerprint']!=row['candidate']['fingerprint'] or snapshot['packet_fingerprint']!=digest(self.packet):
            raise FactoryError('当前执行快照来源与候选/包不匹配')
        preflight=self.load(root/'context/dependency-preflight.json')
        if not preflight['ready'] or preflight['dependencies']!=plan or preflight['candidate_fingerprint']!=row['candidate']['fingerprint'] or preflight['packet_fingerprint']!=digest(self.packet):
            raise FactoryError('历史依赖预检记录无效')

    def evidence_index(self,row,role):
        self.verify_context(row)
        root=relative_file(row['path'],self.folder);context=row['context']
        path='context/'+role.lower()+'-evidence-index.json'
        existing=[e for e in context['indices'] if e['path']==path]
        if existing:return existing[0]
        artifacts=[]
        for prefix in ('checks','workspace/validation','workspace/.quality-evidence',*[p.name for p in root.iterdir() if p.is_dir() and p.name.startswith('preflight-')]):
            folder=relative_file(prefix,root)
            if folder.exists():
                for p in sorted(folder.rglob('*')):
                    safe_path(p,root)
                    if p.is_file() and p.suffix.lower() in {'.json','.jsonl','.log','.txt','.md','.png','.zip'}:
                        artifacts.append({'path':p.relative_to(root).as_posix(),'sha256':file_hash(p),
                                          'bytes':p.stat().st_size,'purpose':'current round artifact; assess AC coverage, no automatic pass'})
        self.save(root/path,{'candidate_fingerprint':row['candidate']['fingerprint'],'packet_fingerprint':digest(self.packet),
                            'artifacts':artifacts,'history':context['history'],'delivery':context['delivery'],'run_records':context['run_records'],
                            'dependency_manifest':{'path':context['manifest_path'],'sha256':context['manifest_sha256']},
                            'dependency_preflight':context['preflight'],
                            'archive_warnings':context['dependencies'].get('archive_warnings',[]),
                            'rules':'Index lists available files, not AC verdicts. New evidence must also carry a verified path/SHA; historical claims cannot replace current tests.'})
        entry={'path':path,'sha256':file_hash(root/path)};context['indices'].append(entry);self.checkpoint()
        return entry

    def context(self,row,role='Tester'):
        entry=self.evidence_index(row,role)
        root=relative_file(row['path'],self.folder)
        return {'protocol':'Goal2/2.0','task_packet':self.packet,'packet_fingerprint':digest(self.packet),
                'candidate':row['candidate'],'execution_workspace':str(relative_file(row['path'],self.folder)/'workspace'),
                'round_root':str(root),'evidence_paths':'relative to round directory: workspace/validation/, workspace/.quality-evidence/, checks/; listed context/history/ for historical documentation only',
                'evidence_index':{**entry,'absolute_path':str(root/entry['path'])},
                'read_only_history_context':str(root/'context/history'),
                'read_only_delivery_context':str(root/'context/delivery'),
                'run_record_context':str(root/'context/run-records'),
                'tester_recovery':({'binding':str(relative_file(row['tester_derivation']['path'],self.folder)),
                    'context':str(root/'context/tester-reuse'),
                    'meaning':'zero-model reclassification of a recovered tool event; original real Tester is preserved, not rerun'}
                    if row.get('tester_derivation') else None),
                'ac012_review_policy':{'focus':'当前交付说明、R/AC/Task映射、真实命令与结果、当前源码指纹、日志/截图/trace索引、操作范围和验收状态',
                    'archive_warnings':row['context']['dependencies'].get('archive_warnings',[]),
                    'disclosure':'仅列明的三条归档引用可unverified且非阻塞；在本轮AC-012审查证据、reason及Reviewer summary披露。其他当前/关键来源缺失仍须blocked。非关键归档warning不是当前AC未验证，不放入表示当前验收阻塞的limitations；不得隐藏实际阻塞。'},
                'baseline_checks':{'passed':row['basic']['passed'],'checks':row['basic']['checks'],
                                   'runtime_passed':row['basic']['runtime']['passed']},
                'budget':self.q['budget'],'ui_required':ui_required(self.packet)}

    def tester_prompt(self,row):
        return ('你是独立 Tester，不是Coder自测。只在execution_workspace测试副本内执行已授权build/test/runtime，业务源码与测试断言只读。\n'
                '可只读访问evidence_index及read_only_history_context；禁止读写原workspace、主控账本、其他项目或凭据，禁止修改context。历史资料只作历史文档审查，不能冒充当前测试。\n'
                '测试副本可生成dist/build/var、validation/.quality-evidence新证据；不得覆盖已有唯一证据。先读受控索引，再定向读所需文件，避免反复打印完整源码/trace/历史日志。\n'
                '按TaskPacket原文逐项执行全部AC，不改变定义。每个AC独立输出{id,result,reason,evidence:[{path,sha256}]}；path相对round_root，不能使用绝对路径、原工程路径或越界路径。\n'
                '每项passed或failed都必须有至少一份真实证据，并说明该文件中支持本项判断的断言/字段；checks的总日志不能代替AC.evidence。同一日志可按实际覆盖被多项引用，禁止自动复制绿灯。\n'
                '历史文档可作为补充引用；passed至少还需一份本轮测试或审查证据，历史通过记录不能单独证明当前AC通过。\n'
                '无证据或未测试的AC只能unverified，并在limitations说明；整体只能failed/blocked，不能passed。返回前自查每项非unverified的evidence非空、文件存在、SHA256准确、候选指纹不变。禁止虚构或由主控补填结果。\n'
                'checks须分别记录实际build/test/runtime的argv、exit_code、result、ac_ids及evidence；独立运行命令需留下CLI工具事件，主控基础检查不是你的自测。\n'
                '正向runtime检查必须是可结束的检查命令：自行启动服务、验证health/监听/行为，finally清理服务，成功检查命令退出0。把实际命令及stdout/stderr/检查结果写入本轮证据。\n'
                '服务进程因Ctrl+C/清理返回非零不是检查命令退出0；两者在证据中分别记录，不能把长驻服务argv及退出1填为正向runtime passed。任何真实检查非零仍不能标passed。\n'
                '预期400/403/404/503等故障必须由断言命令验证预期行为并退出0；保留实际HTTP/进程错误，不删检查、不忽略非零。\n'
                'limitations仅填写影响当前验收或无法核实的限制。移动视口模拟、Full Access无OS隔离等非阻塞事实放在相关AC reason与本轮审查证据披露；不能隐藏真实缺陷。\n'
                'UI必须真实浏览器交互、持久化/服务重启/失败检查；保留浏览器自身沙箱，缺依赖/浏览器/权限blocked，不以HTTP200替代。browser check.evidence本身必须包含两种视口PNG和trace ZIP，不仅放在AC结果中。\n'
                'AC-012按索引分别审查history历史资料、delivery原完成交付记录、run_records派发前快照与本轮artifacts/你新生成的证据；资料齐备预检不是通过结论。历史未生成与旧指纹缺口须保留事实，不能借用当前字节补证。\n'
                '按ac012_review_policy核验当前有效交付，逐条披露archive_warnings为历史追溯unverified，不能仅因这三条非关键归档缺口把当前AC-012标为unverified；也不能由预检替它判passed。当前必需证据或实际依赖的关键来源缺失/错误仍须blocked。\n'
                '只读读取上述context目录；context元数据不能单独证明本轮AC passed，须有本轮测试/审查记录。当前必需资料或关键来源缺失/不匹配不准通过；仅已列明非关键归档限制按披露处理。禁止Git/发布/调用Agent，Full Access没有OS隔离。\n'
                +json.dumps(self.context(row),ensure_ascii=False,sort_keys=True,separators=(',',':')))

    def coder_report(self,row):
        if self.q['repairs'] and self.q['repairs'][-1]['valid_repair'] and self.q['repairs'][-1]['after']==row['candidate']:
            calls=[c for c in self.q['calls'] if c['role']=='CoderRepair' and c['status']=='finished']
            rec=calls[-1];path=relative_file(rec['output_path'],self.folder)
            if file_hash(path)!=rec['output_sha256']:raise FactoryError('当前返工Coder报告被篡改')
            repair=self.q['repairs'][-1]
            return {'report':self.load(path),'repair':{k:repair[k] for k in ('number','before','after','changes','valid_repair','defect_path')}}
        return {'report':self.load(self.control/'coder-result.json'),'repair':None}

    def make_round(self):
        snap=candidate(self.workspace)
        if len(self.q['rounds'])>=BUDGET['max_rounds']:raise FactoryError('最多三轮质量验证，已达上限')
        index=len(self.q['rounds'])+1
        folder=self.folder/'rounds'/f'{index:02d}';folder.mkdir(parents=True,exist_ok=False)
        workspace=folder/'workspace';workspace.mkdir()
        for name in snap['files']:
            target=relative_file(name,workspace);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(relative_file(name,self.workspace),target)
        if candidate(workspace)!=snap:raise FactoryError('候选测试副本指纹不一致')
        row={'number':index,'path':folder.relative_to(self.folder).as_posix(),'candidate':snap,'basic':None,'tester':None,'reviewer':None}
        self.attach_context(row)
        self.q['rounds'].append(row);self.q['round']=index;self.checkpoint()
        return row

    def basic(self,row):
        folder=relative_file(row['path'],self.folder);copy=folder/'workspace'
        if row['basic'] is not None:
            for e in row['basic']['evidence']:self.evidence(e,folder)
            return
        # An interrupted local check may have side effects in its expendable
        # copy. Never overwrite prior logs; recovery uses a new evidence namespace.
        checks=folder/'checks'/str(time.time_ns());checks.mkdir(parents=True)
        results=[]
        for i,item in enumerate(self.packet['checks']):
            res=self.c.executor.check(item['argv'],copy,checks,i,self.packet['budget']['check_timeout_seconds'])
            results.append({'purpose':item['purpose'],'argv':item['argv'],**{k:res[k] for k in ('exit_code','timed_out','elapsed_seconds')}})
        try:
            runtime=self.c.runtime_check(self.packet,copy,checks)
        except FactoryError as e:
            runtime={'passed':False,'error':str(e)}
        data={'checks':results,'runtime':runtime,'passed':all(x['exit_code']==0 and not x['timed_out'] for x in results) and runtime['passed']}
        self.save(checks/'basic.json',data)
        evidence=[{'path':p.relative_to(folder).as_posix(),'sha256':file_hash(p)} for p in sorted(checks.iterdir()) if p.is_file()]
        row['basic']={**data,'evidence':evidence};self.checkpoint()
        if candidate(copy)!=row['candidate']:raise FactoryError('基础检查修改测试或业务源码')

    def issue_key(self,issue):
        # Stable across changed observations and unstable Agent-selected Issue IDs.
        return digest({'ac':sorted(issue['ac_ids']),'category':issue['category'],'expected':issue['expected'].strip()})

    def recover_repair_checkpoint(self):
        pending=self.q.get('pending_repair')
        if not pending:return
        calls=[c for c in self.q['calls'][pending['call_count_before']:] if c['role']=='CoderRepair']
        if not calls or calls[-1]['status']!='finished':return
        rec=calls[-1]
        output=relative_file(rec['output_path'],self.folder);provenance=relative_file(rec['provenance_path'],self.folder)
        if file_hash(output)!=rec['output_sha256'] or file_hash(provenance)!=rec['provenance_sha256']:
            raise FactoryError('返工恢复检查点被篡改')
        coder=self.load(output);source=self.load(provenance);now=candidate(self.workspace)
        schema_check(coder,CODER_SCHEMA)
        if source['before']!=pending['before'] or source['after']!=now:raise FactoryError('返工恢复指纹不一致')
        if coder['status']!='completed' or not coder['tests'] or any(t['exit_code']!=0 for t in coder['tests']):
            raise FactoryError('恢复的Coder返工仍失败')
        for p in coder['files']+coder['evidence']:
            if not relative_file(p,self.workspace).is_file():raise FactoryError('返工恢复文件缺失')
        if any(now['files'].get(p)!=h for p,h in pending['tests'].items()):raise FactoryError('返工恢复发现测试断言修改')
        if pending['before']['files'].get('AGENTS.md')!=now['files'].get('AGENTS.md'):raise FactoryError('返工恢复AGENTS变化')
        diff=changed(pending['before']['files'],now['files'])
        if not diff:raise FactoryError('恢复的返工没有实际源码变化')
        if any(p not in pending['tests'] and (any(x in {'tests','test'} for x in Path(p).parts) or re.search(r'(^|/)(test[^/]*|[^/]*\.(?:test|spec)\.[^/]*)$',p)) for p in now['files']):
            raise FactoryError('返工恢复发现新测试替换')
        if 'package.json' in pending['before']['files']:
            old=self.load(relative_file(self.q['rounds'][-1]['path'],self.folder)/'workspace/package.json')
            new=self.load(self.workspace/'package.json')
            if old.get('scripts',{}).get('test')!=new.get('scripts',{}).get('test'):raise FactoryError('返工恢复修改npm测试入口')
        record={'number':pending['defect']['repair_number'],'before':pending['before'],'after':now,'changes':diff,
                'valid_repair':True,'defect_path':pending['path'],'recovered_finished_call':True}
        old_records=[r for r in self.q['repairs'] if r['number']==record['number']]
        if old_records:
            # Do not turn a recorded validation failure into a recovered success.
            if not old_records[0]['valid_repair']:raise FactoryError('之前返工验证失败，不能借恢复绕过')
        else:self.q['repairs'].append(record)
        self.q.pop('pending_repair',None);self.checkpoint()

    def restore_finished_call(self,rec):
        """Recover the small power-loss window between result files and ledger fsync."""
        folder=relative_file(rec['path'],self.folder)
        execution,output,provenance=(folder/n for n in ('execution.json','output.json','provenance.json'))
        if not all(p.is_file() for p in (execution,output,provenance)):return False
        raw=self.load(execution);value=self.load(output);source=self.load(provenance)
        if raw.get('input_sha256')!=rec['input_sha256'] or raw.get('exit_code')!=0 or raw.get('timed_out') or not raw.get('turn_completed') or raw.get('output')!=value:
            raise FactoryError('中断恢复最终结果与执行检查点不一致')
        rows=[r for r in self.q['rounds'] if r['candidate']['fingerprint']==rec['candidate_fingerprint']]
        if not rows:raise FactoryError('恢复调用没有对应候选轮次')
        row=rows[-1]
        prior={t for r in self.q['calls'] if r is not rec for t in r.get('thread_ids',[])} | {t for r in self.state['calls'] for t in r.get('thread_ids',[])}
        if not raw.get('thread_ids') or prior.intersection(raw['thread_ids']):raise FactoryError('恢复的独立thread不可信')
        if source['before']!=row['candidate'] or source['after']!=candidate(self.workspace):raise FactoryError('恢复调用源码变化不一致')
        if rec['role']=='CoderRepair':schema_check(value,CODER_SCHEMA)
        else:
            if source['before']!=source['after'] or source['execution_copy_changes']:raise FactoryError('恢复调用越权修改源码')
            self.result(value,rec['role'],row,raw)
        if rec['role']=='Tester':row['tester_execution']={'path':execution.relative_to(self.folder).as_posix(),'sha256':file_hash(execution)}
        if rec['role']=='Reviewer':row['reviewer_execution']={'path':execution.relative_to(self.folder).as_posix(),'sha256':file_hash(execution)}
        role=rec['role'];rec.update({k:v for k,v in raw.items() if k!='output'});rec['role']=role
        rec.update({'status':'finished','usage':raw.get('usage') or 'unknown',
                    'output_path':output.relative_to(self.folder).as_posix(),'output_sha256':file_hash(output),
                    'provenance_path':provenance.relative_to(self.folder).as_posix(),'provenance_sha256':file_hash(provenance),
                    'recovered_final_checkpoint':True})
        self.checkpoint();return True

    def repair(self,row,issues):
        if not issues:raise FactoryError('质量失败但没有可执行缺陷，不能盲目返工')
        if any(i['category']!='implementation' for i in issues):
            kinds={i['category'] for i in issues}
            return self.stop('非实现缺陷，停止自动 Coder 返工：'+','.join(sorted(kinds)),wait='ambiguity' in kinds or 'permission' in kinds)
        keys={self.issue_key(i) for i in issues}
        current=candidate(self.workspace)
        if current!=row['candidate']:raise FactoryError('派发返工前候选变化；旧缺陷无效')
        defect={'format_version':'2.0','project_id':self.packet['project_id'],'task_id':self.packet['task_id'],
                'candidate_fingerprint':current['fingerprint'],'packet_fingerprint':digest(self.packet),
                'issues':issues,'repair_number':len(self.q['repairs'])+1}
        validate_schema(defect,DEFECT_SCHEMA)
        path=relative_file(row['path'],self.folder)/'defect-packet.json'
        if path.exists():
            if self.load(path)!=defect:raise FactoryError('同轮历史DefectPacket不一致，拒绝覆盖')
        else:self.save(path,defect)
        if not self.allow_repair:
            return self.stop('本次显式禁用自动返工；保留DefectPacket，不启动Coder')
        if len(self.q['repairs'])>=BUDGET['CoderRepair'] or len(self.q['rounds'])>=BUDGET['max_rounds']:
            raise FactoryError('返工/质量轮数预算耗尽')
        if any(self.q['issue_attempts'].get(k,0)>=BUDGET['max_same_issue_repairs'] for k in keys):raise FactoryError('相同缺陷两次修复上限耗尽')
        self.status('等待返工','实现缺陷已绑定当前候选')
        # Environment check comes before spending a repair call/attempt.
        preflight=self.folder/'preflight'/f'repair-{len(self.q["calls"])+1:02d}';preflight.mkdir(parents=True,exist_ok=True)
        self.c.executor.preflight(self.packet,self.workspace,preflight)
        def test_file(p):
            return any(x in {'tests','test'} for x in Path(p).parts) or bool(re.search(r'(^|/)(test[^/]*|[^/]*\.(?:test|spec)\.[^/]*)$',p))
        test_paths={p:h for p,h in current['files'].items() if test_file(p)}
        for check in self.packet['checks']:
            if check['purpose']=='test' and check['argv'][0]!='npm' and check['argv'][1] in current['files']:
                test_paths[check['argv'][1]]=current['files'][check['argv'][1]]
        prompt=('你是独立 Coder，只针对 DefectPacket 实现缺陷返工。禁止重新规划、重建项目、修改测试断言、删证据、Git/发布/下一Goal。\n'
                '仅修改原候选业务源码，不得修改 AGENTS.md、测试目录、主控控制文件及其他项目。遇到测试自身缺陷/环境/歧义停止并如实报告。\n'
                'Full Access仅在本次调用者显式选择时可用，没有OS工作区隔离。测试自测不代表验收批准。返回Coder结构化结果。\n'
                +json.dumps({'defect_packet':defect,'evidence_root':str(relative_file(row['path'],self.folder)),
                            'task_packet':self.packet,'prior_coder':self.load(self.control/'coder-result.json')},ensure_ascii=False,sort_keys=True))
        # Reserve same-issue attempts before launch; no-op still costs a call.
        self.q['pending_repair']={'before':current,'defect':defect,'path':path.relative_to(self.folder).as_posix(),
                                  'tests':test_paths,'keys':sorted(keys),'call_count_before':len(self.q['calls'])}
        for k in keys:self.q['issue_attempts'][k]=self.q['issue_attempts'].get(k,0)+1
        self.checkpoint()
        coder=self.call('CoderRepair',prompt,self.workspace,row,CODER_SCHEMA)
        after=candidate(self.workspace);diff=changed(current['files'],after['files'])
        record={'number':defect['repair_number'],'before':current,'after':after,'changes':diff,
                'valid_repair':False,'defect_path':path.relative_to(self.folder).as_posix()}
        self.q['repairs'].append(record);self.checkpoint()
        if any(after['files'].get(p)!=h for p,h in test_paths.items()) or any(p not in test_paths and test_file(p) for p in after['files']):
            raise FactoryError('Coder 返工修改测试；不得删除/替换断言换取通过')
        if coder['status']=='needs_confirmation':return self.stop('返工需要用户确认：'+';'.join(coder['questions']),True)
        if coder['status']!='completed' or not coder['tests'] or any(t['exit_code']!=0 for t in coder['tests']):raise FactoryError('Coder 返工未完成/自测失败')
        for name in coder['files']+coder['evidence']:
            if not relative_file(name,self.workspace).is_file():raise FactoryError('Coder 返工引用不存在文件')
        if not diff:raise FactoryError('没有真实源码变化；不是有效返工')
        if 'package.json' in current['files']:
            # The before source is available in the round's immutable copy.
            old_package=self.load(relative_file(row['path'],self.folder)/'workspace/package.json')
            new_package=self.load(self.workspace/'package.json')
            if old_package.get('scripts',{}).get('test')!=new_package.get('scripts',{}).get('test'):
                raise FactoryError('返工修改npm测试入口')
        record['valid_repair']=True;self.q.pop('pending_repair',None);self.checkpoint()
        return None

    def run(self):
        try:
            self.guard()
            if list(self.control.glob('quality-stage-timeout-*.json')):
                return self.stop('质量阶段墙钟预算已耗尽，保留恢复点，需用户决定新的执行预算')
            for rec in self.q['calls']:
                if rec['status']=='running':
                    actual='Coder' if rec['role']=='CoderRepair' else rec['role']
                    proc=relative_file(rec['path'],self.folder)/f'{actual.lower()}-{rec["number"]:02d}.process.json'
                    if proc.exists():
                        saved=self.load(proc);live=process_identity(saved['pid'])
                        if live['live'] and live['creation']==saved['creation']:
                            return self.stop('已确认上次Agent进程仍存活，保留running记录，不重复启动')
                    if self.restore_finished_call(rec):continue
                    rec['status']='interrupted';rec['elapsed_seconds']=rec['timeout_seconds'];self.checkpoint()
                    return self.stop('上次独立调用中断，未伪装完成；显式 Retry 才可继续')
            if self.q['status']=='等待用户确认':return self.state
            if self.q['status']=='质量门槛失败' and not self.retry:return self.state
            if self.q['status']=='质量门槛通过':
                row=self.q['rounds'][-1]
                if candidate(self.workspace)!=row['candidate']:raise FactoryError('通过候选源码变化；旧验收失效')
                self.basic(row);self.result(row['tester'],'Tester',row);self.result(row['reviewer'],'Reviewer',row)
                self.status('质量门槛通过','候选及全部证据仍有效，复用结果；无新增调用');return self.state
            if any(rec['status']=='interrupted' and rec['role']=='CoderRepair' for rec in self.q['calls']):
                return self.stop('Coder返工中断，可能有部分修改/副作用，需用户审查恢复点',True)
            self.recover_repair_checkpoint()
            if self.c.executor is None:self.c.executor=CodexExecutor(full_access=self.c.full_access,codex_path=self.c.codex_path)
            # Preflight uses an isolated source copy; never overwrites old evidence.
            if self.q['rounds']:
                row=self.q['rounds'][-1]
                if candidate(self.workspace)!=row['candidate']:
                    if not self.q['repairs'] or self.q['repairs'][-1]['after']!=candidate(self.workspace) or not self.q['repairs'][-1]['valid_repair']:
                        raise FactoryError('候选非受控变化，旧质量结果失效，停止')
                    row=self.make_round()
            else:row=self.make_round()
            while True:
                folder=relative_file(row['path'],self.folder);copy=folder/'workspace'
                if candidate(copy)!=row['candidate']:raise FactoryError('测试副本源码变化')
                if row.get('tester_derivation'):
                    # Read-only Reviewer continuation reuses actual Tester checks;
                    # never re-run a browser/build just to refresh a green record.
                    self.result(row['tester'],'Tester',row)
                else:
                    pre=folder/('preflight-'+str(time.time_ns()));pre.mkdir()
                    self.c.executor.preflight(self.packet,copy,pre)
                self.basic(row)
                if row['tester'] is None:
                    prompt=self.tester_prompt(row)
                    row['tester']=self.call('Tester',prompt,copy,row,TESTER_SCHEMA);self.checkpoint()
                self.result(row['tester'],'Tester',row)
                if row['tester']['status']!='passed':
                    if row['tester']['status']=='blocked':return self.stop('Tester blocked：'+';'.join(row['tester']['limitations']),any(i['category'] in {'ambiguity','permission'} for i in row['tester']['issues']))
                    outcome=self.repair(row,row['tester']['issues'])
                    if outcome is not None:return outcome
                    row=self.make_round();continue
                if row['reviewer'] is None:
                    prompt=('你是独立内部 Reviewer，默认只读；禁止修改源码/测试/证据、运行带副作用命令、Git/发布或其他Agent。\n'
                            '审查候选源码、TaskPacket、Planner AC、Coder报告及Tester证据有效性/授权范围/覆盖与明显缺陷。\n'
                            '不能因任何completed/pass自报自动批准；当前必需证据不足、未实现或AC unknown/unverified不能approved。按ac012_review_policy区分并在AC-012 reason、本轮审查证据及summary披露三条非关键历史archive_warnings；仅这些追溯限制不自动拒绝，不能扩大到其他关键来源。\n'
                            'approved仅指当前TaskPacket质量门槛，不是APF外部验收/Git冻结/软件正式发布。\n'
                            '如 tester_recovery 存在，必须读取其中原始 Tester 输出、原始命令日志及恢复认定；独立判断工具事件是否确已恢复、是否漏掉关键检查。优先核验当前软件、测试和浏览器证据，勿扩展无关历史审计。\n'
                            'issues只列当前未解决缺陷；有真实恢复证据的辅助工具事件保留在summary及相关AC reason，不隐瞒失败也不当作未解决业务缺陷。limitations只列影响本阶段验收或无法核实的限制；Full Access无OS隔离、视口模拟、未发布等非阻塞事实在summary披露。真正关键未知仍须blocked。\n'
                            +json.dumps({**self.context(row,'Reviewer'),'tester':row['tester'],'coder_report':self.coder_report(row)},ensure_ascii=False,sort_keys=True,separators=(',',':')))
                    row['reviewer']=self.call('Reviewer',prompt,copy,row,REVIEWER_SCHEMA);self.checkpoint()
                self.result(row['reviewer'],'Reviewer',row)
                if row['reviewer']['decision']=='blocked':return self.stop('Reviewer blocked：'+';'.join(row['reviewer']['limitations']),any(i['category'] in {'ambiguity','permission'} for i in row['reviewer']['issues']))
                if row['reviewer']['decision']=='changes_requested':
                    outcome=self.repair(row,row['reviewer']['issues'])
                    if outcome is not None:return outcome
                    row=self.make_round();continue
                if candidate(self.workspace)!=row['candidate']:raise FactoryError('验收结束候选变化，不能批准')
                self.guard()
                self.save(self.folder/'completion.json',{'scope':'内部当前TaskPacket质量门槛；不代表APF外部Reviewer验收','candidate':row['candidate'],
                          'packet_fingerprint':digest(self.packet),'round':row['number'],'calls':len(self.q['calls']),
                          'tester':row['tester'],'reviewer':row['reviewer'],
                          'archive_warnings':row['context']['dependencies'].get('archive_warnings',[])})
                self.state['error']=None;self.status('质量门槛通过','独立Tester/Reviewer绑定当前候选通过；停止，不Git/发布');return self.state
        except KeyboardInterrupt:return self.stop('用户中断质量验证；未完成调用保留')
        except (FactoryError,OSError,ValueError,KeyError,TypeError) as e:return self.stop(str(e))

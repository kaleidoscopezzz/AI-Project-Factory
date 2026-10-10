"""One independent quality revalidation. Prepare is model-free; execute is explicit.

Reuse QualityGate's state machine; never migrate or rewrite the failed ledger.
Full Access is current-user access, not OS workspace isolation.
"""
import argparse
import copy
import json
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from .controller import Controller, ROOT, load, save, locked, manifest
from .contracts import (FactoryError, digest, file_hash, safe_path, relative_file,
                        validate_packet, schema_check, CODER_SCHEMA)
from .executor import CodexExecutor, resolve_codex, redact
from .quality import QualityGate, candidate, protected_factory, reference_snapshot, stage_deadline, recovered_tester_event

LIMITS={'Planner':0,'Coder':0,'CoderRepair':0,'Tester':1,'Reviewer':1,
        'agent_seconds':600,'stage_seconds':1800,'retry':False,'allow_repair':False}
GOAL1='adf680014853618a5f512aae08a47ee55c5dd64c'
GOAL0='11aa80e1dc345d63f9b325d14227b078c0f924bb'
GOAL3_HEAD='e7aa58b232923ea99eedc442567a2600a86b271c'
GOAL2='551107e1041ce55570a9ec0fd396d55666ec0156'
GOAL3_PROJECT='p-867ba2d6987a'
GOAL3_RUNTIME='validation/goal3/planner-validation-20261009T233159-55603f/runtime-root'
GOAL3_SOURCE='validation/goal3/quality-validation-20261010T142212-92dc80'
GOAL3_CANDIDATE='c7959e4d196f1041ff06c2548b8af41de055b04e8c4c239cf0ccaf052d7b670d'


def goal3_baseline(root):
    """The approved WIP identity, not a new frozen Goal3 tag."""
    def read(*args):
        return subprocess.check_output(['git','--no-optional-locks',*args],cwd=root,encoding='utf-8').strip()
    result={k:read('rev-parse',v) for k,v in (
        ('head','HEAD'),('main','main'),('origin_main','origin/main'),
        ('goal0','goal-0-approved^{}'),('goal1','goal-1-approved^{}'),
        ('goal2','goal-2-approved^{}'),('goal2_object','goal-2-approved'),
        ('cli_branch','refs/heads/feat/cli-0.1.0'))}
    result.update(branch=read('branch','--show-current'),staged=read('diff','--cached','--name-only'))
    if (any(result[k]!=GOAL3_HEAD for k in ('head','main','origin_main')) or result['branch']!='main'
        or result['staged'] or result['goal0']!=GOAL0 or result['goal1']!=GOAL1
        or result['goal2']!=GOAL2 or result['goal2_object']!='2fd33d9d0527f27034072124bb3e89356a6c461c'):
        raise FactoryError('Goal3 WIP/冻结基线/分支/暂存区异常')
    return result


def goal3_factory(root):
    # The run is outside the original runtime. Do not hash this run into its own
    # guard; pin actual live code/config plus frozen skills instead.
    files={}
    for directory in ('factory','scripts','tests','skills','templates','docs'):
        for p in (root/directory).rglob('*'):
            safe_path(p,root)
            if p.is_file() and '__pycache__' not in p.parts:files[p.relative_to(root).as_posix()]=file_hash(p)
    for name in ('AGENTS.md','README.md','PROJECT_STATUS.md','.gitignore','.gitattributes'):
        if (root/name).is_file():files[name]=file_hash(root/name)
    return files


def git_baseline(root):
    def read(*args):
        return subprocess.check_output(['git','--no-optional-locks',*args],cwd=root,encoding='utf-8').strip()
    result={'head':read('rev-parse','HEAD'),'main':read('rev-parse','main'),
            'branch':read('branch','--show-current'),'goal0':read('rev-parse','goal-0-approved^{}'),
            'goal1':read('rev-parse','goal-1-approved^{}'),
            'goal0_object':read('rev-parse','refs/tags/goal-0-approved'),
            'goal1_object':read('rev-parse','refs/tags/goal-1-approved'),
            'staged':read('diff','--cached','--name-only')}
    if result['head']!=GOAL1 or result['main']!=GOAL1 or result['goal1']!=GOAL1 or result['goal0']!=GOAL0 or result['branch']!='main' or result['staged']:
        raise FactoryError('冻结基线/分支/暂存区异常，拒绝复验')
    return result


def original_files(project):
    result={}
    for p in sorted(project.rglob('*')):
        safe_path(p,project)
        rel=p.relative_to(project)
        # Windows byte lock cannot be hashed while owned; it is coordination,
        # not task evidence. Never exclude state/events or the old quality tree.
        if rel.as_posix()=='control/controller.lock' or any(x in {'node_modules','.factory-tmp','__pycache__'} for x in rel.parts):continue
        if p.is_file():result[rel.as_posix()]=file_hash(p)
    return result


class SingleDispatchExecutor:
    """Durable dispatch fuse around the existing real/test adapter."""
    def __init__(self,delegate,runner,info,run):
        self.delegate=delegate;self.runner=runner;self.info=info;self.run_root=run
        self.full_access=delegate.full_access
        self.path=run/'dispatches.json'

    def scope(self,cwd,control=None):
        safe_path(cwd,self.run_root/'control/quality/rounds')
        if control is not None:safe_path(control,self.run_root/'control')
        if not self.full_access or not self.delegate.full_access:raise FactoryError('本次必须显式选择Full Access；禁止继承或静默切换')

    def preflight(self,packet,cwd,control):
        self.scope(cwd,control);return self.delegate.preflight(packet,cwd,control)

    def check(self,argv,cwd,control,index,timeout):
        self.scope(cwd,control);return self.delegate.check(argv,cwd,control,index,min(timeout,180))

    def sandbox_argv(self,argv,cwd):
        self.scope(cwd);return self.delegate.sandbox_argv(argv,cwd)

    def run(self,role,prompt,cwd,control,number,schema,timeout):
        self.scope(cwd,control);self.runner.verify(self.info,self.run_root)
        if role not in ('Tester','Reviewer'):raise FactoryError('独立复验禁止Planner/Coder/返工')
        if self.info.get('review_source') and role!='Reviewer':raise FactoryError('派生复核仅授权Reviewer，禁止重新Tester')
        if self.info.get('completed_review_source'):raise FactoryError('真实Reviewer已完成，本次只允许零模型收口')
        entries=load(self.path) if self.path.exists() else []
        if any(r['role']==role for r in entries):raise FactoryError('该角色已占用一次派发额度；禁止重复调用')
        if role=='Reviewer':
            q=load(self.run_root/'control/quality/state.json')
            if not q['rounds'] or not q['rounds'][-1]['tester'] or q['rounds'][-1]['tester']['status']!='passed':
                raise FactoryError('没有合法Tester通过检查点；不得派发Reviewer')
        session=load(self.run_root/'authorization.json')
        remaining=LIMITS['stage_seconds']-(time.time()-session['started_at'])
        seconds=min(timeout,LIMITS['agent_seconds'],remaining)
        if seconds<=0:raise FactoryError('复验墙钟预算耗尽')
        row={'role':role,'number':number,'status':'registered','input_sha256':digest(prompt.encode()),
             'timeout_seconds':seconds,'candidate_fingerprint':self.info['candidate']['fingerprint'],'started_at':time.time()}
        entries.append(row);save(self.path,entries)  # fuse before any delegate launch
        try:
            result=self.delegate.run(role,prompt,cwd,control,number,schema,seconds)
            row.update({k:result.get(k) for k in ('exit_code','timed_out','elapsed_seconds','thread_ids','usage')})
            row['status']='returned';save(self.path,entries);return result
        except BaseException:
            row['status']='interrupted';save(self.path,entries);raise


class OriginBoundGate(QualityGate):
    """Only guards/caps are added; decisions/recovery stay in QualityGate."""
    def guard(self):
        super().guard();self.owner.verify(self.info,self.run_root)

    def context(self,row,role='Tester'):
        value=super().context(row,role)
        value['effective_dispatch_limits']={**LIMITS,'Tester':0 if self.info.get('review_source') else 1}
        return value

    def call(self,role,prompt,cwd,row,schema):
        if role not in ('Tester','Reviewer') or self.allow_repair or self.retry:
            raise FactoryError('复验角色/NoAutoRepair/Retry约束无效')
        key=role+':'+digest(prompt.encode())
        cached=any(c['role']==role and c['key']==key and c['status']=='finished' for c in self.q['calls'])
        if sum(c['role']==role for c in self.q['calls'])>=1 and not cached:
            raise FactoryError('复验角色一次调用上限；不允许用不同输入重复调用')
        return super().call(role,prompt,cwd,row,schema)


class RevalidationRunner:
    def __init__(self,root=ROOT,controller=None,*,goal3_runtime_root=None):
        self.root=Path(root).resolve();self.goal3=goal3_runtime_root is not None
        runtime=self.root
        if self.goal3:
            runtime=safe_path(goal3_runtime_root,self.root/GOAL3_RUNTIME,exact=True)
        self.c=controller or Controller(runtime)
        if self.c.root!=runtime:raise FactoryError('复验Controller运行根不匹配')
        self.base=safe_path(self.root/('validation/goal3/revalidations' if self.goal3 else 'validation/goal2/revalidations'),self.root/'validation')

    def baseline(self):return goal3_baseline(self.root) if self.goal3 else git_baseline(self.root)
    def factory_guard(self):return goal3_factory(self.root) if self.goal3 else protected_factory(self.root)
    def reference_guard(self):return reference_snapshot(self.c.root if self.goal3 else self.root)

    def historical_requirements(self,workspace,completion):
        if not self.goal3:return []
        # Only the two first-failure originals explicitly named by this delivery.
        # No directory scan or inference from later successful evidence.
        doc=relative_file('validation/acceptance.md',workspace)
        if file_hash(doc)!=completion['workspace_manifest'].get('validation/acceptance.md'):
            raise FactoryError('AC-012原验收文档来源SHA不匹配')
        directory='validation/run-2026-10-09T16-07-08.840Z'
        if directory not in doc.read_text(encoding='utf-8'):
            raise FactoryError('AC-012首轮失败引用来源不明确')
        rows=[]
        for name in (directory+'/test.log',directory+'/results.json'):
            path=relative_file(name,workspace);h=completion['workspace_manifest'].get(name)
            if not h or not path.is_file() or file_hash(path)!=h:raise FactoryError('AC-012必要旧失败原件缺失或SHA错误：'+name)
            rows.append({'source':name,'sha256':h,'parent':'validation/acceptance.md',
                         'parent_sha256':file_hash(doc),'purpose':'AC-012 first failed Coder run preservation, never current pass evidence'})
        return rows

    def run_path(self,run_id):
        if not isinstance(run_id,str) or not re.fullmatch(r'rv-[a-f0-9]{12}',run_id):raise FactoryError('复验RunId无效')
        return safe_path(self.base/run_id,self.base)

    def sources(self,project,control,workspace,current,source):
        source=safe_path(source,self.root/GOAL3_SOURCE,exact=True) if self.goal3 else safe_path(source,self.root/'validation/goal2')
        before_name='BEFORE.json' if self.goal3 else 'before.json'
        before_path=relative_file(before_name,source);anchor_path=relative_file('evidence-manifest.json',source)
        anchor=load(anchor_path);before=load(before_path)
        if self.goal3:
            if project.name!=GOAL3_PROJECT or Path(before['project'])!=project or Path(before['runtime_root'])!=self.c.root:
                raise FactoryError('Goal3原项目/运行根/来源身份不匹配')
            rows=anchor['files']
            if len({r['path'] for r in rows})!=len(rows):raise FactoryError('Goal3来源清单重复路径')
            anchor={'files':{r['path']:r for r in rows}}
            before={'state':before['state_before'],'legacy_calls':before['state_before']['calls'],
                    'errors':[],'candidate':before['candidate'],'packet_fingerprint':before['packet_fingerprint'],
                    'packet_file_sha256':before['project_files']['control/task-packet.json'],
                    'original_project_files':{project.relative_to(self.root).as_posix()+'/'+n:h for n,h in before['project_files'].items()}}
        def anchored(path):
            name=path.relative_to(self.root).as_posix()
            row=anchor['files'].get(name)
            if not row or not path.is_file() or file_hash(path)!=row['sha256']:raise FactoryError('来源未被历史清单验证：'+name)
        anchored(before_path)
        completed=before['state']
        if completed.get('status')!='已完成' or before.get('errors') or completed['project_id']!=project.name:
            raise FactoryError('原始完成状态无效；不能伪装原任务完成')
        if completed['calls']!=current['calls'] or before['legacy_calls']!=completed['calls']:
            raise FactoryError('原Planner/Coder历史调用已变化')
        packet=load(control/'task-packet.json');validate_packet(packet,self.c.root,completed)
        completion=load(control/'completion.json');coder=load(control/'coder-result.json')
        names=['task-packet.json','packet-validation.json','completion.json','coder-result.json',*packet['artifacts']]
        for name in names:
            path=relative_file(name,control)
            # The pinned before.json contains the per-file original snapshot;
            # the outer manifest need not duplicate every original metadata file.
            if path.relative_to(self.root).as_posix() in anchor['files']:anchored(path)
            if before['original_project_files'].get(path.relative_to(self.root).as_posix())!=file_hash(path):
                raise FactoryError('原完成快照与来源不一致：'+name)
        if before['packet_fingerprint']!=digest(packet) or before['packet_file_sha256']!=file_hash(control/'task-packet.json'):
            raise FactoryError('原TaskPacket指纹不匹配')
        pv=load(control/'packet-validation.json')
        if not pv['passed'] or pv['packet_fingerprint']!=digest(packet):raise FactoryError('TaskPacket校验记录无效')
        if not completion['passed'] or completion['project_id']!=project.name or completion['packet_fingerprint']!=digest(packet) or completion['workspace_manifest']!=manifest(workspace):
            raise FactoryError('完成记录/原候选完整清单不匹配')
        if not completion['runtime']['passed'] or any(c['exit_code']!=0 or c.get('timed_out') for c in completion['checks']):
            raise FactoryError('原完成检查并非通过')
        if [(c['purpose'],c['argv']) for c in completion['checks']]!=[(c['purpose'],c['argv']) for c in packet['checks']]:
            raise FactoryError('原完成检查遗漏TaskPacket要求')
        schema_check(coder,CODER_SCHEMA)
        if coder['status']!='completed' or not coder['tests'] or any(t['exit_code']!=0 for t in coder['tests']):
            raise FactoryError('原Coder结果无效')
        for name in coder['files']+coder['evidence']:
            if not relative_file(name,workspace).is_file():raise FactoryError('原Coder来源文件缺失')
        snap=candidate(workspace)
        if snap!=before['candidate']:raise FactoryError('候选指纹与完成来源不匹配')
        if self.goal3 and (snap['fingerprint']!=GOAL3_CANDIDATE or packet['goal']!='Goal 0'
                          or len(packet['acceptance'])!=12 or completed.get('coder_execution_intent')!='danger-full-access'):
            raise FactoryError('Goal3候选/阶段/AC/权限意向不匹配')
        old=load(control/'quality/state.json')
        anchored(control/'quality/state.json')
        if self.goal3:
            if protected_factory(self.c.root)!=old['protected_factory']:
                raise FactoryError('Goal3旧运行根工厂哈希守护不匹配')
            for name,h in old['initial_control_manifest'].items():
                if file_hash(relative_file(name,control))!=h:raise FactoryError('Goal3旧控制证据守护不匹配')
        if old['status']!='质量门槛失败' or not old['calls']:raise FactoryError('缺少原质量失败历史，拒绝混淆上下文')
        if current['status']!=old['status'] or current.get('packet_fingerprint')!=digest(packet):
            raise FactoryError('原项目完成来源/当前失败状态不一致，拒绝复验')
        for name in ('state.json','events.jsonl'):
            path=control/name
            if path.relative_to(self.root).as_posix() in anchor['files']:anchored(path)
        ref=self.reference_guard()
        if old.get('protected_reference')!=ref:raise FactoryError('参考项目守护异常')
        return {'names':names,'completed':completed,'candidate':snap,'packet_fingerprint':digest(packet),
                'source_evidence':source.relative_to(self.root).as_posix(),
                'anchor':{before_path.relative_to(self.root).as_posix():file_hash(before_path),
                          anchor_path.relative_to(self.root).as_posix():file_hash(anchor_path)},
                'origin_status':current['status'],'origin_quality_status':old['status'],'reference':ref,
                'before_name':before_name,'state_pointer':'state_before' if self.goal3 else 'state',
                'required_history':self.historical_requirements(workspace,completion)}

    def prepare(self,project_id,source,run_id=None):
        project,control,workspace,current=self.c.locate(project_id)
        with locked(control):
            project,control,workspace,current=self.c.locate(project_id)
            origin=self.sources(project,control,workspace,current,Path(source));baseline=self.baseline()
            run_id=run_id or 'rv-'+uuid.uuid4().hex[:12];run=self.run_path(run_id)
            run.mkdir(parents=True,exist_ok=False);new=run/'control';new.mkdir()
            bindings=[]
            for name in origin['names']:
                src=relative_file(name,control);dst=new/name;shutil.copy2(src,dst)
                bindings.append({'source':src.relative_to(self.root).as_posix(),'sha256':file_hash(src),
                                 'destination':'control/'+name,'copy_sha256':file_hash(dst),'relation':'byte-identical original Goal1 metadata'})
            for src,name in [(control/'state.json','origin-current-state.json'),
                             (control/'quality/state.json','origin-failed-quality.json')]:
                shutil.copy2(src,new/name);bindings.append({'source':src.relative_to(self.root).as_posix(),
                    'sha256':file_hash(src),'destination':'control/'+name,'copy_sha256':file_hash(new/name),'relation':'preserved original failure observation'})
            save(new/'completed-origin-state.json',origin['completed'])
            origin_before=origin['source_evidence']+'/'+origin['before_name']
            bindings.append({'source':origin_before,'sha256':origin['anchor'][origin_before],
                             'json_pointer':'/'+origin['state_pointer'],'content_sha256':digest(origin['completed']),
                             'destination':'control/completed-origin-state.json','copy_sha256':file_hash(new/'completed-origin-state.json'),
                             'relation':'verified completed Goal1 phase extracted from historical container, not current quality success'})
            state=copy.deepcopy(origin['completed']);state.update(status='任务包已验证',error=None,
                independent_revalidation={'run_id':run_id,'authorization_pending':True,'origin_status':origin['origin_status'],
                    'origin_quality_status':origin['origin_quality_status'],'purpose':'independent revalidation of previously failed quality; not a reset',
                    'required_history':origin['required_history']})
            save(new/'state.json',state)
            info={'version':'1.0','run_id':run_id,'purpose':'independent quality revalidation; execute requires new human authorization',
                  'project_id':project_id,'original_project':project.relative_to(self.root).as_posix(),
                  'workspace':workspace.relative_to(self.root).as_posix(),'sources':bindings,'anchor':origin['anchor'],
                  'source_evidence':origin['source_evidence'],'candidate':origin['candidate'],'packet_fingerprint':origin['packet_fingerprint'],
                  'origin_status':origin['origin_status'],'origin_quality_status':origin['origin_quality_status'],
                  'original_files':original_files(project),'factory':self.factory_guard(),
                  'reference':origin['reference'],'git':baseline,'limits':dict(LIMITS),
                  'prepared_state_sha256':file_hash(new/'state.json'),'created_at':time.time(),'authorization_pending':True}
            info.update(goal3=self.goal3,stage=load(control/'task-packet.json')['goal'],
                        before_name=origin['before_name'],state_pointer=origin['state_pointer'],required_history=origin['required_history'])
            info['state_derivation']={'source':origin_before,
                'source_sha256':origin['anchor'][origin_before],'json_pointer':'/'+origin['state_pointer'],
                'verified_completed_content_sha256':digest(origin['completed']),
                'destination':'control/state.json','initial_sha256':file_hash(new/'state.json'),
                'mutable_progress':True,'changes':'explicit independent pending quality identity/status; preserve original calls and original failure facts'}
            save(run/'prepared.json',info);save(run/'receipt.json',{'prepared_sha256':file_hash(run/'prepared.json')})
            self.verify(info,run)
            return {'run_id':run_id,'path':str(run),'status':'prepared, awaiting new execution authorization','new_agent_calls':0}

    def prepare_review(self,source_run_id,source_manifest,run_id=None,*,reviewer_source_run_id=None):
        """Reuse one real Tester in a new ledger; the failed run stays immutable."""
        if not self.goal3:raise FactoryError('恢复工具事件复核仅支持当前Goal3试验')
        source_run=self.run_path(source_run_id);old=load(source_run/'prepared.json')
        manifest_path=safe_path(source_manifest,self.root/'validation/goal3')
        if file_hash(source_run/'prepared.json')!=load(source_run/'receipt.json')['prepared_sha256']:
            raise FactoryError('原复验准备记录被篡改')
        snapshot=original_files(source_run);entries=load(manifest_path)['files']
        listed={e['path']:e['sha256'] for e in entries}
        if any(listed.get((source_run/name).relative_to(self.root).as_posix())!=h for name,h in snapshot.items()):
            raise FactoryError('原真实复验文件与已交付清单不一致')
        live=self.factory_guard()
        changed={p for p in set(old['factory'])|set(live) if old['factory'].get(p)!=live.get(p)}
        allowed={'factory/quality.py','factory/revalidation.py','factory/sequence.py','scripts/revalidate-goal2.ps1',
                 'tests/test_goal3_revalidation.py','docs/GOAL3_QUALITY_REVALIDATION.md'}
        if not changed<=allowed or old['git']!=self.baseline() or old['project_id']!=GOAL3_PROJECT:
            raise FactoryError('非授权工厂变化或复用身份不匹配')
        qold=load(source_run/'control/quality/state.json')
        dispatches=load(source_run/'dispatches.json')
        if (qold['status']!='质量门槛失败' or len(qold['rounds'])!=1 or len(qold['calls'])!=1
            or qold['calls'][0]['role']!='Tester' or len(dispatches)!=1 or dispatches[0]['role']!='Tester'):
            raise FactoryError('不是只有一次真实Tester的原失败上下文')
        reviewer_source=None
        if reviewer_source_run_id:
            reviewer_source=self.run_path(reviewer_source_run_id);review_info=load(reviewer_source/'prepared.json')
            review_q=load(reviewer_source/'control/quality/state.json')
            if (review_info.get('review_source',{}).get('run_id')!=source_run_id
                or review_info['review_source']['files']!=snapshot or review_info['candidate']!=old['candidate']
                or review_info['packet_fingerprint']!=old['packet_fingerprint'] or len(review_q['calls'])!=1
                or review_q['calls'][0]['role']!='Reviewer' or len(review_q['rounds'])!=1):
                raise FactoryError('不能复用不同候选或不同Tester来源的Reviewer')
            if file_hash(reviewer_source/'prepared.json')!=load(reviewer_source/'receipt.json')['prepared_sha256']:
                raise FactoryError('真实Reviewer来源准备记录变化')
            delta={p for p in set(review_info['factory'])|set(live) if review_info['factory'].get(p)!=live.get(p)}
            if not delta<=allowed or review_info['git']!=self.baseline():raise FactoryError('Reviewer来源工厂变化未授权')
            review_snapshot=original_files(reviewer_source)
        prepared=self.prepare(old['project_id'],self.root/old['source_evidence'],run_id)
        run=self.run_path(prepared['run_id']);new=run/'control';info=load(run/'prepared.json')
        project,control,workspace,_=self.c.locate(info['project_id'])
        with locked(control):
            if old['original_files']!=original_files(project) or old['candidate']!=info['candidate'] or old['packet_fingerprint']!=info['packet_fingerprint']:
                raise FactoryError('原业务、来源或任务包变化，不复用旧测试')
            gate=OriginBoundGate(self.c,project,new,workspace,load(new/'state.json'),retry=False,allow_repair=False)
            row=copy.deepcopy((review_q if reviewer_source else qold)['rounds'][0]);row.update(tester=None,reviewer=None)
            row.pop('reviewer_execution',None)
            src_round=relative_file(row['path'],(reviewer_source or source_run)/'control/quality');dst_round=relative_file(row['path'],gate.folder)
            dst_round.parent.mkdir(parents=True,exist_ok=True)
            shutil.copytree(src_round,dst_round,ignore=shutil.ignore_patterns('node_modules','__pycache__','.factory-tmp'))
            reuse=dst_round/'context/tester-reuse';reuse.mkdir(exist_ok=bool(reviewer_source))
            source_call=relative_file(qold['calls'][0]['path'],source_run/'control/quality')
            bindings={}
            for key,name in [('execution','execution.json'),('log','tester-01.log.jsonl'),('raw_result','tester-01.result.json')]:
                shutil.copy2(source_call/name,reuse/name)
                bindings[key]={'path':(reuse/name).relative_to(dst_round).as_posix(),'sha256':file_hash(reuse/name),
                               'source':(source_call/name).relative_to(self.root).as_posix()}
            actual=load(reuse/'execution.json')
            if load(reuse/'tester-01.result.json')!=actual:raise FactoryError('原Tester结果与执行记录不同')
            derived,proof=recovered_tester_event(actual,reuse/'tester-01.log.jsonl',dst_round)
            save(reuse/'recovery.json',proof)
            bindings['proof']={'path':(reuse/'recovery.json').relative_to(dst_round).as_posix(),'sha256':file_hash(reuse/'recovery.json')}
            save(reuse/'binding.json',bindings)
            row['tester_derivation']={'path':(reuse/'binding.json').relative_to(gate.folder).as_posix(),'sha256':file_hash(reuse/'binding.json')}
            row['tester_execution']={'path':(reuse/'execution.json').relative_to(gate.folder).as_posix(),'sha256':file_hash(reuse/'execution.json')}
            row['tester']=derived;gate.q['rounds']=[row]
            gate.result(derived,'Tester',row,actual);gate.basic(row)
            if reviewer_source:
                prior_call=relative_file(review_q['calls'][0]['path'],reviewer_source/'control/quality')
                dest=dst_round/'context/reviewer-reuse';dest.mkdir()
                reviewer_bindings={}
                for name in ('execution.json','reviewer-01.result.json','reviewer-01.log.jsonl','provenance.json'):
                    shutil.copy2(prior_call/name,dest/name)
                    reviewer_bindings[name]={'path':(dest/name).relative_to(gate.folder).as_posix(),'sha256':file_hash(dest/name)}
                review=load(dest/'execution.json');provenance=load(dest/'provenance.json')
                if (review!=load(dest/'reviewer-01.result.json') or review['execution_mode']!='read-only'
                    or review.get('exit_code')!=0 or review.get('timed_out') or not review.get('turn_completed')
                    or not review.get('thread_ids') or review['output']['decision']!='approved'
                    or review['input_sha256']!=review_q['calls'][0]['input_sha256']
                    or set(review['thread_ids'])&set(actual['thread_ids'])
                    or provenance['before']!=info['candidate'] or provenance['after']!=info['candidate']
                    or provenance['execution_copy_changes']):
                    raise FactoryError('真实只读Reviewer来源、权限、完成结果或源码守护无效')
                row['reviewer_execution']=reviewer_bindings['execution.json'];row['reviewer']=review['output']
                gate.result(row['reviewer'],'Reviewer',row,review)
                info['completed_review_source']={'run_id':reviewer_source_run_id,'files':review_snapshot,
                    'copies':reviewer_bindings,'new_Reviewer_calls':0,'meaning':'actual approved read-only Reviewer, revalidated without model replay'}
            gate.q['tester_reuse']={'source_run':source_run_id,'new_Tester_calls':0,'derived_result':digest(derived)}
            gate.checkpoint()
            info['review_source']={'run_id':source_run_id,'manifest':manifest_path.relative_to(self.root).as_posix(),
                'manifest_sha256':file_hash(manifest_path),'files':snapshot,'authorized_factory_changes':sorted(changed)}
            info['prepared_quality_sha256']=file_hash(gate.path);info['prepared_state_sha256']=file_hash(new/'state.json')
            save(run/'prepared.json',info);save(run/'receipt.json',{'prepared_sha256':file_hash(run/'prepared.json')})
            self.verify(info,run)
        return {**prepared,'status':('real Tester and approved Reviewer reused; model-free finalization ready' if reviewer_source
                                    else 'real Tester reused and fully validated; Reviewer pending new authorization'),
                'new_Tester_calls':0,'new_Reviewer_calls':0}

    def verify(self,info,run):
        if self.run_path(info['run_id'])!=run or info['version']!='1.0' or info['limits']!=LIMITS or info.get('goal3',False)!=self.goal3:
            raise FactoryError('复验身份/目录/预算无效')
        if file_hash(run/'prepared.json')!=load(run/'receipt.json')['prepared_sha256']:
            raise FactoryError('准备清单被篡改')
        project,control,workspace,current=self.c.locate(info['project_id'])
        if project.relative_to(self.root).as_posix()!=info['original_project'] or workspace.relative_to(self.root).as_posix()!=info['workspace']:
            raise FactoryError('原项目身份/路径不匹配')
        if original_files(project)!=info['original_files']:raise FactoryError('原历史/源码/账本发生变化，停止')
        for name,h in info['anchor'].items():
            src=relative_file(name,self.root)
            source_base=self.root/GOAL3_SOURCE if self.goal3 else self.root/'validation/goal2'
            if not src.is_relative_to(source_base) or file_hash(src)!=h:raise FactoryError('历史来源锚点无效')
        for binding in info['sources']:
            src=relative_file(binding['source'],self.root);dst=relative_file(binding['destination'],run)
            allowed=src.is_relative_to(control) or src==self.root/info['source_evidence']/info.get('before_name','before.json')
            if not allowed or not dst.is_relative_to(run/'control') or not src.is_file() or file_hash(src)!=binding['sha256'] or not dst.is_file() or file_hash(dst)!=binding['copy_sha256']:
                raise FactoryError('元数据来源无效/副本篡改/路径越界')
            if binding.get('json_pointer'):
                pointer=info.get('state_pointer','state')
                if binding['json_pointer']!='/'+pointer or digest(load(src)[pointer])!=binding['content_sha256'] or load(src)[pointer]!=load(dst):
                    raise FactoryError('原始完成状态来源不匹配')
        if self.factory_guard()!=info['factory'] or self.baseline()!=info['git'] or self.reference_guard()!=info['reference']:
            raise FactoryError('工厂/冻结基线/参考项目发生变化')
        if candidate(workspace)!=info['candidate']:raise FactoryError('候选变化，旧来源无效')
        validate_packet(load(run/'control/task-packet.json'),self.c.root,load(run/'control/state.json'))
        state=load(run/'control/state.json');identity=state.get('independent_revalidation',{})
        if identity.get('run_id')!=info['run_id'] or identity.get('origin_quality_status')!=info['origin_quality_status'] or state['calls']!=load(run/'control/completed-origin-state.json')['calls']:
            raise FactoryError('新旧状态或原Agent调用来源混淆')
        if self.goal3:
            if info['stage']!='Goal 0' or info['project_id']!=GOAL3_PROJECT or info['candidate']['fingerprint']!=GOAL3_CANDIDATE:
                raise FactoryError('Goal3阶段身份变化')
            if state.get('coder_execution_intent')!='danger-full-access':
                raise FactoryError('Goal3显式执行权限意向不匹配')
            required=self.historical_requirements(workspace,load(control/'completion.json'))
            if info['required_history']!=required or identity.get('required_history')!=required:
                raise FactoryError('AC-012必要历史来源绑定变化')
        if (run/'dispatches.json').exists():
            calls=load(run/'dispatches.json')
            if not isinstance(calls,list) or len(calls)>2 or any(c.get('role') not in ('Tester','Reviewer') or not 0<c.get('timeout_seconds',0)<=600 for c in calls) or len({c['role'] for c in calls})!=len(calls):
                raise FactoryError('单次派发账本/预算无效')
            if info.get('review_source') and any(c['role']!='Reviewer' for c in calls):raise FactoryError('派生复核不得派发Tester')
        if info.get('review_source'):
            source=info['review_source'];original=self.run_path(source['run_id'])
            if original==run or original_files(original)!=source['files']:
                raise FactoryError('原真实Tester失败账本或证据变化')
            source_manifest=safe_path(self.root/source['manifest'],self.root/'validation/goal3')
            if file_hash(source_manifest)!=source['manifest_sha256']:raise FactoryError('原交付来源清单变化')
            gate=QualityGate.__new__(QualityGate)
            gate.c=self.c;gate.control=run/'control';gate.folder=gate.control/'quality';gate.workspace=workspace
            gate.state=state;gate.q=load(gate.folder/'state.json');gate.packet=load(gate.control/'task-packet.json');gate.load=load
            row=gate.q['rounds'][0];gate.guard();gate.result(row['tester'],'Tester',row)
            if info.get('completed_review_source'):
                source=info['completed_review_source']
                if original_files(self.run_path(source['run_id']))!=source['files']:raise FactoryError('原Reviewer账本或证据变化')
                for e in source['copies'].values():
                    if file_hash(relative_file(e['path'],gate.folder))!=e['sha256']:raise FactoryError('真实Reviewer副本变化')
                raw=load(relative_file(source['copies']['execution.json']['path'],gate.folder))
                if row['reviewer']!=raw['output']:raise FactoryError('不能改写真实Reviewer决定')
                gate.result(row['reviewer'],'Reviewer',row,raw)

    def precheck(self,run_id):
        """No model or ledger writes: the actual history used by this gate."""
        from .history import history_dependencies
        run=self.run_path(run_id);info=load(run/'prepared.json');self.verify(info,run)
        workspace=self.root/info['workspace']
        plan=history_dependencies(workspace,load(run/'control/completion.json'),candidate(workspace),load,
                                  required_history=info.get('required_history',[]))
        if not plan['ready']:raise FactoryError('复验历史上下文预检失败：'+json.dumps(plan['unverified'],ensure_ascii=False))
        return {'ready':True,'run_id':run_id,'stage':info.get('stage','Goal 0'),'candidate_fingerprint':info['candidate']['fingerprint'],
                'packet_fingerprint':info['packet_fingerprint'],'history_dependencies':plan,'model_calls':0}

    def execute(self,run_id,*,authorization_id,full_access,codex_path=None,owned_worker=False):
        if not authorization_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',authorization_id) or not full_access:
            raise FactoryError('执行需新的明确授权标识及FullAccess，准备不等于运行授权')
        run=self.run_path(run_id);info=load(run/'prepared.json');new=run/'control'
        project,control,workspace,_=self.c.locate(info['project_id'])
        with locked(control):
            self.precheck(run_id)
            # CLI checks are not model calls. Tests inject the existing AgentDouble.
            delegate=self.c.executor
            if isinstance(delegate,SingleDispatchExecutor):delegate=delegate.delegate
            cli=None
            if delegate is None or isinstance(delegate,CodexExecutor):
                if not codex_path:raise FactoryError('真实复验必须显式指定已CheckCli的绝对CLI路径')
                exe,version=resolve_codex(codex_path);cli={'path':exe,'version':version,'sha256':file_hash(Path(exe))}
            if delegate is not None and not delegate.full_access:raise FactoryError('注入适配器权限与显式FullAccess不一致')
            auth_path=run/'authorization.json'
            if auth_path.exists():
                auth=load(auth_path)
                if auth['id']!=authorization_id or auth['full_access']!=full_access or auth['cli']!=cli:
                    raise FactoryError('恢复不能更换授权/权限/CLI')
            else:
                if (run/'dispatches.json').exists() or ((new/'quality/state.json').exists() and
                    (not info.get('review_source') or file_hash(new/'quality/state.json')!=info['prepared_quality_sha256'])):
                    raise FactoryError('无授权来源的已有质量执行，拒绝接管')
                if file_hash(new/'state.json')!=info['prepared_state_sha256']:raise FactoryError('待执行状态被篡改')
                auth={'id':authorization_id,'full_access':True,'cli':cli,'started_at':time.time(),
                      'limits':dict(LIMITS),'permission':'explicit current Windows user; Reviewer read-only; no OS workspace isolation'}
                if info.get('review_source'):
                    auth['new_role_limits']={'Planner':0,'Coder':0,'Tester':0,'Reviewer':0 if info.get('completed_review_source') else 1,'CoderRepair':0}
                    auth['permission']='Reviewer CLI read-only only; no new engineering checks; FullAccess flag does not change Reviewer sandbox'
                save(auth_path,auth)
            if auth['limits']!=LIMITS:raise FactoryError('授权预算被篡改')
            remaining=LIMITS['stage_seconds']-(time.time()-auth['started_at'])
            if remaining<=0:raise FactoryError('原复验1800秒墙钟预算耗尽，不重置时钟')
            if self.goal3 and (run/'stage-approval.json').exists():
                from .sequence import check_receipt
                approval=load(run/'stage-approval.json')
                if (approval['project_id']!=info['project_id'] or approval['goal']!=info['stage']
                    or approval['run_id']!=run_id or approval['candidate_fingerprint']!=info['candidate']['fingerprint']
                    or approval['packet_fingerprint']!=info['packet_fingerprint']):
                    raise FactoryError('独立阶段批准身份不匹配')
                receipt=check_receipt(run,approval['completion'],info['stage'],project_id=info['project_id'])
                if receipt['candidate']!=info['candidate'] or receipt['packet_fingerprint']!=info['packet_fingerprint']:
                    raise FactoryError('独立阶段批准候选/任务包不匹配')
                gate=QualityGate.__new__(QualityGate)
                gate.c=self.c;gate.control=new;gate.folder=new/'quality';gate.workspace=workspace
                gate.state=load(new/'state.json');gate.q=load(new/'quality/state.json');gate.packet=load(new/'task-packet.json');gate.load=load
                if gate.state['status']!='质量门槛通过' or gate.q['status']!='质量门槛通过':raise FactoryError('没有合法批准检查点')
                gate.guard();row=gate.q['rounds'][-1]
                gate.result(row['tester'],'Tester',row);gate.result(row['reviewer'],'Reviewer',row)
                return gate.state
            with stage_deadline(new,remaining,enabled=owned_worker):
                if delegate is None:delegate=CodexExecutor(full_access=True,codex_path=codex_path)
                self.c.executor=SingleDispatchExecutor(delegate,self,info,run);self.c.full_access=True
                state=load(new/'state.json');state['independent_revalidation']['authorization_pending']=False
                marker={'run_id':run_id,'origin_quality_status':info['origin_quality_status'],'limits':dict(LIMITS),'authorization_id':authorization_id}
                if ((new/'quality/state.json').exists() and load(new/'quality/state.json').get('independent_revalidation')!=marker
                    and not (info.get('review_source') and file_hash(new/'quality/state.json')==info['prepared_quality_sha256'])):
                    raise FactoryError('已有质量账本不是本次独立复验，拒绝接管')
                gate=OriginBoundGate(self.c,project,new,workspace,state,retry=False,allow_repair=False)
                gate.owner=self;gate.info=info;gate.run_root=run
                if 'independent_revalidation' in gate.q and gate.q['independent_revalidation']!=marker:raise FactoryError('质量账本不属于本次独立复验')
                gate.q['independent_revalidation']=marker;gate.checkpoint()
                result=gate.run();self.verify(info,run)
                if self.goal3 and result['status']=='质量门槛通过':
                    from .sequence import finish
                    (new/'sequence').mkdir(exist_ok=True)
                    entry=finish(self.c,run,new,workspace,info['stage'],project_id=info['project_id'])
                    save(run/'stage-approval.json',{'project_id':info['project_id'],'goal':info['stage'],
                        'status':'软件 Goal 0 真实质量验证通过，Goal 1 待授权','run_id':run_id,
                        'candidate_fingerprint':info['candidate']['fingerprint'],'packet_fingerprint':info['packet_fingerprint'],
                        'completion':entry,'original_failed_ledger_unchanged':True,'Goal1_executed':False})
                save(run/'RESULTS.json',{'scope':'independent internal quality revalidation, not external APF approval',
                    'run_id':run_id,'status':result['status'],'error':result['error'],'quality':result.get('quality'),
                    'dispatches':load(run/'dispatches.json') if (run/'dispatches.json').exists() else [],
                    'original_history_unchanged':True,'external_approval':False})
                return result


def main(argv=None):
    p=argparse.ArgumentParser(description='Prepare/execute one independently authorized Goal2 revalidation')
    action=p.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare',action='store_true');action.add_argument('--execute',action='store_true');action.add_argument('--check-cli',action='store_true')
    action.add_argument('--prepare-review',action='store_true')
    p.add_argument('--project-id');p.add_argument('--source-evidence');p.add_argument('--run-id')
    p.add_argument('--authorization-id');p.add_argument('--full-access',action='store_true');p.add_argument('--codex-path')
    p.add_argument('--source-run-id');p.add_argument('--source-manifest')
    p.add_argument('--reviewer-source-run-id')
    p.add_argument('--goal3-runtime-root',help='Only the approved Goal3 experiment runtime, not a general root override')
    a=p.parse_args(argv)
    try:
        if not a.prepare_review and (a.source_run_id or a.source_manifest or a.reviewer_source_run_id):raise FactoryError('复核来源参数只能用于PrepareReview')
        if a.check_cli:
            if any([a.project_id,a.source_evidence,a.run_id,a.authorization_id,a.full_access]):raise FactoryError('CheckCli不能与准备/运行参数组合')
            exe,version=resolve_codex(a.codex_path);print(json.dumps({'path':exe,'version':version,'sha256':file_hash(Path(exe)),'model_calls':0}));return 0
        runner=RevalidationRunner(goal3_runtime_root=a.goal3_runtime_root)
        if a.prepare_review:
            if not a.source_run_id or not a.source_manifest or a.project_id or a.source_evidence or a.authorization_id or a.full_access or a.codex_path:
                raise FactoryError('PrepareReview仅接受来源RunId/已交付清单/可选新RunId')
            result=runner.prepare_review(a.source_run_id,a.source_manifest,a.run_id,reviewer_source_run_id=a.reviewer_source_run_id);code=0
        elif a.prepare:
            if not a.project_id or not a.source_evidence or a.authorization_id or a.full_access or a.codex_path:raise FactoryError('Prepare只接受ProjectId/SourceEvidence/可选RunId，不授权执行')
            result=runner.prepare(a.project_id,a.source_evidence,a.run_id);code=0
        else:
            if not a.run_id or a.project_id or a.source_evidence:raise FactoryError('Execute只接受已准备RunId，不提交新需求或替换来源')
            result=runner.execute(a.run_id,authorization_id=a.authorization_id,full_access=a.full_access,codex_path=a.codex_path,owned_worker=True)
            code=0 if result['status']=='质量门槛通过' else 2 if result['status']=='等待用户确认' else 1
        print(json.dumps(result,ensure_ascii=False,indent=2));return code
    except (FactoryError,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:
        print('独立复验停止：'+redact(str(e)),file=sys.stderr);return 1


if __name__=='__main__':sys.exit(main())

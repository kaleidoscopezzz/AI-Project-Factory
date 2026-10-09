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
from .quality import QualityGate, candidate, protected_factory, reference_snapshot, stage_deadline

LIMITS={'Planner':0,'Coder':0,'CoderRepair':0,'Tester':1,'Reviewer':1,
        'agent_seconds':600,'stage_seconds':1800,'retry':False,'allow_repair':False}
GOAL1='adf680014853618a5f512aae08a47ee55c5dd64c'
GOAL0='11aa80e1dc345d63f9b325d14227b078c0f924bb'


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

    def call(self,role,prompt,cwd,row,schema):
        if role not in ('Tester','Reviewer') or self.allow_repair or self.retry:
            raise FactoryError('复验角色/NoAutoRepair/Retry约束无效')
        key=role+':'+digest(prompt.encode())
        cached=any(c['role']==role and c['key']==key and c['status']=='finished' for c in self.q['calls'])
        if sum(c['role']==role for c in self.q['calls'])>=1 and not cached:
            raise FactoryError('复验角色一次调用上限；不允许用不同输入重复调用')
        return super().call(role,prompt,cwd,row,schema)


class RevalidationRunner:
    def __init__(self,root=ROOT,controller=None):
        self.root=Path(root).resolve();self.c=controller or Controller(self.root)
        self.base=safe_path(self.root/'validation/goal2/revalidations',self.root/'validation')

    def run_path(self,run_id):
        if not isinstance(run_id,str) or not re.fullmatch(r'rv-[a-f0-9]{12}',run_id):raise FactoryError('复验RunId无效')
        return safe_path(self.base/run_id,self.base)

    def sources(self,project,control,workspace,current,source):
        source=safe_path(source,self.root/'validation/goal2')
        before_path=relative_file('before.json',source);anchor_path=relative_file('evidence-manifest.json',source)
        anchor=load(anchor_path);before=load(before_path)
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
        packet=load(control/'task-packet.json');validate_packet(packet,self.root,completed)
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
        old=load(control/'quality/state.json')
        anchored(control/'quality/state.json')
        if old['status']!='质量门槛失败' or not old['calls']:raise FactoryError('缺少原质量失败历史，拒绝混淆上下文')
        if current['status']!=old['status'] or current.get('packet_fingerprint')!=digest(packet):
            raise FactoryError('原项目完成来源/当前失败状态不一致，拒绝复验')
        for name in ('state.json','events.jsonl'):
            path=control/name
            if path.relative_to(self.root).as_posix() in anchor['files']:anchored(path)
        ref=reference_snapshot(self.root)
        if old.get('protected_reference')!=ref:raise FactoryError('参考项目守护异常')
        return {'names':names,'completed':completed,'candidate':snap,'packet_fingerprint':digest(packet),
                'source_evidence':source.relative_to(self.root).as_posix(),
                'anchor':{before_path.relative_to(self.root).as_posix():file_hash(before_path),
                          anchor_path.relative_to(self.root).as_posix():file_hash(anchor_path)},
                'origin_status':current['status'],'origin_quality_status':old['status'],'reference':ref}

    def prepare(self,project_id,source,run_id=None):
        project,control,workspace,current=self.c.locate(project_id)
        with locked(control):
            project,control,workspace,current=self.c.locate(project_id)
            origin=self.sources(project,control,workspace,current,Path(source));baseline=git_baseline(self.root)
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
            bindings.append({'source':origin['source_evidence']+'/before.json','sha256':origin['anchor'][origin['source_evidence']+'/before.json'],
                             'json_pointer':'/state','content_sha256':digest(origin['completed']),
                             'destination':'control/completed-origin-state.json','copy_sha256':file_hash(new/'completed-origin-state.json'),
                             'relation':'verified completed Goal1 phase extracted from historical container, not current quality success'})
            state=copy.deepcopy(origin['completed']);state.update(status='任务包已验证',error=None,
                independent_revalidation={'run_id':run_id,'authorization_pending':True,'origin_status':origin['origin_status'],
                    'origin_quality_status':origin['origin_quality_status'],'purpose':'independent revalidation of previously failed quality; not a reset'})
            save(new/'state.json',state)
            info={'version':'1.0','run_id':run_id,'purpose':'independent quality revalidation; execute requires new human authorization',
                  'project_id':project_id,'original_project':project.relative_to(self.root).as_posix(),
                  'workspace':workspace.relative_to(self.root).as_posix(),'sources':bindings,'anchor':origin['anchor'],
                  'source_evidence':origin['source_evidence'],'candidate':origin['candidate'],'packet_fingerprint':origin['packet_fingerprint'],
                  'origin_status':origin['origin_status'],'origin_quality_status':origin['origin_quality_status'],
                  'original_files':original_files(project),'factory':protected_factory(self.root),
                  'reference':origin['reference'],'git':baseline,'limits':dict(LIMITS),
                  'prepared_state_sha256':file_hash(new/'state.json'),'created_at':time.time(),'authorization_pending':True}
            info['state_derivation']={'source':origin['source_evidence']+'/before.json',
                'source_sha256':origin['anchor'][origin['source_evidence']+'/before.json'],'json_pointer':'/state',
                'verified_completed_content_sha256':digest(origin['completed']),
                'destination':'control/state.json','initial_sha256':file_hash(new/'state.json'),
                'mutable_progress':True,'changes':'explicit independent pending quality identity/status; preserve original calls and original failure facts'}
            save(run/'prepared.json',info);save(run/'receipt.json',{'prepared_sha256':file_hash(run/'prepared.json')})
            self.verify(info,run)
            return {'run_id':run_id,'path':str(run),'status':'prepared, awaiting new execution authorization','new_agent_calls':0}

    def verify(self,info,run):
        if self.run_path(info['run_id'])!=run or info['version']!='1.0' or info['limits']!=LIMITS:
            raise FactoryError('复验身份/目录/预算无效')
        if file_hash(run/'prepared.json')!=load(run/'receipt.json')['prepared_sha256']:
            raise FactoryError('准备清单被篡改')
        project,control,workspace,current=self.c.locate(info['project_id'])
        if project.relative_to(self.root).as_posix()!=info['original_project'] or workspace.relative_to(self.root).as_posix()!=info['workspace']:
            raise FactoryError('原项目身份/路径不匹配')
        if original_files(project)!=info['original_files']:raise FactoryError('原历史/源码/账本发生变化，停止')
        for name,h in info['anchor'].items():
            src=relative_file(name,self.root)
            if not src.is_relative_to(self.root/'validation/goal2') or file_hash(src)!=h:raise FactoryError('历史来源锚点无效')
        for binding in info['sources']:
            src=relative_file(binding['source'],self.root);dst=relative_file(binding['destination'],run)
            allowed=src.is_relative_to(control) or src==self.root/info['source_evidence']/'before.json'
            if not allowed or not dst.is_relative_to(run/'control') or not src.is_file() or file_hash(src)!=binding['sha256'] or not dst.is_file() or file_hash(dst)!=binding['copy_sha256']:
                raise FactoryError('元数据来源无效/副本篡改/路径越界')
            if binding.get('json_pointer'):
                if binding['json_pointer']!='/state' or digest(load(src)['state'])!=binding['content_sha256'] or load(src)['state']!=load(dst):
                    raise FactoryError('原始完成状态来源不匹配')
        if protected_factory(self.root)!=info['factory'] or git_baseline(self.root)!=info['git'] or reference_snapshot(self.root)!=info['reference']:
            raise FactoryError('工厂/冻结基线/参考项目发生变化')
        if candidate(workspace)!=info['candidate']:raise FactoryError('候选变化，旧来源无效')
        validate_packet(load(run/'control/task-packet.json'),self.root,load(run/'control/state.json'))
        state=load(run/'control/state.json');identity=state.get('independent_revalidation',{})
        if identity.get('run_id')!=info['run_id'] or identity.get('origin_quality_status')!=info['origin_quality_status'] or state['calls']!=load(run/'control/completed-origin-state.json')['calls']:
            raise FactoryError('新旧状态或原Agent调用来源混淆')
        if (run/'dispatches.json').exists():
            calls=load(run/'dispatches.json')
            if not isinstance(calls,list) or len(calls)>2 or any(c.get('role') not in ('Tester','Reviewer') or not 0<c.get('timeout_seconds',0)<=600 for c in calls) or len({c['role'] for c in calls})!=len(calls):
                raise FactoryError('单次派发账本/预算无效')

    def execute(self,run_id,*,authorization_id,full_access,codex_path=None,owned_worker=False):
        if not authorization_id or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',authorization_id) or not full_access:
            raise FactoryError('执行需新的明确授权标识及FullAccess，准备不等于运行授权')
        run=self.run_path(run_id);info=load(run/'prepared.json');new=run/'control'
        project,control,workspace,_=self.c.locate(info['project_id'])
        with locked(control):
            self.verify(info,run)
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
                if (new/'quality/state.json').exists() or (run/'dispatches.json').exists():raise FactoryError('无授权来源的已有质量执行，拒绝接管')
                if file_hash(new/'state.json')!=info['prepared_state_sha256']:raise FactoryError('待执行状态被篡改')
                auth={'id':authorization_id,'full_access':True,'cli':cli,'started_at':time.time(),
                      'limits':dict(LIMITS),'permission':'explicit current Windows user; Reviewer read-only; no OS workspace isolation'}
                save(auth_path,auth)
            if auth['limits']!=LIMITS:raise FactoryError('授权预算被篡改')
            remaining=LIMITS['stage_seconds']-(time.time()-auth['started_at'])
            if remaining<=0:raise FactoryError('原复验1800秒墙钟预算耗尽，不重置时钟')
            with stage_deadline(new,remaining,enabled=owned_worker):
                if delegate is None:delegate=CodexExecutor(full_access=True,codex_path=codex_path)
                self.c.executor=SingleDispatchExecutor(delegate,self,info,run);self.c.full_access=True
                state=load(new/'state.json');state['independent_revalidation']['authorization_pending']=False
                marker={'run_id':run_id,'origin_quality_status':info['origin_quality_status'],'limits':dict(LIMITS),'authorization_id':authorization_id}
                if (new/'quality/state.json').exists() and load(new/'quality/state.json').get('independent_revalidation')!=marker:
                    raise FactoryError('已有质量账本不是本次独立复验，拒绝接管')
                gate=OriginBoundGate(self.c,project,new,workspace,state,retry=False,allow_repair=False)
                gate.owner=self;gate.info=info;gate.run_root=run
                if 'independent_revalidation' in gate.q and gate.q['independent_revalidation']!=marker:raise FactoryError('质量账本不属于本次独立复验')
                gate.q['independent_revalidation']=marker;gate.checkpoint()
                result=gate.run();self.verify(info,run)
                save(run/'RESULTS.json',{'scope':'independent internal quality revalidation, not external APF approval',
                    'run_id':run_id,'status':result['status'],'error':result['error'],'quality':result.get('quality'),
                    'dispatches':load(run/'dispatches.json') if (run/'dispatches.json').exists() else [],
                    'original_history_unchanged':True,'external_approval':False})
                return result


def main(argv=None):
    p=argparse.ArgumentParser(description='Prepare/execute one independently authorized Goal2 revalidation')
    action=p.add_mutually_exclusive_group(required=True)
    action.add_argument('--prepare',action='store_true');action.add_argument('--execute',action='store_true');action.add_argument('--check-cli',action='store_true')
    p.add_argument('--project-id');p.add_argument('--source-evidence');p.add_argument('--run-id')
    p.add_argument('--authorization-id');p.add_argument('--full-access',action='store_true');p.add_argument('--codex-path')
    a=p.parse_args(argv)
    try:
        if a.check_cli:
            if any([a.project_id,a.source_evidence,a.run_id,a.authorization_id,a.full_access]):raise FactoryError('CheckCli不能与准备/运行参数组合')
            exe,version=resolve_codex(a.codex_path);print(json.dumps({'path':exe,'version':version,'sha256':file_hash(Path(exe)),'model_calls':0}));return 0
        runner=RevalidationRunner()
        if a.prepare:
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

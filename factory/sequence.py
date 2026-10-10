"""Two serial software Goals using Controller and QualityGate, not a scheduler.

The second stage needs a caller-approved prompt. No retry, repair, Git or release.
Completed stages are immutable receipts; unknown partial execution stops.
"""
import copy
import re
import shutil
import uuid
from pathlib import Path
from .controller import Controller, load, save, locked
from .contracts import (FactoryError, STATES, PACKET_FIELDS, digest, file_hash,
                        safe_path, relative_file, validate_packet, validate_plan, command_check)
from .quality import QualityGate, candidate


def validate_spec(spec, plan, workspace):
    if not isinstance(spec,dict) or set(spec)!={'goal','prompt_md','checks','runtime','blocking_questions'} or spec['goal']!='Goal 1':
        raise FactoryError('本增量仅接受独立的Goal 1阶段说明')
    goals={g['id']:g for g in plan['goals']}
    acs=[a for a in plan['acceptance'] if a['goal_id']=='Goal 1']
    tasks=[t for t in plan['tasks'] if t['goal_id']=='Goal 1']
    initial={t['id'] for t in plan['tasks'] if t['goal_id']=='Goal 0'}
    if goals['Goal 0']['depends_on'] or any(not set(t['depends_on'])<=initial for t in plan['tasks'] if t['goal_id']=='Goal 0'):
        raise FactoryError('Goal 0不能依赖尚未执行的后续阶段')
    if goals['Goal 1']['depends_on']!=['Goal 0'] or not goals['Goal 1']['scope'].strip() or not acs or not tasks:
        raise FactoryError('缺少Goal 0→Goal 1进入依赖、范围或AC')
    allowed={t['id'] for t in plan['tasks'] if t['goal_id'] in ('Goal 0','Goal 1')}
    if any(not set(t['depends_on'])<=allowed for t in tasks):
        raise FactoryError('Goal 1依赖超出本轮两个阶段')
    prompt=spec['prompt_md']
    if not isinstance(prompt,str) or len(prompt)<500 or '{{' in prompt or str(workspace) not in prompt:
        raise FactoryError('增量提示词不完整或工作目录不匹配')
    for word in ('Goal 1','增量','禁止','测试','验收','停止','报告',*[a['id'] for a in acs]):
        if word not in prompt:raise FactoryError('增量提示词缺少约束/AC：'+word)
    if not isinstance(spec['blocking_questions'],list) or spec['blocking_questions']:
        raise FactoryError('后续阶段有未确认问题；不得派发')
    if not isinstance(spec['checks'],list) or {c.get('purpose') for c in spec['checks']}!={'build','test'}:
        raise FactoryError('增量阶段缺少独立build/test契约')
    for c in spec['checks']:
        if set(c)!={'purpose','argv'}:raise FactoryError('增量检查格式无效')
        command_check(c['argv'])
    runtime=spec['runtime']
    if not isinstance(runtime,dict) or set(runtime)!={'argv','path','expected_text'}:
        raise FactoryError('增量runtime契约无效')
    command_check(runtime['argv'],True)
    if not isinstance(runtime['path'],str) or not isinstance(runtime['expected_text'],str) or not runtime['path'].startswith('/') or runtime['path'].startswith('//') or not runtime['expected_text'].strip():
        raise FactoryError('增量运行断言无效')


def check_receipt(project, entry, goal, *, project_id=None):
    path=relative_file(entry['path'],project/'control/sequence')
    if file_hash(path)!=entry['sha256']:raise FactoryError('已完成阶段记录被修改')
    value=load(path)
    if value['project_id']!=(project_id or project.name) or value['goal']!=goal or value['status']!='质量门槛通过':
        raise FactoryError('阶段完成身份或进入条件无效')
    for name,h in value['files'].items():
        p=relative_file(name,project)
        if not p.is_file() or file_hash(p)!=h:raise FactoryError('已完成阶段的任务/质量/证据记录变化：'+name)
    if 'source_approval' in value:
        source=value['source_approval']
        directory=safe_path(source['directory'],Path(__file__).resolve().parents[1]/'validation')
        if file_hash(directory/'stage-approval.json')!=source['approval_sha256']:
            raise FactoryError('独立前序批准来源变化')
        prior=check_receipt(directory,{'path':'goal0-completion.json','sha256':source['receipt_sha256']},'Goal 0',project_id=value['project_id'])
        if prior['candidate']!=value['candidate'] or prior['packet_fingerprint']!=value['packet_fingerprint']:
            raise FactoryError('独立前序批准身份不匹配')
    return value


def validate_link(packet, root, state, plan, control):
    project=control.parents[2]
    if state.get('sequence_goal')!='Goal 1' or state['budget']['max_agent_calls']!=1 or state['budget']['max_retries']!=0:
        raise FactoryError('增量阶段身份/单次调用预算无效')
    spec=load(control/'goal-spec.json');validate_spec(spec,plan,project/'workspace')
    if any(packet[k]!=spec[k] for k in ('checks','runtime')):
        raise FactoryError('后续任务包与独立执行契约不符')
    for name in ('plan.md','goals.md','planner-result.json'):
        if file_hash(control/name)!=file_hash(project/'control'/name):
            raise FactoryError('后续阶段没有复用原完整规划')
    parent=packet['predecessor']
    if not isinstance(parent,dict) or set(parent)!={'path','sha256','candidate_fingerprint'} or parent['path']!='goal0-completion.json':
        raise FactoryError('前序阶段引用无效')
    prior=check_receipt(project,{'path':parent['path'],'sha256':parent['sha256']},'Goal 0')
    if prior['candidate']['fingerprint']!=parent['candidate_fingerprint'] or load(control/'increment-before.json')!=prior['candidate']:
        raise FactoryError('前序源码指纹不匹配')
    config=load(project/'control/sequence/config.json')
    if digest(spec)!=config['spec_fingerprint'] or digest(packet['original_request'])!=config['request_fingerprint']:
        raise FactoryError('后续需求/提示词未经原阶段确认')


def prepare(c, project_id, spec, approval_id, *, allow_repair=False):
    project,control,workspace,state=c.locate(project_id)
    with locked(control):
        project,control,workspace,state=c.locate(project_id)
        if not isinstance(approval_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',approval_id):
            raise FactoryError('后续阶段需调用者明确提供范围批准标识')
        validate_packet(load(control/'task-packet.json'),c.root,state)
        plan=load(control/'planner-result.json');validate_plan(plan,workspace);validate_spec(spec,plan,workspace)
        if '已验证TaskPacket指定' not in (workspace/'AGENTS.md').read_text(encoding='utf-8'):
            raise FactoryError('旧工程仅授权Goal 0；本增量不改写旧授权文件，需另行确认迁移')
        folder=safe_path(control/'sequence',control)
        config={'version':'two-goals-1','project_id':project_id,'approval_id':approval_id,
                'request_fingerprint':digest(state['original_request']),
                'goal0_packet_fingerprint':state['packet_fingerprint'],
                'plan_sha256':file_hash(control/'planner-result.json'),
                'spec_fingerprint':digest(spec),'retry':False,'auto_repair':bool(allow_repair),'goals':['Goal 0','Goal 1']}
        if folder.exists():
            if load(folder/'config.json')!=config or load(folder/'goal1-spec.json')!=spec:
                raise FactoryError('已登记的阶段确认内容不同；不能覆盖')
            return load(folder/'state.json')
        folder.mkdir();save(folder/'goal1-spec.json',spec);save(folder/'config.json',config)
        cursor={'project_id':project_id,'config_sha256':file_hash(folder/'config.json'),
                'completed':{},'current_goal':'Goal 0','status':'待执行','error':None}
        save(folder/'state.json',cursor);return cursor


def adopt_goal0(c, project_id, approval_directory):
    """Bind a genuine independent stage receipt; never rewrite its failed origin."""
    project,control,workspace,state=c.locate(project_id)
    source=safe_path(approval_directory,Path(__file__).resolve().parents[1]/'validation')
    with locked(control):
        approval=load(source/'stage-approval.json')
        entry={'path':'goal0-completion.json','sha256':approval['completion']['sha256']}
        prior=check_receipt(source,entry,'Goal 0',project_id=project_id)
        if (approval['project_id']!=project_id or approval['goal']!='Goal 0'
            or approval['completion']['path']!='goal0-completion.json'
            or approval['candidate_fingerprint']!=prior['candidate']['fingerprint']
            or approval['packet_fingerprint']!=prior['packet_fingerprint']
            or candidate(workspace)!=prior['candidate']
            or digest(load(control/'task-packet.json'))!=prior['packet_fingerprint']):
            raise FactoryError('独立前序批准与当前项目/候选/任务包不匹配')
        q=load(source/'control/quality/state.json');row=q['rounds'][-1]
        if q['status']!='质量门槛通过' or row['tester']['status']!='passed' or row['reviewer']['decision']!='approved':
            raise FactoryError('独立前序没有有效Tester/Reviewer批准')
        folder=control/'sequence';cursor=load(folder/'state.json')
        if cursor['completed']:
            check_receipt(project,cursor['completed']['Goal 0'],'Goal 0')
            return cursor
        target=folder/'approved-goal0'
        if target.exists() or (folder/'goal0-completion.json').exists():
            raise FactoryError('前序导入存在不完整现场，禁止覆盖')
        pins={}
        for name,h in prior['files'].items():
            src=relative_file(name,source);dst=relative_file(name,target)
            dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
            if file_hash(dst)!=h:raise FactoryError('前序批准副本哈希错误')
            pins[dst.relative_to(project).as_posix()]=h
        for name,h in prior['candidate']['files'].items():
            dst=relative_file('workspace/'+name,target);dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(relative_file(name,workspace),dst)
            if file_hash(dst)!=h:raise FactoryError('前序源码快照哈希错误')
            pins[dst.relative_to(project).as_posix()]=h
        record={**prior,'files':pins,'source_approval':{'directory':str(source),
                'approval_sha256':file_hash(source/'stage-approval.json'),'receipt_sha256':entry['sha256']}}
        path=folder/'goal0-completion.json';save(path,record)
        local={'path':path.name,'sha256':file_hash(path)}
        check_receipt(project,local,'Goal 0')
        cursor['completed']['Goal 0']=local;cursor.update(current_goal='Goal 1',status='阶段完成',error=None)
        save(folder/'state.json',cursor);return cursor


class _IncrementalController(Controller):
    """Reuse the original single-task engine with a separate control directory."""
    def locate(self,project_id):
        project,_,workspace,_=super().locate(project_id)
        control=safe_path(project/'control/goals/goal-1',project/'control')
        state=load(control/'state.json')
        if state.get('project_id')!=project_id or state.get('status') not in STATES or state.get('sequence_goal')!='Goal 1':
            raise FactoryError('增量执行上下文身份无效')
        return project,control,workspace,state

    def verify(self,packet,coder,workspace,control,before):
        after=candidate(workspace)
        baseline=load(control/'increment-before.json')
        removed=set(baseline['files'])-set(after['files'])
        if removed:raise FactoryError('最小增量禁止删除前序源码：'+','.join(sorted(removed)))
        plan=load(control/'planner-result.json')
        writes=[n.rstrip('/*') for t in plan['tasks'] if t['goal_id']=='Goal 1' for n in t['write_set']]
        delta=[n for n,h in after['files'].items() if baseline['files'].get(n)!=h]
        if any(not any(n==w or n.startswith(w+'/') for w in writes) for n in delta):
            raise FactoryError('增量源码修改超出原Goal 1任务写集')
        return super().verify(packet,coder,workspace,control,before)


def stage_controller(c):
    stage=_IncrementalController(c.root,c.executor,c.full_access,c.codex_path)
    # Preserve an explicitly injected fixture, otherwise use the stage instance's
    # own method/executor (a resumed real controller may not have an executor yet).
    if 'runtime_check' in c.__dict__:stage.runtime_check=c.runtime_check
    if hasattr(c,'_quality_context'):stage._quality_context=c._quality_context
    if hasattr(c,'_run_caps'):stage._run_caps=c._run_caps
    return stage


def prepare_stage(c, project, control, workspace, original, spec, prior_entry):
    folder=safe_path(control/'goals/goal-1',control)
    if folder.exists():
        stage=stage_controller(c);state=stage.locate(project.name)[3]
        validate_packet(load(folder/'task-packet.json'),c.root,state)
        if not state['calls'] and candidate(workspace)!=load(folder/'increment-before.json'):
            raise FactoryError('已准备阶段派发前源码变化；不消费调用预算')
        return stage
    prior=check_receipt(project,prior_entry,'Goal 0')
    if candidate(workspace)!=prior['candidate']:raise FactoryError('进入下阶段前源码已变化')
    folder.mkdir(parents=True)
    for name in ('plan.md','goals.md','planner-result.json'):
        (folder/name).write_bytes((control/name).read_bytes())
    (folder/'goal-prompt.md').write_text(spec['prompt_md']+'\n',encoding='utf-8')
    save(folder/'goal-spec.json',spec);save(folder/'increment-before.json',prior['candidate'])
    state={k:copy.deepcopy(original[k]) for k in ('project_id','original_request','skill_hashes','created_at')}
    if 'coder_execution_intent' in original:
        state['coder_execution_intent']=original['coder_execution_intent']
    state.update(task_id='t-'+uuid.uuid4().hex,sequence_goal='Goal 1',
                 input_fingerprint=digest({'original':original['input_fingerprint'],'spec':digest(spec),'previous':prior_entry['sha256']}),
                 budget={**original['budget'],'max_agent_calls':1,'max_retries':0},
                 calls=[],retries=0,error=None,status='任务包已验证')
    packet=load(control/'task-packet.json')
    packet.update(format_version='1.1',goal='Goal 1',task_id=state['task_id'],
                  input_fingerprint=state['input_fingerprint'],budget=state['budget'],
                  prompt_path=str(folder/'goal-prompt.md'),
                  acceptance=[a for a in load(folder/'planner-result.json')['acceptance'] if a['goal_id']=='Goal 1'],
                  checks=spec['checks'],runtime=spec['runtime'],
                  artifacts={n:file_hash(folder/n) for n in ('plan.md','goals.md','planner-result.json','goal-prompt.md','goal-spec.json','increment-before.json')},
                  predecessor={**prior_entry,'candidate_fingerprint':prior['candidate']['fingerprint']})
    state['packet_fingerprint']=digest(packet);save(folder/'task-packet.json',packet);save(folder/'state.json',state)
    validate_packet(packet,c.root,state)
    save(folder/'packet-validation.json',{'passed':True,'packet_fingerprint':digest(packet),'version':'1.1'})
    return stage_controller(c)


def finish(c, project, control, workspace, goal, *, project_id=None):
    state=load(control/'state.json');quality=control/getattr(c,'_quality_context','quality');q=load(quality/'state.json')
    if state['status']!='质量门槛通过' or q['status']!='质量门槛通过':
        raise FactoryError('阶段未通过现有QualityGate')
    gate=QualityGate.__new__(QualityGate)
    gate.c=c;gate.control=control;gate.folder=quality;gate.workspace=workspace
    gate.state=state;gate.q=q;gate.packet=load(control/'task-packet.json');gate.load=load
    gate.guard();row=q['rounds'][-1]
    gate.result(row['tester'],'Tester',row);gate.result(row['reviewer'],'Reviewer',row)
    pins={control/n for n in ('state.json','task-packet.json','packet-validation.json','completion.json','coder-result.json')}
    pins.update(control/n for n in gate.packet['artifacts'])
    pins.update({gate.folder/'state.json',gate.folder/'completion.json'})
    if quality.name!='quality':
        pins.update(quality/n for n in ('source.json','previous-state.json','previous-quality-state.json'))
    if row.get('reviewer_derivation'):pins.add(relative_file(row['reviewer_derivation']['path'],gate.folder))
    for call in q['calls']:
        pins.update(p for p in relative_file(call['path'],gate.folder).iterdir() if p.is_file())
    root=relative_file(row['path'],gate.folder)
    if row.get('tester_derivation'):
        binding_path=relative_file(row['tester_derivation']['path'],gate.folder);pins.add(binding_path)
        binding=load(binding_path)
        pins.update(relative_file(binding[k]['path'],root) for k in ('execution','log','raw_result','proof'))
        if row.get('reviewer_execution'):pins.add(relative_file(row['reviewer_execution']['path'],gate.folder))
    context=row['context']
    for role in ('tester','reviewer'):
        for ac in row[role]['acceptance']:
            for e in ac['evidence']:pins.add(gate.evidence(e,root,source_inspection=role=='reviewer'))
    for check in row['tester']['checks']:
        for e in check['evidence']:pins.add(gate.evidence(e,root))
    for e in [*context['history'],*context['delivery'],*context['run_records'],*context['indices'],context['preflight'],
              {'path':context['manifest_path'],'sha256':context['manifest_sha256']}]:
        pins.add(relative_file(e['path'],root))
    identity=project_id or project.name
    if identity!=gate.packet['project_id']:raise FactoryError('阶段完成身份与TaskPacket不匹配')
    record={'project_id':identity,'goal':goal,'status':'质量门槛通过','candidate':candidate(workspace),
            'packet_fingerprint':digest(gate.packet),
            'files':{p.relative_to(project).as_posix():file_hash(p) for p in sorted(pins)},
            'scope':'single software Goal; internal quality result, not external APF acceptance'}
    path=project/'control/sequence'/('goal0-completion.json' if goal=='Goal 0' else 'goal1-completion.json')
    if path.exists():
        if load(path)!=record:raise FactoryError('已有阶段完成记录不同；禁止覆盖')
    else:save(path,record)
    return {'path':path.name,'sha256':file_hash(path)}


def run(c, project_id, through):
    if through not in ('Goal 0','Goal 1'):raise FactoryError('本增量只执行两个顺序阶段')
    project,control,workspace,original=c.locate(project_id)
    with locked(control):
        project,control,workspace,original=c.locate(project_id)
        folder=control/'sequence';cursor=load(folder/'state.json');config=load(folder/'config.json')
        spec=load(folder/'goal1-spec.json')
        if cursor['project_id']!=project_id or file_hash(folder/'config.json')!=cursor['config_sha256'] or config['spec_fingerprint']!=digest(spec):
            raise FactoryError('串行计划/批准内容变化')
        if config['goals']!=['Goal 0','Goal 1'] or config['retry'] or type(config['auto_repair']) is not bool or config['project_id']!=project_id:
            raise FactoryError('本次两阶段/无Retry/NoAutoRepair约束变化')
        if config['plan_sha256']!=file_hash(control/'planner-result.json') or config['goal0_packet_fingerprint']!=digest(load(control/'task-packet.json')):
            raise FactoryError('原规划/Goal 0任务包变化')
        validate_spec(spec,load(control/'planner-result.json'),workspace)
        for goal in config['goals']:
            if goal in cursor['completed']:
                receipt=check_receipt(project,cursor['completed'][goal],goal)
                if goal=='Goal 1' or through=='Goal 0':
                    if candidate(workspace)!=receipt['candidate']:raise FactoryError('当前已完成阶段源码变化')
            else:
                cursor['current_goal']=goal;save(folder/'state.json',cursor)
                stage=c if goal=='Goal 0' else prepare_stage(c,project,control,workspace,original,spec,cursor['completed']['Goal 0'])
                stage_control=control if goal=='Goal 0' else project/'control/goals/goal-1'
                state=load(stage_control/'state.json')
                if state['status']!='质量门槛通过':
                    state=stage.run(project_id,quality_gate=True,no_auto_repair=not config['auto_repair'],
                                    _lock_held=goal=='Goal 0',_sequence_active=True)
                    if goal=='Goal 0':c.executor=stage.executor
                if state['status']!='质量门槛通过':
                    cursor.update(status='停止',error=state.get('error') or state['status'])
                    save(folder/'state.json',cursor);return cursor
                if file_hash(folder/'config.json')!=cursor['config_sha256'] or digest(load(folder/'goal1-spec.json'))!=config['spec_fingerprint']:
                    raise FactoryError('阶段执行期间后续授权内容变化')
                cursor['completed'][goal]=finish(stage,project,stage_control,workspace,goal)
                cursor.update(status='阶段完成',error=None);save(folder/'state.json',cursor)
            if goal==through:break
        if len(cursor['completed'])==2:cursor['status']='两阶段已完成'
        save(folder/'state.json',cursor);return cursor

"""Goal 2 control logic: explicitly synthetic AgentDouble, never real E2E."""
import contextlib
import copy
import io
import json
import pathlib
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch
from factory.controller import Controller, ROOT, save, load
from factory.contracts import FactoryError, digest, file_hash
from factory.quality import candidate, QualityGate
from factory.quality_contracts import TESTER_SCHEMA, REVIEWER_SCHEMA, BUDGET
from factory.executor import CodexExecutor
from tests.test_factory import FlowDouble

RUN_ROOT=ROOT/'validation/goal2/test-workspaces'/uuid.uuid4().hex[:10]

class QualityDouble(FlowDouble):
    label='synthetic-quality-AgentDouble-not-real-Tester-Reviewer'
    def __init__(self,scenario='normal',full_access=False):
        super().__init__(full_access);self.scenario=scenario;self.quality_calls=[];self.checks_seen=[]
    def check(self,argv,cwd,control,index,timeout):
        pathlib.Path(control).mkdir(parents=True,exist_ok=True)
        (pathlib.Path(control)/f'check-{index}.log.jsonl').write_text('AgentDouble only: no business process\n',encoding='utf-8')
        self.checks_seen.append(list(argv))
        return {'exit_code':0,'timed_out':False,'elapsed_seconds':0.01}
    def preflight(self,*args):
        if self.scenario=='preflight' and self.quality_calls==[] and pathlib.Path(args[2]).name.startswith('preflight-'):
            raise FactoryError('AgentDouble environment EPERM')
        return {'passed':True,'test_double':True}
    def run(self,role,prompt,workspace,control,*args):
        if role=='Planner':
            result=super().run(role,prompt,workspace,control,*args)
            # Quality fixture is explicitly a non-UI API, so its positive paths
            # cannot accidentally teach the gate to approve UI without browser proof.
            result['output']['project_type']='本机数据处理API服务'
            result['output']['technology']='Node HTTP原生API服务与CLI测试夹具；仅模型控制测试，不是实际业务工程。'
            return result
        if role=='Coder' and not self.quality_calls:return super().run(role,prompt,workspace,control,*args)
        self.roles.append(role);self.quality_calls.append(role)
        if role=='Coder':
            if self.scenario!='noop':
                (workspace/'fixture.mjs').write_text('// targeted synthetic repair '+str(len(self.quality_calls)),encoding='utf-8')
            output={'status':'completed','summary':'AgentDouble targeted repair','files':['fixture.mjs'],
                    'tests':[{'command':'AgentDouble','exit_code':0,'result':'synthetic'}],'evidence':[],'limitations':[],'questions':[]}
            if self.scenario=='coder_fail':output['status']='failed'
            if self.scenario=='test_mutation':
                (workspace/'tests').mkdir(exist_ok=True);(workspace/'tests/assertion.py').write_text('pass')
        else:
            ctx=json.loads(prompt.splitlines()[-1]);snap=ctx['candidate'];packet=ctx['task_packet']
            evidence_dir=workspace/'.quality-evidence';evidence_dir.mkdir(exist_ok=True)
            f=evidence_dir/(role.lower()+'-synthetic.json');save(f,{'label':self.label,'role':role,'observed':snap['fingerprint']})
            e={'path':'workspace/.quality-evidence/'+f.name,'sha256':file_hash(f)}
            acs=[{'id':a['id'],'result':'passed','reason':'AgentDouble artificial assertion, not real evidence','evidence':[e]} for a in packet['acceptance']]
            issue={'id':'ISSUE-1','ac_ids':[acs[0]['id']],'category':'implementation','severity':'major',
                   'reproduce':['AgentDouble injected defect'],'expected':'correct synthetic value','actual':'wrong synthetic value','evidence':[e]}
            issues=[];limitations=[]
            tester_count=self.quality_calls.count('Tester');reviewer_count=self.quality_calls.count('Reviewer')
            if role=='Tester':
                status='passed'
                if self.scenario in {'tester_repair','noop','coder_fail','test_mutation'} and tester_count==1 or self.scenario=='limit':
                    status='failed';issues=[issue];acs[0]['result']='failed'
                if self.scenario in {'environment','ambiguity','test_defect','permission'}:
                    status='failed';issue['category']={'test_defect':'test'}.get(self.scenario,self.scenario);issues=[issue];acs[0]['result']='failed'
                checks=[{'kind':c['purpose'],'argv':c['argv'],'exit_code':0,'result':'passed','ac_ids':[a['id'] for a in acs],'evidence':[e]} for c in packet['checks']]
                checks.append({'kind':'runtime','argv':packet['runtime']['argv'],'exit_code':0,'result':'passed','ac_ids':[a['id'] for a in acs],'evidence':[e]})
                output={'candidate_fingerprint':snap['fingerprint'],'status':status,'acceptance':acs,'checks':checks,'issues':issues,'limitations':limitations}
                if self.scenario=='false_exit':checks[0]['exit_code']=1
                if self.scenario=='missing_build':output['checks']=checks[1:]
                if self.scenario=='unknown_approved':acs[0]['result']='unverified'
                if self.scenario=='source_mutation':(workspace/'fixture.mjs').write_text('Tester illegally changed source')
                if self.scenario=='wrong_fingerprint':output['candidate_fingerprint']='0'*64
                if self.scenario=='missing_ac':output['acceptance']=acs[1:]
                if self.scenario=='forged_hash':e['sha256']='0'*64
                if self.scenario=='traversal':e['path']='../outside.json'
                if self.scenario=='absolute':e['path']=str(f)
                if self.scenario=='source_evidence':e['path']='workspace/fixture.mjs';e['sha256']=file_hash(workspace/'fixture.mjs')
                if self.scenario=='missing_output':output=None
                if self.scenario=='illegal_output':output={'status':'passed'}
                if self.scenario=='interrupt':raise KeyboardInterrupt()
            else:
                decision='approved'
                if self.scenario=='reviewer_repair' and reviewer_count==1:decision='changes_requested';issues=[issue];acs[0]['result']='failed'
                if self.scenario=='reviewer_blocked':decision='blocked';acs[0]['result']='unverified';limitations=['synthetic evidence unavailable']
                output={'candidate_fingerprint':snap['fingerprint'],'decision':decision,'acceptance':acs,'issues':issues,'limitations':limitations,'summary':'AgentDouble review only'}
                if self.scenario=='reviewer_mutation':(workspace/'fixture.mjs').write_text('Reviewer illegal mutation')
                if self.scenario=='reviewer_illegal':output={'decision':'approved'}
                if self.scenario=='reviewer_old':output['candidate_fingerprint']='0'*64
            if role=='Tester' and self.scenario=='ui_no_browser':output['checks']=[c for c in output['checks'] if c['kind']!='browser']
        return {'exit_code':7 if self.scenario=='tester_exit' and role=='Tester' or self.scenario=='reviewer_exit' and role=='Reviewer' else 0,
                'timed_out':self.scenario=='timeout' and role=='Tester' or self.scenario=='reviewer_timeout' and role=='Reviewer','elapsed_seconds':.01,'turn_completed':True,
                'output':output,'usage':None,'thread_ids':['quality-double-'+uuid.uuid4().hex],
                'input_sha256':digest(prompt.encode()),
                'command_executions':[{'command':' '.join(c['argv']),'exit_code':0,'status':'completed','label':self.label}
                    for c in packet['checks']] if role=='Tester' else [{'command':'Get-Content fixture.mjs','exit_code':0,'status':'completed','label':self.label}] if role=='Reviewer' else []}

class QualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN_ROOT.mkdir(parents=True);shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')
    def setUp(self):
        self.agent=QualityDouble();self.c=Controller(RUN_ROOT,self.agent)
        self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        self.pid=self.c.create('Goal2 AgentDouble fixture, no real model',10)
    def run_gate(self,retry=False):
        with contextlib.redirect_stdout(io.StringIO()):return self.c.run(self.pid,retry=retry,quality_gate=True)
    def row(self):return load(self.c.locate(self.pid)[1]/'quality/state.json')
    def scenario(self,name):self.agent.scenario=name;return self.run_gate()
    def test_01_normal_independent_roles(self):
        self.assertEqual(self.run_gate()['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Reviewer']);self.assertEqual(len(self.row()['calls']),2)
        self.assertTrue(all(c['usage']=='unknown' for c in self.row()['calls']))
    def test_02_tester_defect_targeted_repair(self):
        self.assertEqual(self.scenario('tester_repair')['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Coder','Tester','Reviewer'])
        self.assertTrue(self.row()['repairs'][0]['valid_repair']);self.assertEqual(len(self.row()['rounds']),2)
    def test_03_reviewer_defect_repair(self):
        self.assertEqual(self.scenario('reviewer_repair')['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Reviewer','Coder','Tester','Reviewer'])
    def test_04_same_defect_and_round_limits(self):
        state=self.scenario('limit');self.assertEqual(state['status'],'质量门槛失败')
        q=self.row();self.assertEqual(len(q['repairs']),2);self.assertEqual(len(q['rounds']),3);self.assertEqual(self.agent.quality_calls.count('Coder'),2)
    def test_05_environment_not_coder(self):
        self.assertEqual(self.scenario('environment')['status'],'质量门槛失败');self.assertNotIn('Coder',self.agent.quality_calls)
    def test_06_ambiguity_waits(self):self.assertEqual(self.scenario('ambiguity')['status'],'等待用户确认')
    def test_07_test_defect_no_assertion_removal(self):
        self.assertEqual(self.scenario('test_defect')['status'],'质量门槛失败');self.assertNotIn('Coder',self.agent.quality_calls)
    def test_08_permission_waits(self):self.assertEqual(self.scenario('permission')['status'],'等待用户确认')
    def test_09_missing_output(self):self.assertEqual(self.scenario('missing_output')['status'],'质量门槛失败')
    def test_10_illegal_output(self):self.assertEqual(self.scenario('illegal_output')['status'],'质量门槛失败')
    def test_11_timeout(self):self.assertEqual(self.scenario('timeout')['status'],'质量门槛失败')
    def test_12_tester_nonzero_cannot_approve(self):self.assertEqual(self.scenario('tester_exit')['status'],'质量门槛失败')
    def test_13_reviewer_nonzero_cannot_approve(self):self.assertEqual(self.scenario('reviewer_exit')['status'],'质量门槛失败')
    def test_14_coder_failed_cannot_approve(self):self.assertEqual(self.scenario('coder_fail')['status'],'质量门槛失败')
    def test_15_source_change_invalidates_green(self):
        self.run_gate();roles=list(self.agent.roles);workspace=self.c.locate(self.pid)[2]
        (workspace/'fixture.mjs').write_text('externally changed candidate')
        self.assertEqual(self.run_gate()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,roles)
    def test_16_noop_is_not_effective_repair(self):
        self.assertEqual(self.scenario('noop')['status'],'质量门槛失败');self.assertFalse(self.row()['repairs'][0]['valid_repair'])
    def test_17_completed_recovery_no_calls(self):
        self.run_gate();before=list(self.agent.roles)
        self.assertEqual(self.run_gate()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,before)
    def test_18_interruption_persisted_requires_retry(self):
        self.assertEqual(self.scenario('interrupt')['status'],'质量门槛失败');calls=len(self.row()['calls'])
        self.assertEqual(self.run_gate()['status'],'质量门槛失败');self.assertEqual(len(self.row()['calls']),calls)
        self.agent.scenario='normal';self.assertEqual(self.run_gate(True)['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles.count('Planner'),1)
    def test_19_default_no_full_access(self):
        self.run_gate();self.assertFalse(self.agent.full_access)
    def test_20_budget_exhaustion_saved(self):
        self.run_gate();control=self.c.locate(self.pid)[1];q=self.row();q['status']='质量门槛失败';q['rounds'][-1]['reviewer']=None
        q['calls'][-1]['status']='failed'
        for i in range(3):q['calls'].append({'role':'Reviewer','status':'failed','key':'failed-'+str(i),'elapsed_seconds':.1})
        save(control/'quality/state.json',q)
        self.assertEqual(self.run_gate(True)['status'],'质量门槛失败');self.assertIn('预算',self.row()['error'])
    def test_21_traversal(self):self.assertEqual(self.scenario('traversal')['status'],'质量门槛失败')
    def test_22_absolute_evidence(self):self.assertEqual(self.scenario('absolute')['status'],'质量门槛失败')
    def test_23_forged_hash(self):self.assertEqual(self.scenario('forged_hash')['status'],'质量门槛失败')
    def test_24_source_is_not_test_evidence(self):self.assertEqual(self.scenario('source_evidence')['status'],'质量门槛失败')
    def test_25_packet_tampering_stops(self):
        self.run_gate();control=self.c.locate(self.pid)[1];packet=load(control/'task-packet.json');packet['goal']='Goal 1';save(control/'task-packet.json',packet)
        before=list(self.agent.roles)
        self.assertEqual(self.run_gate()['status'],'质量门槛失败')
        self.assertEqual(load(control/'state.json')['status'],'质量门槛失败');self.assertEqual(self.agent.roles,before)
    def test_26_tester_source_mutation(self):self.assertEqual(self.scenario('source_mutation')['status'],'质量门槛失败')
    def test_27_reviewer_readonly(self):self.assertEqual(self.scenario('reviewer_mutation')['status'],'质量门槛失败')
    def test_28_repair_test_mutation_rejected(self):self.assertEqual(self.scenario('test_mutation')['status'],'质量门槛失败')
    def test_29_wrong_candidate_binding(self):self.assertEqual(self.scenario('wrong_fingerprint')['status'],'质量门槛失败')
    def test_30_ac_coverage_required(self):self.assertEqual(self.scenario('missing_ac')['status'],'质量门槛失败')
    def test_31_nonzero_check_is_not_green(self):self.assertEqual(self.scenario('false_exit')['status'],'质量门槛失败')
    def test_32_unknown_cannot_approve(self):self.assertEqual(self.scenario('unknown_approved')['status'],'质量门槛失败')
    def test_33_mandatory_build_test(self):self.assertEqual(self.scenario('missing_build')['status'],'质量门槛失败')
    def test_34_preflight_no_quality_budget_charge(self):
        self.assertEqual(self.scenario('preflight')['status'],'质量门槛失败');self.assertEqual(self.row()['calls'],[])
    def test_35_evidence_tamper_invalidates_reuse(self):
        self.run_gate();control=self.c.locate(self.pid)[1];q=self.row();e=q['rounds'][0]['tester']['acceptance'][0]['evidence'][0]
        (control/'quality'/q['rounds'][0]['path']/e['path']).write_text('tampered')
        roles=list(self.agent.roles);self.assertEqual(self.run_gate()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,roles)
    def test_36_generated_artifacts_do_not_change_candidate(self):
        workspace=self.c.locate(self.pid)[2];before=candidate(workspace)
        for directory in ('dist','var','validation','.factory-tmp'):
            (workspace/directory).mkdir();(workspace/directory/'artifact.txt').write_text('volatile')
        self.assertEqual(candidate(workspace),before)
        (workspace/'test_config.json').write_text('{}');self.assertNotEqual(candidate(workspace),before)
    def test_37_credentials_refused_in_candidate(self):
        workspace=self.c.locate(self.pid)[2];(workspace/'.env').write_text('synthetic forbidden credential file')
        with self.assertRaises(FactoryError):candidate(workspace)
    def test_38_real_adapter_tester_reviewer_permissions(self):
        executor=CodexExecutor.__new__(CodexExecutor);executor.exe='fixture.exe';executor.version='fixture';executor.model=None
        folder=self.c.locate(self.pid)[1]
        for full in (False,True):
            executor.full_access=full
            for role in ('Tester','Reviewer'):
                with patch('factory.executor.bounded',return_value={'exit_code':0,'timed_out':False,'elapsed_seconds':0}) as call:
                    executor.run(role,'AgentDouble argv only',folder,folder,1,{},10)
                argv=call.call_args.args[0];self.assertEqual(argv[argv.index('-s')+1],'read-only' if role=='Reviewer' else 'danger-full-access' if full else 'workspace-write')
    def test_39_cli_quality_gate_switch(self):
        from factory.controller import main
        with patch('factory.controller.Controller',return_value=self.c),contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--request','Goal2 CLI AgentDouble','--quality-gate']),0)
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Reviewer'])
    def test_40_plan_checkcli_reject_qualitygate(self):
        from factory.controller import main
        with patch('factory.controller.resolve_codex') as cli,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--check-cli','--quality-gate']),1);cli.assert_not_called()
            self.assertEqual(main(['--request','fixture','--mode','Plan','--quality-gate']),1)
    def test_41_reviewer_blocked(self):self.assertEqual(self.scenario('reviewer_blocked')['status'],'质量门槛失败')
    def test_42_junction_escape_rejected(self):
        workspace=self.c.locate(self.pid)[2];target=RUN_ROOT/('junction-target-'+uuid.uuid4().hex);target.mkdir()
        if sys.platform=='win32':
            import _winapi
            _winapi.CreateJunction(str(target),str(workspace/'linked'))
        else:(workspace/'linked').symlink_to(target,target_is_directory=True)
        with self.assertRaises(FactoryError):candidate(workspace)
    def test_43_running_process_not_restarted(self):
        self.run_gate();control=self.c.locate(self.pid)[1];q=self.row();rec=q['calls'][-1];rec['status']='running';q['status']='Reviewer审查中'
        save(control/'quality/state.json',q)
        folder=control/'quality'/rec['path'];save(folder/f'reviewer-{rec["number"]:02d}.process.json',{'pid':12345,'creation':'same'})
        roles=list(self.agent.roles)
        with patch('factory.quality.process_identity',return_value={'live':True,'creation':'same'}):
            self.assertEqual(self.run_gate(True)['status'],'质量门槛失败')
        self.assertEqual(self.agent.roles,roles);self.assertEqual(self.row()['calls'][-1]['status'],'running')
    def test_44_completed_step_recovered_without_double_charge(self):
        self.run_gate();control=self.c.locate(self.pid)[1];q=self.row();q['rounds'][0]['reviewer']=None;q['status']='Reviewer审查中'
        save(control/'quality/state.json',q);roles=list(self.agent.roles);calls=len(q['calls'])
        self.assertEqual(self.run_gate()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,roles);self.assertEqual(len(self.row()['calls']),calls)
    def test_45_completed_repair_checkpoint_recovery(self):
        original=QualityGate.make_round
        def interrupt_before_second(gate):
            if gate.q['rounds']:raise KeyboardInterrupt()
            return original(gate)
        with patch.object(QualityGate,'make_round',interrupt_before_second):self.scenario('tester_repair')
        control=self.c.locate(self.pid)[1];q=self.row();repair=q['repairs'][0]
        # Simulate loss after durable Coder result but before repair registration.
        q['rounds']=q['rounds'][:1];q['calls']=q['calls'][:2];q['repairs']=[];q['status']='Coder返工中'
        defect=load(control/'quality'/repair['defect_path'])
        q['pending_repair']={'before':repair['before'],'defect':defect,'path':repair['defect_path'],'tests':{},'keys':[],'call_count_before':1}
        save(control/'quality/state.json',q);coders=self.agent.roles.count('Coder')
        self.agent.scenario='normal';self.assertEqual(self.run_gate()['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles.count('Coder'),coders);self.assertTrue(self.row()['repairs'][0]['recovered_finished_call'])
    def test_46_dead_process_is_interrupted_not_completed(self):
        self.run_gate();control=self.c.locate(self.pid)[1];q=self.row();rec=q['calls'][-1];rec['status']='running';q['status']='Reviewer审查中'
        rec['path']='calls/interrupted-no-result'
        save(control/'quality/state.json',q)
        self.assertEqual(self.run_gate()['status'],'质量门槛失败');self.assertEqual(self.row()['calls'][-1]['status'],'interrupted')
    def test_47_reviewer_illegal_output(self):self.assertEqual(self.scenario('reviewer_illegal')['status'],'质量门槛失败')
    def test_48_reviewer_timeout(self):self.assertEqual(self.scenario('reviewer_timeout')['status'],'质量门槛失败')
    def test_49_old_reviewer_candidate_rejected(self):self.assertEqual(self.scenario('reviewer_old')['status'],'质量门槛失败')
    def test_50_ui_requires_browser_not_http(self):
        from tests.test_factory import fixture_plan
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid,'Plan')
        project,control,workspace,state=self.c.locate(self.pid);plan=load(control/'planner-result.json')
        plan['acceptance'][0]['method']='真实浏览器 Playwright 截图'
        with contextlib.redirect_stdout(io.StringIO()):self.c.packet(plan,state,workspace,control)
        self.assertEqual(self.scenario('ui_no_browser')['status'],'质量门槛失败');self.assertNotIn('Reviewer',self.agent.roles)
    def test_51_claim_without_tool_execution_rejected(self):
        original=self.agent.run
        def fake(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='Tester':result['command_executions']=[]
            return result
        self.agent.run=fake;self.assertEqual(self.run_gate()['status'],'质量门槛失败')
    def test_52_input_hash_mismatch_rejected(self):
        original=self.agent.run
        def fake(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='Tester':result['input_sha256']='0'*64
            return result
        self.agent.run=fake;self.assertEqual(self.run_gate()['status'],'质量门槛失败')
    def test_53_no_auto_repair_cannot_dispatch_coder(self):
        self.agent.scenario='tester_repair'
        with contextlib.redirect_stdout(io.StringIO()):
            result=self.c.run(self.pid,quality_gate=True,no_auto_repair=True)
        self.assertEqual(result['status'],'质量门槛失败');self.assertNotIn('Coder',self.agent.quality_calls)
    def test_54_live_local_process_identity(self):
        from factory.executor import bounded,process_identity
        folder=self.c.locate(self.pid)[1];script=folder/'trusted-sleep.py';script.write_text('import time\ntime.sleep(10)\n')
        observed=[]
        def event(kind,line):
            if kind=='process_started':observed.append((int(line),process_identity(int(line))))
        result=bounded([sys.executable,str(script)],folder,.3,callback=event)
        self.assertTrue(result['timed_out']);self.assertTrue(observed[0][1]['live'])
        self.assertFalse(process_identity(observed[0][0])['live'])
    def test_55_terminal_final_checkpoint_not_recalled(self):
        self.run_gate();control=self.c.locate(self.pid)[1];q=self.row();q['calls'][-1]['status']='running';q['status']='Reviewer审查中';q['rounds'][0]['reviewer']=None
        save(control/'quality/state.json',q);roles=list(self.agent.roles)
        self.assertEqual(self.run_gate()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,roles)
        self.assertTrue(self.row()['calls'][-1]['recovered_final_checkpoint'])
    def test_56_frozen_factory_change_stops(self):
        frozen=RUN_ROOT/'README.md';frozen.write_text('synthetic protected file')
        original=self.agent.run
        def mutate(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='Tester':frozen.write_text('synthetic unauthorized change')
            return result
        self.agent.run=mutate;self.assertEqual(self.run_gate()['status'],'质量门槛失败')
        self.assertIn('冻结文件',self.row()['error']);self.assertNotIn('Reviewer',self.agent.roles)
    def test_57_reference_guard_failure_stops_without_agent(self):
        # Same reference during base stage and initialization, then injected drift.
        with patch('factory.quality.reference_snapshot',side_effect=[None,None,{'synthetic':'before'},{'synthetic':'after'}]):
            self.assertEqual(self.run_gate()['status'],'质量门槛失败')
        self.assertEqual(self.agent.quality_calls,[]);self.assertIn('参考项目',self.row()['error'])
    def test_58_independent_thread_required(self):
        original=self.agent.run
        def reused(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='Tester':result['thread_ids']=['test-double-Coder']
            return result
        self.agent.run=reused;self.assertEqual(self.run_gate()['status'],'质量门槛失败')
    def test_59_real_owned_worker_stage_deadline(self):
        from factory.executor import bounded
        folder=self.c.locate(self.pid)[1];script=folder/'trusted-stage-deadline.py'
        script.write_text('import sys,time\nfrom pathlib import Path\nsys.path.insert(0,'+repr(str(ROOT))+')\nfrom factory.quality import stage_deadline\nwith stage_deadline(Path('+repr(str(folder))+'),seconds=.3):\n time.sleep(10)\n',encoding='utf-8')
        result=bounded([sys.executable,'-B',str(script)],folder,5)
        self.assertNotEqual(result['exit_code'],0);self.assertFalse(result['timed_out'])
        markers=list(folder.glob('quality-stage-timeout-*.json'));self.assertEqual(len(markers),1)
        self.assertEqual(load(markers[0])['status'],'质量门槛失败')
    def test_60_stage_timeout_marker_never_approved(self):
        self.run_gate();control=self.c.locate(self.pid)[1];save(control/'quality-stage-timeout-synthetic.json',{'status':'质量门槛失败','label':'AgentDouble'})
        self.assertEqual(self.c.locate(self.pid)[3]['status'],'质量门槛失败')
        roles=list(self.agent.roles);self.assertEqual(self.run_gate()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,roles)
    def test_61_project_type_ui_cannot_hide_missing_browser(self):
        original=self.agent.run
        def ui_type(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='Planner':result['output']['project_type']='Windows Web UI DEMO'
            return result
        self.agent.run=ui_type;self.assertEqual(self.run_gate()['status'],'质量门槛失败');self.assertNotIn('Reviewer',self.agent.roles)
    def test_62_reviewer_self_report_without_source_inspection_rejected(self):
        original=self.agent.run
        def no_read(*a,**kw):
            result=original(*a,**kw)
            if a[0]=='Reviewer':result['command_executions']=[]
            return result
        self.agent.run=no_read;self.assertEqual(self.run_gate()['status'],'质量门槛失败')

if __name__=='__main__':unittest.main()

"""Deterministic exception tests use explicitly labelled agent doubles.
They are not evidence of real Planner/Coder execution or real E2E success.
"""
import contextlib
import io
import json
import shutil
import sys
import time
import unittest
import uuid
from pathlib import Path
from factory.contracts import FactoryError,SKILLS,validate_packet,validate_plan,digest,command_check
from factory.controller import Controller,ROOT,save,load,manifest,locked
from factory.executor import bounded,redact,clean_env,CodexExecutor,resolve_codex

RUN_ROOT=ROOT/'validation/goal1/test-workspaces'/uuid.uuid4().hex[:10]

def fixture_plan(workspace):
    # Deliberately artificial contract fixture, never production Planner logic.
    acceptance=[{'id':f'AC-{i:02}','requirement_id':f'R-{i:02}','goal_id':'Goal 0','task_id':'T-0',
                 'criterion':'前置条件明确，执行动作后验证可观察的完整结果。','method':'deterministic fixture'} for i in range(8)]
    acceptance.append({'id':'AC-10','requirement_id':'R-10','goal_id':'Goal 1','task_id':'T-1','criterion':'后续业务行为验证可观察结果并检查异常状态。','method':'future'})
    return {'project_name':'测试夹具','project_type':'离线演示','technology':'Node 与纯静态页面测试夹具，不是实际项目规划或执行证据。',
            'skills_used':SKILLS,'plan_md':'测试夹具完整性内容。'*100,'goals_md':'阶段定义仅用于异常测试。'*30,
            'blueprint_md':'工程方案夹具仅用于异常测试。'*120,
            'prompt_md':str(workspace)+'\nGoal 0 禁止 验收 测试 停止 报告 '+ ' '.join(a['id'] for a in acceptance)+'\n'+'测试夹具约束仅供机器异常验证。'*200,
            'goals':[{'id':'Goal 0','title':'基础','depends_on':[],'scope':'骨架'}, {'id':'Goal 1','title':'业务','depends_on':['Goal 0'],'scope':'后续'}],
            'tasks':[{'id':'T-0','goal_id':'Goal 0','depends_on':[],'write_set':['src/'],'acceptance_ids':[a['id'] for a in acceptance[:-1]]},
                     {'id':'T-1','goal_id':'Goal 1','depends_on':['T-0'],'write_set':['src/business/'],'acceptance_ids':['AC-10']}],
            'acceptance':acceptance,'blocking_questions':[],'risks':[],
            'checks':[{'purpose':'build','argv':['node','scripts/build.mjs']},{'purpose':'test','argv':['node','scripts/test.mjs']}],
            'runtime':{'argv':['node','scripts/serve.mjs','{port}'],'path':'/','expected_text':'fixture'}}

class AgentDouble:
    label='deterministic-test-double-not-real-agent'
    def __init__(self,planner='good',coder='fail'):
        self.planner,self.coder=planner,coder; self.roles=[]
    def probe(self,*args):
        return {'test_double':True,'passed':True}
    def preflight(self,*args):
        return {'test_double':True,'passed':True}
    def run(self,role,prompt,workspace,control,*args):
        self.roles.append(role)
        if role=='Planner':
            output=fixture_plan(workspace)
            if self.planner=='incomplete':
                output['prompt_md']='bad'
            if self.planner=='question':
                output['blocking_questions']=['生产数据访问授权未确认']
        else:
            output={'status':'failed','summary':'explicit double failure','files':[],'tests':[],'evidence':[],'limitations':[],'questions':[]}
        return {'exit_code':7 if role=='Coder' and self.coder=='fail' else 0,'timed_out':role=='Coder' and self.coder=='timeout',
                'elapsed_seconds':.01,'turn_completed':True,'output':output,'usage':None,'thread_ids':['test-double-'+role]}

class FlowDouble(AgentDouble):
    """Successful CONTROL-flow fixture; no model/business/browser execution."""
    def __init__(self,full_access=False):
        super().__init__();self.full_access=full_access;self.steps=[]
    def probe(self,*args):
        self.steps.append('policy-probe-double')
        return {'test_double':True,'os_write_boundary_enforced':not self.full_access}
    def preflight(self,packet,workspace,control):
        validate_packet(packet,control.parents[2],load(control/'state.json'))
        self.steps.append('validated-packet-preflight-double')
        return {'test_double':True,'passed':True}
    def run(self,role,prompt,workspace,control,*args):
        self.steps.append(role+'-double')
        if role=='Planner':return super().run(role,prompt,workspace,control,*args)
        validate_packet(load(control/'task-packet.json'),control.parents[2],load(control/'state.json'))
        self.roles.append(role)
        (workspace/'fixture.mjs').write_text('// AgentDouble control fixture, not business implementation\n',encoding='utf-8')
        output={'status':'completed','summary':'Explicit AgentDouble; control flow only','files':['fixture.mjs'],
                'tests':[{'command':'AgentDouble self-test fixture','exit_code':0,'result':'not a real test'}],
                'evidence':[],'limitations':['No real Agent, build or browser execution'],'questions':[]}
        return {'exit_code':0,'timed_out':False,'elapsed_seconds':0,'turn_completed':True,'output':output,'usage':None,'thread_ids':['test-double-Coder']}
    def check(self,*args):
        self.steps.append('check-double');return {'exit_code':0,'timed_out':False,'elapsed_seconds':0,'test_double':True}

class FactoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN_ROOT.mkdir(parents=True)
        shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')
    def setUp(self):
        self.root=RUN_ROOT/self._testMethodName
        self.root.mkdir(parents=True)
        self.agent=AgentDouble(); self.controller=Controller(RUN_ROOT,self.agent)
    def task(self):
        return self.controller.create('测试输入，不是实际 Agent E2E',10)
    def execute(self,*args,**kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.controller.run(*args,**kwargs)
    def plan(self):
        pid=self.task(); state=self.execute(pid,'Plan')
        self.assertEqual(state['status'],'任务包已验证'); self.assertEqual(self.agent.roles,['Planner'])
        return pid,*self.controller.locate(pid)
    def test_blank_request_rejected(self):
        with self.assertRaises(FactoryError): self.controller.create(' \n\t')
        self.assertEqual(self.agent.roles,[])
    def test_invalid_packet_no_coder(self):
        pid,project,control,workspace,state=self.plan()
        packet=load(control/'task-packet.json'); del packet['goal']; save(control/'task-packet.json',packet)
        self.assertEqual(self.execute(pid)['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_invalid_packet_type_no_coder(self):
        pid,project,control,workspace,state=self.plan()
        packet=load(control/'task-packet.json'); packet['workspace']=[]; save(control/'task-packet.json',packet)
        self.assertEqual(self.execute(pid)['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_unsafe_workdir_no_coder(self):
        pid,project,control,workspace,state=self.plan()
        packet=load(control/'task-packet.json'); packet['workspace']=str(workspace/'..'/'..'/'escape')
        save(control/'task-packet.json',packet)
        self.assertEqual(self.execute(pid)['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_external_absolute_workdir_no_coder(self):
        pid,project,control,workspace,state=self.plan()
        packet=load(control/'task-packet.json'); packet['workspace']='C:\\910Program'
        save(control/'task-packet.json',packet)
        self.assertEqual(self.execute(pid)['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_coder_failure_persisted(self):
        pid=self.task(); state=self.execute(pid)
        self.assertEqual(state['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner','Coder'])
        saved=self.controller.locate(pid)[3]
        self.assertEqual(saved['calls'][-1]['exit_code'],7); self.assertIn('Coder',saved['error'])
    def test_coder_timeout_persisted(self):
        self.agent.coder='timeout'; pid=self.task(); state=self.execute(pid)
        self.assertEqual(state['status'],'已失败'); self.assertIn('超时',state['error'])
        self.assertTrue(self.controller.locate(pid)[3]['calls'][-1]['timed_out'])
    def test_coder_reported_failure_is_not_success(self):
        from unittest.mock import patch
        self.agent.coder='reported_failure'; pid=self.task()
        with patch.object(self.controller,'diagnose',return_value={'test_double':True}) as diagnosis:
            state=self.execute(pid)
        self.assertEqual(state['status'],'已失败'); self.assertIn('未完成',state['error'])
        self.assertEqual(self.agent.roles,['Planner','Coder']); diagnosis.assert_called_once()
    def test_process_timeout_really_stops_child(self):
        script=self.root/'sleep.py'; script.write_text('import time\ntime.sleep(30)\n',encoding='utf-8')
        result=bounded([sys.executable,str(script)],self.root,.25,log=self.root/'timeout.log.jsonl')
        self.assertTrue(result['timed_out']); self.assertIsNotNone(result['exit_code']); self.assertLess(result['elapsed_seconds'],10)
    def test_incomplete_planner_no_coder(self):
        self.agent.planner='incomplete'; state=self.execute(self.task())
        self.assertEqual(state['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_major_question_no_coder(self):
        self.agent.planner='question'; state=self.execute(self.task())
        self.assertEqual(state['status'],'等待用户确认'); self.assertEqual(self.agent.roles,['Planner'])
    def test_completed_task_no_agent_calls(self):
        pid,project,control,workspace,state=self.plan()
        save(control/'completion.json',{'packet_fingerprint':state['packet_fingerprint'],'workspace_manifest':manifest(workspace)})
        state['status']='已完成'; save(control/'state.json',state)
        self.assertEqual(self.execute(pid)['status'],'已完成'); self.assertEqual(self.agent.roles,['Planner'])
    def test_changed_completed_files_invalidates_success(self):
        pid,project,control,workspace,state=self.plan()
        save(control/'completion.json',{'packet_fingerprint':state['packet_fingerprint'],'workspace_manifest':manifest(workspace)})
        state['status']='已完成'; save(control/'state.json',state); (workspace/'new.txt').write_text('changed')
        self.assertEqual(self.execute(pid)['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_interruption_never_success(self):
        pid,project,control,workspace,state=self.plan()
        state['status']='Coder执行中'; state['calls'].append({'role':'Coder','status':'running'}); save(control/'state.json',state)
        result=self.execute(pid)
        self.assertEqual(result['status'],'已失败'); self.assertEqual(result['calls'][-1]['status'],'interrupted')
        self.assertEqual(self.agent.roles,['Planner'])
    def test_resume_reuses_planner(self):
        pid=self.task(); self.execute(pid)
        result=self.execute(pid,retry=True)
        self.assertEqual(self.agent.roles,['Planner','Coder','Coder']); self.assertEqual(result['status'],'已失败')
    def test_retry_limit_stops(self):
        pid=self.task(); self.execute(pid); self.execute(pid,retry=True); result=self.execute(pid,retry=True)
        self.assertEqual(len(self.agent.roles),3); self.assertIn('预算',result['error'])
    def test_environment_failure_preserves_retry_and_planning(self):
        pid=self.task(); self.execute(pid)
        project,control,workspace,state=self.controller.locate(pid)
        preserved={p.name:p.read_bytes() for p in control.iterdir()
                   if p.name in ('task-packet.json','planner-result.json','goal0-prompt.md')
                   or p.name.startswith(('sandbox-verification','sandbox-probe'))}
        old_calls=list(state['calls']); old_retries=state['retries']
        def blocked(*args):
            raise FactoryError('隔离环境预检失败：injected EPERM, not a real sandbox result')
        self.agent.preflight=blocked
        result=self.execute(pid,retry=True)
        self.assertEqual(result['status'],'已失败')
        self.assertEqual(result['calls'],old_calls); self.assertEqual(result['retries'],old_retries)
        self.assertEqual(self.agent.roles,['Planner','Coder'])
        self.assertIn('预检失败',result['error'])
        for name,data in preserved.items():
            self.assertEqual((control/name).read_bytes(),data)
    def test_plan_mode_does_not_call_coder(self):
        self.plan()
    def test_dependency_cycle_rejected(self):
        plan=fixture_plan(self.root); plan['goals'][0]['depends_on']=['Goal 1']
        with self.assertRaises(FactoryError): validate_plan(plan,self.root)
    def test_artifact_tamper_rejected(self):
        pid,project,control,workspace,state=self.plan(); (control/'goal0-prompt.md').write_text('tampered')
        self.assertEqual(self.execute(pid)['status'],'已失败'); self.assertEqual(self.agent.roles,['Planner'])
    def test_ids_cannot_construct_path(self):
        for value in ('../910Program','p-abc; cmd','p-123456789abc/..'):
            with self.assertRaises(FactoryError): self.controller.locate(value)
    def test_logs_redact_credentials(self):
        private='-----BEGIN PRIVATE KEY-----\nsecret-private-body\n-----END PRIVATE KEY-----'
        text='sk-test_secret_123456 Bearer abc.token.value access_token=private-value '+private
        script=self.root/'secret_fixture.py'; script.write_text('print('+repr(text)+')',encoding='utf-8')
        log=self.root/'secret-fixture.log.jsonl'; result=bounded([sys.executable,str(script)],self.root,10,log=log)
        for secret in ('sk-test_secret_123456','abc.token.value','private-value','secret-private-body'):
            self.assertNotIn(secret,log.read_text(encoding='utf-8')); self.assertNotIn(secret,result['stdout'])
        self.assertNotIn('secret-private-body',redact(text))
        self.assertNotIn('private-value',redact('{"access_token":"private-value"}'))
    def test_request_with_secret_rejected(self):
        with self.assertRaises(FactoryError): self.controller.create('API key sk-testsecret012345')
    def test_child_env_excludes_desktop_context_and_secrets(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{'CODEX_PERMISSION_PROFILE':'disabled','CODEX_THREAD_ID':'parent','OPENAI_API_KEY':'test-secret','SAFE_FACTORY_TEST':'kept'}):
            env=clean_env(self.root)
        self.assertNotIn('CODEX_PERMISSION_PROFILE',env); self.assertNotIn('CODEX_THREAD_ID',env)
        self.assertNotIn('OPENAI_API_KEY',env); self.assertEqual(env['SAFE_FACTORY_TEST'],'kept')
    def test_shell_commands_not_accepted(self):
        for argv in (['powershell','-Command','echo bad'],['node','../outside.mjs'],['python','-c','print(1)'],['npm','install','package']):
            with self.assertRaises(FactoryError): command_check(argv)
    def test_concurrent_controller_lock(self):
        pid=self.task(); control=self.controller.locate(pid)[1]
        with locked(control):
            with self.assertRaises(FactoryError):
                with locked(control): pass
    def test_reopening_lock_preserves_existing_bytes(self):
        pid=self.task();control=self.controller.locate(pid)[1]
        # Keep legacy lock contents too; no truncation or forced restoration.
        (control/'controller.lock').write_bytes(b'000')
        with locked(control):
            self.assertEqual((control/'controller.lock').stat().st_size,3)
        with locked(control):
            pass
        self.assertEqual((control/'controller.lock').read_bytes(),b'000')
    def test_full_access_command_is_explicit_and_boundary_truthful(self):
        from unittest.mock import patch
        executor=CodexExecutor.__new__(CodexExecutor); executor.exe='codex.exe'
        with patch('factory.executor.shutil.which',return_value='C:/node.exe'):
            executor.full_access=False
            self.assertIn(':workspace',executor.sandbox_argv(['node','scripts/test.mjs'],self.root))
            executor.full_access=True
            self.assertEqual(executor.sandbox_argv(['node','scripts/test.mjs'],self.root),['C:/node.exe','scripts/test.mjs'])
        before=list(self.root.iterdir()); probe=executor.probe(self.root,self.root)
        self.assertFalse(probe['os_write_boundary_enforced'])
        self.assertFalse(probe['outside_write_denial_test_run'])
        self.assertNotIn('passed',probe);self.assertEqual(before,list(self.root.iterdir()))
    def test_full_access_rejects_plan_mode(self):
        self.agent.full_access=True
        state=self.execute(self.task(),'Plan')
        self.assertEqual(state['status'],'已失败'); self.assertEqual(self.agent.roles,[])
        self.assertIn('Auto',state['error'])
    def test_retry_archives_old_evidence_before_preflight_failure(self):
        pid,project,control,workspace,state=self.plan()
        (control/'coder-result.json').write_text('previous coder evidence',encoding='utf-8')
        state['status']='已失败'; save(control/'state.json',state)
        def fail(*args):raise FactoryError('fixed failing preflight')
        self.agent.preflight=fail
        result=self.execute(pid,retry=True)
        backups=list((control/'attempts').glob('*/before/coder-result.json'))
        self.assertEqual(len(backups),1);self.assertEqual(backups[0].read_text(encoding='utf-8'),'previous coder evidence')
        self.assertEqual((control/'coder-result.json').read_text(encoding='utf-8'),'previous coder evidence')
        self.assertEqual(result['retries'],0);self.assertEqual(self.agent.roles,['Planner'])
    def test_retry_existing_source_change_reaches_real_checks(self):
        pid,project,control,workspace,state=self.plan()
        (workspace/'app.mjs').write_text('original',encoding='utf-8');before=manifest(workspace)
        (workspace/'app.mjs').write_text('fixed',encoding='utf-8')
        seen=[]
        def check(*args):seen.append(args);raise FactoryError('expected independent check stop')
        self.agent.check=check
        coder={'status':'completed','files':['app.mjs'],'tests':[{'exit_code':0}],'evidence':[]}
        with self.assertRaisesRegex(FactoryError,'independent check stop'):
            self.controller.verify(load(control/'task-packet.json'),coder,workspace,control,before)
        self.assertEqual(len(seen),1)
        self.assertEqual(load(control/'coder-file-provenance.json')['changed'],['app.mjs'])
    def full_flow_fixture(self,full_access):
        agent=FlowDouble(full_access);self.controller.executor=agent
        self.controller.full_access=full_access
        self.controller.runtime_check=lambda *a:{'passed':True,'test_double':True,'scope':'No HTTP/browser execution'}
        return agent
    def test_new_full_access_request_planner_packet_coder_control_flow(self):
        agent=self.full_flow_fixture(True);pid=self.task();state=self.execute(pid)
        self.assertEqual(state['status'],'已完成');self.assertEqual(agent.roles,['Planner','Coder'])
        self.assertLess(agent.steps.index('Planner-double'),agent.steps.index('validated-packet-preflight-double'))
        self.assertLess(agent.steps.index('validated-packet-preflight-double'),agent.steps.index('Coder-double'))
        self.assertEqual(state['retries'],0);self.assertEqual(len(state['calls']),2)
        project,control,workspace,state=self.controller.locate(pid)
        validate_packet(load(control/'task-packet.json'),RUN_ROOT,state)
        self.assertEqual(load(control/'handoff-02.json')['packet_sha256'],state['packet_fingerprint'])
        self.assertFalse(state['os_write_boundary_enforced']);self.assertEqual(state['execution_mode'],'danger-full-access')
        self.assertTrue(workspace.is_relative_to(RUN_ROOT/'projects'/pid))
    def test_new_full_access_preflight_failure_does_not_call_coder(self):
        agent=self.full_flow_fixture(True)
        def fail(*a):raise FactoryError('explicit test-double preflight failure')
        agent.preflight=fail;state=self.execute(self.task())
        self.assertEqual(state['status'],'已失败');self.assertEqual(agent.roles,['Planner'])
        self.assertEqual(state['retries'],0);self.assertEqual(len(state['calls']),1)
    def test_default_new_request_does_not_enable_full_access(self):
        agent=self.full_flow_fixture(False);state=self.execute(self.task())
        self.assertEqual(state['status'],'已完成');self.assertFalse(agent.full_access)
        self.assertNotIn('danger-full-access',state.get('execution_mode',''))
        self.assertEqual(agent.roles,['Planner','Coder'])
    def test_cli_main_new_full_access_request_is_explicit(self):
        from unittest.mock import patch
        from factory.controller import main
        agent=self.full_flow_fixture(True)
        with patch('factory.controller.Controller',return_value=self.controller) as ctor,contextlib.redirect_stdout(io.StringIO()) as output:
            code=main(['--request','开发一个离线图书管理 Demo','--mode','Auto','--full-access','--codex-path','C:/explicit/codex.exe'])
        self.assertEqual(code,0);self.assertEqual(agent.roles,['Planner','Coder'])
        ctor.assert_called_once_with(full_access=True,codex_path='C:/explicit/codex.exe')
        self.assertIn('工作目录不是OS隔离',output.getvalue())
    def test_cli_main_default_does_not_enable_full_access(self):
        from unittest.mock import patch
        from factory.controller import main
        agent=self.full_flow_fixture(False)
        with patch('factory.controller.Controller',return_value=self.controller) as ctor,contextlib.redirect_stdout(io.StringIO()):
            code=main(['--request','fixture default request'])
        self.assertEqual(code,0);ctor.assert_called_once_with(full_access=False,codex_path=None)
    def test_actual_adapter_role_modes_remain_explicit(self):
        from unittest.mock import patch
        executor=CodexExecutor.__new__(CodexExecutor);executor.exe='C:/fixture/codex.exe';executor.model=None;executor.version='fixture-only'
        for full in (False,True):
            executor.full_access=full
            for role in ('Planner','Reviewer','Coder'):
                with patch('factory.executor.bounded',return_value={'exit_code':0,'timed_out':False,'elapsed_seconds':0}) as call:
                    executor.run(role,'fixture',self.root,self.root,1,{},10)
                argv=call.call_args.args[0];mode=argv[argv.index('-s')+1]
                self.assertEqual(mode,'read-only' if role in ('Planner','Reviewer') else ('danger-full-access' if full else 'workspace-write'))
    def test_plan_records_future_full_access_without_granting_it(self):
        agent=self.full_flow_fixture(False);prompts=[]
        original=agent.run
        def capture(role,prompt,*args):
            prompts.append(prompt);return original(role,prompt,*args)
        agent.run=capture
        pid=self.controller.create('Permission AgentDouble only',10,coder_execution_intent='danger-full-access')
        state=self.execute(pid,'Plan')
        self.assertEqual(state['status'],'任务包已验证')
        self.assertEqual(state['coder_execution_intent'],'danger-full-access')
        self.assertFalse(self.controller.full_access);self.assertFalse(agent.full_access)
        self.assertEqual(agent.roles,['Planner']);self.assertNotIn('execution_mode',state)
        self.assertIn('未来Coder/工程检查的Full Access执行意向',prompts[0])
        self.assertIn('只是规划记录，不授予执行权限',prompts[0])
        self.assertIn('Planner本次始终read-only',prompts[0])
        self.assertNotIn('本次未选择Full Access',prompts[0])
        self.controller.full_access=True;agent.full_access=True
        self.assertEqual(self.execute(pid)['status'],'已完成')
        self.assertEqual(agent.roles,['Planner','Coder'])
    def test_plan_default_intent_stays_restricted_and_legacy_state_works(self):
        agent=self.full_flow_fixture(False);pid=self.task()
        self.assertEqual(self.execute(pid,'Plan')['status'],'任务包已验证')
        _,control,workspace,state=self.controller.locate(pid)
        self.assertEqual(state['coder_execution_intent'],'workspace-write')
        self.assertIn('未确认未来Full Access意向',self.controller.planner_input(state,workspace))
        # Old fixture records have no intent; do not migrate historic records.
        del state['coder_execution_intent'];save(control/'state.json',state)
        self.assertEqual(self.execute(pid)['status'],'已完成')
        self.assertFalse(agent.full_access)
    def test_plan_execution_intent_mismatch_stops_before_dispatch(self):
        for intent,selected in [('danger-full-access',False),('workspace-write',True)]:
            with self.subTest(intent=intent,selected=selected):
                agent=self.full_flow_fixture(False)
                pid=self.controller.create('Mismatch AgentDouble only',10,coder_execution_intent=intent)
                self.assertEqual(self.execute(pid,'Plan')['status'],'任务包已验证')
                count=len(agent.steps)
                self.controller.full_access=selected;agent.full_access=selected
                state=self.execute(pid)
                self.assertEqual(state['status'],'已失败')
                self.assertIn('规划确认',state['error'])
                self.assertEqual(agent.roles,['Planner']);self.assertEqual(len(agent.steps),count)
    def test_executor_full_access_without_caller_selection_is_rejected(self):
        agent=self.full_flow_fixture(False);pid=self.task();agent.full_access=True
        state=self.execute(pid)
        self.assertEqual(state['status'],'已失败');self.assertEqual(agent.roles,[])
        self.assertIn('调用者显式选择',state['error'])
    def test_invalid_execution_intent_stops_before_model(self):
        with self.assertRaisesRegex(FactoryError,'执行意向无效'):
            self.controller.create('invalid intent',10,coder_execution_intent='')
        pid=self.task();_,control,_,state=self.controller.locate(pid)
        state['coder_execution_intent']='unrecognized-mode';save(control/'state.json',state)
        self.assertEqual(self.execute(pid)['status'],'已失败');self.assertEqual(self.agent.roles,[])
    def test_selected_full_access_with_restricted_executor_is_rejected(self):
        agent=self.full_flow_fixture(False);self.controller.full_access=True
        state=self.execute(self.task())
        self.assertEqual(state['status'],'已失败');self.assertEqual(agent.roles,[])
        self.assertIn('调用者显式选择',state['error'])
    def test_explicit_cli_path_without_path_lookup(self):
        from unittest.mock import patch
        import subprocess
        path=self.root/'path with spaces'/'codex.exe';path.parent.mkdir();path.write_bytes(b'fixture-not-an-executable')
        with patch('factory.executor.shutil.which',return_value=None) as lookup,patch('factory.executor.subprocess.run',return_value=subprocess.CompletedProcess([],0,'codex-cli 0.0-fixture\n','')) as run:
            exe,version=resolve_codex(str(path))
        lookup.assert_not_called();self.assertEqual(exe,str(path.resolve()));self.assertEqual(version,'codex-cli 0.0-fixture')
        self.assertEqual(run.call_args.args[0],[str(path),'--version']);self.assertEqual(run.call_args.kwargs['timeout'],10)
    def test_invalid_explicit_cli_path_never_falls_back(self):
        from unittest.mock import patch
        with patch('factory.executor.shutil.which') as lookup,patch('factory.executor.subprocess.run') as run:
            with self.assertRaises(FactoryError):resolve_codex(str(self.root/'missing.exe'))
        lookup.assert_not_called();run.assert_not_called()
    def test_cli_wrong_version_or_timeout_rejected(self):
        from unittest.mock import patch
        import subprocess
        path=self.root/'codex.exe';path.write_bytes(b'fixture')
        with patch('factory.executor.subprocess.run',return_value=subprocess.CompletedProcess([],0,'other-tool 1.0','')):
            with self.assertRaises(FactoryError):resolve_codex(str(path))
        with patch('factory.executor.subprocess.run',side_effect=subprocess.TimeoutExpired([],10)):
            with self.assertRaises(FactoryError):resolve_codex(str(path))
    def test_check_cli_does_not_create_or_execute_task(self):
        from unittest.mock import patch
        from factory.controller import main
        with patch('factory.controller.resolve_codex',return_value=('C:/fixture/codex.exe','codex-cli fixture')),patch('factory.controller.Controller') as ctor,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--check-cli','--codex-path','C:/fixture/codex.exe']),0)
        ctor.assert_not_called()

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FactoryTests)
    buffer=io.StringIO(); started=time.monotonic()
    result=unittest.TextTestRunner(stream=buffer,verbosity=2).run(suite)
    out=ROOT/'validation/goal1'; out.mkdir(parents=True,exist_ok=True)
    log=out/('exception-tests-'+RUN_ROOT.name+'.txt'); log.write_text(buffer.getvalue(),encoding='utf-8')
    report={'kind':'deterministic exception tests with explicit AgentDouble; timeout and redaction subprocess tests use real local processes',
            'run_id':RUN_ROOT.name,'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
            'passed':result.wasSuccessful(),'elapsed_seconds':round(time.monotonic()-started,3),'log':str(log), 'fixtures':str(RUN_ROOT)}
    save(out/('exception-tests-'+RUN_ROOT.name+'.json'),report)
    print(buffer.getvalue()); print(json.dumps(report,ensure_ascii=False,indent=2))
    sys.exit(not result.wasSuccessful())

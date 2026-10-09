"""Synthetic two-goal control fixture; no real model/business/browser run."""
import contextlib
import copy
import io
import shutil
import unittest
import uuid
from pathlib import Path
from factory.controller import Controller, ROOT, load, save, locked
from factory.contracts import FactoryError, digest, file_hash, validate_packet
from factory.sequence import prepare_stage, stage_controller
from tests.test_quality import QualityDouble

RUN_ROOT=ROOT/'validation/goal3/test-workspaces'/uuid.uuid4().hex[:10]


class SequenceDouble(QualityDouble):
    label='two-goal-AgentDouble-control-only'
    def __init__(self):
        super().__init__();self.second_behavior='normal'
    def run(self,role,prompt,workspace,control,*args):
        packet_path=control/'task-packet.json'
        packet=load(packet_path) if packet_path.exists() else {}
        if role=='Coder' and packet.get('goal')=='Goal 1':
            if '本阶段任务、依赖和允许源码写集：' not in prompt or '"T-1"' not in prompt:
                raise FactoryError('Incremental Coder did not receive its approved task/write boundaries')
            self.roles.append(role)
            if self.second_behavior=='interrupt':raise KeyboardInterrupt()
            base=workspace/'fixture.mjs';prior=file_hash(base)
            target=workspace/'src/business/increment.mjs';target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text('// incremental fixture consumes existing foundation '+prior+'\n',encoding='utf-8')
            if self.second_behavior=='delete':base.unlink()
            if self.second_behavior=='outside_write_set':base.write_text('// unexpected replacement')
            return {'exit_code':0,'timed_out':False,'elapsed_seconds':0,'turn_completed':True,
                    'output':{'status':'completed','summary':self.label,'files':['src/business/increment.mjs'],
                              'tests':[{'command':'AgentDouble','exit_code':0,'result':'synthetic'}],
                              'evidence':[],'limitations':['Not real business execution'],'questions':[]},
                    'usage':None,'thread_ids':['sequence-double-'+uuid.uuid4().hex]}
        return super().run(role,prompt,workspace,control,*args)


class SequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN_ROOT.mkdir(parents=True);shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')

    def setUp(self):
        self.agent=SequenceDouble();self.c=Controller(RUN_ROOT,self.agent)
        self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        self.pid=self.c.create('Synthetic sequential API foundation and incremental business operation',10)
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid,'Plan')
        self.project,self.control,self.workspace,_=self.c.locate(self.pid)
        self.spec={'goal':'Goal 1','prompt_md':str(self.workspace)+'\nGoal 1 增量 禁止 测试 验收 停止 报告 AC-10\n'+
                   '使用前序fixture.mjs，添加src/business/increment.mjs，保留基础代码与历史，不清空重建。明确输入输出、错误检查、自测与证据。'*15,
                   'checks':[{'purpose':'build','argv':['node','scripts/build.mjs']},
                             {'purpose':'test','argv':['node','scripts/test.mjs']}],
                   'runtime':{'argv':['node','scripts/serve.mjs','{port}'],'path':'/','expected_text':'incremental fixture'},
                   'blocking_questions':[]}
        self.c.prepare_goal_sequence(self.pid,self.spec,'synthetic-scope-approval')
        self.cursor=self.control/'sequence/state.json'

    def run_chain(self,through='Goal 1'):
        with contextlib.redirect_stdout(io.StringIO()):return self.c.run_goal_sequence(self.pid,through)

    def test_future_full_access_intent_is_preserved_across_both_goals(self):
        self.agent=SequenceDouble();self.c=Controller(RUN_ROOT,self.agent)
        self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        old_workspace=str(self.workspace)
        self.pid=self.c.create('Permission two-goal AgentDouble only',10,coder_execution_intent='danger-full-access')
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid,'Plan')
        self.project,self.control,self.workspace,_=self.c.locate(self.pid)
        spec=copy.deepcopy(self.spec);spec['prompt_md']=spec['prompt_md'].replace(old_workspace,str(self.workspace))
        self.c.prepare_goal_sequence(self.pid,spec,'synthetic-future-full-access')
        self.c.full_access=True;self.agent.full_access=True
        self.assertEqual(self.run_chain()['status'],'两阶段已完成')
        self.assertEqual(load(self.control/'state.json')['coder_execution_intent'],'danger-full-access')
        self.assertEqual(load(self.control/'goals/goal-1/state.json')['coder_execution_intent'],'danger-full-access')
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Reviewer','Coder','Tester','Reviewer'])

    def test_01_two_goals_share_source_but_distinct_packets_and_quality(self):
        result=self.run_chain();self.assertEqual(result['status'],'两阶段已完成')
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Reviewer','Coder','Tester','Reviewer'])
        second=self.control/'goals/goal-1';packet=load(second/'task-packet.json')
        self.assertEqual(packet['goal'],'Goal 1');self.assertEqual(packet['format_version'],'1.1')
        self.assertEqual([a['id'] for a in packet['acceptance']],['AC-10'])
        self.assertNotEqual(packet['task_id'],load(self.control/'task-packet.json')['task_id'])
        self.assertEqual(packet['runtime'],self.spec['runtime'])
        self.assertIn(file_hash(self.workspace/'fixture.mjs'),(self.workspace/'src/business/increment.mjs').read_text())
        self.assertEqual(load(self.control/'quality/state.json')['status'],'质量门槛通过')
        self.assertEqual(load(second/'quality/state.json')['status'],'质量门槛通过')
        self.assertEqual(load(second/'state.json')['calls'][0]['role'],'Coder')
        save(RUN_ROOT/'two-goal-example.json',{'synthetic':True,'real_model_calls':0,'real_business_e2e':False,
             'project_id':self.pid,'project_path':str(self.project),'roles':self.agent.roles,
             'sequence':result,'goal0_candidate':load(self.control/'sequence/goal0-completion.json')['candidate'],
             'goal1_candidate':load(self.control/'sequence/goal1-completion.json')['candidate'],
             'goal1_packet':packet,'original_foundation_still_present':True})

    def test_02_resume_after_goal0_does_not_recall_completed_roles(self):
        first=self.run_chain('Goal 0');self.assertEqual(set(first['completed']),{'Goal 0'})
        protected={n:file_hash(self.control/n) for n in ('state.json','completion.json','quality/state.json')}
        self.run_chain();self.assertEqual(self.agent.roles.count('Planner'),1);self.assertEqual(self.agent.roles.count('Coder'),2)
        self.assertEqual(protected,{n:file_hash(self.control/n) for n in protected})

    def test_03_completed_chain_does_not_dispatch_again(self):
        self.run_chain();roles=list(self.agent.roles);self.run_chain()
        self.assertEqual(self.agent.roles,roles)
        with self.assertRaisesRegex(FactoryError,'禁止旧入口'):self.c.run(self.pid)

    def test_04_failed_quality_prevents_next_goal(self):
        self.agent.scenario='reviewer_blocked'
        result=self.run_chain();self.assertEqual(result['status'],'停止')
        self.assertFalse((self.control/'goals/goal-1').exists())
        roles=list(self.agent.roles);self.run_chain();self.assertEqual(self.agent.roles,roles)

    def test_05_receipt_window_recovered_without_goal0_reexecution(self):
        self.run_chain('Goal 0');cursor=load(self.cursor);cursor['completed']={};save(self.cursor,cursor)
        self.run_chain();self.assertEqual(self.agent.roles.count('Coder'),2);self.assertEqual(self.agent.roles.count('Planner'),1)

    def test_06_partial_coder_stops_without_implicit_retry(self):
        self.agent.second_behavior='interrupt';self.assertEqual(self.run_chain()['status'],'停止')
        roles=list(self.agent.roles);self.run_chain();self.assertEqual(self.agent.roles,roles)
        self.assertEqual(load(self.control/'goals/goal-1/state.json')['retries'],0)

    def test_07_later_candidate_change_invalidates_completion(self):
        self.run_chain();roles=list(self.agent.roles);(self.workspace/'src/business/increment.mjs').write_text('// tampered')
        with self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)

    def test_08_changed_prior_quality_record_stops_without_model(self):
        self.run_chain('Goal 0');roles=list(self.agent.roles)
        (self.control/'quality/completion.json').write_text('{}')
        with self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)

    def test_09_delete_or_replace_foundation_rejected(self):
        self.agent.second_behavior='delete';self.assertEqual(self.run_chain()['status'],'停止')
        self.assertEqual(self.agent.roles.count('Tester'),1)

    def test_10_source_outside_goal1_write_set_rejected(self):
        self.agent.second_behavior='outside_write_set';self.assertEqual(self.run_chain()['status'],'停止')
        self.assertEqual(self.agent.roles.count('Reviewer'),1)

    def test_11_original_project_lock_covers_both_stages(self):
        roles=list(self.agent.roles)
        with locked(self.control),self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)

    def test_12_cross_project_task_packet_rejected(self):
        self.run_chain('Goal 0');cursor=load(self.cursor)
        stage=prepare_stage(self.c,self.project,self.control,self.workspace,self.c.locate(self.pid)[3],
                            self.spec,cursor['completed']['Goal 0'])
        packet_path=self.control/'goals/goal-1/task-packet.json';packet=load(packet_path)
        other=self.c.create('Another fixture workspace',10)
        packet['workspace']=str(self.c.locate(other)[2]);save(packet_path,packet)
        roles=list(self.agent.roles)
        with self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)
        self.assertFalse((self.c.locate(other)[2]/'src/business/increment.mjs').exists())

    def test_13_missing_scope_ac_or_confirmation_is_not_dispatchable(self):
        roles=list(self.agent.roles)
        for key,value in [('blocking_questions',['unresolved business rule']),('prompt_md','missing AC')]:
            spec=copy.deepcopy(self.spec);spec[key]=value
            with self.subTest(key=key),self.assertRaises(FactoryError):
                self.c.prepare_goal_sequence(self.pid,spec,'synthetic-scope-approval')
        with self.assertRaises(FactoryError):self.c.prepare_goal_sequence(self.pid,self.spec,'')
        plan=load(self.control/'planner-result.json');plan['acceptance']=[a for a in plan['acceptance'] if a['goal_id']!='Goal 1']
        save(self.control/'planner-result.json',plan)
        with self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)

    def test_14_goal0_packet_cannot_substitute_for_goal1(self):
        self.run_chain('Goal 0');cursor=load(self.cursor)
        stage=prepare_stage(self.c,self.project,self.control,self.workspace,self.c.locate(self.pid)[3],
                            self.spec,cursor['completed']['Goal 0'])
        _,control,_,state=stage.locate(self.pid);packet=load(control/'task-packet.json')
        packet['goal']='Goal 0';save(control/'task-packet.json',packet)
        roles=list(self.agent.roles)
        with self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)

    def test_15_prepared_stage_rechecks_candidate_before_dispatch(self):
        self.run_chain('Goal 0');cursor=load(self.cursor)
        prepare_stage(self.c,self.project,self.control,self.workspace,self.c.locate(self.pid)[3],
                      self.spec,cursor['completed']['Goal 0'])
        roles=list(self.agent.roles);(self.workspace/'fixture.mjs').write_text('// external mutation')
        with self.assertRaises(FactoryError):self.run_chain()
        self.assertEqual(self.agent.roles,roles)

    def test_16_resumed_stage_runtime_uses_its_own_executor(self):
        uninitialized=Controller(RUN_ROOT,full_access=True)
        stage=stage_controller(uninitialized)
        self.assertIs(stage.runtime_check.__self__,stage)
        self.assertIsNone(stage.executor)

    def test_17_task_dependencies_cannot_reverse_stage_order(self):
        from factory.sequence import validate_spec
        plan=load(self.control/'planner-result.json');plan['tasks'][0]['depends_on']=['T-1']
        # A task DAG can be acyclic while its cross-stage order is invalid.
        plan['tasks'][1]['depends_on']=[]
        roles=list(self.agent.roles)
        with self.assertRaisesRegex(FactoryError,'后续阶段'):
            validate_spec(self.spec,plan,self.workspace)
        self.assertEqual(self.agent.roles,roles)

    def test_18_no_auto_repair_even_for_actionable_defects(self):
        self.agent.scenario='tester_repair'
        self.assertEqual(self.run_chain()['status'],'停止')
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester'])
        self.assertTrue((self.control/'quality/rounds/01/defect-packet.json').is_file())


if __name__=='__main__':unittest.main()

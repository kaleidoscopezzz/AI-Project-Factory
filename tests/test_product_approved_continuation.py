"""AgentDouble tests of an approved-stage continuation, not real quality approval."""
import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory.controller import ROOT, Controller, load, save
from factory.contracts import FactoryError, digest, file_hash
from factory.product import ProductRun, RunExecutor, STAGE_CONTINUATION_LIMITS
from factory.revalidation import original_files
from factory.sequence import check_receipt
from tests.test_product_continuation import HandoffDouble
from tests.test_product import double_controller

class FailedStageDouble(HandoffDouble):
    def __init__(self):super().__init__();self.fail_second=True
    def run(self,role,prompt,workspace,control,*args):
        if role=='Coder' and load(control/'task-packet.json')['goal']=='Goal 1' and self.fail_second:
            self.roles.append(role)
            return dict(exit_code=0,timed_out=False,elapsed_seconds=0,turn_completed=True,usage=None,thread_ids=['double'],
                output=dict(status='failed',summary='AgentDouble missing approval handoff',files=[],tests=[],evidence=[],limitations=[],questions=[]))
        return super().run(role,prompt,workspace,control,*args)

class ApprovedContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation');self.root=Path(self.temp.name)
        self.old=self.root/'old';self.new=self.root/'new';self.agent=FailedStageDouble()
        skills={n:ROOT/'skills'/n for n in ('requirement-planner','goal0-scaffolder','goal-prompt-writer')}
        self.source=ProductRun(self.old,request='AgentDouble Goal1 approved predecessor',full_access=True,executor=self.agent,skills=skills,controller_factory=double_controller)
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(FactoryError):self.source.execute()
        self.project=self.old/'.apf/projects'/self.source.ledger['project_id'];self.control=self.project/'control'
        self.before=original_files(self.project);self.runsha=file_hash(self.source.folder/'run.json')
        self.agent.fail_second=False;self.roles=list(self.agent.roles)
    def tearDown(self):self.temp.cleanup()
    def prepare(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return ProductRun.continue_goal1(self.old,self.new,authorization_id='fresh-goal1-explicit-grant',executor=self.agent,full_access=True)
    def finish(self,run):
        run.controller_factory=double_controller
        with contextlib.redirect_stdout(io.StringIO()),patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'double stop after approval'}),self.assertRaisesRegex(FactoryError,'double stop'):
            run.execute()
    def test_exact_final_input_and_skip_all_goal0_agents(self):
        run=self.prepare();stage=run.folder/'projects'/self.project.name/'control/goals/goal-1'
        pin=load(stage/'coder-input-preflight.json');text=(stage/'coder-input-preflight.md').read_text(encoding='utf8')
        self.assertEqual(pin['input_sha256'],digest(text.encode()))
        self.assertEqual(pin['approval']['status'],'质量门槛通过');self.assertTrue(pin['approval']['approved_at'])
        self.assertEqual(pin['approval']['original_approval']['sha256'],file_hash(self.control/'sequence/goal0-completion.json'))
        self.assertIn('不要求再次外部ChatGPT批准',text);self.assertIn('Goal 1',text)
        self.assertEqual(self.agent.roles,self.roles);self.assertEqual(run.ledger['limits'],STAGE_CONTINUATION_LIMITS)
        self.finish(run)
        self.assertEqual(self.agent.roles[len(self.roles):],['Coder','Tester','Reviewer'])
        self.assertEqual(self.agent.goal1_prompt,text)
        self.assertEqual(original_files(self.project),self.before);self.assertEqual(file_hash(self.source.folder/'run.json'),self.runsha)
    def test_source_approval_and_candidate_tampering_refused(self):
        path=self.control/'sequence/goal0-completion.json';path.write_text('{}')
        with self.assertRaises(FactoryError):self.prepare()
        self.assertEqual(self.agent.roles,self.roles)
    def test_input_drift_stops_before_model(self):
        run=self.prepare();stage=run.folder/'projects'/self.project.name/'control/goals/goal-1'
        pin=load(stage/'coder-input-preflight.json');pin['input_sha256']='0'*64;save(stage/'coder-input-preflight.json',pin)
        run.controller_factory=double_controller
        with contextlib.redirect_stdout(io.StringIO()),self.assertRaises(FactoryError):run.execute()
        self.assertEqual(self.agent.roles,self.roles)
    def test_source_change_after_preparation_refused(self):
        run=self.prepare();(self.control/'goals/goal-1/coder-result.json').write_text('{}')
        with self.assertRaises(FactoryError):RunExecutor(self.agent,run.folder,run.ledger).verify()
    def test_no_budget_refresh_or_goal0_dispatch(self):
        run=self.prepare();wrapper=RunExecutor(self.agent,run.folder,run.ledger)
        for role in ('Planner','Coder','Tester','Reviewer'):
            with self.assertRaises(FactoryError):wrapper.run(role,'forbidden',self.project/'workspace',self.control,1,{},10)
        with self.assertRaises(FactoryError):self.prepare()
        self.assertEqual(self.agent.roles,self.roles)
    def test_relocation_does_not_change_approved_requirements(self):
        run=self.prepare();project=run.folder/'projects'/self.project.name
        path=project/'control/task-packet.json';packet=load(path);packet['acceptance']=[];save(path,packet)
        entry=load(project/'control/sequence/state.json')['completed']['Goal 0']
        with self.assertRaises(FactoryError):check_receipt(project,entry,'Goal 0')

    def test_completed_without_increment_refused(self):
        from factory.sequence import stage_controller
        run=self.prepare();c=double_controller(run.folder,self.agent,True);stage=stage_controller(c)
        control=run.folder/'projects'/self.project.name/'control/goals/goal-1';work=control.parents[2]/'workspace'
        with self.assertRaisesRegex(FactoryError,'没有实际业务源码变更'):
            stage.verify(load(control/'task-packet.json'),{},work,control,{})

if __name__=='__main__':unittest.main()

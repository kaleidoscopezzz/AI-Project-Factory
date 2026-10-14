"""Deterministic handoff tests; AgentDouble does not prove real acceptance."""
import contextlib
import copy
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from factory.controller import Controller,ROOT,load,save
from factory.contracts import FactoryError,file_hash
from factory.product import ProductRun,RunExecutor,CONTINUATION_LIMITS
from factory.revalidation import original_files
from tests.test_product import ProductDouble,double_controller

class HandoffDouble(ProductDouble):
    def run(self,role,prompt,workspace,control,*args):
        if role=='Coder' and load(control/'task-packet.json')['goal']=='Goal 1':self.goal1_prompt=prompt
        result=super().run(role,prompt,workspace,control,*args)
        if role=='Coder' and load(control/'task-packet.json')['goal']=='Goal 0':
            path=workspace/'validation/acceptance.md';path.parent.mkdir(exist_ok=True)
            log=workspace/'validation/round/test.log';log.parent.mkdir(exist_ok=True);log.write_text('fixture log')
            path.write_text('AgentDouble original delivery; no real quality approval.\n[Test](round/test.log)\ntest.log is a prose label.\n',encoding='utf8')
            result['output']['evidence'].append('validation/acceptance.md')
        return result

class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation');self.root=Path(self.temp.name)
        self.old=self.root/'original';self.new=self.root/'continued';self.agent=HandoffDouble()
        skills={n:ROOT/'skills'/n for n in ('requirement-planner','goal0-scaffolder','goal-prompt-writer')}
        run=ProductRun(self.old,request='中文接续AgentDouble',full_access=True,executor=self.agent,skills=skills,controller_factory=double_controller)
        def stop_after_coder(c,pid,*args):
            c._run_goal1(pid)
            raise FactoryError('AgentDouble stop before any quality agent')
        with patch.object(Controller,'run_goal_sequence',stop_after_coder),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(FactoryError):run.execute()
        self.ledger=load(self.old/'.apf/run.json');self.project=self.old/'.apf/projects'/self.ledger['project_id']
        self.snapshot=original_files(self.project)
        self.runsha=file_hash(self.old/'.apf/run.json')
    def tearDown(self):self.temp.cleanup()
    def handoff(self,**kw):
        with patch.object(Controller,'runtime_check',return_value={'passed':True,'AgentDouble':True}),contextlib.redirect_stdout(io.StringIO()):
            return ProductRun.handoff(self.old,self.new,authorization_id='fixture-explicit-new-grant',executor=self.agent,full_access=True,**kw)
    def test_source_immutable_new_budget_without_approval(self):
        run=self.handoff();RunExecutor(self.agent,run.folder,run.ledger).verify()
        self.assertEqual(original_files(self.project),self.snapshot)
        self.assertEqual(file_hash(self.old/'.apf/run.json'),self.runsha)
        self.assertEqual(run.ledger['calls'],[]);self.assertEqual(run.ledger['limits'],CONTINUATION_LIMITS)
        c=run.folder/'projects'/self.project.name/'control'
        self.assertEqual(load(c/'state.json')['status'],'已完成')
        self.assertFalse((c/'quality').exists());self.assertFalse((c/'sequence/goal0-completion.json').exists())
        self.assertEqual(self.agent.roles,['Planner','Coder'])
    def test_old_candidate_tamper_refused_before_model(self):
        (self.project/'workspace/fixture.mjs').write_text('tampered')
        with self.assertRaisesRegex(FactoryError,'候选变化'):self.handoff()
        self.assertEqual(self.agent.roles,['Planner','Coder'])
    def test_source_change_after_handoff_stops(self):
        run=self.handoff();(self.project/'control/plan.md').write_text('changed')
        with self.assertRaisesRegex(FactoryError,'原始成果变化'):RunExecutor(self.agent,run.folder,run.ledger).verify()
    def test_same_authorization_cannot_create_second_budget(self):
        self.handoff();self.new=self.root/'other'
        with self.assertRaisesRegex(FactoryError,'授权已绑定'):self.handoff()
    def test_no_planner_or_goal0_coder_dispatch(self):
        run=self.handoff();wrapper=RunExecutor(self.agent,run.folder,run.ledger)
        c=run.folder/'projects'/self.project.name/'control'
        for role in ('Planner','Coder'):
            with self.assertRaises(FactoryError):wrapper.run(role,'forbidden',c.parent/'workspace',c,1,{},10)
        self.assertEqual(self.agent.roles,['Planner','Coder'])
    def test_unauthorized_permissions_refused(self):
        with self.assertRaisesRegex(FactoryError,'显式Full Access'):
            ProductRun.handoff(self.old,self.new,authorization_id='not-permission',executor=self.agent)
    def test_approval_must_be_fresh_and_sequence_compatible(self):
        run=self.handoff();run.controller_factory=double_controller
        with patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'AgentDouble end after stage receipts'}),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(FactoryError,'AgentDouble end'):run.execute()
        self.assertEqual(self.agent.roles,['Planner','Coder','Tester','Reviewer','Coder','Tester','Reviewer'])
        cursor=load(run.folder/'projects'/self.project.name/'control/sequence/state.json')
        self.assertEqual(cursor['status'],'两阶段已完成')
        self.assertIn('<verified-predecessor-approval>',self.agent.goal1_prompt)
        self.assertIn('receipt_sha256',self.agent.goal1_prompt)
        self.assertIn('不要求再次外部ChatGPT批准',self.agent.goal1_prompt)
    def test_budget_tampering_refused(self):
        run=self.handoff();run.ledger['limits']['Planner']=1
        with self.assertRaisesRegex(FactoryError,'预算被修改'):RunExecutor(self.agent,run.folder,run.ledger).verify()
    def test_archived_relative_evidence_ready_but_tampering_rejected(self):
        from factory.history import history_dependencies
        from factory.quality import candidate
        run=self.handoff();control=run.folder/'projects'/self.project.name/'control';work=control.parent/'workspace'
        completion=load(control/'completion.json')
        self.assertTrue(history_dependencies(work,completion,candidate(work),load)['ready'])
        archive=load(run.folder/'handoff.json')['archive'];(work/archive/'validation/round/test.log').write_text('tampered')
        self.assertFalse(history_dependencies(work,completion,candidate(work),load)['ready'])
    def test_predecessor_context_rejects_tampered_receipt(self):
        from factory.sequence import predecessor_context
        run=self.handoff();run.controller_factory=double_controller
        with patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'fixture'}),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(FactoryError):run.execute()
        control=run.folder/'projects'/self.project.name/'control'
        packet=load(control/'goals/goal-1/task-packet.json')
        value=predecessor_context(control/'goals/goal-1',packet)
        self.assertEqual(value['quality_sources'][0]['reviewer'],'approved')
        (control/'sequence/goal0-completion.json').write_text('{}')
        with self.assertRaises(FactoryError):predecessor_context(control/'goals/goal-1',packet)

if __name__=='__main__':unittest.main()

"""Saved artifacts from a timed-out Agent are not a successful model response."""
import contextlib,copy,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from factory.controller import ROOT,Controller,load,save
from factory.contracts import FactoryError,digest,file_hash
from factory.product import ProductRun,source_files,RunExecutor
from tests.test_product_approved_continuation import FailedStageDouble
from tests.test_product import double_controller

class SavedDouble(FailedStageDouble):
 def __init__(self):super().__init__();self.timeout_delivery=False
 def run(self,role,prompt,workspace,control,*args):
  out=super().run(role,prompt,workspace,control,*args)
  if role=='Planner':
   for t in out['output']['plan']['tasks']:
    if t['goal_id']=='Goal 1':t['write_set'].append('PROJECT_STATUS.md')
  if role=='Coder' and load(control/'task-packet.json')['goal']=='Goal 0':
   (workspace/'scripts').mkdir(exist_ok=True)
   for n in ('build.mjs','test.mjs','serve.mjs'):(workspace/'scripts'/n).write_text('// AgentDouble saved source fixture')
  if role=='Coder' and self.timeout_delivery and load(control/'task-packet.json')['goal']=='Goal 1':
   (workspace/'PROJECT_STATUS.md').write_text('Goal 1：已完成，待外部 Reviewer 验收\nAgentDouble saved report; not real quality approval.',encoding='utf8')
   names=['fixture.mjs','scripts/build.mjs','scripts/test.mjs','scripts/serve.mjs']
   save(workspace/'validation/goal1/candidate-manifest.json',{'source_files':[{'path':n,'sha256':file_hash(workspace/n)} for n in names]})
   out.update(exit_code=1,timed_out=True,turn_completed=False,output=None)
  return out

class SavedDeliveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'validation');self.root=Path(self.tmp.name);self.agent=SavedDouble()
  skills={n:ROOT/'skills'/n for n in ('requirement-planner','goal0-scaffolder','goal-prompt-writer')}
  fake_before=source_files();fake_before['controller.py']='fixture-old-supported-code-checkpoint'
  with patch('factory.product.source_files',return_value=fake_before),contextlib.redirect_stdout(io.StringIO()):
   old=ProductRun(self.root/'old',request='AgentDouble saved artifacts only',full_access=True,executor=self.agent,skills=skills,controller_factory=double_controller)
   with self.assertRaises(FactoryError):old.execute()
   if 'Goal 0' not in load(old.folder/'projects'/old.ledger['project_id']/'control/sequence/state.json')['completed']:raise AssertionError(old.ledger.get('error'))
   self.agent.fail_second=False;self.agent.timeout_delivery=True
   self.run=ProductRun.continue_goal1(self.root/'old',self.root/'new',authorization_id='fixture-saved-artifact-grant',executor=self.agent,full_access=True)
   self.run.controller_factory=double_controller
   with self.assertRaises(FactoryError):self.run.execute()
  if not self.run.ledger['calls']:raise AssertionError(self.run.ledger.get('error'))
  self.control=self.run.folder/'projects'/self.run.ledger['project_id']/'control/goals/goal-1';self.work=self.control.parents[2]/'workspace'
  self.failed=(self.control/'state.json').read_bytes();self.execution=self.run.folder/'execution-1.json';self.raw=file_hash(self.execution)
  self.calls=copy.deepcopy(self.run.ledger['calls']);self.deadline=self.run.ledger['deadline'];self.roles=list(self.agent.roles)
 def tearDown(self):self.tmp.cleanup()
 def accept(self):
  with contextlib.redirect_stdout(io.StringIO()):return self.run.accept_saved_delivery()
 def test_saved_delivery_keeps_timeout_budget_and_raw_result(self):
  self.accept();self.assertEqual(file_hash(self.execution),self.raw)
  self.assertEqual((self.control/'saved-delivery/failed-state.json').read_bytes(),self.failed)
  self.assertEqual(self.run.ledger['calls'],self.calls);self.assertEqual(self.run.ledger['deadline'],self.deadline)
  self.assertEqual(load(self.control/'coder-result.json')['status'],'interrupted_with_verified_delivery')
  self.assertFalse(load(self.execution)['turn_completed']);self.assertIsNone(load(self.execution)['output'])
  RunExecutor(self.agent,self.run.folder,self.run.ledger).verify()
  self.agent.timeout_delivery=False
  with contextlib.redirect_stdout(io.StringIO()),patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'fixture stop after real state machine'}),self.assertRaises(FactoryError):self.run.execute()
  self.assertEqual(self.agent.roles[len(self.roles):],['Tester','Reviewer'])
 def test_missing_self_report_never_infers_completion(self):
  (self.work/'PROJECT_STATUS.md').unlink()
  with self.assertRaises(FactoryError):self.accept()
  self.assertEqual(self.agent.roles,self.roles)
 def test_changed_delivery_hash_rejected(self):
  (self.work/'fixture.mjs').write_text('changed after saved index')
  with self.assertRaises(FactoryError):self.accept()
  self.assertEqual(self.agent.roles,self.roles)
 def test_non_timeout_result_rejected(self):
  value=load(self.execution);value['timed_out']=False;save(self.execution,value)
  # The execution SHA is independently pinned; even before its semantic check.
  with self.assertRaises(FactoryError):self.accept()
 def test_checkpoint_tamper_rejected_without_agents(self):
  self.accept();(self.control/'saved-delivery/failed-state.json').write_text('{}')
  with self.assertRaises(FactoryError):RunExecutor(self.agent,self.run.folder,self.run.ledger).verify()
  self.assertEqual(self.agent.roles,self.roles)
 def test_repaired_history_preparation_keeps_failed_sources_and_budget(self):
  from factory.sequence import stage_controller
  from factory.quality import QualityGate,candidate
  (self.work/'validation/goal1/acceptance.md').write_text('Run `node scripts/build.mjs`.',encoding='utf8')
  self.accept()
  c=stage_controller(double_controller(self.run.folder,self.agent,True))
  project,control,work,state=c.locate(self.run.ledger['project_id'])
  gate=QualityGate(c,project,control,work,state);first=gate.make_round()
  (work/'scripts/build.mjs').write_text('// synthetic controlled repair')
  gate.q['repairs'].append({'valid_repair':True,'before':first['candidate'],'after':candidate(work)})
  folder=gate.folder/'rounds/02/context';folder.mkdir(parents=True)
  save(folder/'dependency-preflight.json',{'ready':False})
  gate.stop('历史资料缺失/哈希不匹配/依赖未验证：synthetic preparation failure')
  prior=gate.path.read_bytes();controller=(control/'state.json').read_bytes()
  self.run.ledger['status']='stopped';save(self.run.folder/'run.json',self.run.ledger)
  roles=list(self.agent.roles);calls=copy.deepcopy(self.run.ledger['calls']);deadline=self.run.ledger['deadline']
  now=source_files();now['history.py']='fixture-local-context-fix'
  with patch('factory.product.source_files',return_value=now),contextlib.redirect_stdout(io.StringIO()):
   result=self.run.recover_repaired_preparation()
   self.assertTrue(result['ready']);self.assertEqual(result['new_model_calls'],0)
   self.assertEqual((gate.folder/'preparation-recovery/quality-state.json').read_bytes(),prior)
   self.assertEqual((gate.folder/'preparation-recovery/controller-state.json').read_bytes(),controller)
   self.assertEqual(load(folder/'dependency-preflight.json'),{'ready':False})
   current=load(gate.path);self.assertEqual(current['rounds'][-1]['path'],'rounds/02p')
   self.assertIsNone(current['rounds'][-1]['tester']);self.assertNotEqual(current['status'],'质量门槛通过')
   self.assertEqual(self.run.ledger['calls'],calls);self.assertEqual(self.run.ledger['deadline'],deadline)
   self.assertEqual(self.agent.roles,roles);RunExecutor(self.agent,self.run.folder,self.run.ledger).verify()
   original_run=(self.run.folder/'run.json').read_bytes();original_quality=gate.path.read_bytes()
   path=self.run.open_quality_window('fixture-new-quality-authorization')
   window=load(path)
   self.assertEqual((self.run.folder/'run.json').read_bytes(),original_run)
   self.assertEqual(gate.path.read_bytes(),original_quality)
   self.assertEqual(window['limits']['Planner'],0);self.assertEqual(window['limits']['Coder'],0)
   self.assertEqual(window['calls'],[]);self.assertEqual(self.agent.roles,roles)
   wrapper=RunExecutor(self.agent,self.run.folder,window,ledger_path=path);wrapper.verify()
   with self.assertRaises(FactoryError):wrapper.run('Coder','forbidden',work,control,1,{},1)
   with self.assertRaises(FactoryError):wrapper.run('Planner','forbidden',work,control,1,{},1)
   self.assertEqual(self.agent.roles,roles);self.assertEqual(window['calls'],[])
   with self.assertRaises(FactoryError):RunExecutor(self.agent,self.run.folder,window)
   with self.assertRaises(FactoryError):self.run.open_quality_window('fixture-new-quality-authorization')
   source=control/window['quality_context']/'source.json';source.write_text('{}')
   with self.assertRaises(FactoryError):wrapper.verify()
   (gate.folder/'preparation-recovery/quality-state.json').write_text('{}')
   with self.assertRaises(FactoryError):RunExecutor(self.agent,self.run.folder,self.run.ledger).verify()

if __name__=='__main__':unittest.main()

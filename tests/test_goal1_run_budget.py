"""Only the finite Goal 1 run adapter fuse; no real model or business tests."""
import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from factory.controller import ROOT,save,load
from factory.contracts import FactoryError

spec=importlib.util.spec_from_file_location('goal1_authorized_run',ROOT/'validation/goal3/goal1-delivery-20261010/run.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class RunBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation/goal3/test-workspaces')
        self.folder=Path(self.temp.name);self.agent=module.BoundedRun.__new__(module.BoundedRun)
        self.scope=patch.object(module,'OUT',self.folder);self.scope.start()
        save(self.folder/'calls.json',{'calls':[]})
    def tearDown(self):self.scope.stop();self.temp.cleanup()
    def invoke(self,role):return self.agent.run(role,'synthetic fixture only',self.folder,self.folder,1,{},900)
    def test_forbidden_roles_and_repeat_quality_never_invoke_model(self):
        fake={'exit_code':0,'elapsed_seconds':1,'timed_out':False,'turn_completed':True,'thread_ids':['double'],
              'usage':None,'execution_mode':'read-only','output':{}}
        with patch.object(module,'protect'),patch('factory.executor.CodexExecutor.run',return_value=fake) as model:
            with self.assertRaises(FactoryError):self.invoke('Planner')
            self.invoke('Tester')
            with self.assertRaises(FactoryError):self.invoke('Tester')
            self.assertEqual(model.call_count,1)
            self.assertEqual(model.call_args.args[-1],600)
    def test_aggregate_exhaustion_and_interruption_refuse(self):
        for row in ({'role':'Tester','status':'finished','elapsed_seconds':3600},
                    {'role':'Tester','status':'running'}):
            save(self.folder/'calls.json',{'calls':[row]})
            with patch('factory.executor.CodexExecutor.run') as model:
                with self.assertRaises(FactoryError):self.invoke('Reviewer')
                model.assert_not_called()

if __name__=='__main__':unittest.main()

"""Explicit AgentDouble product integration; no real model/software claim."""
import contextlib
import copy
import io
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from factory.controller import Controller, ROOT, load, save
from factory.contracts import FactoryError, file_hash
from factory.product import ProductRun, RunExecutor, LIMITS
from tests.test_sequence import SequenceDouble


class ProductDouble(SequenceDouble):
    def run(self, role, prompt, workspace, control, *args):
        result=super().run(role,prompt,workspace,control,*args)
        if role=='Planner':
            plan=result['output']
            plan['runtime']={'argv':['node','scripts/serve.mjs','--host','127.0.0.1','--port','{port}','--data-dir','var'],'path':'/','expected_text':'fixture'}
            spec={'goal':'Goal 1', 'prompt_md':str(workspace)+'\nGoal 1 增量 禁止 测试 验收 停止 报告 AC-10\n'+'保留前序fixture并增量开发，完整回归，记录证据。'*40,
                  'checks':plan['checks'], 'runtime':plan['runtime'], 'blocking_questions':[]}
            result['output']={'plan':plan,'goal1_spec':spec,
                              'release':{'name':'fixture','source_files':['fixture.mjs','scripts/build.mjs','scripts/test.mjs','scripts/serve.mjs'],
                                         'package_files':['fixture.mjs','scripts/serve.mjs'],'runtime_requirement':'Node.js', 'smoke':'http-health'}}
        return result


def double_controller(*args):
    c=Controller(*args);c.runtime_check=lambda *a:{'passed':True,'test_double':True}
    return c


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation')
        self.output=Path(self.temp.name)/'中文输出'
        self.native=ProductDouble()
        self.skills={n:ROOT/'skills'/n for n in ('requirement-planner','goal0-scaffolder','goal-prompt-writer')}
    def tearDown(self):self.temp.cleanup()
    def run_instance(self,**kw):
        return ProductRun(self.output,request=None if kw.get('resume') else '本地待办中文需求',
                          full_access=True,executor=self.native,skills=self.skills,controller_factory=double_controller,**kw)
    def fake_release(self,c,pid,goal,config):
        # Exercise real Sequence, deliberately substitute ONLY final release.
        self.assertEqual(load(c.locate(pid)[1]/'sequence/state.json')['status'],'两阶段已完成')
        self.assertEqual(goal,'Goal 1')
        folder=c.root/'releases'/'fake';folder.mkdir(parents=True,exist_ok=True)
        package=folder/'fake.zip';package.write_bytes(b'NOT A REAL ZIP: AgentDouble')
        record=folder/'fake-record.json';save(record,{'package':{'sha256':file_hash(package)},
             'binding':{'synthetic':True},'runtime_requirement':'AgentDouble only', 'limitations':['Not real E2E']})
        return {'status':'released','package':str(package),'record':str(record)}
    def execute(self,run):
        with contextlib.redirect_stdout(io.StringIO()):return run.execute()
    def released(self,run):
        with patch.object(Controller,'release_approved_stage',autospec=True,side_effect=self.fake_release):
            return self.execute(run)
    def test_two_goals_to_release_adapter(self):
        result=self.released(self.run_instance())
        self.assertEqual(result['status'],'delivered')
        self.assertEqual(self.native.roles,['Planner','Coder','Tester','Reviewer','Coder','Tester','Reviewer'])
        self.assertTrue((self.output/'RUN.md').is_file())
        ledger=load(self.output/'.apf/run.json');self.assertEqual(len(ledger['calls']),7)
    def test_completed_resume_zero_models(self):
        self.released(self.run_instance());roles=list(self.native.roles)
        self.assertEqual(self.execute(self.run_instance(resume=True))['status'],'delivered')
        self.assertEqual(self.native.roles,roles)
    def test_between_goals_resume_no_goal0_replay(self):
        from factory.sequence import run as sequence_run
        def first(c,pid,through='Goal 1'):return sequence_run(c,pid,'Goal 0')
        with patch.object(Controller,'run_goal_sequence',first),self.assertRaises(FactoryError):
            self.execute(self.run_instance())
        self.assertEqual(self.native.roles,['Planner','Coder','Tester','Reviewer'])
        self.released(self.run_instance(resume=True))
        self.assertEqual(self.native.roles.count('Planner'),1);self.assertEqual(self.native.roles.count('Coder'),2)
    def test_existing_output_not_overwritten(self):
        self.output.mkdir();marker=self.output/'mine';marker.write_text('keep')
        with self.assertRaises(FactoryError):self.run_instance()
        self.assertEqual(marker.read_text(),'keep');self.assertEqual(self.native.roles,[])
    def test_full_access_explicit(self):
        with self.assertRaises(FactoryError):ProductRun(self.output,request='todo',skills=self.skills)
        self.assertFalse(self.output.exists())
    def test_unknown_tester_failure_no_release(self):
        self.native.scenario='environment'
        with patch.object(Controller,'release_approved_stage') as release,self.assertRaises(FactoryError):
            self.execute(self.run_instance())
        release.assert_not_called();self.assertNotIn('Reviewer',self.native.roles)
    def test_reviewer_block_no_release(self):
        self.native.scenario='reviewer_blocked'
        with patch.object(Controller,'release_approved_stage') as release,self.assertRaises(FactoryError):
            self.execute(self.run_instance())
        release.assert_not_called();self.assertEqual(self.native.roles.count('Coder'),1)
    def test_one_repair_global_cap(self):
        self.native.scenario='limit'
        with patch.object(Controller,'release_approved_stage') as release,self.assertRaises(FactoryError):
            self.execute(self.run_instance())
        release.assert_not_called()
        calls=load(self.output/'.apf/run.json')['calls']
        self.assertEqual(sum(c['role']=='CoderRepair' for c in calls),1)
    def test_default_git_never_called(self):
        with patch.object(Controller,'configure_project_git') as git:self.released(self.run_instance())
        git.assert_not_called()
    def test_explicit_git_policy(self):
        with patch.object(Controller,'configure_project_git') as policy,patch.object(Controller,'version_approved_stage',return_value={'status':'committed','commit':'fixture'}) as commit:
            self.released(self.run_instance(allow_local_git=True))
        self.assertTrue(policy.call_args.args[1]['allow_local_commit']);commit.assert_called_once()
    def test_fake_quality_cannot_real_release(self):
        with self.assertRaises(FactoryError):self.execute(self.run_instance())
        self.assertEqual(self.native.roles.count('Reviewer'),2)
        self.assertNotEqual(load(self.output/'.apf/run.json')['status'],'delivered')
    def test_resource_tamper_before_model(self):
        run=self.run_instance();path=run.folder/'skills/goal-prompt-writer/SKILL.md';path.write_text('tampered')
        with self.assertRaises(FactoryError):self.execute(run)
        self.assertEqual(self.native.roles,[])
    def test_deadline_before_model(self):
        run=self.run_instance();run.ledger['deadline']=time.time()-1;save(run.folder/'run.json',run.ledger)
        with self.assertRaises(FactoryError):self.execute(run)
        self.assertEqual(self.native.roles,[])
    def test_resume_permissions_cannot_change(self):
        self.run_instance()
        with self.assertRaises(FactoryError):self.run_instance(resume=True,allow_local_git=True)
    def test_running_model_not_relaunched(self):
        run=self.run_instance();run.ledger['calls']=[{'role':'Planner','status':'running'}];save(run.folder/'run.json',run.ledger)
        with self.assertRaises(FactoryError):self.execute(run)
        self.assertEqual(self.native.roles,[])
    def test_archive_tamper_not_reused(self):
        result=self.released(self.run_instance());Path(result['package']).write_bytes(b'changed')
        with self.assertRaises(FactoryError):self.execute(self.run_instance(resume=True))
    def test_delivered_candidate_tamper_not_reused(self):
        result=self.released(self.run_instance());(Path(result['workspace'])/'fixture.mjs').write_text('changed')
        with self.assertRaises(FactoryError):self.execute(self.run_instance(resume=True))
    def test_release_resume_keeps_config_identity(self):
        run=self.run_instance()
        with patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'synthetic failure'}),self.assertRaises(FactoryError):self.execute(run)
        original=load(run.folder/'run.json')['release_config']
        resumed=self.run_instance(resume=True)
        with patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'same failure'}) as release,self.assertRaises(FactoryError):self.execute(resumed)
        self.assertEqual(release.call_args.args[2],original)
    def test_zero_quality_dispatch_preparation_fix_keeps_old_failure_and_budget(self):
        from factory.quality import QualityGate
        from factory.product import source_files
        run=self.run_instance()
        with patch.object(QualityGate,'attach_context',side_effect=FactoryError('历史资料缺失/哈希不匹配/依赖未验证 synthetic preparation')), self.assertRaises(FactoryError):
            self.execute(run)
        control=run.folder/'projects'/run.ledger['project_id']/'control'
        before=file_hash(control/'quality/state.json');deadline=load(run.folder/'run.json')['deadline']
        self.assertEqual(self.native.roles,['Planner','Coder'])
        changed={**source_files(),'history.py':'0'*64}
        with patch('factory.product.source_files',return_value=changed):
            self.released(self.run_instance(resume=True))
        ledger=load(run.folder/'run.json')
        self.assertEqual(file_hash(control/'quality/state.json'),before)
        self.assertEqual(ledger['deadline'],deadline)
        self.assertEqual(self.native.roles,['Planner','Coder','Tester','Reviewer','Coder','Tester','Reviewer'])
        self.assertEqual(ledger['preparation_fix']['quality_context'],'quality-goal0-product-prep')
    def test_cli_build_dispatch_and_legacy_version(self):
        from apf_cli.cli import main
        with patch('apf_cli.build.build') as build,contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['--build','中文','--out','demo','--full-access']),0)
        self.assertEqual(build.call_args.args[0].build,'中文')
        with patch('apf_cli.build.build') as build,contextlib.redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(main(['--version']),0)
        build.assert_not_called();self.assertEqual(stream.getvalue(),"AI Project Factory 1.0.0\nWit beyond measure is man's greatest treasure\n")
    def test_cli_no_authorization_no_process(self):
        from apf_cli.cli import main
        with patch('apf_cli.codex.discover_codex') as cli,contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--build','中文']),1)
        cli.assert_not_called()
    def test_unsupported_goals_preserve_full_plan_no_coder(self):
        original=self.native.run
        def extra(role,*args):
            result=original(role,*args)
            if role=='Planner':
                result['output']['plan']['goals'].append({'id':'Goal 2','title':'extra','depends_on':['Goal 1'],'scope':'保留未执行需求'})
            return result
        self.native.run=extra
        with self.assertRaises(FactoryError):self.execute(self.run_instance())
        self.assertEqual(self.native.roles,['Planner'])
        self.assertEqual(len(load(self.output/'.apf/product-plan.json')['plan']['goals']),3)
    def test_model_global_caps_cannot_restart_in_new_control(self):
        run=self.run_instance();run.ledger['calls']=[{'role':'Planner','status':'finished'}]
        wrapper=RunExecutor(self.native,run.folder,run.ledger)
        with self.assertRaises(FactoryError):wrapper.run('Planner','new',run.folder,run.folder,9,{},600)
        self.assertEqual(self.native.roles,[])
    def test_bad_release_layout_or_runtime_refused_before_coder(self):
        from factory.product import validate_release_plan
        runtime={'argv':['node','src/server.mjs','--host','127.0.0.1','--port','{port}','--data-dir','var']}
        spec={'runtime':runtime,'checks':[{'argv':['node','scripts/build.mjs']},{'argv':['node','scripts/test.mjs']}]}
        recipe={'source_files':['src/server.mjs','scripts/build.mjs','scripts/test.mjs'],'package_files':['src/server.mjs']}
        validate_release_plan({'runtime':runtime},spec,recipe)
        bad=copy.deepcopy(recipe);bad['package_files']=['dist/src/server.mjs']
        with self.assertRaises(FactoryError):validate_release_plan({'runtime':runtime},spec,bad)
        bad_runtime=copy.deepcopy(runtime);bad_runtime['argv']=bad_runtime['argv'][:-2]
        with self.assertRaises(FactoryError):validate_release_plan({'runtime':bad_runtime},spec,recipe)
    def test_no_extra_quality_round_without_repair(self):
        run=self.run_instance();run.ledger['calls']=[{'role':'Tester','status':'finished'}]*2
        wrapper=RunExecutor(self.native,run.folder,run.ledger)
        with self.assertRaises(FactoryError):wrapper.run('Tester','new',run.folder,run.folder,9,{},600)
        self.assertEqual(self.native.roles,[])
    def test_release_block_preserves_approved_stages(self):
        run=self.run_instance()
        with patch.object(Controller,'release_approved_stage',return_value={'status':'blocked','message':'synthetic build error'}),self.assertRaises(FactoryError):
            self.execute(run)
        state=load(run.folder/'projects'/run.ledger['project_id']/'control/sequence/state.json')
        self.assertEqual(set(state['completed']),{'Goal 0','Goal 1'})
        self.assertFalse((self.output/'BUILD_RESULT.json').exists())


if __name__=='__main__':unittest.main()

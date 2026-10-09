"""Independent runner fixtures only. No real CLI model or business E2E."""
import contextlib
import copy
import io
import json
import shutil
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from factory.controller import Controller, ROOT, load, save, locked
from factory.contracts import FactoryError, digest, file_hash
from factory.quality import candidate, QualityGate
from factory.revalidation import RevalidationRunner, LIMITS, original_files, SingleDispatchExecutor, main
from tests.test_quality import QualityDouble

RUN_ROOT=ROOT/'validation/goal2/test-workspaces'/('revalidation-'+uuid.uuid4().hex[:10])


class RevalidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN_ROOT.mkdir(parents=True);shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')

    def setUp(self):
        self.git_patch=patch('factory.revalidation.git_baseline',return_value={'synthetic':'no Git writes or repo init'})
        self.git_patch.start();self.addCleanup(self.git_patch.stop)
        self.agent=QualityDouble(full_access=True);self.c=Controller(RUN_ROOT,self.agent)
        self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        self.pid=self.c.create('Independent runner AgentDouble fixture, NOT real validation',900)
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid)
        self.project,self.control,self.workspace,self.completed=self.c.locate(self.pid)
        before={'state':copy.deepcopy(self.completed),'legacy_calls':copy.deepcopy(self.completed['calls']),
            'errors':[],'candidate':candidate(self.workspace),'packet_fingerprint':self.completed['packet_fingerprint'],
            'packet_file_sha256':file_hash(self.control/'task-packet.json'),
            'original_project_files':{self.project.relative_to(RUN_ROOT).as_posix()+'/'+p:h for p,h in original_files(self.project).items()}}
        self.agent.scenario='missing_output'
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid,quality_gate=True,no_auto_repair=True)
        self.assertEqual(load(self.control/'quality/state.json')['status'],'质量门槛失败')
        self.source=RUN_ROOT/'validation/goal2'/('source-'+uuid.uuid4().hex[:10]);self.source.mkdir(parents=True)
        save(self.source/'before.json',before)
        self.anchor={'files':{(self.source/'before.json').relative_to(RUN_ROOT).as_posix():{'sha256':file_hash(self.source/'before.json')},
                              (self.control/'quality/state.json').relative_to(RUN_ROOT).as_posix():{'sha256':file_hash(self.control/'quality/state.json')}}}
        save(self.source/'evidence-manifest.json',self.anchor)
        self.original=original_files(self.project)
        self.agent.scenario='normal';self.agent.roles=[];self.agent.quality_calls=[]
        self.runner=RevalidationRunner(RUN_ROOT,self.c)

    def prepare(self):
        self.prepared=self.runner.prepare(self.pid,self.source)
        self.run=Path(self.prepared['path']);self.info=load(self.run/'prepared.json')
        return self.prepared

    def execute(self,**kwargs):
        args={'authorization_id':'synthetic-test-approval','full_access':True,**kwargs}
        with contextlib.redirect_stdout(io.StringIO()):return self.runner.execute(self.prepared['run_id'],**args)

    def tamper_before(self,change):
        b=load(self.source/'before.json');change(b);save(self.source/'before.json',b)
        self.anchor['files'][(self.source/'before.json').relative_to(RUN_ROOT).as_posix()]['sha256']=file_hash(self.source/'before.json')
        save(self.source/'evidence-manifest.json',self.anchor)

    def test_01_prepare_never_initializes_cli_or_dispatches(self):
        with patch('factory.revalidation.CodexExecutor') as cli:self.prepare();cli.assert_not_called()
        self.assertEqual(self.agent.roles,[]);self.assertFalse((self.run/'authorization.json').exists())
        self.assertTrue(self.info['authorization_pending']);self.assertFalse((self.run/'control/quality').exists())
        self.assertEqual(original_files(self.project),self.original)

    def test_02_independent_success_preserves_original_failure(self):
        self.prepare();result=self.execute()
        self.assertEqual(result['status'],'质量门槛通过');self.assertEqual(self.agent.roles,['Tester','Reviewer'])
        self.assertEqual(original_files(self.project),self.original)
        self.assertEqual(load(self.control/'state.json')['status'],'质量门槛失败')
        self.assertEqual(load(self.run/'control/origin-failed-quality.json')['status'],'质量门槛失败')
        q=load(self.run/'control/quality/state.json');self.assertEqual(q['independent_revalidation']['run_id'],self.prepared['run_id'])

    def test_03_completed_state_tampered_even_with_updated_anchor_rejected(self):
        self.tamper_before(lambda b:b['state'].update(status='已失败'))
        with self.assertRaisesRegex(FactoryError,'原始完成状态'):self.prepare()

    def test_04_packet_changes_rejected(self):
        packet=load(self.control/'task-packet.json');packet['goal']='Goal 1';save(self.control/'task-packet.json',packet)
        with self.assertRaises(FactoryError):self.prepare()
        self.assertEqual(self.agent.roles,[])

    def test_05_changed_candidate_rejected_before_prepare(self):
        (self.workspace/'fixture.mjs').write_text('Synthetic changed business source')
        with self.assertRaises(FactoryError):self.prepare()

    def test_06_changed_candidate_after_prepare_zero_models(self):
        self.prepare();(self.workspace/'fixture.mjs').write_text('Synthetic changed source')
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])

    def test_07_origin_running_lock_rejects_prepare(self):
        with locked(self.control):
            with self.assertRaisesRegex(FactoryError,'已有主控'):self.prepare()

    def test_08_origin_lock_rejects_execute(self):
        self.prepare()
        with locked(self.control):
            with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])

    def test_09_source_path_escape_rejected(self):
        with self.assertRaises(FactoryError):self.runner.prepare(self.pid,RUN_ROOT/'skills')
        with self.assertRaises(FactoryError):self.runner.run_path('../outside')

    def test_10_invalid_anchor_rejected(self):
        self.anchor['files'].clear();save(self.source/'evidence-manifest.json',self.anchor)
        with self.assertRaisesRegex(FactoryError,'来源'):self.prepare()

    def test_11_source_copy_tampering_rejected(self):
        self.prepare();(self.run/'control/completion.json').write_text('{}')
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])

    def test_12_preflight_failure_zero_quality_dispatches(self):
        self.prepare();self.agent.scenario='preflight';result=self.execute()
        self.assertEqual(result['status'],'质量门槛失败');self.assertEqual(self.agent.roles,[])
        self.assertFalse((self.run/'dispatches.json').exists())
        self.assertEqual(original_files(self.project),self.original)

    def test_13_tester_failure_no_reviewer_no_repair(self):
        self.prepare();self.agent.scenario='tester_repair';result=self.execute()
        self.assertEqual(result['status'],'质量门槛失败');self.assertEqual(self.agent.roles,['Tester'])
        self.assertEqual(load(self.run/'dispatches.json')[0]['role'],'Tester')
        self.assertEqual(original_files(self.project),self.original)

    def test_14_reviewer_changes_requested_no_coder(self):
        self.prepare();self.agent.scenario='reviewer_repair';result=self.execute()
        self.assertEqual(result['status'],'质量门槛失败');self.assertEqual(self.agent.roles,['Tester','Reviewer'])
        self.assertIn('禁用自动返工',result['error'])

    def test_15_completed_resume_no_duplicate_calls(self):
        self.prepare();self.execute();calls=list(self.agent.roles)
        self.assertEqual(self.execute()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,calls)
        self.assertEqual(len(load(self.run/'dispatches.json')),2)

    def test_16_finished_tester_checkpoint_reused_only_reviewer_runs(self):
        self.prepare();original=QualityGate.call
        def interruption(gate,role,*args):
            if role=='Reviewer':raise KeyboardInterrupt()
            return original(gate,role,*args)
        with patch.object(QualityGate,'call',interruption):self.execute()
        # Real interruptions that have been marked failed remain terminal. This
        # fixture emulates a process crash before the status/error checkpoint.
        qpath=self.run/'control/quality/state.json';q=load(qpath);q['status']='Tester执行中';q['error']=None;save(qpath,q)
        self.assertEqual(self.execute()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,['Tester','Reviewer'])

    def test_17_failed_resume_does_not_retry(self):
        self.prepare();self.agent.scenario='missing_output';self.execute();calls=list(self.agent.roles)
        self.execute();self.assertEqual(self.agent.roles,calls)

    def test_18_live_process_record_blocks_resume(self):
        self.prepare();self.execute();qpath=self.run/'control/quality/state.json';q=load(qpath)
        rec=q['calls'][-1];rec['status']='running';q['status']='Reviewer审查中';save(qpath,q)
        save(self.run/'control/quality'/rec['path']/f'reviewer-{rec["number"]:02d}.process.json',{'pid':23456,'creation':'synthetic-same'})
        roles=list(self.agent.roles)
        with patch('factory.quality.process_identity',return_value={'live':True,'creation':'synthetic-same'}):self.execute()
        self.assertEqual(self.agent.roles,roles)

    def test_19_dead_process_without_checkpoint_stops_no_recall(self):
        self.prepare();self.execute();qpath=self.run/'control/quality/state.json';q=load(qpath)
        rec=q['calls'][-1];rec.update(status='running',path='calls/synthetic-lost');q['status']='Reviewer审查中';save(qpath,q)
        roles=list(self.agent.roles);self.assertEqual(self.execute()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,roles)

    def test_20_checkpoint_evidence_tampering_rejected(self):
        self.prepare();self.execute();q=load(self.run/'control/quality/state.json')
        e=q['rounds'][0]['tester']['acceptance'][0]['evidence'][0]
        (self.run/'control/quality'/q['rounds'][0]['path']/e['path']).write_text('Synthetic tamper')
        roles=list(self.agent.roles);self.assertEqual(self.execute()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,roles)

    def test_21_explicit_full_access_and_auth_required(self):
        self.prepare()
        for kw in [{'full_access':False},{'authorization_id':''}]:
            with self.assertRaises(FactoryError):self.execute(**kw)
        self.assertEqual(self.agent.roles,[])

    def test_22_permission_mode_cannot_change_on_resume(self):
        self.prepare();self.execute()
        with self.assertRaises(FactoryError):self.execute(authorization_id='different-approval')
        self.assertEqual(self.agent.roles,['Tester','Reviewer'])

    def test_23_duplicate_dispatch_fuse_and_forbidden_roles(self):
        self.prepare();self.execute();wrapper=self.c.executor;q=load(self.run/'control/quality/state.json')
        cwd=self.run/'control/quality'/q['rounds'][0]['path']/'workspace';folder=self.run/'control'
        for role in ('Tester','Reviewer','Planner','Coder','CoderRepair'):
            with self.assertRaises(FactoryError):wrapper.run(role,'synthetic',cwd,folder,3,{},900)
        self.assertEqual(self.agent.roles,['Tester','Reviewer'])

    def test_24_caps_are_persistent_and_timeout_at_most_600(self):
        self.prepare();self.execute();calls=load(self.run/'dispatches.json')
        self.assertEqual([c['role'] for c in calls],['Tester','Reviewer'])
        self.assertTrue(all(0<c['timeout_seconds']<=600 for c in calls));self.assertEqual(self.info['limits'],LIMITS)

    def test_25_wall_clock_cannot_reset(self):
        self.prepare();self.execute();auth=load(self.run/'authorization.json');auth['started_at']=time.time()-1801;save(self.run/'authorization.json',auth)
        with self.assertRaisesRegex(FactoryError,'预算耗尽'):self.execute()
        self.assertEqual(self.agent.roles,['Tester','Reviewer'])

    def test_26_wrong_run_identity_rejected(self):
        self.prepare();state=load(self.run/'control/state.json');state['independent_revalidation']['run_id']='rv-000000000000';save(self.run/'control/state.json',state)
        with self.assertRaises(FactoryError):self.execute()

    def test_27_prepared_source_escape_even_with_new_receipt_rejected(self):
        self.prepare();info=load(self.run/'prepared.json');info['sources'][0]['source']='../outside';save(self.run/'prepared.json',info)
        save(self.run/'receipt.json',{'prepared_sha256':file_hash(self.run/'prepared.json')})
        with self.assertRaises(FactoryError):self.execute()

    def test_28_existing_run_never_overwritten(self):
        self.prepare();old=file_hash(self.run/'prepared.json')
        with self.assertRaises(FileExistsError):self.runner.prepare(self.pid,self.source,self.prepared['run_id'])
        self.assertEqual(file_hash(self.run/'prepared.json'),old)

    def test_29_cli_prepare_rejects_permission_and_execute_rejects_retry(self):
        with patch('factory.revalidation.RevalidationRunner',return_value=self.runner),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['--prepare','--project-id',self.pid,'--source-evidence',str(self.source),'--full-access']),1)
        with self.assertRaises(SystemExit),contextlib.redirect_stderr(io.StringIO()):main(['--execute','--retry'])
        self.assertEqual(self.agent.roles,[])

    def test_30_unmatched_old_quality_cannot_be_imported(self):
        self.prepare();self.execute();qpath=self.run/'control/quality/state.json';q=load(qpath);q.pop('independent_revalidation');save(qpath,q)
        roles=list(self.agent.roles)
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,roles)

    def test_31_origin_current_status_cannot_hide_failed_quality(self):
        state=load(self.control/'state.json');state['status']='已完成';save(self.control/'state.json',state)
        with self.assertRaisesRegex(FactoryError,'当前失败状态'):self.prepare()
        self.assertEqual(self.agent.roles,[])

    def test_32_origin_state_change_after_prepare_zero_dispatches(self):
        self.prepare();state=load(self.control/'state.json');state['error']='Synthetic altered history';save(self.control/'state.json',state)
        with self.assertRaisesRegex(FactoryError,'原历史'):self.execute()
        self.assertEqual(self.agent.roles,[])


if __name__=='__main__':unittest.main()

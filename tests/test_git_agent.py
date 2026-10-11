"""Real local git.exe integration; quality inputs are labelled contract fixtures.

Only newly created Goal 4 test workspaces receive Git writes. No model calls.
The production quality verifier is mocked only for Git-operation fixtures; its
rejection of synthetic approvals is tested separately without that mock.
"""
import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from factory.controller import Controller, ROOT, load, save, manifest, locked
from factory.contracts import FactoryError, digest, file_hash
from factory.git_agent import GitAgent, sensitive
from factory.quality import candidate

RUN_ROOT=ROOT/'validation/goal4/test-workspaces'/uuid.uuid4().hex[:10]


class GitAgentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which('git'):raise unittest.SkipTest('Local Git not installed')
        RUN_ROOT.mkdir(parents=True)
        cls.proofs=[]

    def setUp(self):
        self.c=Controller(RUN_ROOT)
        self.pid=self.c.create('Synthetic approval metadata for real Git operations; no model calls')
        self.project,self.control,self.workspace,_=self.c.locate(self.pid)
        (self.workspace/'app.py').write_text('print("offline fixture")\n',encoding='utf-8')
        (self.workspace/'README.md').write_text('Contract fixture; not a real business acceptance.\n',encoding='utf-8')
        (self.control/'sequence').mkdir()
        self.packet={'goal':'Goal 0','project_id':self.pid,'workspace':str(self.workspace),'allow_write':[str(self.workspace)]}
        save(self.control/'task-packet.json',self.packet)
        self.receipt={'project_id':self.pid,'goal':'Goal 0','status':'质量门槛通过','candidate':candidate(self.workspace),
                      'packet_fingerprint':digest(self.packet),'files':{'control/task-packet.json':file_hash(self.control/'task-packet.json')},
                      'scope':'Synthetic contract approval fixture, not real Tester/Reviewer approval'}
        self.bind()
        self.a=GitAgent(self.c,self.pid)
        self.policy={'version':1,'project_id':self.pid,'authorization_id':'goal4-isolated-test-only',
                     'allow_init':True,'allow_local_commit':True,'branch':'main'}
        self.a.configure(self.policy)

    def bind(self):
        name='goal0-completion.json' if self.receipt['goal']=='Goal 0' else 'goal1-completion.json'
        save(self.control/'sequence'/name,self.receipt)
        old=load(self.control/'sequence/state.json') if (self.control/'sequence/state.json').exists() else {'project_id':self.pid,'completed':{}}
        old['completed'][self.receipt['goal']]={'path':name,'sha256':file_hash(self.control/'sequence'/name)}
        save(self.control/'sequence/state.json',old)

    def git(self,*args,allowed=(0,)):
        # Refuse even test-helper writes if a path is not our new test workspace.
        self.assertTrue(self.workspace.resolve().is_relative_to(RUN_ROOT.resolve()))
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_GLOBAL=os.devnull)
        res=subprocess.run(['git','--no-optional-locks',*args],cwd=self.workspace,env=env,capture_output=True)
        self.assertIn(res.returncode,allowed,res.stderr.decode(errors='replace'))
        return res.stdout.decode('utf-8').strip()

    def init(self):
        self.git('init','--initial-branch=main','--template=')
        self.git('config','user.name','APF Isolated Test')
        self.git('config','user.email','apf-test@example.invalid')

    def commit(self,goal='Goal 0'):
        with patch.object(self.a,'_validate_quality',return_value=None):return self.a.commit(goal)

    def test_01_real_init_commit_content_and_idempotence(self):
        # Agent performs real initialization. The test supplies a synthetic
        # local identity after init, never commits under a personal identity.
        real=self.a._git
        def local_test_identity(*args,**kw):
            result=real(*args,**kw)
            if args[0]=='init':
                self.git('config','user.name','APF Isolated Test')
                self.git('config','user.email','apf-test@example.invalid')
            return result
        with patch.object(self.a,'_git',side_effect=local_test_identity):result=self.commit()
        self.assertTrue((self.workspace/'.git').is_dir())
        # Identity can exist in user's global config; do not rely on it.
        if result['status']=='committed':
            self.assertEqual(self.a._tree('HEAD'),self.receipt['candidate']['files'])
        else:
            self.assertEqual(result['status'],'blocked');self.assertIn('身份',result['message'])
            self.git('config','user.name','APF Isolated Test');self.git('config','user.email','apf-test@example.invalid')
            result=self.commit()
        self.assertEqual(result['status'],'committed')
        sha=result['commit'];record=load(self.project/result['record'])
        self.assertEqual(record['packet_fingerprint'],digest(self.packet))
        self.assertEqual(record['approval']['sha256'],file_hash(self.control/'sequence/goal0-completion.json'))
        self.assertEqual(self.git('rev-list','--count','HEAD'),'1')
        self.assertEqual(self.a._tree('HEAD'),self.receipt['candidate']['files'])
        self.assertEqual(self.commit()['status'],'already_versioned')
        self.assertEqual(self.git('rev-list','--count','HEAD'),'1')
        self.assertFalse(self.a.inspect()['staged'])
        self.assertEqual(candidate(self.workspace),self.receipt['candidate'])
        self.assertEqual(manifest(self.workspace),self.receipt['candidate']['files'])
        self.proofs.append({'project':self.project.relative_to(ROOT).as_posix(),'quality_input':'synthetic contract fixture; production verifier mocked',
                            'git_execution':'real git.exe','commit':sha,'log':self.git('log','--oneline'),
                            'tree':self.git('ls-tree','-r','HEAD'),'record':record,'real_model_calls':0})

    def test_02_read_does_not_discover_parent_factory_repo(self):
        self.assertFalse(self.c.inspect_project_git(self.pid)['repository'])
        self.assertFalse((self.workspace/'.git').exists())

    def test_03_default_no_authorization_no_init(self):
        (self.a.folder/'policy.json').unlink()
        self.assertEqual(self.commit()['status'],'authorization_required')
        self.assertFalse((self.workspace/'.git').exists())

    def test_04_init_not_authorized(self):
        self.policy['allow_init']=False;self.a.configure(self.policy)
        self.assertEqual(self.commit()['status'],'authorization_required')
        self.assertFalse((self.workspace/'.git').exists())

    def test_05_local_commit_not_authorized(self):
        self.policy['allow_local_commit']=False;self.a.configure(self.policy)
        self.assertEqual(self.commit()['status'],'authorization_required')

    def test_06_unapproved_stage(self):
        save(self.control/'sequence/state.json',{'project_id':self.pid,'completed':{}})
        self.assertEqual(self.commit()['status'],'blocked');self.assertFalse((self.workspace/'.git').exists())

    def test_07_real_verifier_rejects_synthetic_receipt(self):
        result=self.a.commit('Goal 0')
        self.assertEqual(result['status'],'blocked');self.assertIn('QualityGate',result['message'])
        self.assertFalse((self.workspace/'.git').exists())

    def test_08_candidate_drift(self):
        (self.workspace/'app.py').write_text('different')
        self.assertEqual(self.commit()['status'],'blocked');self.assertFalse((self.workspace/'.git').exists())

    def test_09_receipt_hash_tamper(self):
        (self.control/'sequence/goal0-completion.json').write_text('{}')
        self.assertEqual(self.commit()['status'],'blocked')

    def test_10_packet_source_tamper(self):
        (self.control/'task-packet.json').write_text('{}')
        self.assertEqual(self.commit()['status'],'blocked')

    def test_11_unrelated_working_change(self):
        self.init();(self.workspace/'validation').mkdir();(self.workspace/'outside.txt').write_text('user change')
        result=self.commit();self.assertEqual(result['status'],'blocked')
        self.assertEqual((self.workspace/'outside.txt').read_text(),'user change')
        self.assertEqual(self.git('rev-list','--all','--count'),'0')

    def test_12_existing_staging_is_not_overwritten(self):
        self.init();self.git('add','--','app.py');before=(self.workspace/'.git/index').read_bytes()
        self.assertEqual(self.commit()['status'],'blocked')
        self.assertEqual(before,(self.workspace/'.git/index').read_bytes())

    def test_13_branch_mismatch(self):
        self.init();self.policy['branch']='approved-branch';self.a.configure(self.policy)
        self.assertEqual(self.commit()['status'],'blocked');self.assertEqual(self.git('branch','--show-current'),'main')

    def test_14_gitfile_external_repository_refused(self):
        (self.workspace/'.git').write_text('gitdir: ../outside')
        with self.assertRaisesRegex(FactoryError,'外部'):self.a.inspect()

    def test_15_sensitive_unapproved_env_never_committed(self):
        self.init();(self.workspace/'.env').write_text('private placeholder')
        self.assertEqual(self.commit()['status'],'blocked')
        self.assertTrue((self.workspace/'.env').exists());self.assertEqual(self.git('rev-list','--all','--count'),'0')

    def test_16_sensitive_approved_source_rejected(self):
        (self.workspace/'app.py').write_text('api_key="sk-'+ 'a'*32+'"')
        self.receipt['candidate']=candidate(self.workspace);self.bind()
        self.assertEqual(self.commit()['status'],'blocked');self.assertFalse((self.workspace/'.git').exists())

    def test_17_generated_cache_not_in_commit(self):
        self.init();(self.workspace/'node_modules').mkdir();(self.workspace/'node_modules/cache').write_text('unrelated cache')
        result=self.commit();self.assertEqual(result['status'],'committed')
        self.assertNotIn('node_modules/cache',self.git('ls-tree','-r','--name-only','HEAD'))
        self.assertTrue((self.workspace/'node_modules/cache').exists())

    def test_18_missing_identity_safe_failure(self):
        self.init();self.git('config','user.name','');self.git('config','user.email','')
        # Explicitly disable auto identity guessing for this isolated repo.
        self.git('config','user.useConfigOnly','true')
        result=self.commit()
        self.assertEqual(result['status'],'blocked');self.assertIn('身份',result['message'])
        self.assertFalse(self.a.inspect()['staged'])

    def test_19_command_failure_preserves_sources_and_approval(self):
        self.init();before={p:file_hash(self.workspace/p) for p in self.receipt['candidate']['files']}
        pin=file_hash(self.control/'sequence/goal0-completion.json');real=self.a._git
        def fail(*args,**kw):
            if args[0]=='commit':raise FactoryError('Git commit退出1；injected failure, no retry')
            return real(*args,**kw)
        with patch.object(self.a,'_git',side_effect=fail):result=self.commit()
        self.assertEqual(result['status'],'blocked');self.assertEqual(self.git('rev-list','--all','--count'),'0')
        self.assertEqual(before,{p:file_hash(self.workspace/p) for p in before})
        self.assertEqual(pin,file_hash(self.control/'sequence/goal0-completion.json'))
        self.assertTrue(self.a.inspect()['staged'])

    def test_20_postcommit_record_interruption_recovers_without_commit(self):
        self.init()
        with patch.object(self.a,'_record',side_effect=OSError('injected record disk failure')):self.assertEqual(self.commit()['status'],'blocked')
        self.assertEqual(self.git('rev-list','--count','HEAD'),'1')
        self.assertEqual(self.commit()['status'],'recovered')
        self.assertEqual(self.git('rev-list','--count','HEAD'),'1')

    def test_21_no_changes_no_empty_commit(self):
        self.init();self.git('add','--',*sorted(self.receipt['candidate']['files']))
        self.git('commit','-m','User existing exact source')
        result=self.commit();self.assertEqual(result['status'],'no_changes')
        self.assertEqual(self.git('rev-list','--count','HEAD'),'1')

    def test_22_two_approved_goals_distinct_versions(self):
        self.init();first=self.commit();self.assertEqual(first['status'],'committed')
        (self.workspace/'app.py').write_text('print("incremental fixture")\n')
        self.packet['goal']='Goal 1';stage=self.control/'goals/goal-1';stage.mkdir(parents=True)
        save(stage/'task-packet.json',self.packet)
        # Fixture old packet pins remain stable in a separate stage control.
        self.receipt['goal']='Goal 1';self.receipt['packet_fingerprint']=digest(self.packet)
        self.receipt['files']={'control/goals/goal-1/task-packet.json':file_hash(stage/'task-packet.json')}
        self.receipt['candidate']=candidate(self.workspace);self.bind()
        second=self.commit('Goal 1');self.assertEqual(second['status'],'committed')
        self.assertNotEqual(first['commit'],second['commit']);self.assertEqual(self.git('rev-list','--count','HEAD'),'2')

    def test_23_traversal_and_personal_config(self):
        self.receipt['candidate']['files']['../outside']=digest(b'x');self.bind()
        self.assertEqual(self.commit()['status'],'blocked')
        for name,data in [('credentials.json',b'{}'),('notes.md',b'C:\\Users\\private\\secret'),('.env',b'x')]:
            with self.assertRaises(FactoryError):sensitive(name,data)

    def test_24_project_lock_prevents_git_mutation(self):
        with locked(self.control):
            with self.assertRaises(FactoryError):self.commit()
        self.assertFalse((self.workspace/'.git').exists())

    def test_25_attributes_cannot_rewrite_approved_bytes(self):
        self.init();(self.workspace/'.gitattributes').write_text('*.py text eol=lf\n')
        (self.workspace/'app.py').write_bytes(b'print("x")\r\n')
        self.receipt['candidate']=candidate(self.workspace);self.bind()
        self.assertEqual(self.commit()['status'],'blocked')
        self.assertEqual(self.git('rev-list','--all','--count'),'0')

    def test_26_hooks_not_executed(self):
        self.init();hook=self.workspace/'.git/hooks/pre-commit';hook.parent.mkdir(exist_ok=True)
        hook.write_text('#!/bin/sh\necho executed > hook-ran\nexit 1\n');hook.chmod(0o755)
        self.assertEqual(self.commit()['status'],'committed');self.assertFalse((self.workspace/'hook-ran').exists())

    def test_27_filter_refused_before_status(self):
        self.init();self.git('config','filter.unsafe.clean','echo unexpected')
        with self.assertRaisesRegex(FactoryError,'filter'):self.a.inspect()
        self.assertEqual(self.commit()['status'],'blocked')

    def test_28_inherited_git_redirection_cannot_target_main(self):
        self.init()
        with patch.dict(os.environ,{'GIT_DIR':str(ROOT/'.git'),'GIT_WORK_TREE':str(ROOT),'GIT_INDEX_FILE':str(ROOT/'.git/index')}):
            self.assertEqual(self.commit()['status'],'committed')
        self.assertEqual(self.git('rev-list','--count','HEAD'),'1')

    def quality_fixture(self, reviewer_mode='read-only', shared_thread=False, synthetic_thread=False):
        """Metadata-only fixtures for dispatch provenance, not model approvals."""
        folder=self.control/'quality';folder.mkdir()
        row={'candidate':self.receipt['candidate'],'tester':{'status':'passed'},'reviewer':{'decision':'approved'}}
        first=str(uuid.uuid4())
        for role in ('tester','reviewer'):
            thread=first if role=='tester' or shared_thread else str(uuid.uuid4())
            if synthetic_thread:thread='AgentDouble-'+thread
            path=folder/(role+'-execution.json')
            save(path,{'role':role.capitalize(),'version':'codex-cli contract fixture','exit_code':0,'timed_out':False,
                       'turn_completed':True,'thread_ids':[thread],
                       'execution_mode':reviewer_mode if role=='reviewer' else 'danger-full-access'})
            row[role+'_execution']={'path':path.name,'sha256':file_hash(path)}
            self.receipt['files'][path.relative_to(self.project).as_posix()]=file_hash(path)
        save(folder/'state.json',{'version':'2.0','status':'质量门槛通过','rounds':[row]})
        for path in (folder/'state.json',self.control/'state.json'):
            self.receipt['files'][path.relative_to(self.project).as_posix()]=file_hash(path)
        self.bind()

    def test_29_reviewer_must_be_read_only_before_git(self):
        self.quality_fixture(reviewer_mode='danger-full-access')
        with patch('factory.git_agent.QualityGate.result') as semantic:
            result=self.a.commit('Goal 0')
        self.assertEqual(result['status'],'blocked');semantic.assert_not_called()
        self.assertFalse((self.workspace/'.git').exists())

    def test_30_quality_threads_must_be_independent(self):
        self.quality_fixture(shared_thread=True)
        with patch('factory.git_agent.QualityGate.result') as semantic:
            result=self.a.commit('Goal 0')
        self.assertEqual(result['status'],'blocked');self.assertIn('独立',result['message']);semantic.assert_not_called()

    def test_31_agent_double_threads_not_production_approval(self):
        self.quality_fixture(synthetic_thread=True)
        with patch('factory.git_agent.QualityGate.result') as semantic:
            result=self.a.commit('Goal 0')
        self.assertEqual(result['status'],'blocked');semantic.assert_not_called()

    def test_32_version_metadata_tamper_not_idempotent_success(self):
        self.init();result=self.commit();self.assertEqual(result['status'],'committed')
        path=self.project/result['record'];record=load(path);record['packet_fingerprint']='0'*64;save(path,record)
        self.assertEqual(self.commit()['status'],'blocked');self.assertEqual(self.git('rev-list','--count','HEAD'),'1')

    def test_33_cli_policy_utf8_bom_is_explicit_configuration_only(self):
        from factory.git_agent import main
        source=self.control/'input-policy.json';source.write_text(json.dumps(self.policy),encoding='utf-8-sig')
        with patch('sys.argv',['git_agent','--root',str(RUN_ROOT),'--project-id',self.pid,'--configure',str(source)]), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(),0)
        self.assertEqual(load(self.a.folder/'policy.json'),self.policy)
        self.assertFalse((self.workspace/'.git').exists())

    def test_34_metadata_escape_rejected_before_git_reads_config(self):
        self.init()
        from factory.contracts import safe_path as original
        def guarded(path,root,*args,**kw):
            if Path(path)==self.workspace/'.git/config':raise FactoryError('路径包含符号链接或 junction')
            return original(path,root,*args,**kw)
        with patch('factory.git_agent.safe_path',side_effect=guarded), patch.object(self.a,'_git') as command:
            with self.assertRaisesRegex(FactoryError,'路径'):self.a.inspect()
        command.assert_not_called()

    def test_35_sequence_continues_after_real_goal0_git_commit(self):
        # Reuse the existing serial/QualityGate fixture, but redirect its root
        # BEFORE creation. Real Git may never touch old Goal3 test directories.
        from tests.test_sequence import SequenceTests
        if not (RUN_ROOT/'skills').exists():shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')
        fixture=SequenceTests('test_01_two_goals_share_source_but_distinct_packets_and_quality')
        with patch('tests.test_sequence.RUN_ROOT',RUN_ROOT):fixture.setUp()
        self.assertTrue(fixture.workspace.resolve().is_relative_to(RUN_ROOT.resolve()))
        self.assertEqual(fixture.run_chain('Goal 0')['status'],'阶段完成')
        a=GitAgent(fixture.c,fixture.pid);policy={**self.policy,'project_id':fixture.pid};a.configure(policy)
        self.workspace=fixture.workspace;self.init()
        with patch.object(a,'_validate_quality',return_value=None):first=a.commit('Goal 0')
        self.assertEqual(first['status'],'committed')
        self.assertEqual(fixture.run_chain()['status'],'两阶段已完成')
        with patch.object(a,'_validate_quality',return_value=None):second=a.commit('Goal 1')
        self.assertEqual(second['status'],'committed');self.assertEqual(self.git('rev-list','--count','HEAD'),'2')
        roles=list(fixture.agent.roles);fixture.run_chain();self.assertEqual(fixture.agent.roles,roles)
        self.proofs.append({'project':fixture.project.relative_to(ROOT).as_posix(),'quality_input':'existing Sequence/QualityGate AgentDouble fixture; Git approval provenance verifier mocked',
                            'git_execution':'real git.exe','goal0_commit':first['commit'],'goal1_commit':second['commit'],
                            'log':self.git('log','--oneline'),'tree':self.git('ls-tree','-r','HEAD'),'no_repeated_agents_on_resume':True})

    @classmethod
    def tearDownClass(cls):
        save(RUN_ROOT/'REAL_GIT_PROOF.json',{'quality_inputs':'synthetic fixtures only; no new business quality approval',
             'real_model_calls':0,'real_git_operations':cls.proofs,'test_repos_preserved_for_inspection':True})


if __name__=='__main__':unittest.main()

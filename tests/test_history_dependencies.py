"""AC-012 deterministic fixtures. Original history is read-only, no real Agents."""
import contextlib
import copy
import io
import shutil
import stat
import unittest
import uuid
from unittest.mock import patch
from factory.controller import ROOT,Controller,load,save,manifest
from factory.contracts import FactoryError,file_hash
from factory.quality import QualityGate,candidate
from factory.history import history_dependencies
from tests.test_quality import QualityDouble

RUN_ROOT=ROOT/'validation/goal2/test-workspaces'/('history-'+uuid.uuid4().hex[:10])
ORIGINAL=ROOT/'projects/p-dc1e9d42b5ae/workspace'

class HistoryDependencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN_ROOT.mkdir(parents=True);shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')
    def setUp(self):
        self.agent=QualityDouble();self.c=Controller(RUN_ROOT,self.agent);self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        self.pid=self.c.create('History dependency fixture, not actual business validation',10)
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid)
        self.project,self.control,self.workspace,self.state=self.c.locate(self.pid)
        rows=load(ROOT/'validation/goal2/real-revalidation-20261009T153459-afe247/historical-reference-availability.json')['selected_acceptance_document_references']
        self.names=[]
        for r in rows:
            name=str(__import__('pathlib').Path(r['original_path']).relative_to(ORIGINAL)).replace('\\','/')
            target=self.workspace/name;target.parent.mkdir(parents=True,exist_ok=True)
            # Original bytes are copied, not executed or changed. This fixture's
            # own index avoids adopting a historical state as a new approval.
            shutil.copy2(ORIGINAL/name,target);self.names.append(name)
        h=self.workspace/'validation/goal0';h.mkdir(parents=True,exist_ok=True)
        (h/'acceptance.md').write_text('# SYNTHETIC fixture dependency index, no real approval\n'+'\n'.join('- `'+n+'`' for n in self.names),encoding='utf-8')
        save(h/'session-environment.json',{'fixture':True});save(h/'source-sha256.json',{'fixture':True})
        # Original archived status copied above cites extra archives. Treat its
        # actual references faithfully by adding their raw docs/logs and let the
        # test's explicitly synthetic status narrow to this fixture's index.
        self.status_name='validation/history-20261009-095732-444/PROJECT_STATUS.md'
        (self.workspace/self.status_name).write_text('Synthetic archived status; `validation/goal0/build.log`\n',encoding='utf-8')
        target=self.workspace/'validation/history-20261009-095732-444/goal0/acceptance.md'
        target.write_text('Synthetic indirect index; `build.log` and `test.log`\n',encoding='utf-8')
        self.refresh()
        self.gate=QualityGate(self.c,self.project,self.control,self.workspace,self.state,allow_repair=False)
    def refresh(self):
        d=load(self.control/'completion.json');d['workspace_manifest']=manifest(self.workspace);save(self.control/'completion.json',d)
    def attach(self):
        self.row=self.gate.make_round();self.round_root=self.gate.folder/self.row['path'];return self.row
    def test_01_eleven_original_paths_assembled_and_hashed(self):
        # Byte-copy primitive test only: synthetic selected plan, not an assertion
        # that the actual graph is complete (actual unknowns tested in test_13).
        shutil.copy2(ORIGINAL/self.status_name,self.workspace/self.status_name);self.refresh()
        plan={'ready':True,'unverified':[],'candidate_fingerprint':candidate(self.workspace)['fingerprint'],
              'files':[{'source':n,'sha256':file_hash(self.workspace/n),'kind':'history'} for n in self.names]}
        with patch.object(self.gate,'history_plan',return_value=plan):
            self.attach();entries={e['source']:e for e in self.row['context']['history']}
            for n in self.names:
                self.assertIn(n,entries);self.assertEqual(file_hash(self.round_root/entries[n]['path']),file_hash(ORIGINAL/n))
            self.gate.verify_context(self.row)
        self.assertEqual(self.agent.quality_calls,[])
    def test_02_indirect_markdown_and_json_index_closure(self):
        h=self.workspace/'validation/goal0';(h/'acceptance.md').write_text('Synthetic: `nested.json`');save(h/'nested.json',{'path':'validation/goal0/deep.log'})
        (h/'deep.log').write_text('synthetic leaf');self.refresh();self.attach()
        self.assertIn('validation/goal0/deep.log',self.gate.history_files())
    def test_03_each_of_eleven_missing_dependencies_zero_calls(self):
        for n in self.names:
            p=self.workspace/n;raw=p.read_bytes();p.unlink()
            try:
                with self.subTest(n=n),self.assertRaises(FactoryError):self.gate.history_files()
            finally:p.write_bytes(raw)
        self.assertEqual(self.agent.quality_calls,[])
    def test_04_original_dependency_tampering_refused(self):
        (self.workspace/self.names[0]).write_text('synthetic corrupted original')
        with self.assertRaises(FactoryError):self.attach()
    def test_05_copy_tampering_refused(self):
        self.attach();e=self.row['context']['history'][0];p=self.round_root/e['path'];p.chmod(stat.S_IWRITE);p.write_text('synthetic corrupted copy')
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)
    def test_06_typed_forged_hash_rejected(self):
        save(self.workspace/'validation/goal0/source-sha256.json',{'files':[{'path':self.names[0],'sha256':'0'*64}]});self.refresh()
        with self.assertRaises(FactoryError):self.attach()
    def test_07_explicit_escaping_refs_rejected(self):
        for text in ['`../outside.log`','[evidence](C:/outside.log)','[evidence](/outside.log)']:
            (self.workspace/'validation/goal0/acceptance.md').write_text(text);self.refresh()
            with self.subTest(text=text),self.assertRaises(FactoryError):self.gate.history_files()
    def test_08_reparse_path_rejected(self):
        self.attach();e=self.row['context']['history'][0]
        with patch('pathlib.Path.is_junction',lambda p:str(p)==str(self.workspace/e['source']),create=True):
            with self.assertRaises(FactoryError):self.gate.verify_context(self.row)
    def test_09_candidate_rebinding_refused(self):
        self.attach();self.row['context']['candidate_fingerprint']='0'*64
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)
    def test_10_history_delivery_and_current_records_separate(self):
        self.attach();self.gate.basic(self.row);prompt=self.gate.tester_prompt(self.row)
        ctx=load(self.round_root/self.row['context']['indices'][0]['path'])
        self.assertTrue(ctx['history']);self.assertTrue(ctx['delivery']);self.assertTrue(ctx['run_records']);self.assertTrue(ctx['artifacts'])
        self.assertTrue(all(e['path'].startswith('context/history/') for e in ctx['history']))
        self.assertTrue(all(e['path'].startswith('context/delivery/') for e in ctx['delivery']))
        self.assertNotIn('validation/',candidate(self.round_root/'workspace')['files'])
        self.assertEqual(candidate(self.workspace),candidate(self.round_root/'workspace'))
        self.assertIn('资料齐备预检不是通过结论',prompt)
    def test_11_metadata_alone_cannot_pass(self):
        self.attach();self.gate.basic(self.row);prompt=self.gate.tester_prompt(self.row)
        raw=self.agent.run('Tester',prompt,self.round_root/'workspace',self.control,1,{},10)
        value=raw['output'];e=self.row['context']['delivery'][0]
        value['acceptance'][0]['evidence']=[{k:e[k] for k in ('path','sha256')}]
        with self.assertRaisesRegex(FactoryError,'历史记录不能单独'):self.gate.result(value,'Tester',self.row,raw)
    def test_12_actual_second_blocked_result_not_rewritten(self):
        p=ROOT/'validation/goal2/revalidations/rv-f04210b3a29d/control/quality/calls/01-tester/output.json';h=file_hash(p);raw=load(p)
        self.assertEqual(raw['status'],'blocked');self.assertEqual(raw['acceptance'][-1]['result'],'unverified');self.assertEqual(file_hash(p),h)
    def test_13_actual_three_archive_gaps_are_disclosed_not_blocking(self):
        plan=history_dependencies(ORIGINAL,load(ORIGINAL.parent/'control/completion.json'),candidate(ORIGINAL),load)
        self.assertTrue(plan['ready']);self.assertGreater(len(plan['files']),11)
        self.assertEqual(plan['unverified'],[]);self.assertEqual(len(plan['archive_warnings']),3)
        self.assertTrue(all(e['result']=='unverified' and not e['blocking'] for e in plan['archive_warnings']))
        self.assertTrue(any('dab1ed47' in e['reason'] for e in plan['archive_warnings']))
        reader=QualityGate.__new__(QualityGate);reader.control=ORIGINAL.parent/'control';reader.workspace=ORIGINAL;reader.load=load
        reader.packet=load(reader.control/'task-packet.json')
        self.assertEqual(len(reader.history_files()),38)
    def test_14_missing_index_stops_dispatch_before_registration(self):
        (self.workspace/'validation/goal0/acceptance.md').write_text('Required `missing-index.json`');self.refresh()
        with contextlib.redirect_stdout(io.StringIO()):result=self.gate.run()
        self.assertEqual(result['status'],'质量门槛失败');self.assertEqual(self.agent.quality_calls,[]);self.assertEqual(self.gate.q['calls'],[])
    def test_15_declared_not_generated_stays_historical_fact(self):
        (self.workspace/'validation/goal0/acceptance.md').write_text('missing.png：计划产物，未生成。',encoding='utf-8');self.refresh();self.attach()
        plan=self.row['context']['dependencies'];self.assertTrue(plan['declared_not_generated']);self.assertNotIn('validation/goal0/missing.png',self.gate.history_files())
    def test_16_delivery_copy_and_origin_tampering_fail(self):
        self.attach();e=self.row['context']['delivery'][0];(self.round_root/e['path']).write_text('{}')
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)
    def test_17_context_cannot_relabel_history_as_current(self):
        self.attach();self.row['context']['history'][0]['path']='workspace/validation/fake.json'
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)
    def test_18_current_snapshot_binding_cannot_change(self):
        self.attach();p=self.round_root/'context/run-records/before-dispatch.json';d=load(p);d['packet_fingerprint']='0'*64;save(p,d)
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)

    def test_19_preflight_is_persisted_and_tampering_rejected(self):
        self.attach();p=self.round_root/self.row['context']['preflight']['path'];d=load(p)
        self.assertTrue(d['ready']);self.assertEqual(d['registered_quality_calls'],0)
        d['ready']=False;save(p,d)
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)

    def test_20_delivery_original_change_rejected(self):
        self.attach();save(self.control/'packet-validation.json',{'synthetic':'tampering'})
        with self.assertRaises(FactoryError):self.gate.verify_context(self.row)

    def actual_archive_fixture(self):
        """Copy the already selected graph, never search or execute business code.

        Completion metadata here belongs to an AgentDouble fixture, not to the
        real task. Finalize the fixture before exercising its dispatch guard.
        """
        plan=history_dependencies(ORIGINAL,load(ORIGINAL.parent/'control/completion.json'),candidate(ORIGINAL),load)
        for node in plan['files']:
            target=self.workspace/node['source'];target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ORIGINAL/node['source'],target)
        self.refresh()
        self.gate.q['initial_control_manifest']['completion.json']=file_hash(self.control/'completion.json')
        self.gate.checkpoint()
        return self.gate.history_plan()

    def test_21_only_three_gaps_can_enter_synthetic_tester_no_auto_pass(self):
        plan=self.actual_archive_fixture();self.assertTrue(plan['ready']);self.assertEqual(len(plan['archive_warnings']),3)
        self.agent.scenario='missing_output'
        with contextlib.redirect_stdout(io.StringIO()):result=self.gate.run()
        self.assertEqual(self.agent.quality_calls,['Tester'])
        self.assertEqual(result['status'],'质量门槛失败')  # entering Tester is not approval
        self.assertEqual(len(self.gate.q['calls']),1)

    def test_22_current_and_critical_sources_missing_still_refused(self):
        self.actual_archive_fixture()
        for name in ('README.zh-CN.md','validation/goal0/acceptance.md','validation/goal0/build-recheck.log'):
            path=self.workspace/name;raw=path.read_bytes();path.unlink()
            try:
                with self.subTest(name=name),self.assertRaises(FactoryError):self.gate.history_files()
            finally:path.write_bytes(raw)
        self.assertEqual(self.agent.quality_calls,[])

    def test_23_required_hash_and_current_bytes_cannot_be_forged(self):
        self.actual_archive_fixture()
        d=load(self.control/'completion.json');original=copy.deepcopy(d)
        d['workspace_manifest']['validation/goal0/build-recheck.log']='0'*64;save(self.control/'completion.json',d)
        with self.assertRaises(FactoryError):self.gate.history_files()
        save(self.control/'completion.json',original)
        (self.workspace/'README.zh-CN.md').write_text('tampered current delivery',encoding='utf-8')
        with self.assertRaises(FactoryError):self.gate.history_files()
        self.assertEqual(self.agent.quality_calls,[])

    def test_24_exception_requires_original_parent_bytes_even_if_reindexed(self):
        self.actual_archive_fixture()
        path=self.workspace/'validation/history-20261009-095808-578/goal0/acceptance.md'
        path.write_text(path.read_text(encoding='utf-8')+'\nModified fixture parent\n',encoding='utf-8')
        with self.assertRaises(FactoryError):self.gate.history_files()
        self.refresh()  # a forged completion hash cannot inherit the exception
        plan=self.gate.history_plan();self.assertFalse(plan['ready'])
        self.assertTrue(any(e['reference']=='PROJECT_STATUS.md' for e in plan['unverified']))

    def test_25_no_general_exemption_for_unknown_history_or_changed_index(self):
        self.actual_archive_fixture()
        path=self.workspace/'validation/goal0/acceptance.md';raw=path.read_bytes()
        path.write_text(path.read_text(encoding='utf-8')+'\n`missing-critical.log`\n',encoding='utf-8');self.refresh()
        with self.assertRaises(FactoryError):self.gate.history_files()
        path.write_bytes(raw);self.refresh()
        path=self.workspace/'validation/history-20261009-095732-444/goal0/source-sha256.json'
        path.write_text(path.read_text(encoding='utf-8').replace('dab1ed47ae7a127d46fc745f2bdcc3da4bdeff53e40c20ada1394c16fbe0d1a1','f'*64),encoding='utf-8');self.refresh()
        with self.assertRaises(FactoryError):self.gate.history_files()

    def test_26_warnings_persist_in_index_and_both_roles_context(self):
        self.actual_archive_fixture();self.attach();self.gate.basic(self.row)
        for role in ('Tester','Reviewer'):
            ctx=self.gate.context(self.row,role);policy=ctx['ac012_review_policy']
            self.assertEqual(len(policy['archive_warnings']),3)
            index=load(self.round_root/ctx['evidence_index']['path'])
            self.assertEqual(index['archive_warnings'],policy['archive_warnings'])
            self.assertIn('当前',policy['focus']);self.assertIn('披露',policy['disclosure'])
        self.assertEqual(self.agent.quality_calls,[])

    def test_27_noncritical_warning_does_not_relax_result_semantics(self):
        self.actual_archive_fixture();self.attach();self.gate.basic(self.row)
        raw=self.agent.run('Tester',self.gate.tester_prompt(self.row),self.round_root/'workspace',self.control,1,{},10)
        raw['output']['acceptance'][0]['result']='unverified'
        with self.assertRaises(FactoryError):self.gate.result(raw['output'],'Tester',self.row,raw)
        raw['output']['acceptance'][0]['result']='passed';raw['output']['acceptance'][0]['evidence'][0]['sha256']='0'*64
        with self.assertRaises(FactoryError):self.gate.result(raw['output'],'Tester',self.row,raw)

if __name__=='__main__':unittest.main()

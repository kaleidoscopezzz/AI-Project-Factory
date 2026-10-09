"""Evidence handoff regression. Synthetic fixtures; no real agents or Demo run."""
import contextlib
import copy
import io
import json
import shutil
import stat
import unittest
import uuid
from pathlib import Path
from factory.controller import Controller, ROOT, load, save, manifest
from factory.contracts import FactoryError, file_hash
from factory.quality import QualityGate, candidate
from tests.test_quality import QualityDouble

RUN_ROOT=ROOT/'validation/goal2/test-workspaces'/('evidence-'+uuid.uuid4().hex[:10])


class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        RUN_ROOT.mkdir(parents=True);shutil.copytree(ROOT/'skills',RUN_ROOT/'skills')

    def setUp(self):
        self.agent=QualityDouble();self.c=Controller(RUN_ROOT,self.agent)
        self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        self.pid=self.c.create('Synthetic evidence repair regression, no real model',10)
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid)
        self.project,self.control,self.workspace,self.state=self.c.locate(self.pid)
        self.history=self.workspace/'validation/goal0';self.history.mkdir(parents=True)
        for name in ('acceptance.md','session-environment.json','source-sha256.json'):
            (self.history/name).write_text('Synthetic historical documentation; NOT real acceptance' if name.endswith('.md') else '{}',encoding='utf-8')
        completion=load(self.control/'completion.json');completion['workspace_manifest']=manifest(self.workspace)
        save(self.control/'completion.json',completion)
        self.gate=QualityGate(self.c,self.project,self.control,self.workspace,self.state,allow_repair=False)
        self.row=self.gate.make_round();self.gate.basic(self.row)
        self.prompt=self.gate.tester_prompt(self.row)
        self.root=self.gate.folder/self.row['path']
        result=self.agent.run('Tester',self.prompt,self.root/'workspace',self.control,1,{},10)
        self.execution={k:v for k,v in result.items() if k!='output'};self.good=result['output']

    def test_01_legal_explicit_refs_pass_without_autofill(self):
        original=copy.deepcopy(self.good)
        self.assertEqual(self.gate.result(self.good,'Tester',self.row,self.execution),original)
        self.assertEqual(self.good,original)

    def test_02_original_failed_raw_still_rejected(self):
        source=ROOT/'projects/p-dc1e9d42b5ae/control/quality/calls/01-tester/tester-01.result.json'
        raw=load(source)['output'];original=copy.deepcopy(raw)
        # Reuse actual packet/round only in an in-memory reader; no constructor,
        # no writes into the real failed execution ledger and no model dispatch.
        gate=QualityGate.__new__(QualityGate)
        gate.packet=load(ROOT/'projects/p-dc1e9d42b5ae/control/task-packet.json')
        gate.folder=ROOT/'projects/p-dc1e9d42b5ae/control/quality'
        row=load(gate.folder/'state.json')['rounds'][0]
        with self.assertRaisesRegex(FactoryError,'AC 无证据'):gate.result(raw,'Tester',row)
        self.assertEqual(raw,original)

    def test_03_check_level_refs_do_not_replace_ac_refs(self):
        value=copy.deepcopy(self.good);value['acceptance'][0]['evidence']=[]
        with self.assertRaisesRegex(FactoryError,'AC 无证据'):self.gate.result(value,'Tester',self.row,self.execution)

    def test_04_unverified_without_refs_never_approved(self):
        value=copy.deepcopy(self.good);value['status']='blocked'
        value['acceptance'][0].update(result='unverified',evidence=[]);value['limitations']=['Synthetic AC not executed']
        self.gate.result(value,'Tester',self.row,self.execution)
        value['status']='passed'
        with self.assertRaises(FactoryError):self.gate.result(value,'Tester',self.row,self.execution)

    def test_05_history_read_only_copy_outside_candidate(self):
        self.assertEqual(candidate(self.workspace),candidate(self.root/'workspace'))
        for e in self.row['context']['history']:
            self.assertTrue(e['path'].startswith('context/history/'))
            target=self.root/e['path'];self.assertEqual(file_hash(target),file_hash(self.workspace/e['source']))
            self.assertFalse(target.stat().st_mode & stat.S_IWRITE)
        self.assertFalse((self.root/'workspace/validation/goal0/acceptance.md').exists())

    def test_06_history_docs_are_valid_refs_not_auto_verdicts(self):
        value=copy.deepcopy(self.good);e=self.row['context']['history'][0]
        value['acceptance'][-1]['evidence'].append({k:e[k] for k in ('path','sha256')})
        self.gate.result(value,'Tester',self.row,self.execution)
        # Source files outside the history allowlist remain prohibited.
        value['acceptance'][0]['evidence']=[{'path':'workspace/fixture.mjs','sha256':file_hash(self.root/'workspace/fixture.mjs')}]
        with self.assertRaises(FactoryError):self.gate.result(value,'Tester',self.row,self.execution)

    def test_07_missing_source_history_rejected(self):
        (self.history/'acceptance.md').unlink()
        with self.assertRaisesRegex(FactoryError,'历史资料缺失'):self.gate.result(self.good,'Tester',self.row,self.execution)

    def test_08_tampered_source_history_rejected(self):
        (self.history/'acceptance.md').write_text('Synthetic tampering',encoding='utf-8')
        with self.assertRaisesRegex(FactoryError,'哈希不匹配'):self.gate.verify_context(self.row)

    def test_09_tampered_or_missing_copy_rejected(self):
        target=self.root/self.row['context']['history'][0]['path'];target.chmod(stat.S_IWRITE);target.write_text('Synthetic tampering')
        with self.assertRaisesRegex(FactoryError,'被篡改'):self.gate.result(self.good,'Tester',self.row,self.execution)
        target.unlink()
        with self.assertRaisesRegex(FactoryError,'缺失'):self.gate.verify_context(self.row)

    def test_10_index_tampering_rejected(self):
        entry=self.row['context']['indices'][0];(self.root/entry['path']).write_text('{}')
        with self.assertRaisesRegex(FactoryError,'被篡改'):self.gate.result(self.good,'Tester',self.row,self.execution)

    def test_11_forged_or_escaped_refs_rejected(self):
        for e in [{'path':'../outside.json','sha256':'0'*64},
                  {'path':str(self.history/'acceptance.md'),'sha256':file_hash(self.history/'acceptance.md')},
                  {'path':self.row['context']['history'][0]['path'],'sha256':'0'*64}]:
            with self.subTest(e=e):
                value=copy.deepcopy(self.good);value['acceptance'][0]['evidence']=[e]
                with self.assertRaises(FactoryError):self.gate.result(value,'Tester',self.row,self.execution)

    def test_12_candidate_change_invalidates_old_evidence(self):
        (self.workspace/'fixture.mjs').write_text('Synthetic changed candidate')
        with self.assertRaisesRegex(FactoryError,'旧证据失效'):self.gate.result(self.good,'Tester',self.row,self.execution)

    def test_13_context_fingerprint_cannot_be_rebound(self):
        self.row['context']['candidate_fingerprint']='0'*64
        with self.assertRaisesRegex(FactoryError,'指纹不匹配'):self.gate.verify_context(self.row)

    def test_14_required_context_cannot_be_removed(self):
        self.row.pop('context')
        with self.assertRaisesRegex(FactoryError,'历史证据上下文'):self.gate.result(self.good,'Tester',self.row,self.execution)

    def test_15_compact_prompt_retains_ac_and_explicit_rules(self):
        ctx=json.loads(self.prompt.splitlines()[-1]);self.assertEqual(ctx['task_packet']['acceptance'],self.gate.packet['acceptance'])
        self.assertEqual(ctx['candidate']['fingerprint'],self.row['candidate']['fingerprint'])
        self.assertNotIn('evidence',ctx['baseline_checks']);self.assertNotIn('aggregated_output',self.prompt)
        for rule in ('每个AC独立输出','checks的总日志不能代替AC.evidence','unverified','browser check.evidence','只读访问evidence_index'):
            self.assertIn(rule,self.prompt)
        index=load(Path(ctx['evidence_index']['absolute_path']))
        self.assertTrue(index['artifacts']);self.assertEqual(index['candidate_fingerprint'],ctx['candidate']['fingerprint'])

    def test_16_new_source_with_old_result_fingerprint_rejected(self):
        value=copy.deepcopy(self.good);value['candidate_fingerprint']='0'*64
        with self.assertRaisesRegex(FactoryError,'不属于当前候选'):self.gate.result(value,'Tester',self.row,self.execution)

    def test_17_history_alone_cannot_prove_current_pass(self):
        value=copy.deepcopy(self.good);e=self.row['context']['history'][0]
        value['acceptance'][0]['evidence']=[{k:e[k] for k in ('path','sha256')}]
        with self.assertRaisesRegex(FactoryError,'历史记录不能单独'):self.gate.result(value,'Tester',self.row,self.execution)

    def test_18_history_manifest_tampering_rejected(self):
        (self.root/self.row['context']['manifest_path']).write_text('{}')
        with self.assertRaisesRegex(FactoryError,'被篡改'):self.gate.verify_context(self.row)


if __name__=='__main__':unittest.main()

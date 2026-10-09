"""Read-only regression against the third real Tester evidence; no dispatch.

Only in-memory results are mutated. The original failed ledger stays failed.
"""
import copy
import unittest
from factory.controller import ROOT, load
from factory.contracts import FactoryError, file_hash
from factory.quality import QualityGate, REVIEWED_TESTER_DISCLOSURES

RUN = ROOT/'validation/goal2/revalidations/rv-548ec488c49d'


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.gate = QualityGate.__new__(QualityGate)
        self.gate.folder = RUN/'control/quality'
        self.gate.control = RUN/'control'
        self.gate.workspace = ROOT/load(RUN/'prepared.json')['workspace']
        self.gate.packet = load(self.gate.control/'task-packet.json')
        self.gate.q = load(self.gate.folder/'state.json')
        self.gate.load = load
        self.row = copy.deepcopy(self.gate.q['rounds'][0])
        self.execution = load(self.gate.folder/'calls/01-tester/execution.json')
        self.value = copy.deepcopy(self.execution['output'])
        self.protected = {p:file_hash(p) for p in (
            self.gate.folder/'state.json',
            self.gate.folder/'calls/01-tester/execution.json',
            self.gate.folder/'calls/01-tester/tester-01.result.json',
            self.gate.control/'task-packet.json',
        )}

    def tearDown(self):
        self.assertEqual(self.protected, {p:file_hash(p) for p in self.protected})
        self.assertFalse((self.gate.folder/'calls/01-tester/output.json').exists())

    def check(self, value=None, execution=None):
        return self.gate.result(self.value if value is None else value, 'Tester',
                                self.row, self.execution if execution is None else execution)

    def test_01_real_raw_four_disclosures_full_validation_passes_unchanged(self):
        before = copy.deepcopy(self.value)
        self.assertEqual(tuple(self.value['limitations']), REVIEWED_TESTER_DISCLOSURES)
        self.assertEqual(self.check(), before)
        self.assertEqual(self.value, before)
        self.assertEqual(len(self.value['acceptance']), 12)
        self.assertEqual(sum(len(a['evidence']) for a in self.value['acceptance']), 27)

    def test_02_unknown_limitations_rejected(self):
        self.value['limitations'].append('重要持久化测试未运行')
        with self.assertRaises(FactoryError): self.check()

    def test_03_near_match_does_not_inherit_scope_approval(self):
        self.value['limitations'][0] += ' 因而目标浏览器也未验证。'
        with self.assertRaises(FactoryError): self.check()

    def test_04_ac_failed_or_unverified_still_blocks(self):
        for result in ('failed', 'unverified'):
            value = copy.deepcopy(self.value); value['acceptance'][0]['result'] = result
            with self.subTest(result=result), self.assertRaises(FactoryError): self.check(value)

    def test_05_missing_ac_evidence_still_blocks(self):
        self.value['acceptance'][0]['evidence'] = []
        with self.assertRaisesRegex(FactoryError, 'AC 无证据'): self.check()

    def test_06_actionable_issue_still_blocks(self):
        self.value['issues'] = [{
            'id':'ISSUE-REGRESSION', 'ac_ids':['AC-001'], 'category':'implementation',
            'severity':'major', 'reproduce':['Synthetic issue payload, not a real defect'],
            'expected':'Expected behavior', 'actual':'Incorrect behavior',
            'evidence':copy.deepcopy(self.value['acceptance'][0]['evidence']),
        }]
        with self.assertRaisesRegex(FactoryError, '有缺陷'): self.check()

    def test_07_required_check_missing_or_failed_still_blocks(self):
        for kind in ('build', 'test', 'runtime', 'browser'):
            for mode in ('missing', 'failed'):
                value = copy.deepcopy(self.value)
                if mode == 'missing':
                    value['checks'] = [c for c in value['checks'] if c['kind'] != kind]
                else:
                    for check in value['checks']:
                        if check['kind'] == kind: check.update(result='failed', exit_code=1)
                with self.subTest(kind=kind, mode=mode), self.assertRaises(FactoryError): self.check(value)

    def test_08_independent_cli_command_evidence_required(self):
        execution = copy.deepcopy(self.execution); execution['command_executions'] = []
        with self.assertRaisesRegex(FactoryError, 'CLI工具事件'): self.check(execution=execution)

    def test_09_both_viewports_and_real_trace_required(self):
        for suffix in ('.png', '.zip'):
            value = copy.deepcopy(self.value)
            for check in value['checks']:
                if check['kind'] == 'browser':
                    check['evidence'] = [e for e in check['evidence'] if not e['path'].endswith(suffix)]
            with self.subTest(suffix=suffix), self.assertRaises(FactoryError): self.check(value)

    def test_10_forged_hash_path_or_candidate_rejected(self):
        for field, forged in (('sha256', '0'*64), ('path', '../outside.json')):
            value = copy.deepcopy(self.value); value['acceptance'][0]['evidence'][0][field] = forged
            with self.subTest(field=field), self.assertRaises(FactoryError): self.check(value)
        self.value['candidate_fingerprint'] = '0'*64
        with self.assertRaises(FactoryError): self.check()

    def test_11_other_packet_cannot_reuse_scope_exception(self):
        self.gate.packet = copy.deepcopy(self.gate.packet)
        self.gate.packet['title'] = self.gate.packet.get('title', '') + ' Different requirement'
        with self.assertRaises(FactoryError): self.check()

    def test_12_reviewer_approval_not_exempted(self):
        value = {k:copy.deepcopy(v) for k,v in self.value.items() if k not in ('status', 'checks')}
        value.update(decision='approved', summary='Synthetic Reviewer payload; no real Reviewer called')
        with self.assertRaisesRegex(FactoryError, '有限制'):
            self.gate.result(value, 'Reviewer', self.row, self.execution)

    def test_13_failed_ledger_cannot_be_restored_as_finished(self):
        self.assertEqual(self.gate.q['calls'][0]['status'], 'failed')
        self.assertIsNone(self.row['tester'])
        self.assertFalse(self.gate.restore_finished_call(self.gate.q['calls'][0]))
        self.assertEqual(self.gate.q['calls'][0]['status'], 'failed')

    def test_14_basic_failure_still_blocks(self):
        self.row['basic']['passed'] = False
        with self.assertRaisesRegex(FactoryError, '基础检查失败'): self.check()


if __name__ == '__main__':
    unittest.main()

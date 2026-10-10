"""Read-only inspection is candidate-bound; it is not Tester execution proof."""
import tempfile
import unittest
from pathlib import Path
from factory.quality import QualityGate
from factory.contracts import FactoryError, file_hash


class ReviewerSourceTests(unittest.TestCase):
    def test_candidate_source_only_for_readonly_inspection(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1]/'validation/goal3/test-workspaces') as directory:
            folder=Path(directory);root=folder/'round';source=root/'workspace/src/main.mjs'
            source.parent.mkdir(parents=True);source.write_text('// bound source',encoding='utf-8')
            gate=QualityGate.__new__(QualityGate);gate.folder=folder
            gate.q={'rounds':[{'path':'round','candidate':{'files':{'src/main.mjs':file_hash(source)}}}]}
            entry={'path':'workspace/src/main.mjs','sha256':file_hash(source)}
            self.assertEqual(gate.evidence(entry,root,source_inspection=True),source)
            with self.assertRaises(FactoryError):gate.evidence(entry,root)
            for invalid in ({**entry,'sha256':'0'*64},{**entry,'path':'../outside.mjs'}):
                with self.assertRaises(FactoryError):gate.evidence(invalid,root,source_inspection=True)
            source.write_text('// changed',encoding='utf-8')
            with self.assertRaises(FactoryError):gate.evidence(entry,root,source_inspection=True)


if __name__=='__main__':unittest.main()

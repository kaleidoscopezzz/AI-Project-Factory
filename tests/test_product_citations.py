"""Qualified document citations are dependencies; prose labels are not verdicts."""
import tempfile
import unittest
from pathlib import Path
from factory.controller import ROOT,manifest,load
from factory.contracts import digest,file_hash
from factory.quality import candidate
from factory.history import history_dependencies

class ProductCitationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation');self.w=Path(self.temp.name)
        (self.w/'fixture.mjs').write_text('// synthetic')
        for n in ('round-1/test.log','round-3/test.log','round-3/desktop.png'):
            p=self.w/'validation'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('synthetic not business evidence')
        self.doc=self.w/'validation/acceptance.md'
        self.doc.write_text('AC table: test.log, desktop.png\n[original failure](round-1/test.log)\n[final](round-3/test.log), [screen](round-3/desktop.png)\n',encoding='utf8')
        self.completion={'workspace_manifest':manifest(self.w)}
    def tearDown(self):self.temp.cleanup()
    def check(self):return history_dependencies(self.w,self.completion,candidate(self.w),load)
    def test_prose_label_does_not_invent_path_or_select_old_version(self):
        result=self.check();self.assertTrue(result['ready'])
        self.assertEqual({f['source'] for f in result['files']},{'validation/acceptance.md','validation/round-1/test.log','validation/round-3/test.log','validation/round-3/desktop.png'})
    def test_missing_qualified_source_still_rejects(self):
        (self.w/'validation/round-3/test.log').unlink();self.assertFalse(self.check()['ready'])
    def test_tampered_qualified_source_still_rejects(self):
        (self.w/'validation/round-3/test.log').write_text('tampered');self.assertFalse(self.check()['ready'])
    def test_explicit_bare_reference_not_exempt(self):
        self.doc.write_text(self.doc.read_text()+'\n`test.log`\n');self.completion={'workspace_manifest':manifest(self.w)}
        self.assertFalse(self.check()['ready'])
    def test_escaping_link_not_exempt(self):
        self.doc.write_text(self.doc.read_text()+'\n[bad](../test.log)\n');self.completion={'workspace_manifest':manifest(self.w)}
        self.assertFalse(self.check()['ready'])

"""Finite Goal 1 document parsing fixtures; no Agent or business execution."""
import tempfile,unittest
from pathlib import Path
from factory.controller import ROOT,save,load,manifest
from factory.contracts import file_hash
from factory.quality import candidate
from factory.history import history_dependencies

class Goal1ContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation/goal3/test-workspaces');self.workspace=Path(self.temp.name)
        for name,text in {'README.md':'synthetic current delivery','scripts/build.mjs':'// fixture',
            'public/app.js':'// source','dist/app.js':'// built fixture',
            'validation/acceptance.md':'old Goal0 context references missing-old.log',
            'validation/goal1/acceptance.md':'Run `node scripts/build.mjs`. [fingerprint.json](run/fingerprint.json) [test.log](run/test.log)',
            'validation/goal1/run/test.log':'fixture assertions, not actual tests'}.items():
            p=self.workspace/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
        save(self.workspace/'validation/goal1/run/fingerprint.json',{'dist/app.js':file_hash(self.workspace/'dist/app.js')})
        self.completion={'workspace_manifest':manifest(self.workspace)}
    def tearDown(self):self.temp.cleanup()
    def plan(self):return history_dependencies(self.workspace,self.completion,candidate(self.workspace),load,
                                             acceptance_path='validation/goal1/acceptance.md')
    def test_links_commands_and_generated_artifact_keep_exact_sources(self):
        result=self.plan();self.assertTrue(result['ready'],result['unverified'])
        paths={n['source'] for n in result['files']}
        self.assertIn('validation/goal1/run/test.log',paths);self.assertIn('dist/app.js',paths)
        self.assertNotIn('validation/acceptance.md',paths)
    def test_missing_or_changed_generated_and_command_sources_still_rejected(self):
        for name in ('dist/app.js','scripts/build.mjs','validation/goal1/run/test.log'):
            p=self.workspace/name;original=p.read_bytes();p.write_bytes(b'tampered')
            self.assertFalse(self.plan()['ready']);p.write_bytes(original)

    def test_verified_pre_repair_code_is_historical_only(self):
        src=self.workspace/'scripts/build.mjs';h=file_hash(src)
        old=self.workspace/'validation/pre-repair/build.mjs';old.parent.mkdir();old.write_bytes(src.read_bytes())
        src.write_text('// controlled new business source')
        self.assertFalse(self.plan()['ready'])
        result=history_dependencies(self.workspace,self.completion,candidate(self.workspace),load,
             acceptance_path='validation/goal1/acceptance.md',historical_sources={'scripts/build.mjs':{'path':old,'sha256':h}})
        self.assertTrue(result['ready'],result['unverified'])
        entry=next(n for n in result['files'] if n['source']=='scripts/build.mjs')
        self.assertEqual(entry['kind'],'history');self.assertEqual(entry['sha256'],h)
        self.assertIn('NOT current',entry['result'])
        old.write_text('tampered historical bytes')
        result=history_dependencies(self.workspace,self.completion,candidate(self.workspace),load,
             acceptance_path='validation/goal1/acceptance.md',historical_sources={'scripts/build.mjs':{'path':old,'sha256':h}})
        self.assertFalse(result['ready'])

if __name__=='__main__':unittest.main()

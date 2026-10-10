"""Synthetic path/SHA fixtures only; no model or business execution."""
import unittest
import uuid
from unittest.mock import patch
from factory.controller import ROOT, load
from factory.contracts import file_hash
from factory.quality import candidate
from factory.history import history_dependencies


class AcceptancePathTests(unittest.TestCase):
    def setUp(self):
        self.base=ROOT/'validation/goal3/test-workspaces'/('acceptance-'+uuid.uuid4().hex[:12])
        self.base.mkdir(parents=True)

    def fixture(self,layout='validation/acceptance.md'):
        workspace=self.base/uuid.uuid4().hex[:8];workspace.mkdir()
        (workspace/'README.md').write_text('Synthetic delivery: acceptance.md',encoding='utf-8')
        path=workspace/layout;path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text('Synthetic acceptance documentation, not a quality verdict.',encoding='utf-8')
        completion={'workspace_manifest':{'README.md':file_hash(workspace/'README.md'),layout:file_hash(path)}}
        return workspace,completion,path

    def plan(self,workspace,completion):
        return history_dependencies(workspace,completion,candidate(workspace),load)

    def test_supported_layouts_use_completion_sha(self):
        for layout in ('validation/goal0/acceptance.md','validation/acceptance.md'):
            w,c,p=self.fixture(layout)
            with self.subTest(layout=layout):
                plan=self.plan(w,c);self.assertTrue(plan['ready'],plan['unverified'])
                entry=next(n for n in plan['files'] if n['source']==layout)
                self.assertEqual(entry['sha256'],c['workspace_manifest'][layout])
                self.assertEqual(entry['kind'],'history')

    def test_missing_unrecorded_and_tampered_are_rejected(self):
        for case in ('missing','unrecorded','tampered','forged_sha'):
            w,c,p=self.fixture()
            if case=='missing':p.unlink()
            elif case=='unrecorded':del c['workspace_manifest']['validation/acceptance.md']
            elif case=='tampered':p.write_text('Changed bytes',encoding='utf-8')
            else:c['workspace_manifest']['validation/acceptance.md']='0'*64
            with self.subTest(case=case):self.assertFalse(self.plan(w,c)['ready'])

    def test_conflicting_layouts_rejected_even_if_alternative_unrecorded(self):
        for recorded in (False,True):
            w,c,p=self.fixture();other=w/'validation/goal0/acceptance.md';other.parent.mkdir()
            other.write_text('Different acceptance bytes',encoding='utf-8')
            if recorded:c['workspace_manifest']['validation/goal0/acceptance.md']=file_hash(other)
            with self.subTest(recorded=recorded):self.assertFalse(self.plan(w,c)['ready'])

    def test_arbitrary_same_name_not_discovered(self):
        w,c,p=self.fixture('validation/untrusted/acceptance.md')
        plan=self.plan(w,c);self.assertFalse(plan['ready'])
        self.assertFalse(any(n['source']=='validation/untrusted/acceptance.md' for n in plan['files']))

    def test_escaping_references_and_reparse_paths_rejected(self):
        for ref in ('../outside.log','C:/outside.log','/outside.log'):
            w,c,p=self.fixture();p.write_text('[evidence]('+ref+')',encoding='utf-8')
            c['workspace_manifest']['validation/acceptance.md']=file_hash(p)
            with self.subTest(ref=ref):self.assertFalse(self.plan(w,c)['ready'])
        w,c,p=self.fixture();snap=candidate(w)
        with patch('pathlib.Path.is_junction',lambda q:str(q)==str(p),create=True):
            self.assertFalse(history_dependencies(w,c,snap,load)['ready'])

    def test_legacy_missing_source_does_not_fall_back_to_unrecorded_new_file(self):
        w,c,p=self.fixture('validation/goal0/acceptance.md');p.unlink()
        (w/'validation/acceptance.md').write_text('Untrusted substitute',encoding='utf-8')
        self.assertFalse(self.plan(w,c)['ready'])

    def log_fixture(self,context=False):
        w,c,p=self.fixture()
        directory='validation/run-fixed' if context else 'validation'
        log=w/directory/'test.log';log.parent.mkdir(exist_ok=True)
        log.write_text('Synthetic log, no business run.',encoding='utf-8')
        c['workspace_manifest'][log.relative_to(w).as_posix()]=file_hash(log)
        text='test.log'
        if context:
            anchor=log.parent/'results.json';anchor.write_text('{}',encoding='utf-8')
            c['workspace_manifest'][anchor.relative_to(w).as_posix()]=file_hash(anchor)
            text='| AC | validation/run-fixed/results.json，test.log |'
        p.write_text(text,encoding='utf-8');c['workspace_manifest']['validation/acceptance.md']=file_hash(p)
        return w,c,p,log

    def test_log_relative_to_document_or_verified_same_cell_anchor(self):
        for context in (False,True):
            w,c,p,log=self.log_fixture(context)
            plan=self.plan(w,c)
            with self.subTest(context=context):
                self.assertTrue(plan['ready'],plan['unverified'])
                self.assertTrue(any(n['source']==log.relative_to(w).as_posix() and n['sha256']==file_hash(log) for n in plan['files']))

    def test_log_missing_tampered_forged_or_unrecorded_rejected(self):
        for case in ('missing','tampered','forged','unrecorded','anchor_tampered','anchor_unrecorded'):
            w,c,p,log=self.log_fixture(True);name=log.relative_to(w).as_posix()
            if case=='missing':log.unlink()
            elif case=='tampered':log.write_text('Changed bytes',encoding='utf-8')
            elif case=='forged':c['workspace_manifest'][name]='0'*64
            elif case=='unrecorded':del c['workspace_manifest'][name]
            elif case=='anchor_tampered':(log.parent/'results.json').write_text('{"changed":true}',encoding='utf-8')
            else:del c['workspace_manifest']['validation/run-fixed/results.json']
            with self.subTest(case=case):self.assertFalse(self.plan(w,c)['ready'])

    def test_log_conflicts_or_unrecorded_local_file_rejected(self):
        for recorded in (False,True):
            w,c,p,log=self.log_fixture(True);local=w/'validation/test.log';local.write_text('Conflicting local bytes',encoding='utf-8')
            if recorded:c['workspace_manifest']['validation/test.log']=file_hash(local)
            with self.subTest(recorded=recorded):self.assertFalse(self.plan(w,c)['ready'])

    def test_log_does_not_search_other_rounds_or_other_table_cells(self):
        w,c,p,log=self.log_fixture(True)
        for text in ('test.log','| validation/run-fixed/results.json | test.log |'):
            p.write_text(text,encoding='utf-8');c['workspace_manifest']['validation/acceptance.md']=file_hash(p)
            with self.subTest(text=text):self.assertFalse(self.plan(w,c)['ready'])

    def test_log_local_link_is_rejected(self):
        w,c,p,log=self.log_fixture();snap=candidate(w)
        with patch('pathlib.Path.is_junction',lambda q:str(q)==str(log),create=True):
            self.assertFalse(history_dependencies(w,c,snap,load)['ready'])


if __name__=='__main__':unittest.main()

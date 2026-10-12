"""Real build/ZIP/extracted-launch tests with explicitly synthetic approvals.

Production approval rejection is tested without a mock. The real Goal 3 release
is validated separately with the production verifier and no business model calls.
"""
import copy
import json
import os
import unittest
import uuid
import zipfile
from pathlib import Path
from unittest.mock import patch

from factory.controller import Controller, ROOT, load, save, locked
from factory.contracts import FactoryError, digest, file_hash
from factory.git_agent import GitAgent
from factory.quality import candidate
from factory.release_agent import ReleaseAgent, unpack_checked

RUN_ROOT=ROOT/'validation/goal5/test-workspaces'/uuid.uuid4().hex[:10]
SERVER='''import argparse
from http.server import HTTPServer,BaseHTTPRequestHandler
p=argparse.ArgumentParser();p.add_argument('--host');p.add_argument('--port',type=int);a=p.parse_args()
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(b'release-fixture')
HTTPServer((a.host,a.port),Handler).serve_forever()
'''


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.c=Controller(RUN_ROOT);self.pid=self.c.create('Synthetic release contract fixture; no model approval')
        self.project,self.control,self.workspace,_=self.c.locate(self.pid)
        (self.workspace/'server.py').write_text(SERVER,encoding='utf8')
        (self.workspace/'build.py').write_text("from pathlib import Path\nPath('build').mkdir(exist_ok=True)\nPath('build/server.py').write_bytes(Path('server.py').read_bytes())\nprint('actual build passed')\n",encoding='utf8')
        (self.workspace/'selftest.py').write_text("print('fixture self-check passed')\n",encoding='utf8')
        self.packet={'goal':'Goal 0','project_id':self.pid,'workspace':str(self.workspace),'allow_write':[str(self.workspace)],
                     'checks':[{'purpose':'build','argv':['python','build.py']},{'purpose':'test','argv':['python','selftest.py']}],
                     'runtime':{'argv':['python','server.py','--host','127.0.0.1','--port','{port}'],'path':'/health','expected_text':'release-fixture'}}
        self.bind()
        self.a=ReleaseAgent(self.c,self.pid)
        self.config={'version':1,'project_id':self.pid,'goal':'Goal 0','authorization_id':'isolated-release-test-only',
                     'name':'release-fixture','source_files':['server.py','build.py','selftest.py'],
                     'package_files':['server.py','build/server.py'],'runtime_requirement':'Python 3.10 or newer on PATH',
                     'timeout_seconds':10,'smoke':'http-health'}

    def bind(self):
        (self.control/'sequence').mkdir(exist_ok=True)
        save(self.control/'task-packet.json',self.packet)
        self.receipt={'project_id':self.pid,'goal':'Goal 0','status':'质量门槛通过','candidate':candidate(self.workspace),
                      'packet_fingerprint':digest(self.packet),'files':{'control/task-packet.json':file_hash(self.control/'task-packet.json')},
                      'scope':'Synthetic fixture; production verifier is mocked only for operation tests'}
        save(self.control/'sequence/goal0-completion.json',self.receipt)
        save(self.control/'sequence/state.json',{'project_id':self.pid,'completed':{'Goal 0':{'path':'goal0-completion.json','sha256':file_hash(self.control/'sequence/goal0-completion.json')}}})

    def release(self):
        with patch.object(GitAgent,'_validate_quality',return_value=None):
            return self.c.release_approved_stage(self.pid,'Goal 0',self.config)

    def test_real_build_archive_launch_and_repeat(self):
        before=candidate(self.workspace);receipt=file_hash(self.control/'sequence/goal0-completion.json')
        result=self.release();self.assertEqual(result['status'],'released',result)
        record=load(result['record']);package=Path(result['package'])
        self.assertEqual(file_hash(package),record['package']['sha256'])
        self.assertTrue(all(p['exit_code']==0 for p in record['checks']))
        self.assertEqual(record['binding']['candidate_fingerprint'],before['fingerprint'])
        self.assertTrue(record['runtime']['checks']);self.assertFalse(any(p['still_running'] for p in record['runtime']['processes']))
        with zipfile.ZipFile(package) as z:
            self.assertIsNone(z.testzip());self.assertEqual(set(z.namelist()),set(record['files']))
        hashes={p.name:file_hash(p) for p in package.parent.iterdir() if p.is_file()}
        self.assertEqual(self.release()['status'],'already_released')
        self.assertEqual(hashes,{p.name:file_hash(p) for p in package.parent.iterdir() if p.is_file()})
        self.assertEqual(candidate(self.workspace),before);self.assertEqual(file_hash(self.control/'sequence/goal0-completion.json'),receipt)

    def test_production_rejects_fake_quality(self):
        self.assertEqual(self.a.release('Goal 0',self.config)['status'],'blocked')
        self.assertFalse(self.a.output.exists())

    def test_unapproved(self):
        save(self.control/'sequence/state.json',{'project_id':self.pid,'completed':{}})
        self.assertEqual(self.release()['status'],'blocked');self.assertFalse(self.a.output.exists())

    def test_no_authorization(self):
        self.config['authorization_id']=''
        self.assertEqual(self.release()['status'],'blocked');self.assertFalse(self.a.output.exists())

    def test_candidate_drift(self):
        (self.workspace/'server.py').write_text('modified')
        self.assertEqual(self.release()['status'],'blocked')

    def test_build_failure_preserved_no_success(self):
        (self.workspace/'build.py').write_text("raise SystemExit(7)\n");self.bind()
        result=self.release();self.assertEqual(result['status'],'blocked')
        folder=Path(result['diagnostics']);self.assertFalse((folder/'release-record.json').exists())
        self.assertEqual(load(folder/'build-0-result.json')['exit_code'],7)
        old={p.name:file_hash(p) for p in folder.iterdir() if p.is_file()}
        self.assertEqual(self.release()['status'],'blocked')
        self.assertEqual(old,{p.name:file_hash(p) for p in folder.iterdir() if p.is_file()})

    def test_test_failure(self):
        (self.workspace/'selftest.py').write_text('raise SystemExit(9)\n');self.bind()
        result=self.release();self.assertEqual(result['status'],'blocked')
        self.assertEqual(load(Path(result['diagnostics'])/'test-1-result.json')['exit_code'],9)

    def test_runtime_failure_not_success(self):
        (self.workspace/'server.py').write_text('raise SystemExit(4)\n');self.bind()
        result=self.release();self.assertEqual(result['status'],'blocked')
        folder=Path(result['diagnostics']);self.assertFalse((folder/'release-record.json').exists())
        self.assertFalse(list(folder.glob('*.zip')));self.assertTrue(list(folder.glob('*.partial')))

    def test_sensitive_and_cache_files_excluded(self):
        (self.workspace/'.factory-tmp').mkdir();(self.workspace/'.factory-tmp/private.txt').write_text('private')
        result=self.release();self.assertEqual(result['status'],'released',result)
        with zipfile.ZipFile(result['package']) as z:self.assertFalse(any('factory-tmp' in n for n in z.namelist()))
        self.config['source_files'].append('.factory-tmp/private.txt')
        self.assertEqual(self.release()['status'],'blocked')
        self.config['source_files'][-1]='.env'
        self.assertEqual(self.release()['status'],'blocked')

    def test_generated_secret_rejected(self):
        (self.workspace/'build.py').write_text("from pathlib import Path\nPath('build').mkdir()\nPath('build/server.py').write_text('api_key=sk-'+'x'*30)\n",encoding='utf8');self.bind()
        self.assertEqual(self.release()['status'],'blocked')

    def test_traversal_and_absolute_rejected(self):
        for name in ('../outside.txt','C:/private.txt','src/../../private.txt','CON.txt'):
            with self.subTest(name=name):
                self.config['package_files']=[name];self.assertEqual(self.release()['status'],'blocked')

    def test_modified_source_copy_rejected(self):
        (self.workspace/'build.py').write_text("from pathlib import Path\nPath('server.py').write_text('changed')\n",encoding='utf8');self.bind()
        result=self.release();self.assertEqual(result['status'],'blocked');self.assertIn('副本',result['message'])

    def test_interrupt_no_false_success_or_retry(self):
        with patch.object(self.a,'_command',side_effect=KeyboardInterrupt):
            with patch.object(GitAgent,'_validate_quality',return_value=None):
                with self.assertRaises(KeyboardInterrupt):self.a.release('Goal 0',self.config)
        folder=next(self.a.output.iterdir());before=file_hash(folder/'state.json')
        self.assertEqual(load(folder/'state.json')['status'],'running')
        self.assertEqual(self.release()['status'],'blocked');self.assertEqual(file_hash(folder/'state.json'),before)
        self.assertFalse((folder/'release-record.json').exists())

    def test_bad_hash_record_or_zip_rejected(self):
        result=self.release();self.assertEqual(result['status'],'released',result)
        p=Path(result['package']);p.write_bytes(p.read_bytes()+b'tampered')
        self.assertEqual(self.release()['status'],'blocked')

    def test_project_lock(self):
        with locked(self.control):
            with self.assertRaises(FactoryError):self.release()

    def test_missing_artifact(self):
        self.config['package_files'].append('dist/missing.js')
        self.assertEqual(self.release()['status'],'blocked')

    def test_recipe_cannot_execute_arbitrary_command(self):
        self.packet['checks'][0]['argv']=['powershell','private.ps1'];self.bind()
        self.assertEqual(self.release()['status'],'blocked');self.assertFalse(self.a.output.exists())

    def test_private_note_and_case_conflict(self):
        self.config['runtime_requirement']='Node at C:/Users/private/bin/node.exe'
        self.assertEqual(self.release()['status'],'blocked')
        self.config['runtime_requirement']='Python 3.10 or newer'
        self.config['package_files'].append('SERVER.py')
        self.assertEqual(self.release()['status'],'blocked')

    def test_zip_traversal_symlink_and_no_overwrite(self):
        base=self.project/'zip-test';base.mkdir()
        archive=base/'unsafe.zip'
        for name in ('../outside.txt','C:/outside.txt'):
            with zipfile.ZipFile(archive,'w') as z:z.writestr(name,b'bad')
            with self.assertRaises(FactoryError):unpack_checked(archive,base/'unpacked',{})
        info=zipfile.ZipInfo('link.txt');info.create_system=3;info.external_attr=0o120777<<16
        with zipfile.ZipFile(archive,'w') as z:z.writestr(info,b'outside')
        with self.assertRaises(FactoryError):unpack_checked(archive,base/'unpacked',{'link.txt':digest(b'outside')})
        with zipfile.ZipFile(archive,'w') as z:z.writestr('file.txt',b'good')
        target=base/'unpacked';target.mkdir();(target/'user.txt').write_text('keep')
        with self.assertRaises(FactoryError):unpack_checked(archive,target,{'file.txt':digest(b'good')})
        self.assertEqual((target/'user.txt').read_text(),'keep')

    def test_build_only_local_path_never_shipped(self):
        with (self.workspace/'selftest.py').open('a',encoding='utf8') as f:
            f.write("# Synthetic build-only runtime path: C:/Users/private/test-runtime\n")
        self.bind();result=self.release();self.assertEqual(result['status'],'released',result)
        self.config['package_files'].append('selftest.py')
        self.assertEqual(self.release()['status'],'blocked')

    def test_timeout_keeps_exit_and_stops_owned_process(self):
        (self.workspace/'build.py').write_text('import time\ntime.sleep(30)\n');self.bind()
        self.config['timeout_seconds']=1
        result=self.release();self.assertEqual(result['status'],'blocked')
        record=load(Path(result['diagnostics'])/'build-0-result.json')
        self.assertTrue(record['timed_out']);self.assertNotEqual(record['exit_code'],0)

    def test_optional_version_requires_software_repository(self):
        (self.control/'git').mkdir()
        save(self.control/'git/goal0-version.json',{'commit':'a'*40})
        with patch.object(GitAgent,'_tree') as tree:
            self.assertEqual(self.release()['status'],'blocked');tree.assert_not_called()
        self.assertFalse((self.workspace/'.git').exists())

    def test_optional_version_binding_and_mismatch(self):
        (self.control/'git').mkdir()
        version={'commit':'a'*40,'candidate_fingerprint':self.receipt['candidate']['fingerprint'],
                 'packet_fingerprint':self.receipt['packet_fingerprint'],
                 'approval':{'path':'control/sequence/goal0-completion.json','sha256':file_hash(self.control/'sequence/goal0-completion.json')}}
        save(self.control/'git/goal0-version.json',version)
        with patch.object(GitAgent,'_repository',return_value=True),patch.object(GitAgent,'_tree',return_value=self.receipt['candidate']['files']):
            result=self.release();self.assertEqual(result['status'],'released',result)
            self.assertEqual(load(result['record'])['binding']['git_commit'],'a'*40)
            version['candidate_fingerprint']='0'*64;save(self.control/'git/goal0-version.json',version)
            self.assertEqual(self.release()['status'],'blocked')


if __name__=='__main__':unittest.main()

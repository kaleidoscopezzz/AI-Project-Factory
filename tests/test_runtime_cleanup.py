"""Real local Node/PowerShell cleanup checks; no models or quality approvals."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from factory.controller import Controller, ROOT
from factory.executor import popen, runtime_launch, stop_runtime
from factory.release_agent import ReleaseAgent


@unittest.skipUnless(shutil.which('node'), 'Node runtime unavailable')
class RuntimeCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'validation')
        self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def script(self,body):
        path=self.root/'runtime.mjs';path.write_text(body,encoding='utf8');return path
    def launch(self,body):
        path=self.script(body)
        argv,graceful=runtime_launch(['node',str(path)])
        p=popen(argv,self.root)
        self.addCleanup(lambda: stop_runtime(p,graceful,timeout=.1))
        self.assertEqual(p.stdout.readline().strip(),'READY')
        return p,graceful
    def test_normal_shutdown_runs_existing_handler(self):
        p,g=self.launch("import{writeFileSync}from'node:fs';setInterval(()=>{},1000);"
            "process.on('SIGINT',()=>{writeFileSync('released.txt','released');process.exit(0)});console.log('READY');")
        result=stop_runtime(p,g)
        self.assertFalse(result['forced']);self.assertEqual(result['exit_code'],0)
        self.assertEqual((self.root/'released.txt').read_text(),'released')
    def test_uncooperative_runtime_falls_back_only_owned_process(self):
        p,g=self.launch("setInterval(()=>{},1000);console.log('READY')")
        result=stop_runtime(p,g,timeout=.1)
        self.assertTrue(result['forced']);self.assertTrue(result['process_stopped'])
    def test_startup_failure_retains_nonzero_exit_without_hanging(self):
        path=self.script("console.error('startup failed');process.exitCode=7;")
        argv,g=runtime_launch(['node',str(path)]);p=popen(argv,self.root)
        try:p.wait(timeout=5);self.assertEqual(p.returncode,7)
        finally:stop_runtime(p,g,timeout=.1)
    def test_non_node_argv_unchanged(self):
        argv=['python','server.py','--port','1234']
        self.assertEqual(runtime_launch(argv),(argv,False))
    def test_controller_restarts_file_mutex_app_without_stale_lock(self):
        self.script("import http from'node:http';import{openSync,closeSync,unlinkSync}from'node:fs';"
            "const h=openSync('store.lock','wx');const port=Number(process.argv[2]);"
            "const server=http.createServer((q,s)=>s.end('healthy'));"
            "server.listen(port,'127.0.0.1');process.on('SIGINT',()=>server.close(()=>{"
            "closeSync(h);unlinkSync('store.lock');process.exit(0)}));")
        c=Controller(self.root/'factory');c.executor=type('Direct',(),{'sandbox_argv':lambda _,a,w:a})()
        packet={'runtime':{'argv':['node','runtime.mjs','{port}'],'path':'/','expected_text':'healthy'},
                'budget':{'check_timeout_seconds':5}}
        for n in (1,2):
            out=self.root/str(n);out.mkdir()
            result=c.runtime_check(packet,self.root,out)
            self.assertTrue(result['passed']);self.assertFalse(result['cleanup']['forced'])
            self.assertFalse((self.root/'store.lock').exists())
    @unittest.skipUnless(os.name=='nt','Windows PowerShell-specific launcher')
    def test_release_powershell_child_gets_bounded_graceful_shutdown(self):
        unpacked=self.root/'unpacked';unpacked.mkdir()
        (unpacked/'app.mjs').write_text("import http from'node:http';import{writeFileSync}from'node:fs';"
            "const s=http.createServer((q,r)=>r.end('healthy'));s.listen(Number(process.argv[2]),'127.0.0.1');"
            "process.on('SIGINT',()=>s.close(()=>{writeFileSync('released.txt','yes');process.exit(0)}));",encoding='utf8')
        (unpacked/'START.ps1').write_text("param([int]$Port)\n& node app.mjs $Port\nexit $LASTEXITCODE\n",encoding='utf8')
        # Calls the actual extraction-smoke implementation, no fabricated approval.
        a=object.__new__(ReleaseAgent)
        result=a._smoke(self.root,{'argv':['node','app.mjs'],'path':'/','expected_text':'healthy'},
                        {'timeout_seconds':10,'smoke':'http-health'}, {})
        self.assertEqual((unpacked/'released.txt').read_text(),'yes')
        self.assertEqual(result['processes'][0]['cleanup']['exit_code'],0)
        self.assertFalse(result['processes'][0]['cleanup']['forced'])


if __name__=='__main__':unittest.main()

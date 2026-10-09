"""Trusted diagnostic only: never executes generated project source or changes ACLs.

Run INSIDE Codex workspace sandbox. Exit 0 means collection finished, not that
the environment passed. The caller must inspect each recorded result.
"""
import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from ctypes import wintypes as W
from pathlib import Path

def token_and_pipe():
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    a = ctypes.WinDLL('advapi32', use_last_error=True)
    k.GetCurrentProcess.restype = W.HANDLE
    k.CloseHandle.argtypes = [W.HANDLE]
    k.LocalFree.argtypes = [ctypes.c_void_p]
    a.OpenProcessToken.argtypes = [W.HANDLE, W.DWORD, ctypes.POINTER(W.HANDLE)]
    a.GetTokenInformation.argtypes = [W.HANDLE, ctypes.c_int, ctypes.c_void_p, W.DWORD, ctypes.POINTER(W.DWORD)]
    a.IsTokenRestricted.argtypes = [W.HANDLE]
    a.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p, ctypes.POINTER(W.LPWSTR)]
    handle = W.HANDLE()
    if not a.OpenProcessToken(k.GetCurrentProcess(), 8, ctypes.byref(handle)):
        return {'token_query_error': ctypes.get_last_error()}
    def info(kind):
        size = W.DWORD()
        a.GetTokenInformation(handle, kind, None, 0, ctypes.byref(size))
        buf = ctypes.create_string_buffer(size.value)
        if not a.GetTokenInformation(handle, kind, buf, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return buf
    class SID_ATTR(ctypes.Structure):
        _fields_ = [('sid', ctypes.c_void_p), ('attributes', W.DWORD)]
    class GROUPS(ctypes.Structure):
        _fields_ = [('count', W.DWORD), ('first', SID_ATTR)]
    try:
        data = info(11)
        count = W.DWORD.from_buffer(data).value
        groups = (SID_ATTR * count).from_buffer(data, GROUPS.first.offset)
        sids = []
        for group in groups:
            string = W.LPWSTR()
            if a.ConvertSidToStringSidW(group.sid, ctypes.byref(string)):
                sids.append({'sid': string.value, 'attributes': group.attributes})
                k.LocalFree(ctypes.cast(string, ctypes.c_void_p))
        result = {'is_restricted': bool(a.IsTokenRestricted(handle)),
                  'restricted_sids': sids, 'is_app_container': W.DWORD.from_buffer(info(29)).value,
                  'integrity_info_obtained': bool(info(25))}
        # Read the token default ACL without replacing it or changing any
        # security descriptor. This distinguishes token defaults from pipes.
        default_info = info(6)
        default_acl = ctypes.c_void_p.from_buffer(default_info).value
        result['token_default_acl'] = []
        a.GetAce.argtypes = [ctypes.c_void_p, W.DWORD, ctypes.POINTER(ctypes.c_void_p)]
        if default_acl:
            count = ctypes.c_ushort.from_address(default_acl+4).value
            for index in range(count):
                ace = ctypes.c_void_p()
                if not a.GetAce(default_acl, index, ctypes.byref(ace)):
                    result['token_default_acl_query_error'] = ctypes.get_last_error()
                    break
                kind = ctypes.c_ubyte.from_address(ace.value).value
                record = {'type': kind, 'flags': ctypes.c_ubyte.from_address(ace.value+1).value}
                if kind in (0, 1):
                    record['mask'] = hex(W.DWORD.from_address(ace.value+4).value)
                    string = W.LPWSTR()
                    if a.ConvertSidToStringSidW(ace.value+8, ctypes.byref(string)):
                        record['sid'] = string.value
                        k.LocalFree(ctypes.cast(string, ctypes.c_void_p))
                result['token_default_acl'].append(record)
    finally:
        k.CloseHandle(handle)
    k.CreateNamedPipeW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, W.DWORD, ctypes.c_void_p]
    k.CreateNamedPipeW.restype = W.HANDLE
    k.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
    k.CreateFileW.restype = W.HANDLE
    invalid = ctypes.c_void_p(-1).value
    name = r'\\.\pipe\apf-readonly-probe-' + uuid.uuid4().hex
    server = k.CreateNamedPipeW(name, 3 | 0x40000000, 0, 1, 4096, 4096, 0, None)
    result['named_pipe_server_error'] = ctypes.get_last_error() if server == invalid else 0
    if server != invalid:
        try:
            a.GetKernelObjectSecurity.argtypes = [W.HANDLE, W.DWORD, ctypes.c_void_p,
                                                  W.DWORD, ctypes.POINTER(W.DWORD)]
            a.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
                ctypes.c_void_p, W.DWORD, W.DWORD, ctypes.POINTER(W.LPWSTR), ctypes.c_void_p]
            size = W.DWORD()
            a.GetKernelObjectSecurity(server, 7, None, 0, ctypes.byref(size))
            descriptor = ctypes.create_string_buffer(size.value)
            security_ok = bool(size.value and a.GetKernelObjectSecurity(server, 7, descriptor, size, ctypes.byref(size)))
            result['named_pipe_acl_query_error'] = 0 if security_ok else ctypes.get_last_error()
            if security_ok:
                string = W.LPWSTR()
                if a.ConvertSecurityDescriptorToStringSecurityDescriptorW(descriptor, 1, 7, ctypes.byref(string), None):
                    result['named_pipe_security_sddl'] = string.value
                    k.LocalFree(ctypes.cast(string, ctypes.c_void_p))
            for label, rights in [('read_write', 0xC0000000), ('read', 0x80000000), ('write', 0x40000000),
                                  ('read_write_dac', 0x80040000), ('libuv_write', 0x40040080),
                                  ('chromium_mojo', 0x0012019B)]:
                # Each mode uses a fresh pipe to avoid PIPE_BUSY from a previous
                # successful connection. Closing handles destroys the object.
                if label != 'read_write':
                    k.CloseHandle(server)
                    name = r'\\.\pipe\apf-readonly-probe-' + uuid.uuid4().hex
                    server = k.CreateNamedPipeW(name, 3 | 0x40000000, 0, 1, 4096, 4096, 0, None)
                    if server == invalid:
                        result['named_pipe_'+label+'_server_error'] = ctypes.get_last_error()
                        break
                client = k.CreateFileW(name, rights, 0, None, 3, 0x40000000, None)
                result['named_pipe_client_'+label+'_error'] = ctypes.get_last_error() if client == invalid else 0
                if client != invalid:
                    k.CloseHandle(client)
        finally:
            k.CloseHandle(server)
    return result

def boundary_probe(paths):
    """Request write access to EXISTING objects, then close without writing.

    No external markers are created, even if an unexpected permission is found.
    Covers tested objects only; is not a complete host security audit.
    """
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateFileW.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, ctypes.c_void_p, W.DWORD, W.DWORD, W.HANDLE]
    k.CreateFileW.restype = W.HANDLE
    k.CloseHandle.argtypes = [W.HANDLE]
    result = []
    for target in paths:
        target = Path(target)
        handle = k.CreateFileW(str(target), 0x40000000, 7, None, 3, 0x02000000 if target.is_dir() else 0, None)
        denied = handle == ctypes.c_void_p(-1).value
        error = ctypes.get_last_error() if denied else 0
        if not denied:
            k.CloseHandle(handle)
        result.append({'path': str(target), 'exists': target.exists(), 'write_access_denied': denied,
                       'winerror': error, 'mutated': False})
    return result

def run(argv, cwd, timeout=12):
    from .executor import kill_tree
    started = time.monotonic()
    try:
        process = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
    except OSError as error:
        return {'started': False, 'winerror': error.winerror, 'error': str(error)}
    timed_out = False
    try:
        out, err = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(process)
        out, err = process.communicate(timeout=5)
    return {'started': True, 'pid': process.pid, 'exit_code': process.returncode,
            'timed_out': timed_out, 'elapsed_seconds': round(time.monotonic()-started, 3),
            'stdout': out.decode('utf-8', 'replace'), 'stderr': err.decode('utf-8', 'replace')}

NODE_MATRIX = r'''
const {spawnSync} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const rows=[];
for (const mode of ['inherit','ignore','pipe','file']) {
  let fd;
  try {
    if(mode==='file') fd=fs.openSync(path.join(process.argv[1], 'node-child.txt'),'w');
    const r=spawnSync(process.execPath,['--version'],{stdio:mode==='file'?['ignore',fd,fd]:mode,timeout:4000});
    rows.push({mode,status:r.status,error:r.error?{code:r.error.code,syscall:r.error.syscall,message:r.error.message}:null});
  } catch(e) {rows.push({mode,error:{code:e.code,message:e.message}})}
  finally {if(fd!==undefined) fs.closeSync(fd)}
}
for(const cwd of [process.cwd(),process.env.TEMP,process.argv[1]]) {
  const r=spawnSync(process.execPath,['--version'],{cwd,encoding:'utf8',timeout:4000});
  rows.push({mode:'pipe-cwd',cwd,status:r.status,error:r.error?.code,stdout:r.stdout});
}
console.log('APF_MATRIX='+JSON.stringify(rows));
'''

def collect(workspace, include_browsers=True):
    workspace = Path(workspace).resolve()
    scratch = workspace / '.factory-tmp' / ('environment-probe-' + uuid.uuid4().hex[:10])
    scratch.mkdir(parents=True)
    node = shutil.which('node')
    results = {'source': 'trusted environment diagnostic, not business tests',
               'cwd': str(workspace), 'temp': os.environ.get('TEMP'), 'scratch': str(scratch),
               'python': sys.version, 'node_executable': node, 'token_and_pipe': token_and_pipe(),
               'ordinary_command': run([shutil.which('cmd.exe'), '/d', '/c', 'ver'], workspace),
               'python_child': run([sys.executable, '-B', '-c', 'print("python-child-ok")'], workspace)}
    if node:
        results['node_version'] = run([node, '--version'], workspace)
        results['node_matrix'] = run([node, '-e', NODE_MATRIX, str(scratch)], workspace)
        network = r'''const net=require('node:net');const s=net.createServer(c=>c.end('ok'));s.on('error',e=>{console.log(JSON.stringify({code:e.code,message:e.message}));process.exit(1)});s.listen(0,'127.0.0.1',()=>{const c=net.connect(s.address().port,'127.0.0.1');c.on('data',d=>console.log(d.toString()));c.on('end',()=>s.close());c.on('error',e=>{console.error(e);process.exit(1)});});'''
        results['node_loopback_tcp'] = run([node, '-e', network], workspace)
    if include_browsers:
        results['browsers'] = {}
        for label, exe in [('chrome', Path('C:/Program Files/Google/Chrome/Application/chrome.exe')),
                           ('edge', Path('C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'))]:
            if exe.is_file():
                user = scratch / label
                user.mkdir()
                # Keep Chromium's own sandbox enabled. No generated app is served.
                results['browsers'][label] = run([str(exe), '--headless=new', '--no-first-run',
                    '--no-default-browser-check', '--disable-background-networking',
                    '--user-data-dir='+str(user), '--crash-dumps-dir='+str(user),
                    '--dump-dom', 'about:blank'], workspace, timeout=12)
            else:
                results['browsers'][label] = {'available': False}
    return results

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browsers', action='store_true')
    args = parser.parse_args()
    print(json.dumps(collect(Path.cwd(), not args.no_browsers), ensure_ascii=False))

if __name__ == '__main__':
    main()

"""One bounded diagnostic session, reusing existing task; no Agent calls.

Never runs generated source outside the workspace sandbox; never overwrites
earlier diagnostics. Does not install tools or change Windows security.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from factory.executor import CodexExecutor, bounded, clean_env, popen, kill_tree, redact
from factory.controller import manifest
from reference_guard import inventory, sha

def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def file_set(root, exclude=()):
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*')
            if p.is_file() and not any(x in p.relative_to(root).parts for x in exclude)}

def snapshot(output, project):
    names = subprocess.check_output(['git','--no-optional-locks','ls-files'],cwd=ROOT,encoding='utf-8').splitlines()
    data = {'captured_utc': datetime.now(timezone.utc).isoformat(),
            'frozen': {name: sha(ROOT/name) for name in names if name != 'PROJECT_STATUS.md'},
            'factory_git': file_set(ROOT/'.git'),
            'control': file_set(project/'control'), 'workspace': manifest(project/'workspace'),
            'historical_goal1': file_set(ROOT/'validation/goal1', (output.name, 'test-workspaces')),
            'reference': inventory(),
            'user_config_sha256': sha(Path.home()/'.codex/config.toml')}
    write(output/'before.json', data)
    return data

def main():
    started = time.monotonic()
    project = ROOT/'projects/p-dc1e9d42b5ae'
    workspace = project/'workspace'
    output = ROOT/'validation/goal1'/datetime.now().strftime('environment-repair-%Y%m%dT%H%M%S')
    output.mkdir()
    write(output/'session.json', {'started_utc': datetime.now(timezone.utc).isoformat(),
        'project': str(project), 'agent_calls': 0, 'formal_e2e_calls': 0,
        'scope': 'independent trusted probes under unchanged restricted sandbox'})
    snapshot(output, project)
    executor = CodexExecutor()
    code = 'import sys; sys.path.insert(0,sys.argv[1]); from factory.windows_probe import main; sys.argv=sys.argv[2:]; main()'
    argv = executor.sandbox_argv(['python','-B','-c',code,str(ROOT),'apf-probe'],workspace)
    result = bounded(argv, workspace, 50, log=output/'restricted-probe.log.jsonl')
    write(output/'restricted-probe.json', result)
    if not result['exit_code'] and not result['timed_out']:
        try:
            write(output/'diagnostics.json', json.loads(result['stdout']))
        except json.JSONDecodeError:
            pass
    # Check whether inherited desktop package identity is the trigger, while
    # preserving exactly the same workspace-write sandbox and private desktop.
    env = clean_env(workspace)
    env.pop('CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY', None)
    alternate = argv[:-1] + ['apf-probe', '--no-browsers']
    process = popen(alternate,workspace,env)
    timed_out = False
    t = time.monotonic()
    try:
        stdout, stderr = process.communicate(timeout=25)
    except subprocess.TimeoutExpired:
        timed_out = True
        kill_tree(process)
        stdout, stderr = process.communicate(timeout=5)
    write(output/'without-package-context.json', {'exit_code': process.returncode, 'timed_out': timed_out,
        'elapsed_seconds': round(time.monotonic()-t,3), 'stdout':redact(stdout), 'stderr':redact(stderr),
        'sandbox_changed':False, 'removed_inherited_variable':'CODEX_WINDOWS_SANDBOX_PACKAGE_FAMILY'})
    native = {}
    for name, args in [('node_version',[shutil.which('node'),'--version']),
                       ('wsl_list',['wsl.exe','--list','--verbose'])]:
        r = subprocess.run(args, capture_output=True, timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
        encoding = 'utf-16-le' if name=='wsl_list' else 'utf-8'
        native[name] = {'exit_code':r.returncode,'stdout':r.stdout.decode(encoding,'replace'),
                        'stderr':r.stderr.decode(encoding,'replace')}
    write(output/'native-inventory.json', native)
    write(output/'metrics.json', {'elapsed_seconds':round(time.monotonic()-started,3),
        'real_planner_calls':0,'real_coder_calls':0,'formal_e2e_calls':0,
        'model_token_usage':None,'token_note':'No model invoked by diagnostic script; parent chat tokens not exposed by CLI.'})
    print(json.dumps({'output':str(output),'collection_exit_code':result['exit_code'],
                      'timed_out':result['timed_out']},ensure_ascii=False))

if __name__ == '__main__':
    main()

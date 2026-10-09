"""Goal 1 evidence only; never overwrites Goal 0 validation records."""
import json
import subprocess
import sys
from pathlib import Path
from reference_guard import inventory, sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'validation/goal1'

def frozen():
    names = subprocess.check_output(['git', '--no-optional-locks', 'ls-files'], cwd=ROOT, encoding='utf-8').splitlines()
    return {name: sha(ROOT / name) for name in names if name != 'PROJECT_STATUS.md'}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if sys.argv[1] == 'before':
        target = OUT / 'guard-before.json'
        if target.exists():
            raise SystemExit('Refuse to overwrite initial Goal 1 guard')
        data = {'frozen': frozen(), 'reference': inventory()}
    else:
        old = json.loads((OUT / 'guard-before.json').read_text(encoding='utf-8'))
        new = {'frozen': frozen(), 'reference': inventory()}
        data = {'frozen_differences': [k for k in old['frozen'] if old['frozen'][k] != new['frozen'].get(k)],
                'reference_differences': [k for k in set(old['reference']['files']) | set(new['reference']['files'])
                                          if old['reference']['files'].get(k) != new['reference']['files'].get(k)],
                'git_differences': [k for k in ('head','branch','status','refs') if old['reference'][k] != new['reference'][k]],
                'files_compared': len(new['reference']['files']), 'coverage': new['reference']['coverage']}
        data['passed'] = not any(data[k] for k in ('frozen_differences','reference_differences','git_differences'))
        target = OUT / 'guard-after.json'
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(target), 'passed': data.get('passed'), 'frozen_files': len(data.get('frozen',{}))}, ensure_ascii=False))

if __name__ == '__main__':
    main()

"""Read-only reference inventory; all output stays in the factory workspace."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path('C:/910Program')
OUT = ROOT / 'validation' / 'reference'

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def git(*args):
    result = subprocess.run(['git', '--no-optional-locks', '-C', str(REFERENCE), *args],
                            capture_output=True, check=True, encoding='utf-8',
                            env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    return result.stdout.strip()

def inventory():
    # No command builds, tests, starts, installs or writes in the reference.
    files = {}
    for directory, dirs, names in os.walk(REFERENCE, followlinks=False):
        for name in names:
            p = Path(directory) / name
            stat = p.stat()
            rel = p.relative_to(REFERENCE).as_posix()
            record = {'size': stat.st_size, 'mtime_ns': stat.st_mtime_ns}
            # Hash all original project and Git files. Dependency tree is huge;
            # record size/mtime for it, clearly disclose this weaker coverage.
            if rel.split('/')[0] != 'node_modules':
                record['sha256'] = sha(p)
            files[rel] = record
    return {'captured_utc': datetime.now(timezone.utc).isoformat(),
            'reference': str(REFERENCE), 'files': files,
            'head': git('rev-parse', 'HEAD'),
            'branch': git('symbolic-ref', '--short', 'HEAD'),
            'status': git('status', '--porcelain=v1', '--untracked-files=all'),
            'refs': git('show-ref'),
            'coverage': 'All files size/mtime; SHA-256 except node_modules. No access-time comparison.'}

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1]
    baseline = OUT / 'before.json'
    if mode == 'before':
        if baseline.exists():
            raise SystemExit('Refuse to overwrite the initial baseline')
        result = inventory()
        baseline.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"Captured {len(result['files'])} files; HEAD {result['head']}; clean={not result['status']}")
    elif mode == 'after':
        old = json.loads(baseline.read_text(encoding='utf-8'))
        new = inventory()
        differences = [key for key in set(old['files']) | set(new['files'])
                       if old['files'].get(key) != new['files'].get(key)]
        state = [key for key in ('head', 'branch', 'status', 'refs') if old[key] != new[key]]
        result = {'captured_utc': new['captured_utc'], 'files_compared': len(new['files']),
                  'file_differences': sorted(differences), 'git_differences': state,
                  'passed': not differences and not state, 'coverage': new['coverage']}
        (OUT / 'after.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['passed'] else 1
    else:
        raise SystemExit('Usage: reference_guard.py before|after')
    return 0

if __name__ == '__main__':
    sys.exit(main())

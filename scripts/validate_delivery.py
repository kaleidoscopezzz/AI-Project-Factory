"""Delivery QA only. Never runs business commands, Git writes, agents or releases."""
import argparse
import copy
import hashlib
import json
import platform
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ('requirement-planner', 'goal0-scaffolder', 'goal-prompt-writer')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def index_unique(items, label):
    require(isinstance(items, list) and items, f'{label}: empty or invalid list')
    keys = [item['id'] for item in items]
    require(all(isinstance(key, str) and key for key in keys), f'{label}: invalid IDs')
    require(len(set(keys)) == len(keys), f'{label}: duplicate IDs')
    return {item['id']: item for item in items}

def check_packet(packet):
    require(packet['schema_version'] == '1.0', 'Unexpected design schema')
    require(packet['status'] == 'ready_for_coder_design_only', 'Design must not claim execution')
    require(re.match(r'^[A-Z]:[\\/]', packet['target_workdir']), 'Target must be absolute')
    baseline = packet['baseline']
    require(baseline['kind'] == 'unverified_target' and baseline['head'] is None
            and baseline['verification_required'] is True, 'Unverified baseline misrepresented')
    for key in ('git_write', 'deploy', 'global_install'):
        require(packet['policy'][key] is False, f'Unauthorized policy: {key}')
    require(packet['retry_budget']['per_issue'] == 2 and
            packet['retry_budget']['total_rounds'] == 3, 'Unexpected retry limits')
    requirements = index_unique(packet['requirements'], 'requirements')
    acceptance = index_unique(packet['acceptance'], 'acceptance')
    tasks = index_unique(packet['tasks'], 'tasks')
    for rid, req in requirements.items():
        require(req['goal'] and req['acceptance_ids'], f'{rid}: no goal/acceptance')
        for aid in req['acceptance_ids']:
            require(aid in acceptance, f'{rid}: unknown acceptance {aid}')
            require(acceptance[aid]['requirement_id'] == rid, f'{aid}: requirement mismatch')
    for aid, ac in acceptance.items():
        require(ac['requirement_id'] in requirements, f'{aid}: unknown requirement')
        require(aid in requirements[ac['requirement_id']]['acceptance_ids'], f'{aid}: unmapped')
        for key in ('given', 'when', 'then', 'method', 'evidence'):
            require(ac.get(key), f'{aid}: missing observable {key}')
    mapped = set()
    for tid, task in tasks.items():
        require(task['role'] and task['outputs'] and task['write_set'], f'{tid}: missing contract')
        for dep in task['depends_on']:
            require(dep in tasks, f'{tid}: unknown dependency {dep}')
        for path in task['write_set'] + task.get('operation_artifact_write_set', []):
            require(isinstance(path, str) and path and '..' not in Path(path).parts
                    and not re.match(r'^[A-Za-z]:|^[/\\]', path), f'{tid}: unsafe relative write path')
        for aid in task['acceptance_ids']:
            require(aid in acceptance, f'{tid}: unknown acceptance {aid}')
            mapped.add(aid)
    require(mapped == set(acceptance), 'Some acceptance criteria have no task')
    done, active = set(), set()
    def visit(tid):
        require(tid not in active, f'Dependency cycle at {tid}')
        if tid in done:
            return
        active.add(tid)
        for dep in tasks[tid]['depends_on']:
            visit(dep)
        active.remove(tid)
        done.add(tid)
    for tid in tasks:
        visit(tid)
    for question in packet['blocking_questions']:
        require(question['question'], 'Empty question')
        for tid in question['blocks_tasks']:
            require(tid in tasks, 'Question blocks unknown task')
    return {'requirements': len(requirements), 'acceptance': len(acceptance), 'tasks': len(tasks)}

def negative_checks(packet):
    mutations = {
        'duplicate_task': lambda p: p['tasks'].append(copy.deepcopy(p['tasks'][0])),
        'unknown_dependency': lambda p: p['tasks'][0]['depends_on'].append('NONEXISTENT'),
        'cycle': lambda p: p['tasks'][0]['depends_on'].append(p['tasks'][0]['id']),
        'git_authorization_expansion': lambda p: p['policy'].update(git_write=True),
        'unmapped_acceptance': lambda p: p['requirements'][0].update(acceptance_ids=['MISSING']),
        'path_escape': lambda p: p['tasks'][0]['write_set'].append('../outside.txt'),
    }
    results = []
    for name, mutate in mutations.items():
        probe = copy.deepcopy(packet)
        mutate(probe)
        try:
            check_packet(probe)
        except ValueError as error:
            results.append({'probe': name, 'rejected': True, 'reason': str(error)})
        else:
            raise ValueError(f'Validator accepted invalid packet: {name}')
    return results

def skill_checks(validator):
    results = []
    for name in SKILLS:
        folder = ROOT / 'skills' / name
        text = (folder / 'SKILL.md').read_text(encoding='utf-8')
        front = yaml.safe_load(text.split('---', 2)[1])
        require(front['name'] == name and front['description'].strip(), f'{name}: invalid metadata')
        official = subprocess.run([sys.executable, '-X', 'utf8', str(validator), str(folder)],
                                  capture_output=True, encoding='utf-8')
        require(official.returncode == 0, f'{name}: official validator: {official.stdout}{official.stderr}')
        count = 0
        for file in folder.rglob('*.md'):
            content = file.read_text(encoding='utf-8')
            for link in re.findall(r'\]\(([^)]+)\)', content):
                if '://' in link or link.startswith('#'):
                    continue
                target = (file.parent / link.split('#')[0]).resolve()
                require(target.is_relative_to(folder.resolve()), f'{file}: nonportable reference {link}')
                require(target.exists(), f'{file}: broken reference {link}')
                count += 1
        ui = yaml.safe_load((folder / 'agents' / 'openai.yaml').read_text(encoding='utf-8'))
        require(25 <= len(ui['interface']['short_description']) <= 64, f'{name}: UI description length')
        require('$' + name in ui['interface']['default_prompt'], f'{name}: UI invocation missing')
        results.append({'skill': name, 'official_exit_code': official.returncode,
                        'official_output': official.stdout.strip(), 'portable_links_checked': count,
                        'ui_metadata': 'valid'})
    return results

def document_links():
    count = 0
    for file in ROOT.rglob('*.md'):
        if '.tools' in file.relative_to(ROOT).parts:
            continue
        for link in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):
                continue
            path = link.split('#')[0].strip('<>')
            if '{{' in path:
                continue
            require((file.parent / path).is_file(), f'{file}: broken document link {link}')
            count += 1
    return count

def fingerprints():
    artifacts = {}
    # Only source deliverables, not the mutable check report, venv or huge reference inventory.
    candidates = [ROOT / name for name in ('AGENTS.md', 'README.md', 'PROJECT_STATUS.md',
                                           'validation/REPORT.md', 'validation/INDEPENDENT_REVIEW.md')]
    for folder in ('skills', 'docs', 'scripts', 'validation/cases'):
        candidates.extend(p for p in (ROOT / folder).rglob('*') if p.is_file()
                          and '__pycache__' not in p.parts)
    for path in sorted(candidates):
        artifacts[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    digest = hashlib.sha256(json.dumps(artifacts, sort_keys=True).encode('utf-8')).hexdigest()
    return {'sha256_by_file': artifacts, 'manifest_sha256': digest,
            'meaning': 'Content fingerprint only, not Git freeze or external acceptance'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--official-validator', required=True, type=Path)
    parser.add_argument('--skills-only', action='store_true')
    args = parser.parse_args()
    result = {'captured_utc': datetime.now(timezone.utc).isoformat(), 'purpose': 'artifact_qa_only',
              'skills': [], 'cases': [], 'passed': False}
    try:
        require(args.official_validator.is_file(), 'Official validator missing')
        result['environment'] = {'python': sys.version.split()[0], 'pyyaml': yaml.__version__,
                                 'platform': platform.platform(),
                                 'official_validator': str(args.official_validator.resolve()),
                                 'official_validator_sha256': hashlib.sha256(args.official_validator.read_bytes()).hexdigest()}
        result['skills'] = skill_checks(args.official_validator)
        if not args.skills_only:
            for cid in ('case-a', 'case-b'):
                folder = ROOT / 'validation' / 'cases' / cid
                for name in ('input.md', 'plan.md', 'goal0-blueprint.md', 'goal0-prompt.md', 'evaluation.md', 'task-packet.json'):
                    require((folder / name).is_file(), f'{cid}: missing {name}')
                packet = json.loads((folder / 'task-packet.json').read_text(encoding='utf-8-sig'))
                require(packet['case_id'] == cid, 'Case mismatch')
                metrics = check_packet(packet)
                for key, expected in [('plan', 'plan.md'), ('blueprint', 'goal0-blueprint.md'), ('prompt', 'goal0-prompt.md')]:
                    require(packet['artifact_paths'][key] == expected, f'{cid}: bad artifact path')
                prompt = (folder / 'goal0-prompt.md').read_text(encoding='utf-8')
                require(not re.search(r'\{\{[^}]+\}\}|\[TODO:', prompt), f'{cid}: unfilled prompt')
                # This is traceability QA, not a semantic proof or a business test.
                goal0 = [a['id'] for a in packet['acceptance'] if re.sub(r'[^a-z0-9]', '',
                         next(r['goal'] for r in packet['requirements'] if r['id'] == a['requirement_id']).lower()) == 'goal0']
                require(goal0, f'{cid}: no Goal 0 criteria')
                require(all(aid in prompt for aid in goal0), f'{cid}: Goal 0 AC absent from prompt')
                result['cases'].append({'case': cid, **metrics, 'goal0_criteria': len(goal0),
                                        'negative_probes': negative_checks(packet)})
            for name in ('AGENTS.md', 'PROJECT_STATUS.md', 'README.md', 'docs/USAGE.md',
                         'docs/SOURCE_EXPERIENCE.md', 'docs/MULTI_AGENT_ROADMAP.md', 'validation/REPORT.md',
                         'validation/INDEPENDENT_REVIEW.md'):
                require((ROOT / name).is_file(), f'Missing deliverable: {name}')
            for name in ('after.json', 'source-inspection.json'):
                evidence = json.loads((ROOT / 'validation/reference' / name).read_text(encoding='utf-8'))
                require(evidence['passed'] is True, f'Reference protection/evidence check failed: {name}')
            result['reference_checks'] = 'passed; coverage limits in reference/after.json'
            result['document_links_checked'] = document_links()
            result['delivery_fingerprint'] = fingerprints()
        result['passed'] = True
    except (ValueError, KeyError, TypeError, OSError, yaml.YAMLError) as error:
        result['error'] = str(error)
    out = ROOT / 'validation' / ('skill-checks.json' if args.skills_only else 'checks.json')
    out.parent.mkdir(exist_ok=True)
    if out.exists():
        previous = out.read_bytes()
        history = out.parent / 'check-runs'
        history.mkdir(exist_ok=True)
        old_path = history / f'{out.stem}-{hashlib.sha256(previous).hexdigest()[:12]}.json'
        if not old_path.exists():
            old_path.write_bytes(previous)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    summary = {key: result[key] for key in ('purpose', 'passed', 'error', 'document_links_checked') if key in result}
    summary['skills'] = result['skills']
    summary['cases'] = [{key: case[key] for key in ('case', 'requirements', 'acceptance', 'tasks', 'goal0_criteria')}
                        | {'negative_probes_rejected': len(case['negative_probes'])} for case in result['cases']]
    if 'delivery_fingerprint' in result:
        summary['manifest_sha256'] = result['delivery_fingerprint']['manifest_sha256']
    summary['report'] = str(out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    sys.exit(main())

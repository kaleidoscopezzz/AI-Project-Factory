"""Read-only guards and source audit; writes a new Goal2 report only."""
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from reference_guard import inventory
from factory.quality_contracts import TESTER_SCHEMA,REVIEWER_SCHEMA,DEFECT_SCHEMA

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*a):return subprocess.check_output(['git','--no-optional-locks',*a],cwd=ROOT,text=True).strip()

def main():
    before=json.loads((ROOT/'validation/goal2/baseline.json').read_text(encoding='utf-8'))
    differences=[]
    for label,files in [('frozen',before['frozen']),('approved_project',before['approved_project'])]:
        for name,h in files.items():
            p=ROOT/name
            if not p.is_file() or sha(p)!=h:differences.append(label+':'+name)
    probe={p.as_posix():sha(p) for p in (ROOT/'projects/sandbox-probe').rglob('*') if p.is_file() and not any(x in {'node_modules','__pycache__','.factory-tmp'} for x in p.parts)}
    if probe!=before['probe_at_closeout']:differences.append('historical_probe')
    old=json.loads((ROOT/before['reference_baseline']).read_text(encoding='utf-8'))['reference'];new=inventory()
    ref_diffs=[p for p in set(old['files'])|set(new['files']) if old['files'].get(p)!=new['files'].get(p)]
    ref_git=[k for k in ('head','branch','status','refs') if old[k]!=new[k]]
    differences.extend('reference:'+p for p in ref_diffs);differences.extend('reference_git:'+k for k in ref_git)
    for key,args in [('head',('rev-parse','HEAD')),('goal0_tag_object',('rev-parse','refs/tags/goal-0-approved')),('goal1_tag_object',('rev-parse','refs/tags/goal-1-approved'))]:
        if git(*args)!=before[key]:differences.append(key)
    assert git('branch','--show-current')=='main'
    allowed={'factory/controller.py','factory/executor.py','factory/contracts.py','scripts/factory.ps1','PROJECT_STATUS.md'}
    modified=git('diff','--name-only','HEAD').splitlines()
    differences.extend('unknown_tracked:'+p for p in modified if p not in allowed)
    if git('diff','--cached','--name-only'):differences.append('unexpected_staged_changes')
    additions={'factory/quality.py','factory/quality_contracts.py','tests/test_quality.py','scripts/validate_goal2.py',
               'scripts/inspect_goal2.py','docs/GOAL2_USAGE.md','factory/schemas/tester-response.schema.json',
               'factory/schemas/reviewer-response.schema.json','factory/schemas/defect-packet.schema.json'}
    untracked=git('ls-files','--others','--exclude-standard').splitlines()
    differences.extend('unknown_untracked:'+p for p in untracked if p not in additions and not p.startswith(('validation/goal2/','projects/sandbox-probe/')))
    for name,schema in [('tester-response',TESTER_SCHEMA),('reviewer-response',REVIEWER_SCHEMA),('defect-packet',DEFECT_SCHEMA)]:
        value=json.loads((ROOT/'factory/schemas'/f'{name}.schema.json').read_text(encoding='utf-8'))
        value.pop('$schema');value.pop('title')
        if value!=schema:differences.append('schema_drift:'+name)
    report={'passed':not differences,'differences':differences,'head':git('rev-parse','HEAD'),
            'frozen_files':len(before['frozen']),'approved_project_files':len(before['approved_project']),
            'reference_files':len(new['files']),'reference_coverage':new['coverage'],
            'probe_files':len(probe),'staged_changes':0,'modified_files':modified,
            'new_source_files':sorted(additions),'source_hashes':{p:sha(ROOT/p) for p in sorted(allowed|additions)},
            'git_write_commands_executed':False,'real_agents_called':False}
    out=ROOT/'validation/goal2'/('audit-'+time.strftime('%Y%m%dT%H%M%S'));out.mkdir(exist_ok=False)
    (out/'guard.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    patch=subprocess.check_output(['git','--no-optional-locks','diff','--no-ext-diff','--no-textconv','HEAD'],cwd=ROOT)
    (out/'changes.patch').write_bytes(patch)
    print(json.dumps({'directory':str(out),'passed':report['passed'],'differences':differences,'frozen':report['frozen_files'],
                      'reference':report['reference_files'],'modified':modified},ensure_ascii=False,indent=2))
    return 0 if report['passed'] else 1

if __name__=='__main__':sys.exit(main())

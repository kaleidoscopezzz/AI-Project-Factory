"""Bounded evidence context. No execution or quality decisions.

Read Markdown file citations and typed JSON path/hash indexes, not log prose or
URLs. Archived paths keep their own namespace; unavailable old bytes stay unknown.
"""
import re
from pathlib import PurePosixPath
from .contracts import FactoryError, file_hash, relative_file

FILE_REF=re.compile(r'(?<![\w./\\:-])(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.(?:md|json|jsonl|log|txt|png|zip|mjs|js|html|css)(?![\w.-])')
ARCHIVE_REF=re.compile(r'validation/history-[A-Za-z0-9-]+(?![\w/-])')

# Reviewer-scoped exceptions, not a policy to ignore historical evidence. The
# referring originals remain required and hash-checked. Never substitute newer
# files for the unavailable bytes or repair an old index.
OLD_TEST_SHA='dab1ed47ae7a127d46fc745f2bdcc3da4bdeff53e40c20ada1394c16fbe0d1a1'
ARCHIVE_GAPS={
    ('validation/history-20261009-095808-578/goal0/acceptance.md','PROJECT_STATUS.md',None):
        '37cfa4e501c3f01a6cedc895c27d0db71c80b9bc54bffe533b354d924495dadf',
    ('validation/history-20261009-095732-444/goal0/source-sha256.json','tests/goal0.test.mjs',OLD_TEST_SHA):
        '48ff440502c276b0ae4d9d28b7e19a9bfc0fd6e73ce6b3d0233b5c8b0b41d8b8',
    ('validation/history-20261009-095808-578/goal0/source-sha256.json','tests/goal0.test.mjs',OLD_TEST_SHA):
        '48ff440502c276b0ae4d9d28b7e19a9bfc0fd6e73ce6b3d0233b5c8b0b41d8b8',
}

def history_dependencies(workspace,completion,candidate,load):
    files=completion.get('workspace_manifest',{});nodes={};edges=[];unknown=[];warnings=[];absent=[];queue=[];runtime_mentions=[]
    def issue(parent,ref,reason,archive_gap=False,expected=None):
        pinned=ARCHIVE_GAPS.get((parent,ref,expected)) if archive_gap else None
        noncritical=bool(pinned and nodes.get(parent,{}).get('sha256')==pinned)
        row={'parent':parent,'reference':ref,'result':'unverified','reason':reason,
             'blocking':not noncritical,'category':'noncritical_archive_reference' if noncritical else 'required_evidence'}
        if noncritical:row.update({'parent_sha256':pinned,'expected_sha256':expected,
                                  'disclosure':'Reviewer-confirmed historical tracing limitation; not current AC pass evidence'})
        target=warnings if noncritical else unknown
        if row not in target:target.append(row)
    def archive(name):
        p=PurePosixPath(name).parts
        return '/'.join(p[:2]) if len(p)>1 and p[0]=='validation' and p[1].startswith('history-') else None
    def add(name,parent,ref,kind='history',expected=None):
        try:path=relative_file(name,workspace)
        except FactoryError as e:issue(parent,ref,str(e));return
        h=files.get(name)
        if not h or not path.is_file() or file_hash(path)!=h:
            issue(parent,ref,'missing or not matched by original completion: '+name);return
        if expected is not None and h!=expected:
            issue(parent,ref,'referenced SHA256 differs from available original bytes: '+name);return
        if not name.startswith('validation/') and candidate['files'].get(name)!=h:
            issue(parent,ref,'delivery/source reference is not current candidate: '+name);return
        e={'parent':parent,'reference':ref,'source':name,'sha256':h,'kind':kind}
        if e not in edges:edges.append(e)
        if name not in nodes:
            nodes[name]={'source':name,'sha256':h,'kind':'history' if name.startswith('validation/') else 'delivery',
                         'bytes':path.stat().st_size,'result':'verified original bytes, not AC approval'}
            queue.append(name)
    def resolve(parent,ref,expected=None,declared_absent=False,descriptive=False):
        if not isinstance(ref,str) or not ref:return
        # Legacy SHA indexes use Windows separators. Normalize only this data
        # spelling; relative_file still rejects drives, traversal and reparse links.
        ref=ref.replace('\\','/')
        if ':' in ref or ref.startswith('/') or '..' in ref.split('/'):
            issue(parent,ref,'absolute/escaping reference is forbidden');return
        # Slash-separated log names in prose are a list, not a directory path.
        segments=ref.split('/')
        if len(segments)>1 and all(FILE_REF.fullmatch(p) for p in segments):
            for part in segments:resolve(parent,part,expected,declared_absent,descriptive)
            return
        if descriptive and ref.split('/')[0] in {'var','dist','build'}:
            runtime_mentions.append({'parent':parent,'reference':ref,'kind':'runtime location described by delivery docs, not historical evidence'})
            return
        a=archive(parent);base=str(PurePosixPath(parent).parent)
        choices=[]
        if ref.startswith('validation/history-'):choices=[ref]
        elif a:
            if ref.startswith('validation/goal0/'):choices=[a+'/goal0/'+ref.split('validation/goal0/',1)[1]]
            elif '/' not in ref:
                choices=[base+'/'+ref,a+'/'+ref,a+'/goal0/'+ref]
                # These are current delivery inputs, not archived state records.
                if ref in {'AGENTS.md','package.json'}:choices.append(ref)
            else:choices=[a+'/'+ref,ref]  # current source bytes require explicit hash match below
        elif '/' not in ref:choices=[base+'/'+ref,'validation/goal0/'+ref,ref]
        else:choices=[ref,base+'/'+ref]
        choices=list(dict.fromkeys(choices))
        available=[n for n in choices if n in files]
        if expected:
            available=[n for n in available if files[n]==expected]
            if not available:
                issue(parent,ref,'historical indexed bytes unavailable for SHA256 '+expected,archive_gap=True,expected=expected);return
        if available:add(available[0],parent,ref,expected=expected)
        elif declared_absent:
            if any(relative_file(n,workspace).is_file() for n in choices):
                issue(parent,ref,'declared missing artifact exists but is not pinned by completion');return
            absent.append({'parent':parent,'reference':ref,'result':'declared not generated in historical document',
                           'checked_completion_paths':choices,'not_pass_evidence':True})
        else:issue(parent,ref,'required reference has no original completion entry in its namespace',archive_gap=True)
    documents=[n for n in candidate['files'] if n.endswith('.md')]
    # Completed root delivery documents remain required even if deletion makes
    # them disappear from the current candidate's enumeration. No new scan.
    for name in files:
        if '/' not in name and name.endswith('.md') and name not in candidate['files']:
            issue('current delivery',name,'original root delivery document missing from current candidate')
    text='\n'.join(relative_file(n,workspace).read_text(encoding='utf-8') for n in documents)
    for name in ('acceptance.md','session-environment.json','source-sha256.json'):
        path='validation/goal0/'+name
        if path in files or name in text:add(path,'completion / delivery docs',path)
    for n in documents:
        # Actual project delivery documents are already in the candidate; scan
        # them for references, keeping their provenance separately from history.
        add(n,'current candidate',n,'delivery')
    while queue:
        if len(nodes)>256 or sum(n['bytes'] for n in nodes.values() if n['source'].endswith(('.md','.json')))>8*1024*1024:
            raise FactoryError('历史依赖索引超过明确读取预算；停止，需人工定向索引')
        name=queue.pop(0);path=relative_file(name,workspace)
        if name.endswith('.md'):
            try:content=path.read_text(encoding='utf-8')
            except UnicodeError:issue(name,name,'historical Markdown is not valid UTF-8');continue
            for line in content.splitlines():
                # Preserve explicit planned/not-generated facts. Do not demand
                # files that the historical record explicitly says never existed.
                planned='计划产物' in line and '未生成' in line
                # Explicit citations are parsed before filename prose; never
                # silently drop escaping or unsupported linked references.
                explicit=re.findall(r'`([^`]+)`|\[[^\]]*\]\(([^)]+)\)',line)
                for pair in explicit:
                    ref=next(x for x in pair if x).strip()
                    if re.search(r'\.[A-Za-z0-9]+$',ref):resolve(name,ref,declared_absent=planned,descriptive=True)
                unsafe=re.findall(r'(?<![\w/])(?:\.\./|[A-Za-z]:[\\/]|/)[^\s`<>，、；;|]+\.(?:md|json|log|txt|png|zip)',line)
                for ref in unsafe:resolve(name,ref)
                for ref in FILE_REF.findall(line):
                    # Bare source/asset mentions are descriptions, not evidence
                    # citations. Qualified source paths and evidence names count.
                    if '/' not in ref and ref.endswith(('.js','.mjs','.html','.css')):continue
                    resolve(name,ref,declared_absent=planned,descriptive=True)
                for ref in ARCHIVE_REF.findall(line):
                    resolve(name,ref+'/goal0/acceptance.md')
        elif name.endswith('.json'):
            try:data=load(path)
            except (ValueError,UnicodeError) as e:issue(name,name,'invalid JSON index: '+str(e));continue
            def walk(value):
                if isinstance(value,dict):
                    if 'path' in value:
                        h=value.get('sha256')
                        if h is not None and (not isinstance(h,str) or not re.fullmatch('[0-9a-f]{64}',h)):
                            issue(name,str(value['path']),'invalid indexed SHA256')
                        else:resolve(name,value['path'],expected=h)
                    # Support explicit filename -> SHA maps without interpreting
                    # arbitrary environment fields or HTTP request URL records.
                    for k,v in value.items():
                        if isinstance(v,str) and re.fullmatch('[0-9a-f]{64}',v) and FILE_REF.fullmatch(k):resolve(name,k,expected=v)
                        elif isinstance(v,(dict,list)):walk(v)
                elif isinstance(value,list):
                    for x in value:walk(x)
            walk(data)
    return {'version':'history-dependencies/1','candidate_fingerprint':candidate['fingerprint'],
            'files':sorted(nodes.values(),key=lambda n:n['source']),'edges':edges,
            'declared_not_generated':absent,'runtime_mentions':runtime_mentions,'unverified':unknown,'archive_warnings':warnings,'ready':not unknown,
            'policy':'Only the three pinned Reviewer-confirmed archive gaps are nonblocking and must be disclosed. Current evidence and other necessary sources remain required. Ready permits testing, never AC approval.',
            'coverage':'Markdown file citations/archive indexes and JSON path/SHA or filename/SHA indexes; logs/source/PNG/trace are leaves. Arbitrary prose is not a universal dependency grammar.'}

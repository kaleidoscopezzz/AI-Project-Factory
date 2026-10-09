"""Versioned agent response contracts and TaskPacket integrity checks."""
import hashlib
import json
import os
import re
from pathlib import Path

STATES = ['待规划','规划中','规划完成','任务包已验证','Coder执行中','基础验证中','已完成','已失败','等待用户确认',
          'Tester执行中','Reviewer审查中','等待返工','Coder返工中','质量门槛通过','质量门槛失败']
SKILLS = ['requirement-planner','goal0-scaffolder','goal-prompt-writer']

class FactoryError(Exception):
    pass

def digest(value):
    return hashlib.sha256(value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()).hexdigest()

def file_hash(path):
    return digest(Path(path).read_bytes())

def obj(properties):
    return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}

S = {'type':'string'}
def arr(item):
    return {'type':'array','items':item}

GOAL = obj({'id':S,'title':S,'depends_on':arr(S),'scope':S})
AC = obj({'id':S,'requirement_id':S,'goal_id':S,'task_id':S,'criterion':S,'method':S})
TASK = obj({'id':S,'goal_id':S,'depends_on':arr(S),'write_set':arr(S),'acceptance_ids':arr(S)})
COMMAND = obj({'purpose':{'type':'string','enum':['build','test']},'argv':arr(S)})
PLAN_SCHEMA = obj({'project_name':S,'project_type':S,'technology':S,'skills_used':arr(S),
                   'plan_md':S,'goals_md':S,'blueprint_md':S,'prompt_md':S,
                   'goals':arr(GOAL),'acceptance':arr(AC),'tasks':arr(TASK),
                   'blocking_questions':arr(S),'risks':arr(S),'checks':arr(COMMAND),
                   'runtime':obj({'argv':arr(S),'path':S,'expected_text':S})})
CODER_SCHEMA = obj({'status':{'type':'string','enum':['completed','failed','needs_confirmation']},
                    'summary':S,'files':arr(S),'tests':arr(obj({'command':S,'exit_code':{'type':'integer'},'result':S})),
                    'evidence':arr(S),'limitations':arr(S),'questions':arr(S)})

def schema_check(value, schema, path='$'):
    typ = schema['type']
    match = {'object': isinstance(value,dict),'array':isinstance(value,list),
             'string':isinstance(value,str),'integer':type(value) is int}
    if not match[typ]:
        raise FactoryError(f'{path} 类型错误：需要 {typ}')
    if 'enum' in schema and value not in schema['enum']:
        raise FactoryError(f'{path} 不在允许值中')
    if typ == 'object':
        if set(value) != set(schema['required']):
            raise FactoryError(f'{path} 字段缺失或多余')
        for k, sub in schema['properties'].items():
            schema_check(value[k],sub,path+'.'+k)
    if typ == 'array':
        for i,v in enumerate(value):
            schema_check(v,schema['items'],f'{path}[{i}]')

def safe_path(path, root, exact=False):
    raw = str(path)
    if '..' in re.split(r'[\\/]',raw) or '\x00' in raw:
        raise FactoryError('路径包含穿越或空字符')
    candidate, base = Path(path), Path(root).resolve()
    # Reject symlinks and Windows junctions at every existing ancestor.
    for node in [candidate,*candidate.parents]:
        if node.is_symlink() or (hasattr(node,'is_junction') and node.is_junction()):
            raise FactoryError('路径包含符号链接或 junction')
    resolved = candidate.resolve()
    if (exact and resolved != base) or (not exact and not resolved.is_relative_to(base)):
        raise FactoryError('路径越出受控项目目录')
    return resolved

def relative_file(name, workspace):
    if not isinstance(name,str) or not name or Path(name).is_absolute() or ':' in name or '\\' in name:
        raise FactoryError('文件必须使用项目内相对路径')
    return safe_path(Path(workspace)/name,workspace)

def dag(rows):
    indexed = {x['id']: x for x in rows}
    if len(indexed) != len(rows):
        raise FactoryError('依赖节点 ID 重复')
    done, active = set(), set()
    def visit(key):
        if key not in indexed:
            raise FactoryError('依赖引用不存在：'+key)
        if key in active:
            raise FactoryError('依赖存在循环：'+key)
        if key in done:
            return
        active.add(key)
        for other in indexed[key]['depends_on']:
            visit(other)
        active.remove(key)
        done.add(key)
    for key in indexed:
        visit(key)

def command_check(argv, start=False):
    if not isinstance(argv,list) or len(argv)<2 or any(not isinstance(x,str) or '\x00' in x for x in argv):
        raise FactoryError('命令必须是非空 argv 数组')
    if argv[0] not in ('node','python','npm'):
        raise FactoryError('基础验证只允许 node/python/npm，其他技术栈先 Plan 人工评审')
    if argv[0] == 'python' and (argv[1] == '-c' or argv[1].startswith('-')):
        raise FactoryError('Python 检查必须是项目脚本')
    if argv[0] == 'node' and argv[1].startswith('-'):
        raise FactoryError('Node 检查必须是项目脚本')
    if argv[0] == 'npm' and not (len(argv)==3 and argv[1]=='run' and argv[2] in ('build','test','start','dev')):
        raise FactoryError('npm 仅允许固定项目 scripts')
    for arg in argv[1:]:
        if '..' in re.split(r'[\\/]',arg) or re.match(r'^[A-Za-z]:',arg) or arg.startswith(('\\','/')):
            raise FactoryError('命令参数包含绝对路径或穿越')
    if start and not any('{port}' in a for a in argv):
        raise FactoryError('启动接口必须接受 {port}，仅绑定 127.0.0.1')

def validate_plan(plan, workspace):
    schema_check(plan,PLAN_SCHEMA)
    if set(plan['skills_used']) != set(SKILLS):
        raise FactoryError('Planner 未声明使用全部三个 Skills')
    for key,minimum in [('project_name',2),('project_type',2),('technology',20),('plan_md',700),('goals_md',200),('blueprint_md',1000),('prompt_md',2200)]:
        if len(plan[key].strip()) < minimum:
            raise FactoryError('Planner 输出不完整：'+key)
    if '{{' in plan['prompt_md'] or str(workspace) not in plan['prompt_md']:
        raise FactoryError('提示词有未填写变量或缺少准确工作目录')
    for word in ('禁止','验收','测试','停止','报告','Goal 0'):
        if word not in plan['prompt_md']:
            raise FactoryError('提示词缺少关键约束：'+word)
    dag(plan['goals']); dag(plan['tasks'])
    goals = {g['id'] for g in plan['goals']}
    tasks = {t['id']:t for t in plan['tasks']}
    if not {'Goal 0','Goal 1'} <= goals:
        raise FactoryError('至少需要 Goal 0 和后续业务 Goal 1')
    acs = {a['id']:a for a in plan['acceptance']}
    if len(acs)!=len(plan['acceptance']) or sum(a['goal_id']=='Goal 0' for a in acs.values()) < 8:
        raise FactoryError('Goal 0 验收不足或 ID 重复')
    for a in acs.values():
        if a['goal_id'] not in goals or a['task_id'] not in tasks or tasks[a['task_id']]['goal_id']!=a['goal_id']:
            raise FactoryError('验收 Goal/Task 映射不一致')
        if len(a['criterion'])<15 or not a['method'].strip() or not a['requirement_id'].strip():
            raise FactoryError('验收不可观察或没有需求来源')
        if a['id'] not in tasks[a['task_id']]['acceptance_ids']:
            raise FactoryError('任务未覆盖映射的验收')
        if a['goal_id']=='Goal 0' and a['id'] not in plan['prompt_md']:
            raise FactoryError('提示词遗漏 Goal 0 验收：'+a['id'])
    for t in tasks.values():
        if t['goal_id'] not in goals or not t['write_set'] or not t['acceptance_ids']:
            raise FactoryError('任务缺少 Goal/写集/验收')
        for name in t['write_set']:
            relative_file(name.rstrip('/*'),workspace)
        if any(a not in acs or acs[a]['task_id']!=t['id'] for a in t['acceptance_ids']):
            raise FactoryError('任务验收引用不一致')
    if not {'build','test'} <= {c['purpose'] for c in plan['checks']}:
        raise FactoryError('缺少构建或测试接口')
    for c in plan['checks']:
        command_check(c['argv'])
    command_check(plan['runtime']['argv'],True)
    if not plan['runtime']['path'].startswith('/') or plan['runtime']['path'].startswith('//') or not plan['runtime']['expected_text'].strip():
        raise FactoryError('运行检查接口无效')

PACKET_FIELDS = {'format_version','task_id','project_id','original_request','goal','project_type','technology','workspace','allow_write','deny_write','prompt_path','acceptance','checks','runtime','budget','input_fingerprint','artifacts','state'}
def validate_packet(packet, root, state):
    if not isinstance(packet,dict) or set(packet)!=PACKET_FIELDS or packet['format_version']!='1.0':
        raise FactoryError('TaskPacket 格式/版本无效')
    for key in ('task_id','project_id','original_request','goal','project_type','technology','workspace','prompt_path','input_fingerprint','state'):
        if not isinstance(packet[key],str) or not packet[key].strip():
            raise FactoryError('TaskPacket 字符串字段无效：'+key)
    for key in ('allow_write','deny_write','acceptance','checks'):
        if not isinstance(packet[key],list):
            raise FactoryError('TaskPacket 列表字段无效：'+key)
    for key in ('artifacts','runtime','budget'):
        if not isinstance(packet[key],dict):
            raise FactoryError('TaskPacket 对象字段无效：'+key)
    for key in ('task_id','project_id','original_request','input_fingerprint'):
        if packet[key] != state[key]:
            raise FactoryError('TaskPacket 与持久化任务身份不一致：'+key)
    project = safe_path(Path(root)/'projects'/state['project_id'],Path(root)/'projects')
    workspace = safe_path(packet['workspace'],project/'workspace',exact=True)
    if packet['allow_write']!=[str(workspace)] or packet['goal']!='Goal 0' or packet['state']!='任务包已验证':
        raise FactoryError('任务范围/状态无效')
    expected_deny = [str(Path(root)/'skills'),str(Path(root)/'validation'),str(Path(root)/'.git'),'C:\\910Program',str(project/'control')]
    if packet['deny_write'] != expected_deny or packet['budget']!=state['budget']:
        raise FactoryError('禁止范围或预算被篡改')
    prompt = safe_path(packet['prompt_path'],project/'control'/'goal0-prompt.md',exact=True)
    expected_files = ('plan.md','goals.md','goal0-blueprint.md','goal0-prompt.md','planner-result.json')
    if set(packet['artifacts'])!=set(expected_files):
        raise FactoryError('任务包产物不齐全')
    for name in expected_files:
        p = safe_path(project/'control'/name,project/'control')
        if not p.is_file() or file_hash(p)!=packet['artifacts'][name]:
            raise FactoryError('规划文件哈希不匹配：'+name)
    plan = json.loads((project/'control/planner-result.json').read_text(encoding='utf-8'))
    validate_plan(plan,workspace)
    for key in ('project_type','technology','checks','runtime'):
        if packet[key]!=plan[key]:
            raise FactoryError('任务包与规划不一致：'+key)
    if packet['acceptance'] != [a for a in plan['acceptance'] if a['goal_id']=='Goal 0']:
        raise FactoryError('任务包验收映射不一致')
    if digest(packet)!=state.get('packet_fingerprint'):
        raise FactoryError('任务包指纹不匹配')
    return workspace, prompt

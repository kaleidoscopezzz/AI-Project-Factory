"""Small product adapter over Controller -> Sequence -> GitAgent -> ReleaseAgent.

This ledger limits the whole CLI run; it does not replace stage/quality ledgers.
Interrupted model calls are never automatically relaunched.
"""
import copy
import shutil
import time
import uuid
from pathlib import Path

from .contracts import (FactoryError, PLAN_SCHEMA, COMMAND, S, arr, obj,
                        digest, file_hash, schema_check, safe_path, relative_file)
from .controller import Controller, load, save, locked
from .sequence import validate_spec, check_receipt

SPEC_SCHEMA = obj({'goal': S, 'prompt_md': S, 'checks': arr(COMMAND),
                   'runtime': PLAN_SCHEMA['properties']['runtime'], 'blocking_questions': arr(S)})
RECIPE_SCHEMA = obj({'name': S, 'source_files': arr(S), 'package_files': arr(S),
                     'runtime_requirement': S, 'smoke': {'type':'string','enum':['http-health','offline-todo']}})
BUILD_SCHEMA = obj({'plan': PLAN_SCHEMA, 'goal1_spec': SPEC_SCHEMA, 'release': RECIPE_SCHEMA})
LIMITS = {'Planner': 1, 'Coder': 2, 'CoderRepair': 1, 'Tester': 3, 'Reviewer': 3}
SOURCE = Path(__file__).parent


def validate_release_plan(plan, spec, recipe):
    """Validate the existing ReleaseAgent contract before spending a Coder call."""
    for runtime in (plan['runtime'],spec['runtime']):
        argv=runtime['argv']
        for flag,value in (('--host','127.0.0.1'),('--port','{port}'),('--data-dir','var')):
            if flag not in argv or argv.index(flag)+1>=len(argv) or argv[argv.index(flag)+1]!=value:
                raise FactoryError('产品运行契约需要 '+flag+' '+value+'；完整规划已保留，不派发不兼容工程')
    for argv in [c['argv'] for c in spec['checks']]+[spec['runtime']['argv']]:
        if argv[1] not in recipe['source_files']:
            raise FactoryError('发行来源清单缺少获批的构建/测试/运行入口')
    if spec['runtime']['argv'][1] not in recipe['package_files']:
        raise FactoryError('发行包必须保留获批运行入口的原相对路径，不能只放入dist子目录')


def source_files():
    return {p.name: file_hash(p) for p in sorted(SOURCE.glob('*.py'))}


class RunExecutor:
    """One durable shared budget across both stages and quality repair calls."""
    def __init__(self, native, folder, ledger):
        self.native, self.folder, self.ledger = native, folder, ledger
        self.planning = True

    @property
    def full_access(self): return self.native.full_access

    @full_access.setter
    def full_access(self, value): self.native.full_access = value

    def verify(self):
        expected=self.ledger.get('preparation_fix',{}).get('factory_files',self.ledger['factory_files'])
        if expected != source_files():
            raise FactoryError('运行绑定的工厂代码发生变化；停止，不绕过检查点')
        if 'preparation_fix' in self.ledger:
            pin=self.ledger['preparation_fix']
            if file_hash(relative_file(pin['record'],self.folder))!=pin['sha256']:
                raise FactoryError('零派发准备修复来源记录已变化')
        for n, h in self.ledger['resources'].items():
            if file_hash(relative_file(n, self.folder)) != h:
                raise FactoryError('工厂/Skill 快照已变化')

    def remaining(self):
        left = self.ledger['deadline'] - time.time()
        if left < 1: raise FactoryError('整轮 3600 秒墙钟预算已耗尽；不追加调用')
        return left

    def probe(self, cwd, control):
        self.verify()
        if self.planning:
            return {'mode':'read-only Planner', 'future_coder_intent':'danger-full-access',
                    'scope':'planning only; no engineering permission granted by intent'}
        return self.native.probe(cwd, control)

    def preflight(self, *args):
        self.verify(); self.remaining()
        return self.native.preflight(*args)

    def sandbox_argv(self, *args): return self.native.sandbox_argv(*args)

    def check(self, argv, cwd, control, index, timeout=180):
        self.verify()
        return self.native.check(argv, cwd, control, index, min(timeout, self.remaining()))

    def run(self, role, prompt, cwd, control, attempt, schema, timeout):
        self.verify()
        logical = 'CoderRepair' if role == 'Coder' and control.parent.name == 'calls' else role
        calls = self.ledger['calls']
        if any(c['status'] in ('running', 'interrupted') for c in calls):
            raise FactoryError('存在未确认完成的模型调用；不隐式重试')
        if sum(c['role'] == logical for c in calls) >= LIMITS[logical]:
            raise FactoryError(logical + ' 整轮调用预算已用尽')
        if logical in ('Tester','Reviewer'):
            # More than two calls is only permitted after the single real repair.
            if sum(c['role'] == logical for c in calls) >= 2 and not any(c['role']=='CoderRepair' for c in calls):
                raise FactoryError('额外质量调用必须用于已登记的返工后复验')
        timeout = min(timeout, 600, self.ledger['agent_timeout'], self.remaining())
        rec = {'role':logical, 'status':'running', 'started_at':time.time(),
               'input_sha256':digest(prompt.encode()), 'control':str(control.relative_to(self.folder)),
               'timeout_seconds':timeout}
        calls.append(rec); save(self.folder/'run.json', self.ledger)
        print('[APF] '+logical+'，整轮调用 '+str(len(calls))+'/10', flush=True)
        try:
            if role == 'Planner':
                prompt += PRODUCT_INSTRUCTIONS
                if self.ledger.get('browser_tool'):
                    prompt += '\n已验证的本机浏览器测试工具目录（仅执行环境，不得写入交付源码）：'+self.ledger['browser_tool']+'\n'
                schema = BUILD_SCHEMA
            result = self.native.run(role, prompt, cwd, control, attempt, schema, timeout)
            original = copy.deepcopy(result)
            out = self.folder/('execution-'+str(len(calls))+'.json')
            save(out, original)
            rec.update(status='finished', result=out.name, sha256=file_hash(out),
                       exit_code=result.get('exit_code'), elapsed_seconds=result.get('elapsed_seconds'),
                       usage=result.get('usage'), thread_ids=result.get('thread_ids'))
            save(self.folder/'run.json', self.ledger)
            if role == 'Planner' and result.get('output') is not None:
                value=result['output']; schema_check(value, BUILD_SCHEMA)
                # Save the complete original response, including unsupported goals.
                save(self.folder/'product-plan.json', value)
                self.ledger['plan_sha256']=file_hash(self.folder/'product-plan.json')
                save(self.folder/'run.json', self.ledger)
                result={**result,'output':value['plan']}
            return result
        except BaseException:
            if rec['status']=='running':
                rec['status']='interrupted'; save(self.folder/'run.json', self.ledger)
            raise


PRODUCT_INSTRUCTIONS = '''
\n本次是统一产品入口：只规划一次，随后主控执行两个软件Goal，并以已批准的Goal1发行。
输出顶层 plan（原PLAN_SCHEMA完整对象）、goal1_spec、release。不得只输出旧四份Markdown。
完整保留全部需求。当前自动支持两个Goal：Goal0是可运行基础及核心功能，Goal1在已有工程完成其余需求、回归及交付。
如果需求确实无法收敛到两阶段，保留完整goals，并写blocking_questions解释不支持，不能偷偷删功能。
两阶段均使用无第三方运行依赖的Node或Python回环HTTP服务；需安装其他运行依赖/非服务程序则列重大问题停止。
两份实施提示词须包含约定文件布局；Goal1提示词明确最终source_files/package_files，使Coder能交付这份已规划清单。
goal1_spec.goal严格为Goal 1；prompt_md包含实际工作目录、所有Goal1 AC、增量、禁止、测试、验收、停止、报告。
Goal1任务write_set必须包含所有需要修改的源码、UI、配置和测试路径，但不能删除前序源码。
checks分别至少build/test，必须使用直接node或python脚本；runtime接受单独{port}并绑定127.0.0.1。
两个runtime.argv必须明确包含 --host 127.0.0.1 --port {port} --data-dir var，Coder实现这些参数。
持久数据和锁放var，源码/测试不放var；不能让检查产生的数据/排他锁成为候选源码。
主控和发行检查会终止其拥有的服务进程；之后使用同一数据目录必须仍能启动。
排他锁需有可验证的owner并能安全恢复已退出owner的锁，不能永久留下无owner的空锁，也不能删除活进程持有的锁。
两阶段交付验收文档使用validation/acceptance.md（Goal1可validation/goal1/acceptance.md），引用同目录或明确相对路径的真实日志。
本轮AC-012如存在只核验当前交付说明、映射、真实命令结果、日志/截图/Trace和操作范围；新项目没有历史失败原件时不能凭空要求。
build/test脚本必须在无第三方开发工具的独立发行构建副本内可运行；浏览器专项另用本机已安装Playwright/Edge，不把私有绝对路径写入软件交付源码。
release是最终Goal1的明确文件清单：source_files包含构建及基础测试所需全部源文件/配置/脚本/资源；package_files包含运行必须文件，可引用dist/build输出。
package_files必须保留runtime.argv[1]的原相对路径；例如node src/server.mjs要求ZIP内src/server.mjs，不能只有dist/src/server.mjs。
运行入口推荐src/server.mjs；Node用ESM和标准库，HTTP健康端点。浏览器测试由独立Tester执行，不让发行脚本依赖Playwright。
release.name为小写英文短横线slug；runtime_requirement准确注明Node/Python版本、非独立EXE；smoke一般http-health。
待办工具使用offline-todo发行配方：根页面含html，/app.js和/style.css可用；GET/POST /api/todos，PATCH/DELETE /api/todos/:id。
使用title与completed字段；GET返回{items:[...]}, POST成功201并直接返回条目，PATCH支持title/completed并200直接返回条目，DELETE成功204。
这用于解压后真实新增、完成、编辑、删除和重启持久化检查，不等同于其他软件类型的通用业务验收。
不要输出安装器、云部署、GitHub下载或已验收结论。Git/发行由主控在Reviewer批准后处理。
'''


class ProductRun:
    def __init__(self, output, *, request=None, resume=False, full_access=False,
                 allow_local_git=False, executor=None, skills=None, timeout=600, controller_factory=Controller):
        if not full_access:
            raise FactoryError('当前 --build 工程执行需要显式 --full-access；使用当前用户权限，没有OS工作区隔离')
        if not 1 <= timeout <= 600: raise FactoryError('--build 单次Agent超时为1–600秒')
        self.output=Path(output).absolute()
        safe_path(self.output,self.output)
        self.folder=safe_path(self.output/'.apf',self.output)
        self.native=executor; self.controller_factory=controller_factory
        self.resuming=resume
        if resume:
            if request is not None: raise FactoryError('恢复不接受新的需求')
            self.ledger=load(self.folder/'run.json')
            if self.ledger['version']!=1 or self.ledger['output']!=str(self.output):
                raise FactoryError('恢复运行身份不匹配')
            if self.ledger['allow_local_git']!=allow_local_git or self.ledger['agent_timeout']!=timeout:
                raise FactoryError('恢复参数须与原授权一致，不能改变预算或Git授权')
        else:
            if not isinstance(request,str) or not request.strip() or len(request)>16000:
                raise FactoryError('需求不能为空且最多16000字符')
            from .executor import redact
            if redact(request)!=request: raise FactoryError('需求疑似包含秘密；拒绝记录')
            if self.output.exists(): raise FactoryError('输出目录已存在；禁止覆盖，已有运行请用 --resume')
            self.output.mkdir(parents=True,exist_ok=False); self.folder.mkdir()
            resources={}
            for name, source in skills.items():
                dest=self.folder/'skills'/name; shutil.copytree(source,dest)
            shutil.copytree(SOURCE,self.folder/'factory',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            for p in [*self.folder.joinpath('skills').rglob('*'),*self.folder.joinpath('factory').rglob('*')]:
                if p.is_file(): resources[p.relative_to(self.folder).as_posix()]=file_hash(p)
            self.ledger={'version':1,'run_id':'run-'+uuid.uuid4().hex[:12], 'output':str(self.output),
                         'request':request,'allow_local_git':allow_local_git,'agent_timeout':timeout,
                         'started_at':time.time(),'deadline':time.time()+3600,'limits':LIMITS,
                         'calls':[],'factory_files':source_files(),'resources':resources,
                         'project_id':None,'status':'prepared','plan_sha256':None,'result':None}
            save(self.folder/'run.json',self.ledger)

    def recover_preparation(self):
        """Single local resume of a zero-call document assembly error only.

        Original runtime resources, model results and failed quality ledger stay
        immutable. No invocation/time budget is renewed by this operation.
        """
        if not self.resuming or self.ledger.get('preparation_fix'):return
        if self.ledger['status']!='stopped' or not self.ledger.get('project_id'):return
        c=self.controller_factory(self.folder,self.native,True)
        project,control,workspace,state=c.locate(self.ledger['project_id'])
        if state['status']!='质量门槛失败' or not (state.get('error') or '').startswith('历史资料缺失/哈希不匹配/依赖未验证'):return
        q=load(control/'quality/state.json')
        if q['calls'] or q['rounds'] or q['repairs']:raise FactoryError('准备恢复只允许未派发质量Agent的上下文')
        now=source_files();before=self.ledger['factory_files']
        delta={n for n in set(now)|set(before) if now.get(n)!=before.get(n)}
        if not delta or not delta<={'product.py','controller.py','history.py'}:
            raise FactoryError('零派发路径修复之外的工厂变化，不自动接续')
        from .contracts import validate_packet
        from .quality import candidate
        from .history import history_dependencies
        packet=load(control/'task-packet.json');validate_packet(packet,c.root,state)
        completion=load(control/'completion.json')
        proof=history_dependencies(workspace,completion,candidate(workspace),load)
        if not proof['ready']:raise FactoryError('修复后历史引用仍未验证；不调用模型')
        name='quality-goal0-product-prep'
        c.use_unstarted_quality_context(project.name,name)
        record=self.folder/'preparation-fix.json'
        save(record,{'kind':'zero-model document preparation fix; not Tester retry/approval',
             'original_factory_files':before,'factory_files':now,'changed':sorted(delta),
             'original_quality_sha256':file_hash(control/'quality/state.json'),
             'completion_sha256':file_hash(control/'completion.json'),'packet_fingerprint':digest(packet),
             'candidate':candidate(workspace),'dependencies':proof,'calls_before':copy.deepcopy(self.ledger['calls']),
             'deadline_unchanged':self.ledger['deadline'],'quality_context':name})
        self.ledger['preparation_fix']={'record':record.name,'sha256':file_hash(record),'factory_files':now,'quality_context':name}
        save(self.folder/'run.json',self.ledger)

    def execute(self):
        with locked(self.folder):
            # Second process must read the actual ledger under the run lock.
            self.ledger=load(self.folder/'run.json')
            if self.ledger['limits']!=LIMITS: raise FactoryError('整轮调用预算被修改')
            self.recover_preparation()
            wrapper=RunExecutor(self.native,self.folder,self.ledger)
            wrapper.verify()
            if self.ledger['status']=='delivered':
                result=self.ledger['result']
                for key in ('package','record'): safe_path(result[key],self.folder/'releases')
                if file_hash(result['package'])!=result['sha256'] or file_hash(result['record'])!=result['record_sha256']:
                    raise FactoryError('交付文件已变化，不能沿用成功结果')
                c=self.controller_factory(self.folder)
                project,control,workspace,_=c.locate(self.ledger['project_id'])
                cursor=load(control/'sequence/state.json')
                receipt=check_receipt(project,cursor['completed']['Goal 1'],'Goal 1')
                from .quality import candidate
                if receipt['candidate']!=candidate(workspace):raise FactoryError('交付后的工程候选发生变化')
                record=load(result['record'])
                for name,h in record.get('evidence',{}).items():
                    if file_hash(relative_file(name,Path(result['record']).parent))!=h:
                        raise FactoryError('发行验证证据已变化')
                return result
            wrapper.remaining()
            c=self.controller_factory(self.folder,wrapper,False)
            if self.ledger['project_id'] is None:
                self.ledger['project_id']=c.create(self.ledger['request'],self.ledger['agent_timeout'],
                                                 coder_execution_intent='danger-full-access')
                save(self.folder/'run.json',self.ledger)
            pid=self.ledger['project_id']
            print('[APF] '+self.ledger['run_id']+'，项目 '+pid,flush=True)
            try:
                wrapper.full_access=False
                project,control,workspace,state=c.locate(pid)
                if not (control/'task-packet.json').exists():
                    from .executor import playwright_path
                    # Provide installed browser tooling as runtime context, never
                    # require a private tool path in delivered software sources.
                    if not getattr(self.native,'label',None):
                        self.ledger['browser_tool']=playwright_path()
                    state=c.run(pid,'Plan')
                    if state['status']!='任务包已验证': raise FactoryError(state.get('error') or state['status'])
                if file_hash(self.folder/'product-plan.json')!=self.ledger['plan_sha256']:
                    raise FactoryError('产品规划来源SHA不匹配')
                value=load(self.folder/'product-plan.json')
                if value['plan']!=load(control/'planner-result.json'): raise FactoryError('产品规划与原Planner结果不一致')
                if [g['id'] for g in value['plan']['goals']]!=['Goal 0','Goal 1']:
                    raise FactoryError('目前只支持两个顺序Goal；完整规划已保存，需求未丢弃')
                validate_spec(value['goal1_spec'],value['plan'],workspace)
                for checks in (value['plan']['checks'],value['goal1_spec']['checks']):
                    if len(checks)!=2 or {i['purpose'] for i in checks}!={'build','test'} or any(i['argv'][0] not in ('node','python') for i in checks):
                        raise FactoryError('产品首版每阶段仅支持一条直接Node/Python build和test；规划完整保留')
                if any(r['argv'][0] not in ('node','python') for r in (value['plan']['runtime'],value['goal1_spec']['runtime'])):
                    raise FactoryError('产品发行仅支持直接Node/Python服务')
                validate_release_plan(value['plan'],value['goal1_spec'],value['release'])
                for key in ('source_files','package_files'):
                    if not value['release'][key]: raise FactoryError('发行文件清单为空')
                    for name in value['release'][key]: relative_file(name,workspace)
                c.full_access=True; wrapper.full_access=True; wrapper.planning=False
                c.prepare_goal_sequence(pid,value['goal1_spec'],self.ledger['run_id'],allow_repair=True)
                self.ledger['status']='developing'; save(self.folder/'run.json',self.ledger)
                # The existing Sequence skips source-bound, already completed stages.
                if self.ledger.get('preparation_fix'):
                    c._quality_context=self.ledger['preparation_fix']['quality_context']
                    seq=c.run_goal_sequence(pid,'Goal 0')
                    if 'Goal 0' not in seq['completed']:raise FactoryError(seq.get('error') or 'Goal0质量未通过')
                    del c._quality_context
                seq=c.run_goal_sequence(pid)
                if seq['status']!='两阶段已完成': raise FactoryError(seq.get('error') or str(seq))
                if self.ledger['allow_local_git']:
                    c.configure_project_git(pid,{'version':1,'project_id':pid,'authorization_id':self.ledger['run_id'],
                        'allow_init':True,'allow_local_commit':True,'branch':'main'})
                    version=c.version_approved_stage(pid,'Goal 1')
                    self.ledger['git']=version; save(self.folder/'run.json',self.ledger)
                    if version['status'] not in ('committed','already_versioned','recovered','no_changes'): raise FactoryError('本地Git版本管理未成功：'+str(version))
                wrapper.remaining()
                if 'release_config' not in self.ledger:
                    self.ledger['release_config']={**value['release'],'version':1,'project_id':pid,'goal':'Goal 1',
                        'authorization_id':self.ledger['run_id'],'timeout_seconds':min(120,int(wrapper.remaining()))}
                    save(self.folder/'run.json',self.ledger)
                config=self.ledger['release_config']
                if wrapper.remaining()<config['timeout_seconds']:raise FactoryError('剩余时间不足以安全恢复原发行配置；不更换发行身份重试')
                release=c.release_approved_stage(pid,'Goal 1',config)
                if release['status'] not in ('released','already_released'): raise FactoryError(release.get('message','发行失败'))
                record=load(release['record'])
                result={'status':'delivered','run_id':self.ledger['run_id'],'project_id':pid,
                        'workspace':str(workspace),'package':release['package'],'sha256':record['package']['sha256'],
                        'record':release['record'],'record_sha256':file_hash(release['record']),
                        'runtime_requirement':record['runtime_requirement'],
                        'start_command':'powershell -NoProfile -ExecutionPolicy Bypass -File .\\START.ps1 -Port 3000',
                        'source':record['binding'],'limitations':record['limitations'],
                        'validation':'new-directory extraction, real startup and configured smoke passed'}
                self.ledger.update(status='delivered',result=result,error=None)
                save(self.folder/'run.json',self.ledger);save(self.output/'BUILD_RESULT.json',result)
                (self.output/'RUN.md').write_text('运行环境：'+result['runtime_requirement']+'\n\n解压发行ZIP到新的可写目录，在该目录执行：\n\n'+result['start_command']+'\n\n打开 http://127.0.0.1:3000 。\nSHA-256：'+result['sha256']+'\n',encoding='utf-8')
                return result
            except BaseException as exc:
                from .executor import redact
                self.ledger.update(status='stopped',error=redact(str(exc)))
                save(self.folder/'run.json',self.ledger)
                raise

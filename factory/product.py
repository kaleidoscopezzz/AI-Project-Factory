"""Small product adapter over Controller -> Sequence -> GitAgent -> ReleaseAgent.

This ledger limits the whole CLI run; it does not replace stage/quality ledgers.
Interrupted model calls are never automatically relaunched.
"""
import copy
import json
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
CONTINUATION_LIMITS = {'Planner':0,'Coder':1,'CoderRepair':1,'Tester':3,'Reviewer':3}
STAGE_CONTINUATION_LIMITS = {'Planner':0,'Coder':1,'CoderRepair':1,'Tester':2,'Reviewer':2}
QUALITY_CONTINUATION_LIMITS = {'Planner':0,'Coder':0,'CoderRepair':1,'Tester':2,'Reviewer':2}
SOURCE = Path(__file__).parent

def limits_for(ledger):
    expected=(QUALITY_CONTINUATION_LIMITS if ledger.get('quality_continuation') else
              STAGE_CONTINUATION_LIMITS if ledger.get('approved_goal0_continuation') else
              CONTINUATION_LIMITS if ledger.get('continuation') else LIMITS)
    if ledger['limits']!=expected:raise FactoryError('整轮调用预算被修改')
    return expected


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
    def __init__(self, native, folder, ledger, *, ledger_path=None):
        self.native, self.folder, self.ledger = native, folder, ledger
        self.path=safe_path(ledger_path or folder/'run.json',folder)
        if ledger.get('quality_continuation') and self.path!=relative_file(ledger['quality_continuation']['ledger'],folder):
            raise FactoryError('独立质量授权必须使用独立账本，不能覆盖原运行')
        self.planning = True

    @property
    def full_access(self): return self.native.full_access

    @full_access.setter
    def full_access(self, value): self.native.full_access = value

    def verify_sources(self):
        limits_for(self.ledger)
        if self.ledger.get('quality_continuation'):
            pin=self.ledger['quality_continuation'];record=relative_file(pin['record'],self.folder)
            if file_hash(record)!=pin['sha256']:raise FactoryError('新质量授权来源变化')
            value=load(record)
            if value['limits']!=limits_for(self.ledger) or value['deadline']!=self.ledger['deadline'] or value['factory_files']!=self.ledger['factory_files']:
                raise FactoryError('新质量授权的预算或代码检查点变化')
            for name,h in value['files'].items():
                if file_hash(relative_file(name,self.folder))!=h:raise FactoryError('质量接续原件变化：'+name)
        if self.ledger.get('continuation'):
            entry=self.ledger['continuation'];path=relative_file(entry['record'],self.folder)
            if file_hash(path)!=entry['sha256']:raise FactoryError('接续授权来源变化')
            source=load(path);root=Path(source['source_runtime'])
            if source['limits']!=limits_for(self.ledger):raise FactoryError('接续授权预算范围不匹配')
            if bool(self.ledger.get('approved_goal0_continuation'))!=(source['kind']=='authorized Goal 1 continuation of actual approved Goal 0'):
                raise FactoryError('接续阶段授权模式不匹配')
            for name,h in source.get('prepared_input_files',{}).items():
                if file_hash(relative_file(name,self.folder))!=h:raise FactoryError('Coder交接预检原件变化')
            claim=safe_path(source['claim']['path'],root.parent.parent)
            if file_hash(claim)!=source['claim']['sha256']:raise FactoryError('接续授权占用记录变化')
            for name,h in source['source_files'].items():
                if file_hash(relative_file(name,root))!=h:raise FactoryError('接续原始成果变化：'+name)
        for n,h in self.ledger['resources'].items():
            if file_hash(relative_file(n,self.folder))!=h:raise FactoryError('工厂/Skill快照变化')

    def verify(self):
        self.verify_sources()
        expected=self.ledger.get('quality_preparation',self.ledger.get('saved_delivery',self.ledger.get('preparation_fix',{}))).get('factory_files',self.ledger['factory_files'])
        if expected != source_files():
            raise FactoryError('运行绑定的工厂代码发生变化；停止，不绕过检查点')
        if self.ledger.get('quality_preparation'):
            pin=self.ledger['quality_preparation'];value=load(relative_file(pin['record'],self.folder))
            if file_hash(relative_file(pin['record'],self.folder))!=pin['sha256'] or value['calls']!=self.ledger['calls'][:len(value['calls'])] or value['deadline']!=self.ledger['deadline']:
                raise FactoryError('质量准备修复的原预算/调用来源变化')
            for name,h in value['files'].items():
                if file_hash(relative_file(name,self.folder))!=h:raise FactoryError('质量准备历史来源变化')
        if self.ledger.get('saved_delivery'):
            pin=self.ledger['saved_delivery'];record=relative_file(pin['record'],self.folder)
            if file_hash(record)!=pin['sha256']:raise FactoryError('保存产物接续检查点变化')
            value=load(record)
            if value['original_factory_files']!=self.ledger['factory_files'] or value['calls']!=self.ledger['calls'][:1] or value['deadline']!=self.ledger['deadline']:
                raise FactoryError('保存产物接续不能刷新原调用或时限')
            for name,h in value['files'].items():
                if file_hash(relative_file(name,self.folder))!=h:raise FactoryError('保存产物来源变化')
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
        if self.ledger.get('approved_goal0_continuation') and 'goals/goal-1' not in control.as_posix():
            raise FactoryError('本次只授权Goal 1，禁止重复任何Goal 0 Agent')
        calls = self.ledger['calls']
        if any(c['status'] in ('running', 'interrupted') for c in calls):
            raise FactoryError('存在未确认完成的模型调用；不隐式重试')
        if self.ledger.get('continuation') and logical=='Coder' and 'goals/goal-1' not in control.as_posix():
            raise FactoryError('接续禁止重复派发Goal 0 Coder')
        if sum(c['role'] == logical for c in calls) >= limits_for(self.ledger)[logical]:
            raise FactoryError(logical + ' 整轮调用预算已用尽')
        if logical in ('Tester','Reviewer'):
            if self.ledger.get('approved_goal0_continuation') and any(c['role']==logical for c in calls) and not any(c['role']=='CoderRepair' for c in calls):
                raise FactoryError('第二次质量调用仅用于真实返工后的复验')
            # More than two calls is only permitted after the single real repair.
            if sum(c['role'] == logical for c in calls) >= 2 and not any(c['role']=='CoderRepair' for c in calls):
                raise FactoryError('额外质量调用必须用于已登记的返工后复验')
        timeout = min(timeout, 600, self.ledger['agent_timeout'], self.remaining())
        rec = {'role':logical, 'status':'running', 'started_at':time.time(),
               'input_sha256':digest(prompt.encode()), 'control':str(control.relative_to(self.folder)),
               'timeout_seconds':timeout}
        calls.append(rec); save(self.path, self.ledger)
        print('[APF] '+logical+'，整轮调用 '+str(len(calls))+'/'+str(sum(limits_for(self.ledger).values())), flush=True)
        try:
            if role == 'Planner':
                prompt += PRODUCT_INSTRUCTIONS
                if self.ledger.get('browser_tool'):
                    prompt += '\n已验证的本机浏览器测试工具目录（仅执行环境，不得写入交付源码）：'+self.ledger['browser_tool']+'\n'
                schema = BUILD_SCHEMA
            result = self.native.run(role, prompt, cwd, control, attempt, schema, timeout)
            original = copy.deepcopy(result)
            out = self.path.parent/('execution-'+str(len(calls))+'.json')
            save(out, original)
            rec.update(status='finished', result=out.relative_to(self.folder).as_posix(), sha256=file_hash(out),
                       exit_code=result.get('exit_code'), elapsed_seconds=result.get('elapsed_seconds'),
                       usage=result.get('usage'), thread_ids=result.get('thread_ids'))
            save(self.path, self.ledger)
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
                rec['status']='interrupted'; save(self.path, self.ledger)
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
    def open_quality_window(self,authorization_id):
        """New explicit quality grant over a verified repair; old run stays frozen."""
        import re
        from .sequence import stage_controller,predecessor_context
        from .quality import QualityGate,candidate
        if not self.native.full_access or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',authorization_id):
            raise FactoryError('独立质量续跑需要本次授权标识和显式Full Access')
        with locked(self.folder):
            old=load(self.folder/'run.json');RunExecutor(self.native,self.folder,old).verify_sources()
            before=old.get('quality_preparation',{}).get('factory_files',{})
            now=source_files()
            if not before or not {n for n in set(before)|set(now) if before.get(n)!=now.get(n)}<={'product.py','quality.py'}:
                raise FactoryError('质量续跑之外的工厂代码变化')
            pin=old['quality_preparation'];proof=relative_file(pin['record'],self.folder)
            if file_hash(proof)!=pin['sha256']:raise FactoryError('修复后检查点变化')
            for name,h in load(proof)['files'].items():
                if file_hash(relative_file(name,self.folder))!=h:raise FactoryError('修复来源变化')
            c=stage_controller(self.controller_factory(self.folder,self.native,True))
            project,control,work,state=c.locate(old['project_id'])
            with locked(control):
                packet=load(control/'task-packet.json');predecessor_context(control,packet)
                q=load(control/'quality/state.json');snap=candidate(work)
                if (packet['goal']!='Goal 1' or not q['repairs'] or not q['repairs'][-1]['valid_repair']
                    or q['repairs'][-1]['after']!=snap or q['rounds'][-1]['candidate']!=snap
                    or q['rounds'][-1]['tester'] is not None or q['rounds'][-1]['reviewer'] is not None):
                    raise FactoryError('不是已修复且未复验的Goal 1候选')
                check=QualityGate.__new__(QualityGate)
                check.c=c;check.control=control;check.folder=control/'quality';check.workspace=work
                check.state=state;check.packet=packet;check.q=q;check.load=load
                check.guard();check.verify_context(q['rounds'][-1])
                directory=self.folder/'quality-windows'/('qc-'+digest(authorization_id)[:12])
                if directory.exists():raise FactoryError('本次独立质量授权已使用；恢复原账本，不能重复派发')
                directory.mkdir(parents=True,exist_ok=False)
                name='quality-goal1-'+directory.name;new=control/name;new.mkdir(exist_ok=False)
                for source,target in ((control/'state.json','previous-state.json'),(control/'quality/state.json','previous-quality-state.json')):
                    (new/target).write_bytes(source.read_bytes())
                save(new/'source.json',{'kind':'explicitly authorized quality continuation of verified repaired candidate',
                    'old_quality_path':str(control/'quality/state.json'),'old_quality_sha256':file_hash(control/'quality/state.json'),
                    'previous_state_sha256':file_hash(new/'previous-state.json'),'completion_sha256':file_hash(control/'completion.json'),
                    'packet_fingerprint':digest(packet),'historical_code_quality':True})
                c._quality_context=name;gate=QualityGate(c,project,control,work,state,allow_repair=True)
                row=gate.make_round();gate.verify_context(row)
                files=[self.folder/'run.json',proof,control/'quality/state.json',new/'source.json',new/'previous-state.json',
                    control/'task-packet.json',control/'completion.json',control/'coder-result.json']
                files.extend(relative_file(x['result'],self.folder) for x in old['calls'])
                started=time.time();record=directory/'authorization.json';path=directory/'run.json'
                save(record,{'authorization_id':authorization_id,'limits':QUALITY_CONTINUATION_LIMITS,'deadline':started+3600,
                    'factory_files':now,'candidate':snap,'packet_fingerprint':digest(packet),
                    'permission':'explicit current-user CoderRepair/Tester; independent Reviewer read-only; no OS isolation',
                    'files':{p.relative_to(self.folder).as_posix():file_hash(p) for p in files}})
                ledger={'run_id':directory.name,'project_id':old['project_id'],'approved_goal0_continuation':True,
                    'factory_files':now,'resources':old['resources'],'agent_timeout':600,'deadline':started+3600,
                    'limits':QUALITY_CONTINUATION_LIMITS,'calls':[],'status':'prepared','quality_context':name,
                    'quality_continuation':{'record':record.relative_to(self.folder).as_posix(),'sha256':file_hash(record),
                        'ledger':path.relative_to(self.folder).as_posix()}}
                save(path,ledger);return path

    def recover_repaired_preparation(self):
        """Prepare the already authorized repaired candidate; never renew a grant.

        Only a failed history assembly before the next model dispatch qualifies.
        The failed ledgers and all prior model outcomes are retained as sources.
        """
        from .sequence import stage_controller
        from .quality import QualityGate, candidate
        with locked(self.folder):
            self.ledger=load(self.folder/'run.json');limits_for(self.ledger)
            if self.ledger.get('quality_preparation') or not self.ledger.get('saved_delivery') or self.ledger['status']!='stopped':
                raise FactoryError('不是可恢复的修复后材料准备失败')
            wrapper=RunExecutor(self.native,self.folder,self.ledger);wrapper.verify_sources()
            before=self.ledger['saved_delivery']['factory_files'];now=source_files()
            if not {n for n in set(before)|set(now) if before.get(n)!=now.get(n)}<={'product.py','history.py','quality.py'}:
                raise FactoryError('超出修复后材料准备的局部代码范围')
            c=stage_controller(self.controller_factory(self.folder,self.native,True))
            project,control,work,state=c.locate(self.ledger['project_id'])
            with locked(control):
                gate=QualityGate(c,project,control,work,state);gate.guard()
                q=gate.q;snap=candidate(work)
                if (q['status']!='质量门槛失败' or not (q.get('error') or '').startswith('历史资料缺失/哈希不匹配/依赖未验证')
                    or not q['repairs'] or not q['repairs'][-1]['valid_repair'] or q['repairs'][-1]['after']!=snap
                    or any(r['candidate_fingerprint']==snap['fingerprint'] for r in q['calls'])):
                    raise FactoryError('不是尚未派发新候选的材料准备失败')
                plan=gate.history_plan()
                if not plan['ready']:raise FactoryError('修复后材料仍不完整；模型调用为0')
                archive=control/'quality/preparation-recovery';archive.mkdir(exist_ok=False)
                originals=[(gate.path,'quality-state.json'),(control/'state.json','controller-state.json'),(self.folder/'run.json','run.json')]
                for path,name in originals:(archive/name).write_bytes(path.read_bytes())
                row=gate.make_round();gate.verify_context(row)
                q['error']=None;state['error']=None;gate.status('基础验证中','修复后材料已验证；尚未调用Tester/Reviewer，不代表批准')
                files=[archive/name for _,name in originals]+[relative_file(call['result'],self.folder) for call in self.ledger['calls']]
                files.append(relative_file(self.ledger['saved_delivery']['record'],self.folder))
                record=self.folder/'quality-preparation.json'
                save(record,{'kind':'post-repair evidence preparation; no new grant, model call or approval',
                    'calls':copy.deepcopy(self.ledger['calls']),'deadline':self.ledger['deadline'],
                    'factory_files':now,'candidate':snap,'packet_fingerprint':digest(gate.packet),
                    'files':{p.relative_to(self.folder).as_posix():file_hash(p) for p in files},'dependencies':plan})
                self.ledger['quality_preparation']={'record':record.name,'sha256':file_hash(record),'factory_files':now}
                save(self.folder/'run.json',self.ledger);wrapper.verify()
                return {'ready':True,'round':row['number'],'candidate':snap,'packet_fingerprint':digest(gate.packet),'new_model_calls':0}

    def accept_saved_delivery(self):
        """Same grant, remaining time and calls; only hand off verified artifacts."""
        from .sequence import stage_controller
        with locked(self.folder):
            prior_ledger=(self.folder/'run.json').read_bytes()
            self.ledger=load(self.folder/'run.json');limits_for(self.ledger)
            if (not self.ledger.get('approved_goal0_continuation') or self.ledger['status']!='stopped'
                or self.ledger.get('saved_delivery') or len(self.ledger['calls'])!=1):
                raise FactoryError('仅处理本次单次Goal 1超时产物，不追加调用')
            call=self.ledger['calls'][0];path=relative_file(call['result'],self.folder)
            if call['role']!='Coder' or call['status']!='finished' or file_hash(path)!=call['sha256']:
                raise FactoryError('原调用来源无效')
            now=source_files();delta={n for n in set(now)|set(self.ledger['factory_files']) if now.get(n)!=self.ledger['factory_files'].get(n)}
            if not delta or not delta<={'controller.py','product.py','sequence.py'}:
                raise FactoryError('超出局部保存产物接续修复范围')
            RunExecutor(self.native,self.folder,self.ledger).remaining()
            RunExecutor(self.native,self.folder,self.ledger).verify_sources()
            # Original snapshots, source grant and execution stay intact. New live
            # code has an explicit separate checkpoint, never edited old hashes.
            c=self.controller_factory(self.folder,self.native,True);stage=stage_controller(c)
            proof=stage.accept_saved_delivery(self.ledger['project_id'],load(path),load(self.folder/'product-plan.json')['release']['source_files'])
            control=Path(proof['path']).parents[1]
            prior=self.folder/'saved-delivery-prior-run.json';prior.write_bytes(prior_ledger)
            pins=[path,Path(proof['path']),Path(proof['path']).parent/'failed-state.json',prior]
            record=self.folder/'saved-delivery.json'
            save(record,{'kind':'saved delivery handoff, no budget renewal or successful Coder turn',
                'original_factory_files':self.ledger['factory_files'],'factory_files':now,
                'calls':self.ledger['calls'],'deadline':self.ledger['deadline'],
                'files':{p.relative_to(self.folder).as_posix():file_hash(p) for p in pins}})
            self.ledger.update(status='prepared',error=None,saved_delivery={'record':record.name,'sha256':file_hash(record),'factory_files':now})
            save(self.folder/'run.json',self.ledger)
            return proof

    @classmethod
    def continue_goal1(cls, source_output, output, *, authorization_id, executor, full_access=False, timeout=600):
        """New explicit grant after an actual Goal 0 approval; old ledgers stay immutable."""
        import re
        from .contracts import validate_packet, validate_plan
        from .quality import candidate
        from .revalidation import original_files
        from .sequence import adopt_completed_goal0, prepare_stage
        if not full_access:raise FactoryError('Goal 1接续需本次显式Full Access')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',authorization_id):raise FactoryError('接续授权标识无效')
        old=Path(source_output).resolve();output=Path(output).absolute();source=old/'.apf'
        if output.is_relative_to(old) or old.is_relative_to(output):raise FactoryError('新旧接续目录不可覆盖或嵌套')
        with locked(source):
            ledger=load(source/'run.json')
            if ledger['status']!='stopped' or ledger['output']!=str(old):raise FactoryError('原运行不是合法停止状态')
            claim=old.parent/('.continuation-'+digest({'source':str(source),'authorization':authorization_id})+'.json')
            if claim.exists():raise FactoryError('接续授权已使用；只能恢复既有运行')
            oldc=Controller(source);project,control,workspace,state=oldc.locate(ledger['project_id'])
            with locked(control):
                packet=load(control/'task-packet.json');validate_packet(packet,source,state)
                cursor=load(control/'sequence/state.json')
                if set(cursor['completed'])!={'Goal 0'}:raise FactoryError('只能接续已批准Goal 0、未批准Goal 1')
                receipt=check_receipt(project,cursor['completed']['Goal 0'],'Goal 0')
                if candidate(workspace)!=receipt['candidate']:raise FactoryError('原已批准候选变化')
                # Validate the existing quality result, not a workspace self-report.
                from .git_agent import GitAgent
                if not getattr(executor,'label',None):GitAgent(oldc,project.name)._validate_quality(receipt)
                oldstage=control/'goals/goal-1'
                if oldstage.exists():
                    priorstate=load(oldstage/'state.json')
                    validate_packet(load(oldstage/'task-packet.json'),source,priorstate)
                    if priorstate['status']!='已失败' or load(oldstage/'increment-before.json')!=receipt['candidate']:
                        raise FactoryError('前次Goal 1不是源码未变的失败尝试')
                full=load(source/'product-plan.json')
                if file_hash(source/'product-plan.json')!=ledger['plan_sha256'] or full['plan']!=load(control/'planner-result.json'):
                    raise FactoryError('原规划来源不匹配')
                if oldstage.exists() and load(oldstage/'goal-spec.json')!=full['goal1_spec']:
                    raise FactoryError('前次Goal 1任务与原完整规划不符')
                for call in ledger['calls']:
                    if call['status']!='finished' or file_hash(relative_file(call['result'],source))!=call['sha256']:
                        raise FactoryError('原模型执行未完成或结果SHA变化')
                for name,h in ledger['resources'].items():
                    if file_hash(relative_file(name,source))!=h:raise FactoryError('原工厂/Skill快照变化')
                pins={('projects/'+project.name+'/'+n):h for n,h in original_files(project).items()}
                for n in ('run.json','product-plan.json',*[x['result'] for x in ledger['calls']],*ledger['resources']):
                    pins[n]=file_hash(relative_file(n,source))
                skills={n:source/'skills'/n for n in ('requirement-planner','goal0-scaffolder','goal-prompt-writer')}
                run=cls(output,request=ledger['request'],full_access=True,executor=executor,skills=skills,timeout=timeout)
                dest=run.folder/'projects'/project.name;dest.mkdir(parents=True)
                target=dest/'workspace';shutil.copytree(workspace,target,ignore=shutil.ignore_patterns('.factory-tmp','__pycache__','node_modules'))
                newcontrol=dest/'control';newcontrol.mkdir()
                def rebind(v):
                    if isinstance(v,str):return v.replace(str(source),str(run.folder))
                    if isinstance(v,list):return [rebind(x) for x in v]
                    if isinstance(v,dict):return {k:rebind(x) for k,x in v.items()}
                    return v
                derived=rebind(full)
                for n in packet['artifacts']:
                    if n.endswith('.json'):save(newcontrol/n,rebind(load(control/n)))
                    else:(newcontrol/n).write_text(rebind((control/n).read_text(encoding='utf8')),encoding='utf8')
                newpacket=rebind(packet);newpacket['artifacts']={n:file_hash(newcontrol/n) for n in packet['artifacts']}
                copied=copy.deepcopy(state);copied.update(status='任务包已验证',packet_fingerprint=digest(newpacket),error=None,calls=[])
                for n in ('quality','quality_gate_enabled','active_quality_deadline','quality_bootstrap_failure'):copied.pop(n,None)
                save(newcontrol/'state.json',copied);save(newcontrol/'task-packet.json',newpacket)
                validate_packet(newpacket,run.folder,copied);validate_plan(derived['plan'],target)
                validate_spec(derived['goal1_spec'],derived['plan'],target)
                validate_release_plan(derived['plan'],derived['goal1_spec'],derived['release'])
                save(newcontrol/'packet-validation.json',{'passed':True,'packet_fingerprint':digest(newpacket),'relocated_from':digest(packet)})
                save(run.folder/'product-plan.json',derived)
                c=Controller(run.folder,executor,True)
                c.prepare_goal_sequence(project.name,derived['goal1_spec'],run.ledger['run_id'],allow_repair=True)
                adopted=adopt_completed_goal0(c,project.name,project,cursor['completed']['Goal 0'])
                stage=prepare_stage(c,dest,newcontrol,target,copied,derived['goal1_spec'],adopted['completed']['Goal 0'])
                stage_control=dest/'control/goals/goal-1';finalpacket=load(stage_control/'task-packet.json')
                # Assemble and verify the EXACT final input before any new model call.
                stage._check_coder_permission(load(stage_control/'state.json'),'Auto')
                proof=executor.preflight(finalpacket,target,stage_control)
                context=__import__('factory.sequence',fromlist=['predecessor_context']).predecessor_context(stage_control,finalpacket)
                if not context['approved_at'] or context['candidate_fingerprint']!=receipt['candidate']['fingerprint']:
                    raise FactoryError('前序批准时间或候选身份缺失')
                prompt=stage.coder_input(finalpacket,load(stage_control/'state.json'),target,stage_control,preflight_result=proof)
                (stage_control/'coder-input-preflight.md').write_text(prompt,encoding='utf8')
                save(stage_control/'coder-input-preflight.json',{'passed':True,'packet_fingerprint':digest(finalpacket),
                    'input_sha256':digest(prompt.encode()),'approval':context,'preflight':proof})
                if candidate(target)!=receipt['candidate']:raise FactoryError('零模型预检改变已批准源码')
                record=run.folder/'handoff.json'
                save(record,{'kind':'authorized Goal 1 continuation of actual approved Goal 0',
                    'authorization_id':authorization_id,'source_runtime':str(source),'source_run_id':ledger['run_id'],
                    'source_files':pins,'source_deadline_unchanged':ledger['deadline'],
                    'source_candidate':receipt['candidate'],'source_packet_fingerprint':receipt['packet_fingerprint'],
                    'source_receipt':cursor['completed']['Goal 0'],'derived_packet_fingerprint':digest(finalpacket),
                    'prepared_input_files':{p.relative_to(run.folder).as_posix():file_hash(p)
                        for p in (stage_control/'coder-input-preflight.json',stage_control/'coder-input-preflight.md')},
                    'limits':STAGE_CONTINUATION_LIMITS})
                with claim.open('x',encoding='utf8') as f:
                    json.dump({'authorization_id':authorization_id,'run_id':run.ledger['run_id'],'output':str(output)},f)
                binding=load(record);binding['claim']={'path':str(claim),'sha256':file_hash(claim)};save(record,binding)
                run.ledger.update(project_id=project.name,limits=dict(STAGE_CONTINUATION_LIMITS),
                    approved_goal0_continuation=True,plan_sha256=file_hash(run.folder/'product-plan.json'),
                    continuation={'record':record.name,'sha256':file_hash(record)})
                save(run.folder/'run.json',run.ledger)
                return run

    @classmethod
    def handoff(cls, source_output, output, *, authorization_id, executor,
                full_access=False, amendments=None, normalize_runtime=False, runtime_data=None, timeout=600):
        """Explicit new budget for a completed Coder, never an old approval.

        The immutable source is checked at preparation AND every later dispatch.
        Caller-authorized local amendments create a new candidate. Fresh basic
        checks below do not stand in for real Tester/Reviewer approval.
        """
        import re
        from .contracts import validate_packet, validate_plan
        from .controller import manifest
        from .quality import candidate, GENERATED_ROOTS
        from .revalidation import original_files
        if not full_access:raise FactoryError('接续仍需本次显式Full Access选择')
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,80}',authorization_id):raise FactoryError('缺少明确接续授权标识')
        source_output=Path(source_output).resolve();output=Path(output).absolute()
        if output.is_relative_to(source_output) or source_output.is_relative_to(output):raise FactoryError('接续目录不能覆盖或嵌套原运行')
        source=source_output/'.apf'
        with locked(source):
            claim=source_output.parent/('.continuation-'+digest({'source':str(source),'authorization':authorization_id})+'.json')
            if claim.exists():raise FactoryError('该接续授权已绑定运行；只允许恢复原接续，不新开额度')
            ledger=load(source/'run.json')
            if ledger.get('continuation'):raise FactoryError('不链式续期接续预算')
            if ledger['output']!=str(source_output) or ledger['status']!='stopped':raise FactoryError('原运行身份或停止状态无效')
            oldc=Controller(source);project,control,workspace,state=oldc.locate(ledger['project_id'])
            with locked(control):
                packet=load(control/'task-packet.json');validate_packet(packet,source,state)
                completion=load(control/'completion.json');coder=load(control/'coder-result.json')
                if (not completion['passed'] or not completion['runtime']['passed']
                    or completion['workspace_manifest']!=manifest(workspace)
                    or completion['packet_fingerprint']!=digest(packet) or coder['status']!='completed'):
                    raise FactoryError('原始Coder完成记录或候选变化')
                if ([x['role'] for x in ledger['calls']]!=['Planner','Coder']
                    or any(x['status']!='finished' or x['exit_code'] for x in ledger['calls'])):
                    raise FactoryError('只接续已完成一次真实Planner/Goal0 Coder、未派发质量Agent的运行')
                for call in ledger['calls']:
                    if file_hash(relative_file(call['result'],source))!=call['sha256']:raise FactoryError('原真实执行记录SHA变化')
                for name,h in ledger['resources'].items():
                    if file_hash(relative_file(name,source))!=h:raise FactoryError('原Skill/工厂快照变化')
                if ledger.get('preparation_fix'):
                    pin=ledger['preparation_fix']
                    if file_hash(relative_file(pin['record'],source))!=pin['sha256']:raise FactoryError('原准备修复检查点变化')
                for q in control.glob('quality*/state.json'):
                    if load(q).get('calls'):raise FactoryError('已有质量模型调用不能借接续刷新额度')
                full=load(source/'product-plan.json')
                if file_hash(source/'product-plan.json')!=ledger['plan_sha256'] or full['plan']!=load(control/'planner-result.json'):
                    raise FactoryError('原完整规划身份变化')
                pins=original_files(project)
                pins={str(Path('projects')/project.name/n).replace('\\','/'):h for n,h in pins.items()}
                for name in ('run.json','product-plan.json',*[x['result'] for x in ledger['calls']],*ledger['resources']):
                    pins[name]=file_hash(relative_file(name,source))
                if ledger.get('preparation_fix'):
                    name=ledger['preparation_fix']['record'];pins[name]=file_hash(relative_file(name,source))
                skills={name:source/'skills'/name for name in ('requirement-planner','goal0-scaffolder','goal-prompt-writer')}
                run=cls(output,request=ledger['request'],full_access=True,executor=executor,skills=skills,timeout=timeout)
                dest=run.folder/'projects'/project.name;dest.mkdir(parents=True)
                target=dest/'workspace';shutil.copytree(workspace,target,ignore=shutil.ignore_patterns('.factory-tmp','__pycache__','node_modules'))
                newcontrol=dest/'control';newcontrol.mkdir()
                # Preserve the entire original evidence namespace and source
                # bytes together, so its indexed hashes retain their meaning.
                archive='validation/history-'+run.ledger['run_id']
                archived=target/archive;archived.mkdir(parents=True)
                for name,h in completion['workspace_manifest'].items():
                    p=relative_file(name,workspace);d=relative_file(name,archived)
                    d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d)
                    if file_hash(d)!=h:raise FactoryError('历史副本SHA错误')
                # Keep original relative evidence paths readable for the real
                # Coder result. Its immutable archive binds the old source SHA;
                # only the new current acceptance page is replaced below.
                for name in ('dist','build'):
                    p=target/name
                    if p.exists():
                        shutil.rmtree(safe_path(p,target))
                if runtime_data:
                    if runtime_data not in ('data','var'):raise FactoryError('仅允许明确的项目数据目录迁移')
                    p=relative_file(runtime_data,target)
                    if p.exists():
                        legacy=newcontrol/'source-data';shutil.move(str(p),legacy)
                        (target/'var').mkdir(exist_ok=True)
                        for f in legacy.iterdir():
                            if f.name not in ('store.lock','store.guard.sqlite') and f.is_file():shutil.copy2(f,target/'var'/f.name)
                repairs={}
                for name,data in (amendments or {}).items():
                    p=relative_file(name,target)
                    if (name=='AGENTS.md' or Path(name).parts[0] in GENERATED_ROOTS or not p.is_file() or not isinstance(data,bytes)):
                        raise FactoryError('接续修复必须是现有业务源文件，禁止修改授权或历史')
                    oldhash=file_hash(p);p.write_bytes(data);repairs[name]={'before':oldhash,'after':file_hash(p)}
                derived=copy.deepcopy(full)
                for item in (derived['plan'],derived['goal1_spec']):
                    item['prompt_md']=item['prompt_md'].replace(str(workspace),str(target))
                    if normalize_runtime:
                        argv=item['runtime']['argv'];item['runtime']['argv']=[*argv[:2],'--host','127.0.0.1','--port','{port}','--data-dir','var']
                if normalize_runtime:
                    derived['release']['package_files']=[n.removeprefix('dist/') for n in derived['release']['package_files']]
                    derived['goal1_spec']['prompt_md']+='\n当前接续的正式运行契约：'+str(derived['goal1_spec']['runtime'])+'\n最终ZIP根清单：'+str(derived['release']['package_files'])+'\n此前dist构建布局保留，发行选择上述原相对路径。数据仅放var，不覆盖前序历史。保留已验证的OS互斥修复。\n'
                if derived['plan']['acceptance']!=full['plan']['acceptance'] or derived['plan']['tasks']!=full['plan']['tasks']:
                    raise FactoryError('禁止改变原AC或任务范围')
                validate_plan(derived['plan'],target);validate_spec(derived['goal1_spec'],derived['plan'],target)
                validate_release_plan(derived['plan'],derived['goal1_spec'],derived['release'])
                for name in packet['artifacts']:
                    shutil.copy2(control/name,newcontrol/name)
                save(newcontrol/'planner-result.json',derived['plan'])
                (newcontrol/'goal0-prompt.md').write_text(derived['plan']['prompt_md']+'\n',encoding='utf8')
                save(newcontrol/'coder-result.json',coder)
                copied=copy.deepcopy(state);copied.update(status='基础验证中',error=None)
                for name in ('quality','quality_gate_enabled','quality_bootstrap_failure','active_quality_deadline'):
                    copied.pop(name,None)
                # Original calls remain historical facts, not new paid calls.
                copied['continuation_source']=str(control)
                newpacket=copy.deepcopy(packet);newpacket.update(workspace=str(target),allow_write=[str(target)],
                    deny_write=[str(run.folder/'skills'),str(run.folder/'validation'),str(run.folder/'.git'),packet['deny_write'][3],str(newcontrol)],
                    prompt_path=str(newcontrol/'goal0-prompt.md'),runtime=derived['plan']['runtime'],
                    artifacts={n:file_hash(newcontrol/n) for n in packet['artifacts']})
                copied['packet_fingerprint']=digest(newpacket)
                save(newcontrol/'state.json',copied);save(newcontrol/'task-packet.json',newpacket)
                validate_packet(newpacket,run.folder,copied)
                save(newcontrol/'packet-validation.json',{'passed':True,'packet_fingerprint':digest(newpacket),'source_packet_fingerprint':digest(packet)})
                # Current delivery explicitly reports basic checks, not AC pass.
                acceptances=[n for n in ('validation/acceptance.md','validation/goal0/acceptance.md') if n in completion['workspace_manifest']]
                if len(acceptances)!=1:raise FactoryError('原完成记录的验收文档缺失或冲突')
                (target/'validation/acceptance.md').write_text('# 当前Goal 0接续交付\n\n原AC定义未改变，独立Tester和Reviewer尚未执行。\n\n原始开发与失败资料：[原验收文档]('+archive.removeprefix('validation/')+'/'+acceptances[0]+')\n\n'
                    +'\n'.join(json.dumps(a,ensure_ascii=False) for a in newpacket['acceptance'])+'\n',encoding='utf8')
                (target/'PROJECT_STATUS.md').write_text('软件Goal 0：原真实Coder成果经授权定点修锁，等待真实独立质量验收；Goal 1未执行。\n',encoding='utf8')
                run.ledger.update(project_id=project.name,limits=dict(CONTINUATION_LIMITS),plan_sha256=None)
                save(run.folder/'product-plan.json',derived);run.ledger['plan_sha256']=file_hash(run.folder/'product-plan.json')
                record=run.folder/'handoff.json'
                save(record,{'kind':'explicit authorized continuation; no inherited quality approval',
                    'authorization_id':authorization_id,'source_runtime':str(source),'source_run_id':ledger['run_id'],
                    'source_files':pins,'source_candidate':candidate(workspace),'source_packet_fingerprint':digest(packet),
                    'source_deadline_unchanged':ledger['deadline'],'amendments':repairs,'normalization':normalize_runtime,
                    'original_plan_fingerprint':digest(full),'derived_plan_fingerprint':digest(derived),
                    'candidate':candidate(target),'limits':CONTINUATION_LIMITS,'archive':archive})
                run.ledger['continuation']={'record':record.name,'sha256':file_hash(record)}
                save(run.folder/'run.json',run.ledger)
                # These are real, model-free engineering checks on new bytes.
                c=Controller(run.folder,executor,True)
                provenance=load(control/'coder-file-provenance.json')
                c.verify(newpacket,coder,target,newcontrol,provenance['before'])
                evidence=target/'validation/continuation-checks';evidence.mkdir()
                for p in newcontrol.iterdir():
                    if p.is_file() and (p.name.startswith('check-') or p.name in ('basic-checks.json','runtime-check.json','runtime-log.json')):
                        shutil.copy2(p,evidence/p.name)
                report=target/'validation/acceptance.md'
                with report.open('a',encoding='utf8') as stream:
                    stream.write('\n本轮零模型基础检查（不是独立Tester批准）：\n'+
                        '\n'.join('['+p.name+'](continuation-checks/'+p.name+')' for p in evidence.iterdir())+'\n')
                completed=load(newcontrol/'completion.json');completed['workspace_manifest']=manifest(target)
                completed['continuation']={'source_completion_sha256':file_hash(control/'completion.json'),'handoff':record.name,
                    'scope':'new deterministic basic checks; real Tester/Reviewer approval still required'}
                save(newcontrol/'completion.json',completed)
                c.transition(copied,newcontrol,'已完成','原Coder来源已验证；新候选实际基础检查通过，质量未批准')
                with claim.open('x',encoding='utf8') as stream:
                    json.dump({'authorization_id':authorization_id,'run_id':run.ledger['run_id'],'output':str(output)},stream)
                binding=load(record);binding['claim']={'path':str(claim),'sha256':file_hash(claim)};save(record,binding)
                run.ledger['continuation']['sha256']=file_hash(record);save(run.folder/'run.json',run.ledger)
                return run

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
            limits_for(self.ledger)
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

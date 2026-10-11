"""Explicit project policy + immutable Sequence receipt -> local Git version.

No models, tags, remotes, resets or cleanup. The original project lock is used.
Working directories and file checks are application boundaries, not OS isolation.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from .controller import Controller, ROOT, load, save, locked
from .contracts import FactoryError, digest, file_hash, relative_file, safe_path
from .executor import redact
from .quality import QualityGate, candidate, GENERATED_ROOTS, GENERATED_ANY
from .sequence import check_receipt

POLICY_FIELDS = {'version','project_id','authorization_id','allow_init','allow_local_commit','branch'}
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_TOTAL_BYTES = 50 * 1024 * 1024


def validate_policy(policy, project_id):
    if (not isinstance(policy,dict) or set(policy)!=POLICY_FIELDS or policy['version']!=1
        or policy['project_id']!=project_id or type(policy['allow_init']) is not bool
        or type(policy['allow_local_commit']) is not bool
        or not isinstance(policy['authorization_id'],str)
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,79}',policy['authorization_id'])
        or not isinstance(policy['branch'],str)
        or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9/_-]{0,79}',policy['branch'])
        or policy['branch'].endswith('/') or '//' in policy['branch']):
        raise FactoryError('项目Git策略无效；需明确授权ID、初始化/本地提交开关和目标分支')
    return policy


def sensitive(name, data):
    """Fail closed for credentials/private configuration; never prints contents."""
    parts=Path(name).parts; lower=name.lower(); base=Path(name).name.lower()
    if (base=='.env' or base.startswith('.env.') or Path(name).suffix.lower() in
        {'.pem','.key','.pfx','.p12','.keystore'} or
        any(x.lower() in {'.ssh','.aws','.azure','.codex','.config','control','quality','node_modules'} for x in parts)
        or base in {'credentials','credentials.json','auth.json','.npmrc','.pypirc','.netrc'}
        or re.search(r'(?:^|[/.])(?:secrets?|tokens?|passwords?)(?:[/.]|$)',lower)):
        raise FactoryError('敏感/私有文件禁止提交：'+name)
    text=data.decode('utf-8',errors='replace')
    if (redact(text)!=text or re.search(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b',text)
        or re.search(r'(?i)[A-Z]:[\\/](?:Users|Documents and Settings)[\\/]|/home/[^/\s]+/|/mnt/data/|sandbox:/',text)):
        raise FactoryError('文件疑似含凭据或个人环境信息，需人工检查：'+name)
    # Arbitrary configured filters could execute code or transform approved bytes.
    if base=='.gitattributes' and re.search(r'(?i)\bfilter\s*=|\bworking-tree-encoding\s*=',text):
        raise FactoryError('交付属性含外部filter/编码变换；本增量不自动执行：'+name)


class GitAgent:
    def __init__(self, controller, project_id):
        self.c=controller; self.project_id=project_id
        self.project,self.control,self.workspace,_=controller.locate(project_id)
        self.folder=safe_path(self.control/'git',self.control)
        self.git=shutil.which('git')
        if not self.git:raise FactoryError('git.exe不可用；请配置本机Git后再执行')

    def _git(self, *args, input=None, allowed=(0,)):
        # Ignore inherited redirection to another repository/index or config.
        env={k:v for k,v in os.environ.items() if not k.upper().startswith('GIT_')}
        # System-installed LFS filters are irrelevant to these byte-preserving
        # commits. Leave user/local identity available; do not edit any config.
        env.update(GIT_OPTIONAL_LOCKS='0',GIT_TERMINAL_PROMPT='0',GIT_LITERAL_PATHSPECS='1',GIT_CONFIG_NOSYSTEM='1')
        argv=[self.git,'--no-optional-locks','-c','core.autocrlf=false',
              '-c','core.hooksPath='+str(self.folder/'empty-hooks'),'-c','commit.gpgSign=false',
              '-c','core.fsmonitor=false','-c','core.untrackedCache=false','-c','core.pager=cat',*args]
        try:
            result=subprocess.run(argv,cwd=self.workspace,env=env,input=input,
                                  capture_output=True,timeout=30)
        except (OSError,subprocess.TimeoutExpired) as e:
            raise FactoryError('Git命令未完成：'+args[0]+'；保留工作区，不自动重试') from e
        if result.returncode not in allowed:
            # Do not echo author identity, paths or credential-bearing Git output.
            raise FactoryError(f'Git {args[0]}退出{result.returncode}；保留工作区/暂存区，未自动回滚')
        return result

    def _text(self,*args,**kw):
        return self._git(*args,**kw).stdout.decode('utf-8').strip()

    def _repository(self):
        marker=self.workspace/'.git'
        if not marker.exists():return False  # Never discover the APF parent repo.
        safe_path(marker,self.workspace)
        if not marker.is_dir():raise FactoryError('拒绝外部worktree/submodule的.git文件')
        # Check metadata links before even rev-parse reads repository config.
        for p in marker.rglob('*'):safe_path(p,self.workspace)
        if (marker/'objects/info/alternates').exists():raise FactoryError('拒绝外部Git对象库')
        top=Path(self._text('rev-parse','--show-toplevel')).resolve()
        common=Path(self._text('rev-parse','--path-format=absolute','--git-common-dir')).resolve()
        actual=Path(self._text('rev-parse','--absolute-git-dir')).resolve()
        if top!=self.workspace.resolve() or common!=marker.resolve() or actual!=common:
            raise FactoryError('仓库边界不符；禁止操作父仓库或共享Git目录')
        if self._text('rev-parse','--is-bare-repository')!='false':raise FactoryError('拒绝裸仓库')
        # Git object/reference redirection is not a software-local repository.
        if self._git('config','--get-regexp',r'^filter\.',allowed=(0,1)).returncode==0:
            raise FactoryError('仓库/用户配置存在自定义filter；本增量不执行外部过滤器')
        return True

    def _snapshot(self):
        if not self._repository():return {'repository':False,'branch':None,'head':None,'changes':[],'staged':[]}
        branch=self._text('symbolic-ref','--quiet','--short','HEAD',allowed=(0,1))
        head=self._text('rev-parse','--verify','HEAD',allowed=(0,128)) or None
        changes=[]
        # Disable renames for unambiguous literal paths; include ignored files in
        # the candidate check independently, so ignores cannot hide source.
        raw=self._git('status','--porcelain=v1','-z','--untracked-files=all','--no-renames').stdout
        for item in raw.split(b'\0'):
            if item:
                code=item[:2].decode('ascii');name=item[3:].decode('utf-8')
                relative_file(name,self.workspace)
                changes.append({'status':code,'path':name})
        staged=self._git('diff','--cached','--name-only','-z','--no-renames','--no-ext-diff').stdout.decode('utf-8').split('\0')
        return {'repository':True,'branch':branch or None,'head':head,'changes':changes,'staged':[p for p in staged if p]}

    def inspect(self):
        with locked(self.control):
            self._control_paths()
            value=self._snapshot();value.update(project_id=self.project_id,policy='read-only' if not (self.folder/'policy.json').exists() else load(self.folder/'policy.json'))
            return value

    def configure(self, policy):
        validate_policy(policy,self.project_id)
        with locked(self.control):
            self._control_paths()
            self.folder.mkdir(exist_ok=True)
            save(self.folder/'policy.json',policy)
        return policy

    def _control_paths(self):
        safe_path(self.folder,self.control)
        if self.folder.exists():
            for p in self.folder.rglob('*'):safe_path(p,self.control)

    def _validate_quality(self, receipt):
        """Recheck pinned QualityGate results, not current factory execution hashes.

        No guard/checkpoint/call is invoked: this reads already approved evidence
        and does not reopen old quality ledgers or dispatch any model.
        """
        options=[]
        for name in receipt['files']:
            if name.endswith('/state.json'):
                path=relative_file(name,self.project);value=load(path)
                if value.get('version')=='2.0' and value.get('status')=='质量门槛通过' and value.get('rounds'):
                    options.append((path,value))
        if len(options)!=1:raise FactoryError('正式阶段缺少唯一的已批准QualityGate来源')
        path,q=options[0];folder=path.parent;control=folder.parent
        for name in ('task-packet.json','state.json'):
            if (control/name).relative_to(self.project).as_posix() not in receipt['files']:
                raise FactoryError('质量批准未绑定任务包与阶段状态')
        packet=load(control/'task-packet.json');row=q['rounds'][-1]
        if (digest(packet)!=receipt['packet_fingerprint'] or packet['goal']!=receipt['goal']
            or packet['project_id']!=self.project_id or packet['workspace']!=str(self.workspace)
            or packet['allow_write']!=[str(self.workspace)] or row['candidate']!=receipt['candidate']
            or row.get('tester',{}).get('status')!='passed' or row.get('reviewer',{}).get('decision')!='approved'):
            raise FactoryError('TaskPacket/Tester/Reviewer批准身份不匹配')
        threads=[]
        for role in ('tester','reviewer'):
            entry=row.get(role+'_execution')
            if not entry:raise FactoryError('缺少真实独立CLI执行来源')
            p=relative_file(entry['path'],folder)
            if p.relative_to(self.project).as_posix() not in receipt['files'] or file_hash(p)!=entry['sha256']:
                raise FactoryError('CLI执行来源未被正式回执绑定')
            execution=load(p)
            if (execution.get('role')!=role.capitalize() or not execution.get('version')
                or execution.get('exit_code')!=0 or execution.get('timed_out') or not execution.get('turn_completed')
                or not execution.get('thread_ids')
                or any(not re.fullmatch(r'[0-9a-fA-F-]{36}',t) for t in execution['thread_ids'])
                or execution.get('execution_mode') not in (('read-only',) if role=='reviewer' else ('danger-full-access','workspace-write'))):
                raise FactoryError('质量来源不是成功的独立真实CLI执行；不能以AgentDouble批准业务版本')
            threads.append(set(execution['thread_ids']))
        if threads[0]&threads[1]:raise FactoryError('Tester/Reviewer不是独立线程')
        gate=QualityGate.__new__(QualityGate)
        gate.c=self.c;gate.control=control;gate.folder=folder;gate.workspace=self.workspace
        gate.state=load(control/'state.json');gate.q=q;gate.packet=packet;gate.load=load
        gate.result(row['tester'],'Tester',row);gate.result(row['reviewer'],'Reviewer',row)

    def _approval(self,goal):
        if goal not in ('Goal 0','Goal 1'):raise FactoryError('本增量只支持现有Sequence的Goal 0/Goal 1')
        cursor=load(self.control/'sequence/state.json')
        if cursor['project_id']!=self.project_id or goal not in cursor['completed']:
            raise FactoryError('软件阶段尚无正式质量批准，不得提交')
        entry=cursor['completed'][goal];receipt=check_receipt(self.project,entry,goal)
        if candidate(self.workspace)!=receipt['candidate']:raise FactoryError('当前源码与正式批准候选不一致')
        if receipt['candidate']['fingerprint']!=digest(receipt['candidate']['files']):raise FactoryError('候选清单指纹无效')
        self._validate_quality(receipt)
        return receipt,{'path':'control/sequence/'+entry['path'],'sha256':entry['sha256']}

    def _tree(self,rev):
        files={};total=0
        for item in self._git('ls-tree','-r','-z',rev).stdout.split(b'\0'):
            if not item:continue
            meta,name=item.split(b'\t',1);mode,kind,oid=meta.split();name=name.decode('utf-8')
            relative_file(name,self.workspace)
            if kind!=b'blob' or mode not in (b'100644',b'100755'):raise FactoryError('Git树包含链接/submodule，禁止版本化')
            size=int(self._text('cat-file','-s',oid.decode()));total+=size
            if size>MAX_FILE_BYTES or total>MAX_TOTAL_BYTES:raise FactoryError('Git树超过受控源码体积限制')
            data=self._git('cat-file','blob',oid.decode()).stdout
            sensitive(name,data);files[name]=digest(data)
        return files

    def _log(self,status,detail):
        self.folder.mkdir(exist_ok=True)
        with (self.folder/'events.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({'at':time.time(),'status':status,'detail':redact(detail)},ensure_ascii=False)+'\n')

    def commit(self,goal):
        with locked(self.control):
            self._control_paths()
            try:
                result=self._commit(goal);self._log(result['status'],result.get('message',''))
                return result
            except (FactoryError,OSError,ValueError,KeyError) as e:
                # Approval and quality states remain untouched even on Git error.
                self._log('blocked',str(e))
                return {'status':'blocked','message':redact(str(e)),'project_id':self.project_id,'goal':goal}

    def _commit(self,goal):
        policy_path=self.folder/'policy.json'
        if not policy_path.exists():return {'status':'authorization_required','message':'默认只读；请明确项目级allow_local_commit/allow_init及目标分支授权。'}
        policy=validate_policy(load(policy_path),self.project_id)
        if not policy['allow_local_commit']:return {'status':'authorization_required','message':'项目策略尚未授权本地提交；没有Git写入。'}
        receipt,approval=self._approval(goal)
        files=receipt['candidate']['files'];total=0
        for name,h in files.items():
            p=relative_file(name,self.workspace);data=p.read_bytes()
            if digest(data)!=h:raise FactoryError('批准后源码漂移：'+name)
            if len(data)>MAX_FILE_BYTES:raise FactoryError('文件超过20MiB，需人工确定交付范围：'+name)
            total+=len(data);sensitive(name,data)
        if total>MAX_TOTAL_BYTES:raise FactoryError('源码超过50MiB，本增量不自动提交大体量交付')
        self.folder.mkdir(exist_ok=True)
        hooks=self.folder/'empty-hooks';hooks.mkdir(exist_ok=True)
        if any(hooks.iterdir()):raise FactoryError('受控空hooks目录已变化')
        state=self._snapshot()
        if not state['repository']:
            if not policy['allow_init']:return {'status':'authorization_required','message':'软件workspace没有自身仓库；需明确allow_init授权。'}
            self._git('init','--template='+str(hooks),'--initial-branch='+policy['branch'],str(self.workspace))
            state=self._snapshot()
        if state['branch']!=policy['branch']:raise FactoryError('当前分支不符合项目策略；不自动switch/branch')
        record_path=self.folder/('goal0-version.json' if goal=='Goal 0' else 'goal1-version.json')
        key=digest({'project_id':self.project_id,'goal':goal,'approval':approval,'candidate':receipt['candidate']['fingerprint'],
                    'packet':receipt['packet_fingerprint']})
        if record_path.exists():
            record=load(record_path)
            if (record['key']!=key or record['project_id']!=self.project_id or record['goal']!=goal
                or record['approval']!=approval or record['candidate_fingerprint']!=receipt['candidate']['fingerprint']
                or record['packet_fingerprint']!=receipt['packet_fingerprint'] or record['files']!=files
                or record['branch']!=state['branch'] or self._tree(record['commit'])!=files
                or self._git('merge-base','--is-ancestor',record['commit'],'HEAD',allowed=(0,1,128)).returncode!=0):
                raise FactoryError('已有Git版本来源/历史不一致；禁止自动替换')
            return {'status':'already_versioned','commit':record['commit'],'record':str(record_path.relative_to(self.project))}
        intent_path=self.folder/('goal0-intent.json' if goal=='Goal 0' else 'goal1-intent.json')
        message=f'apf: approve {goal}\n\nAPF-Version: {key}\nAPF-Candidate: {receipt["candidate"]["fingerprint"]}\nAPF-Approval: {approval["sha256"]}\n'
        intent=load(intent_path) if intent_path.exists() else None
        if intent:
            if intent['key']!=key or intent['policy_sha256']!=file_hash(policy_path):raise FactoryError('未完成Git请求来源/授权变化，停止人工检查')
            if state['head']!=intent['parent']:
                # Recover only our exact commit, including parent, message and bytes.
                parents=self._text('rev-list','--parents','-n','1','HEAD').split()[1:]
                if (parents!=([intent['parent']] if intent['parent'] else []) or self._text('show','-s','--format=%B','HEAD')!=message.strip()
                    or self._tree('HEAD')!=files or state['staged']):raise FactoryError('中断后HEAD/暂存区不属于本次操作，停止人工检查')
                return self._record(record_path,key,goal,receipt,approval,policy,state['head'],'recovered')
        if state['staged']:raise FactoryError('存在用户或未完成操作的暂存改动；不覆盖/清理，请先人工处理')
        tracked=self._git('ls-files','-z').stdout.decode('utf-8').split('\0');tracked={p for p in tracked if p}
        previous={}
        if goal=='Goal 1' and (self.folder/'goal0-version.json').exists():
            old=load(self.folder/'goal0-version.json')
            if state['head']!=old['commit'] or self._tree(old['commit'])!=old['files']:
                raise FactoryError('前序Git版本与当前HEAD不一致')
            previous=old['files']
        deletions=tracked-set(files)
        if not deletions<=set(previous):raise FactoryError('仓库存在不属于已批准阶段的跟踪文件；不自动删除或纳入')
        warnings=[]
        for change in state['changes']:
            name=change['path'];parts=Path(name).parts
            if name not in files and name not in deletions:
                if parts[0] in GENERATED_ROOTS or any(p in GENERATED_ANY for p in parts):warnings.append(name)
                else:raise FactoryError('存在不属于本阶段的工作区变更：'+name)
        filters=self._git('config','--get-regexp',r'^filter\.',allowed=(0,1))
        if filters.returncode==0:raise FactoryError('仓库/用户配置存在自定义filter；本增量不执行外部过滤器')
        identity=self._git('var','GIT_AUTHOR_IDENT',allowed=(0,128))
        committer=self._git('var','GIT_COMMITTER_IDENT',allowed=(0,128))
        if identity.returncode or committer.returncode:raise FactoryError('Git用户身份未配置；请由用户配置该软件仓库身份，不修改全局配置')
        base=self._tree('HEAD') if state['head'] else {}
        intent={'key':key,'parent':state['head'],'policy_sha256':file_hash(policy_path),'approval':approval,'files':files}
        save(intent_path,intent)
        # Recheck files/approval immediately before mutation, under project lock.
        again,_=self._approval(goal)
        if again!=receipt:raise FactoryError('提交前批准来源变化')
        selected=sorted(set(files)|deletions)
        for offset in range(0,len(selected),40):
            self._git('add','--',*selected[offset:offset+40])
        tree=self._text('write-tree')
        if self._tree(tree)!=files:raise FactoryError('暂存字节不等于批准源码；属性转换/忽略规则或并发变化，停止，不提交')
        if candidate(self.workspace)!=receipt['candidate'] or self._snapshot()['head']!=intent['parent']:
            raise FactoryError('暂存期间源码或HEAD变化；停止，不提交')
        if base==files:
            return self._record(record_path,key,goal,receipt,approval,policy,state['head'],'no_changes',warnings)
        self._git('commit','--no-verify','--no-gpg-sign','-F','-',input=message.encode('utf-8'))
        after=self._snapshot()
        parents=self._text('rev-list','--parents','-n','1','HEAD').split()[1:]
        if (self._tree('HEAD')!=files or after['staged'] or parents!=([intent['parent']] if intent['parent'] else [])
            or self._text('show','-s','--format=%B','HEAD')!=message.strip()
            or candidate(self.workspace)!=receipt['candidate']):
            raise FactoryError('提交后字节/来源/暂存状态不符，保留现场等待人工检查')
        return self._record(record_path,key,goal,receipt,approval,policy,after['head'],'committed',warnings)

    def _record(self,path,key,goal,receipt,approval,policy,sha,status,warnings=()):
        record={'version':1,'project_id':self.project_id,'goal':goal,'key':key,'branch':policy['branch'],
                'commit':sha,'candidate_fingerprint':receipt['candidate']['fingerprint'],
                'packet_fingerprint':receipt['packet_fingerprint'],'approval':approval,'files':receipt['candidate']['files'],
                'authorization_id':policy['authorization_id'],'policy_sha256':file_hash(self.folder/'policy.json'),
                'status':status,'warnings':list(warnings),'at':time.time(),'scope':'local commit only; not external acceptance/tag/push'}
        save(path,record)
        return {'status':status,'commit':sha,'record':path.relative_to(self.project).as_posix(),'warnings':list(warnings)}


def main():
    parser=argparse.ArgumentParser(description='Controlled generated-software local Git; no models or push')
    parser.add_argument('--root',type=Path,default=ROOT)
    parser.add_argument('--project-id',required=True)
    operation=parser.add_mutually_exclusive_group()
    operation.add_argument('--configure',type=Path,help='Explicit project Git policy JSON')
    operation.add_argument('--commit',choices=['Goal 0','Goal 1'])
    args=parser.parse_args()
    try:
        agent=GitAgent(Controller(args.root),args.project_id)
        value=agent.configure(json.loads(args.configure.read_text(encoding='utf-8-sig'))) if args.configure else (agent.commit(args.commit) if args.commit else agent.inspect())
        print(json.dumps(value,ensure_ascii=False,indent=2))
        return 1 if value.get('status') in ('blocked','authorization_required') else 0
    except (FactoryError,OSError,ValueError,KeyError) as e:
        print(json.dumps({'status':'blocked','message':redact(str(e))},ensure_ascii=False));return 1


if __name__=='__main__':raise SystemExit(main())

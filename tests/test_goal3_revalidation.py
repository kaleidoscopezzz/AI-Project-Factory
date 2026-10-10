"""Bounded Goal3 source fixtures; AgentDouble, no real model/business/browser."""
import contextlib
import copy
import io
import unittest
import uuid
import shutil
import json
from pathlib import Path
from unittest.mock import patch
from factory.controller import ROOT,Controller,load,save,manifest
from factory.contracts import FactoryError,file_hash,digest
from factory.quality import candidate,recovered_tester_event,QualityGate
from factory.revalidation import RevalidationRunner,original_files
from tests.test_quality import QualityDouble


class TwelveACDouble(QualityDouble):
    def run(self,role,*args):
        if role=='Tester':self.last_tester_prompt=args[0]
        value=super().run(role,*args)
        if role=='Planner':
            plan=value['output']
            for i in (8,9,11,12):
                ac=copy.deepcopy(plan['acceptance'][0]);ac['id']=f'AC-{i:03}';ac['requirement_id']=f'R-{i:02}'
                plan['acceptance'].insert(-1,ac);plan['tasks'][0]['acceptance_ids'].append(ac['id'])
                plan['prompt_md']+=' '+ac['id']
        return value


class Goal3RevalidationTests(unittest.TestCase):
    def setUp(self):
        self.root=ROOT/'validation/goal3/test-workspaces'/('rv3-'+uuid.uuid4().hex[:10]);self.root.mkdir(parents=True)
        self.runtime=self.root/'validation/goal3/fixture/runtime-root';self.runtime.mkdir(parents=True)
        shutil.copytree(ROOT/'skills',self.runtime/'skills')
        self.agent=TwelveACDouble(full_access=True);self.c=Controller(self.runtime,self.agent,full_access=True)
        self.c.runtime_check=lambda *a:{'passed':True,'test_double':True}
        self.pid=self.c.create('Synthetic twelve AC Goal3 revalidation fixture, not real software',600)
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid)
        self.project,self.control,self.workspace,self.completed=self.c.locate(self.pid)
        fail=self.workspace/'validation/run-2026-10-09T16-07-08.840Z';fail.mkdir(parents=True)
        (fail/'test.log').write_text('Synthetic first failure, preserved bytes',encoding='utf-8')
        save(fail/'results.json',{'status':'failed','label':'AgentDouble historical evidence'})
        (self.workspace/'validation/acceptance.md').write_text('历史：原结果、日志与隔离数据保留在 validation/run-2026-10-09T16-07-08.840Z。',encoding='utf-8')
        completion=load(self.control/'completion.json');completion['workspace_manifest']=manifest(self.workspace);save(self.control/'completion.json',completion)
        before={'project':str(self.project),'runtime_root':str(self.runtime),'state_before':copy.deepcopy(self.completed),
                'candidate':candidate(self.workspace),'packet_fingerprint':self.completed['packet_fingerprint'],
                'project_files':original_files(self.project)}
        self.agent.scenario='missing_output'
        with contextlib.redirect_stdout(io.StringIO()):self.c.run(self.pid,quality_gate=True,no_auto_repair=True)
        self.source=self.root/'validation/goal3/source';self.source.mkdir(parents=True)
        save(self.source/'BEFORE.json',before)
        self.anchor={'files':[{'path':f.relative_to(self.root).as_posix(),'sha256':file_hash(f)} for f in (
            self.source/'BEFORE.json',self.control/'quality/state.json',self.control/'state.json',self.control/'events.jsonl')]}
        save(self.source/'evidence-manifest.json',self.anchor)
        for key,value in [('GOAL3_PROJECT',self.pid),('GOAL3_RUNTIME','validation/goal3/fixture/runtime-root'),
                          ('GOAL3_SOURCE','validation/goal3/source'),('GOAL3_CANDIDATE',before['candidate']['fingerprint'])]:
            pt=patch('factory.revalidation.'+key,value);pt.start();self.addCleanup(pt.stop)
        pt=patch('factory.revalidation.goal3_baseline',return_value={'synthetic':'no Git writes'});pt.start();self.addCleanup(pt.stop)
        self.original=original_files(self.project)
        self.agent.scenario='normal';self.agent.roles=[];self.agent.quality_calls=[]
        self.runner=RevalidationRunner(self.root,self.c,goal3_runtime_root=self.runtime)

    def prepare(self):
        self.prepared=self.runner.prepare(self.pid,self.source);self.run=Path(self.prepared['path'])
        return self.prepared

    def execute(self,**kw):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.runner.execute(self.prepared['run_id'],authorization_id='new-fixture-authorization',full_access=True,**kw)

    def test_independent_pass_receipt_is_origin_bound_and_old_failure_unchanged(self):
        self.prepare();self.assertTrue(self.runner.precheck(self.prepared['run_id'])['ready'])
        self.assertEqual(self.execute()['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles,['Tester','Reviewer']);self.assertEqual(original_files(self.project),self.original)
        approved=load(self.run/'stage-approval.json');self.assertEqual(approved['project_id'],self.pid)
        receipt=load(self.run/'control/sequence/goal0-completion.json')
        self.assertEqual(receipt['project_id'],self.pid);self.assertEqual(receipt['candidate'],candidate(self.workspace))
        self.assertFalse(approved['Goal1_executed']);self.assertEqual(load(self.control/'quality/state.json')['status'],'质量门槛失败')
        q=load(self.run/'control/quality/state.json');history=q['rounds'][0]['context']['history']
        self.assertTrue(any(x['source'].endswith('16-07-08.840Z/test.log') for x in history))
        self.assertTrue(all(file_hash(self.run/'control/quality/rounds/01'/x['path'])==x['sha256'] for x in history))
        self.assertEqual(self.execute()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,['Tester','Reviewer'])

    def test_missing_or_tampered_required_history_rejects_zero_models(self):
        self.prepare();file=self.workspace/'validation/run-2026-10-09T16-07-08.840Z/test.log'
        file.write_text('Tampered first failure',encoding='utf-8')
        with self.assertRaises(FactoryError):self.runner.precheck(self.prepared['run_id'])
        self.assertEqual(self.agent.roles,[])

    def test_old_failed_ledger_tampering_rejects(self):
        self.prepare();old=load(self.control/'quality/state.json');old['status']='质量门槛通过';save(self.control/'quality/state.json',old)
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])

    def test_packet_candidate_permission_and_copy_tampering_reject(self):
        self.prepare();new=load(self.run/'control/state.json');new['coder_execution_intent']='workspace-write';save(self.run/'control/state.json',new)
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])

    def test_preflight_failure_never_dispatches(self):
        self.prepare();self.agent.scenario='preflight';self.assertEqual(self.execute()['status'],'质量门槛失败')
        self.assertEqual(self.agent.roles,[]);self.assertEqual(original_files(self.project),self.original)

    def test_nonzero_positive_check_and_failed_tester_never_start_reviewer(self):
        self.prepare();self.agent.scenario='false_exit';self.assertEqual(self.execute()['status'],'质量门槛失败')
        self.assertEqual(self.agent.roles,['Tester']);self.assertFalse((self.run/'stage-approval.json').exists())
        self.assertIn('非零退出',load(self.run/'RESULTS.json')['error'])

    def test_wrong_runtime_or_untrusted_source_rejected(self):
        with self.assertRaises(FactoryError):RevalidationRunner(self.root,goal3_runtime_root=self.root)
        with self.assertRaises(FactoryError):self.runner.prepare(self.pid,self.root/'validation/goal2/source')
        self.assertEqual(self.agent.roles,[])

    def test_prepared_live_code_guard_and_source_anchor_reject(self):
        self.prepare();(self.root/'README.md').write_text('Unexpected config change',encoding='utf-8')
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])

    def test_runtime_prompt_requires_finite_honest_check(self):
        self.prepare();self.execute()
        text=self.agent.last_tester_prompt
        self.assertIn('finally清理服务',text);self.assertIn('不能把长驻服务argv及退出1',text)

    def reusable_tool_failure(self):
        """Explicit synthetic CLI events; not a real Tester result."""
        self.prepare();original_run=self.agent.run
        def synthetic_run(role,prompt,workspace,control,*args):
            result=original_run(role,prompt,workspace,control,*args)
            if role!='Tester':return result
            value=result['output'];folder=workspace/'validation';folder.mkdir(exist_ok=True)
            data=folder/'synthetic-assertions.json';save(data,{'AgentDouble':'all synthetic checks'})
            e={'path':'workspace/validation/'+data.name,'sha256':file_hash(data)}
            for ac in value['acceptance']:ac['evidence']=[e]
            for check in value['checks']:check['evidence']=[e]
            error=folder/'hash-enumeration-error.json'
            save(error,{'kind':'evidence hash enumeration','exit_code':1,'error':'ParserError: empty pipe element',
                        'synthetic':'AgentDouble no real subprocess'})
            err={'path':'workspace/validation/'+error.name,'sha256':file_hash(error)}
            value['issues']=[{'id':'TESTER-TOOL-001','ac_ids':[],'category':'test','severity':'minor',
                'reproduce':['PowerShell 将 foreach 语句直接接到 ConvertTo-Json 管道。'],
                'expected':'输出证据 SHA256 清单。','actual':'Synthetic ParserError recovered, no real process','evidence':[err]}]
            bad={'id':'synthetic-failed','type':'command_execution','command':'foreach($p in $paths){Get-FileHash} | ConvertTo-Json',
                 'exit_code':1,'status':'failed','aggregated_output':'ParserError: An empty pipe element is not allowed.'}
            good={'id':'synthetic-corrected','type':'command_execution',
                  'command':'$out=foreach($p in $paths){Get-FileHash}; $out | ConvertTo-Json; Candidate changed',
                  'exit_code':0,'status':'completed','aggregated_output':json.dumps([e,err])}
            summaries=result['command_executions']
            events=[{'type':'item.completed','item':{**item,'type':'command_execution','id':'synthetic-'+str(i)}} for i,item in enumerate(summaries)]
            events.extend({'type':'item.completed','item':item} for item in (bad,good))
            (control/'tester-01.log.jsonl').write_text('\n'.join(json.dumps({'stream':'stdout','text':json.dumps(x)}) for x in events),encoding='utf-8')
            result['command_executions']=summaries+[{k:item[k] for k in ('command','exit_code','status')} for item in (bad,good)]
            result['execution_mode']='danger-full-access';save(control/'tester-01.result.json',result)
            return result
        self.agent.run=synthetic_run
        self.assertEqual(self.execute()['status'],'质量门槛失败')
        self.source_run=self.run;self.failed_run=original_files(self.run)
        manifest_path=self.root/'validation/goal3/delivered-evidence.json'
        save(manifest_path,{'files':[{'path':(self.run/n).relative_to(self.root).as_posix(),'sha256':h} for n,h in self.failed_run.items()]})
        self.agent.run=original_run;self.agent.roles=[];self.agent.quality_calls=[]
        return manifest_path

    def test_recovered_event_reuses_tester_only_reviewer_and_preserves_failed_run(self):
        manifest_path=self.reusable_tool_failure()
        result=self.runner.prepare_review(self.prepared['run_id'],manifest_path)
        self.prepared=result;self.run=Path(result['path'])
        self.assertEqual(self.agent.roles,[])
        self.assertEqual(self.execute()['status'],'质量门槛通过')
        self.assertEqual(self.agent.roles,['Reviewer'])
        self.assertEqual(original_files(self.source_run),self.failed_run)
        self.assertEqual(original_files(self.project),self.original)
        q=load(self.run/'control/quality/state.json');self.assertEqual([c['role'] for c in q['calls']],['Reviewer'])
        self.assertTrue(q['rounds'][0]['tester_derivation']);self.assertEqual(q['rounds'][0]['tester']['issues'],[])
        self.assertTrue((self.run/'stage-approval.json').is_file())
        self.assertEqual(self.execute()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,['Reviewer'])

    def test_recovery_rejects_unknown_issue_or_extra_failure_or_missing_corrected_hash(self):
        self.reusable_tool_failure();call=self.source_run/'control/quality/calls/01-tester'
        execution=load(call/'execution.json');log=call/'tester-01.log.jsonl';round_root=self.source_run/'control/quality/rounds/01'
        derived,proof=recovered_tester_event(execution,log,round_root)
        self.assertEqual(derived['issues'],[]);self.assertEqual(proof['failed_command']['exit_code'],1)
        unknown=copy.deepcopy(execution);unknown['output']['issues'][0]['id']='UNKNOWN'
        with self.assertRaises(FactoryError):recovered_tester_event(unknown,log,round_root)
        blocked=copy.deepcopy(execution);blocked['output']['acceptance'][0]['result']='unverified'
        with self.assertRaises(FactoryError):recovered_tester_event(blocked,log,round_root)
        nonzero=copy.deepcopy(execution);nonzero['output']['checks'][0]['exit_code']=1
        with self.assertRaises(FactoryError):recovered_tester_event(nonzero,log,round_root)
        extra=self.root/'extra.log';extra.write_text(log.read_text(encoding='utf-8')+'\n'+json.dumps({'stream':'stdout','text':json.dumps({'type':'item.completed','item':{'type':'command_execution','exit_code':2}})}),encoding='utf-8')
        with self.assertRaises(FactoryError):recovered_tester_event(execution,extra,round_root)
        missing=self.root/'missing.log';rows=log.read_text(encoding='utf-8').splitlines();row=json.loads(rows[-1]);event=json.loads(row['text']);event['item']['aggregated_output']='[]';row['text']=json.dumps(event);rows[-1]=json.dumps(row);missing.write_text('\n'.join(rows),encoding='utf-8')
        with self.assertRaises(FactoryError):recovered_tester_event(execution,missing,round_root)

    def test_recovery_source_tamper_or_derived_verdict_tamper_rejects_zero_models(self):
        manifest_path=self.reusable_tool_failure();result=self.runner.prepare_review(self.prepared['run_id'],manifest_path)
        self.prepared=result;self.run=Path(result['path']);q=load(self.run/'control/quality/state.json')
        q['rounds'][0]['tester']['acceptance'][0]['reason']='Forged rewrite';save(self.run/'control/quality/state.json',q)
        with self.assertRaises(FactoryError):self.execute()
        self.assertEqual(self.agent.roles,[])
        raw=self.source_run/'control/quality/calls/01-tester/execution.json';raw.write_text('{}',encoding='utf-8')
        with self.assertRaises(FactoryError):self.runner.verify(load(self.run/'prepared.json'),self.run)

    def test_recovery_reviewer_rejects_no_repair_or_duplicate_dispatch(self):
        manifest_path=self.reusable_tool_failure();result=self.runner.prepare_review(self.prepared['run_id'],manifest_path)
        self.prepared=result;self.run=Path(result['path']);self.agent.scenario='reviewer_blocked'
        self.assertEqual(self.execute()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,['Reviewer'])
        self.assertFalse((self.run/'stage-approval.json').exists())
        self.assertEqual(self.execute()['status'],'质量门槛失败');self.assertEqual(self.agent.roles,['Reviewer'])

    def completed_reviewer_source(self):
        manifest_path=self.reusable_tool_failure();tester_run=self.prepared['run_id']
        result=self.runner.prepare_review(tester_run,manifest_path);self.prepared=result;self.run=Path(result['path'])
        original_run=self.agent.run;original_result=QualityGate.result
        def synthetic_reviewer(role,prompt,workspace,control,*args):
            result=original_run(role,prompt,workspace,control,*args)
            if role=='Reviewer':
                result['execution_mode']='read-only';save(control/'reviewer-01.result.json',result)
                (control/'reviewer-01.log.jsonl').write_text('Synthetic Reviewer, not real model',encoding='utf-8')
            return result
        def old_rule(gate,value,role,*args):
            if role=='Reviewer':raise FactoryError('Synthetic old Reviewer context-only misclassification')
            return original_result(gate,value,role,*args)
        self.agent.run=synthetic_reviewer
        with patch.object(QualityGate,'result',old_rule):self.assertEqual(self.execute()['status'],'质量门槛失败')
        self.agent.run=original_run;self.agent.roles=[];self.agent.quality_calls=[]
        source=self.run;before=original_files(source)
        result=self.runner.prepare_review(tester_run,manifest_path,reviewer_source_run_id=self.prepared['run_id'])
        self.prepared=result;self.run=Path(result['path'])
        return source,before

    def test_completed_real_shape_reviewer_revalidated_without_new_model_or_old_state_rewrite(self):
        source,before=self.completed_reviewer_source()
        self.assertEqual(self.execute()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,[])
        self.assertEqual(original_files(source),before);self.assertTrue((self.run/'stage-approval.json').is_file())
        self.assertEqual(load(self.run/'control/quality/state.json')['calls'],[])
        self.assertEqual(self.execute()['status'],'质量门槛通过');self.assertEqual(self.agent.roles,[])

    def test_reviewer_current_index_allowed_only_for_bound_delivery_review(self):
        self.reusable_tool_failure();gate=QualityGate.__new__(QualityGate)
        gate.c=self.c;gate.control=self.source_run/'control';gate.folder=gate.control/'quality';gate.workspace=self.workspace
        gate.state=load(gate.control/'state.json');gate.q=load(gate.folder/'state.json');gate.packet=load(gate.control/'task-packet.json');gate.load=load;gate.save=save
        row=gate.q['rounds'][0];folder=gate.folder/row['path'];call=gate.folder/'calls/01-tester'
        raw=load(call/'execution.json');derived,proof=recovered_tester_event(raw,call/'tester-01.log.jsonl',folder)
        # Construct the same bound source by using the production prepare API.
        manifest=self.root/'validation/goal3/delivered-evidence.json'
        result=self.runner.prepare_review(self.prepared['run_id'],manifest)
        control=Path(result['path'])/'control';gate.control=control;gate.folder=control/'quality';gate.path=gate.folder/'state.json'
        gate.state=load(control/'state.json');gate.q=load(gate.folder/'state.json');row=gate.q['rounds'][0]
        index=gate.evidence_index(row,'Reviewer');e={'path':index['path'],'sha256':index['sha256']}
        review={'candidate_fingerprint':row['candidate']['fingerprint'],'decision':'approved','acceptance':copy.deepcopy(row['tester']['acceptance']),
                'issues':[],'limitations':[],'summary':'Synthetic read-only current delivery review'}
        next(a for a in review['acceptance'] if a['id']=='AC-012')['evidence']=[e]
        execution={'command_executions':[{'command':'Get-Content fixture.mjs','status':'completed','exit_code':0}]}
        self.assertEqual(gate.result(review,'Reviewer',row,execution)['decision'],'approved')
        unknown=copy.deepcopy(review);unknown['acceptance'][0]['evidence']=[e]
        with self.assertRaises(FactoryError):gate.result(unknown,'Reviewer',row,execution)
        old_only=copy.deepcopy(review);next(a for a in old_only['acceptance'] if a['id']=='AC-012')['evidence']=[row['context']['history'][0]]
        with self.assertRaises(FactoryError):gate.result(old_only,'Reviewer',row,execution)
        forged=copy.deepcopy(review);next(a for a in forged['acceptance'] if a['id']=='AC-012')['evidence'][0]['sha256']='0'*64
        with self.assertRaises(FactoryError):gate.result(forged,'Reviewer',row,execution)


if __name__=='__main__':unittest.main()

"""Goal 2 execution-layer contracts; TaskPacket 1.0 remains unchanged."""
import re
from .contracts import obj, arr, S, FactoryError, schema_check

H = {'type':'string','pattern':'^[a-f0-9]{64}$'}
CHOICE = lambda *values: {'type':'string','enum':list(values)}
EVIDENCE = obj({'path':S,'sha256':H})
ISSUE = obj({'id':S,'ac_ids':arr(S),'category':CHOICE('implementation','test','environment','ambiguity','permission','evidence'),
             'severity':CHOICE('critical','major','minor'),'reproduce':arr(S),'expected':S,'actual':S,'evidence':arr(EVIDENCE)})
CHECK = obj({'kind':CHOICE('build','test','runtime','browser','persistence','failure','other'),
             'argv':arr(S),'exit_code':{'type':'integer'},'result':CHOICE('passed','failed','unverified'),
             'ac_ids':arr(S),'evidence':arr(EVIDENCE)})
AC_RESULT = obj({'id':S,'result':CHOICE('passed','failed','unverified'),'reason':S,'evidence':arr(EVIDENCE)})
TESTER_SCHEMA = obj({'candidate_fingerprint':H,'status':CHOICE('passed','failed','blocked'),
                     'acceptance':arr(AC_RESULT),'checks':arr(CHECK),'issues':arr(ISSUE),
                     'limitations':arr(S)})
REVIEWER_SCHEMA = obj({'candidate_fingerprint':H,'decision':CHOICE('approved','changes_requested','blocked'),
                       'acceptance':arr(AC_RESULT),'issues':arr(ISSUE),'limitations':arr(S),'summary':S})
DEFECT_SCHEMA = obj({'format_version':CHOICE('2.0'),'project_id':S,'task_id':S,'candidate_fingerprint':H,
                     'packet_fingerprint':H,'issues':arr(ISSUE),'repair_number':{'type':'integer'}})

BUDGET = {'Tester':3,'Reviewer':3,'CoderRepair':2,'max_calls':8,'max_rounds':3,
          'max_same_issue_repairs':2,'timeout_seconds':600,'max_agent_seconds':4800,'stage_timeout_seconds':6600}

def validate_schema(value,schema):
    schema_check(value,schema)
    def hashes(v,s):
        if s.get('pattern') and not re.fullmatch(s['pattern'],v):
            raise FactoryError('质量契约哈希格式无效')
        if s['type']=='object':
            for k in v: hashes(v[k],s['properties'][k])
        if s['type']=='array':
            for x in v: hashes(x,s['items'])
    hashes(value,schema)

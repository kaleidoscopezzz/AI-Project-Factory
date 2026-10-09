"""Runs unchanged Goal 1 tests plus labelled Goal 2 tests, no model calls."""
import io
import json
import sys
import time
import unittest
import uuid
from pathlib import Path

sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests import test_factory, test_quality

def main():
    out=ROOT/'validation/goal2'/('regression-'+time.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6])
    out.mkdir(parents=True)
    test_factory.RUN_ROOT=ROOT/'validation/goal2/test-workspaces'/(out.name+'-goal1')
    test_quality.RUN_ROOT=ROOT/'validation/goal2/test-workspaces'/(out.name+'-goal2')
    results={}
    for label,cls in [('goal1_original',test_factory.FactoryTests),('goal2_new',test_quality.QualityTests)]:
        stream=io.StringIO();start=time.monotonic()
        with __import__('contextlib').redirect_stdout(stream):
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(cls))
        (out/(label+'.txt')).write_text(stream.getvalue(),encoding='utf-8')
        results[label]={'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
                        'passed':result.wasSuccessful(),'elapsed_seconds':round(time.monotonic()-start,3)}
    data={'kind':'deterministic AgentDouble control tests; real local subprocess timeout/redaction checks only',
          'real_model_calls':0,'real_business_e2e':False,'results':results,'passed':all(r['passed'] for r in results.values())}
    (out/'RESULTS.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'directory':str(out),**data},ensure_ascii=False,indent=2))
    return 0 if data['passed'] else 1

if __name__=='__main__':sys.exit(main())

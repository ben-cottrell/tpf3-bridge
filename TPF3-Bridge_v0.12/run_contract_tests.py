"""Run only the v0.12 contract/metadata tests; do not imply legacy reruns."""
from pathlib import Path
import hashlib
import importlib.metadata
import io
import json
import platform
import sys
import time
import unittest
ROOT=Path(__file__).resolve().parent

class Result(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.ids=[];self.passed=[]
    def startTest(self,test):self.ids.append(test.id());super().startTest(test)
    def addSuccess(self,test):self.passed.append(test.id());super().addSuccess(test)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.discover(str(ROOT/'validation'),pattern='test_contracts.py')
    stream=io.StringIO();t=time.perf_counter()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    elapsed=time.perf_counter()-t
    paths=[ROOT/'contract_checks.py',ROOT/'run_contract_tests.py',ROOT/'validation/test_contracts.py',ROOT/'requirements-contracts.txt']
    paths+=sorted((ROOT/'contracts').rglob('*.json'))+sorted((ROOT/'implementation').rglob('*.json'))
    report={'release':'0.12.0','scope':'offline contract, policy and handoff metadata checks; no legacy suite or game rerun','python':sys.version,'platform':platform.platform(),'jsonschema_version':importlib.metadata.version('jsonschema'),'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'successful':result.wasSuccessful(),'elapsed_s':elapsed,'executed_test_ids':result.ids,'passed_test_ids':result.passed,'tested_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},'game_calls':0,'model_calls':0,'legacy_suite_rerun':False}
    (ROOT/'validation/contract_test_report.json').write_text(json.dumps(report,indent=2)+'\n')
    (ROOT/'validation/contract_test_log.txt').write_text(stream.getvalue())
    print(stream.getvalue());print(json.dumps({k:report[k] for k in ['tests_run','failures','errors','skipped','successful','elapsed_s']},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)

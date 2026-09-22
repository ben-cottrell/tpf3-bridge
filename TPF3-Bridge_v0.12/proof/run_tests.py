"""Run legacy, geometry, motion, sectional and numerical-profile tests; retain actual per-test IDs and byte hashes."""
from pathlib import Path
import hashlib
import json
import platform
import time
import unittest

ROOT=Path(__file__).resolve().parent

class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self.started_ids=[];self.passed_ids=[]
    def startTest(self,test):
        self.started_ids.append(test.id());super().startTest(test)
    def addSuccess(self,test):
        self.passed_ids.append(test.id());super().addSuccess(test)

if __name__=='__main__':
    import os
    os.chdir(ROOT);out=ROOT/'results';out.mkdir(exist_ok=True)
    started=time.perf_counter();suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    with (out/'test_log.txt').open('w',encoding='utf-8') as stream:
        result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=RecordedResult).run(suite)
    sources=[p for sub in ('railproof','railgeom','railops','railclear','railstation','railcompact','railinterface','railcorridor','railbranch','railterrain','tests') for p in sorted((ROOT/sub).glob('*.py'))]+[ROOT/'run_tests.py']
    fixtures=[p for sub in ('fixtures','geometry_fixtures','sectional_fixtures','clearance_fixtures','station_fixtures','compact_fixtures','interface_fixtures','corridor_fixtures','branch_fixtures','terrain_fixtures') for p in sorted((ROOT/sub).glob('*.json'))]
    report={'proof_version':'0.11.0','tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
       'skipped':len(result.skipped),'successful':result.wasSuccessful(),'elapsed_seconds_this_run':time.perf_counter()-started,
       'python':platform.python_version(),'platform':platform.platform(),
       'legacy_v02_tests_run':sum(not x.startswith(('test_geom_','test_ops_','test_uk_','test_clear_','test_station_','test_compact_','test_interface_','test_corridor_','test_branch_','test_terrain_')) for x in result.started_ids),
       'geometry_v03_tests_run':sum(x.startswith('test_geom_') for x in result.started_ids),
       'v04_tests_run':sum(x.startswith(('test_ops_','test_uk_')) for x in result.started_ids),
       'v011_tests_run':sum(x.startswith('test_terrain_') for x in result.started_ids),
       'v010_tests_run':sum(x.startswith('test_branch_') for x in result.started_ids),
       'v09_tests_run':sum(x.startswith('test_corridor_') for x in result.started_ids),
       'v08_tests_run':sum(x.startswith('test_interface_') for x in result.started_ids),
       'v07_tests_run':sum(x.startswith('test_compact_') for x in result.started_ids),
       'v06_tests_run':sum(x.startswith('test_station_') for x in result.started_ids),
       'v05_tests_run':sum(x.startswith('test_clear_') for x in result.started_ids),
       'evidence_input_sha256':{str(p.relative_to(ROOT.parent)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT.parent/'evidence').glob('*.json'))},
       'numerical_register_sha256':hashlib.sha256((ROOT.parent/'evidence/uk_parameters.json').read_bytes()).hexdigest(),
       'scope':'Authored model tests, not completion of all production requirements or project benchmarks',
       'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
       'fixture_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fixtures},
       'executed_test_ids':result.started_ids,'passed_test_ids':result.passed_ids,
       'failure_details':[{'test':str(t),'traceback':err} for t,err in result.failures+result.errors]}
    (out/'test_report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('tests_run','legacy_v02_tests_run','geometry_v03_tests_run','v04_tests_run','v05_tests_run','v06_tests_run','v07_tests_run','v08_tests_run','v09_tests_run','v010_tests_run','v011_tests_run','failures','errors','skipped','successful','elapsed_seconds_this_run')},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)

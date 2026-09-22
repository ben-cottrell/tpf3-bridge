from functools import lru_cache
from pathlib import Path
from railstation.composition import build_station,compile_station
from railstation.demo import read_fixture,scenario
from railstation.operations import schedule_station
from railstation.checks import check_result

ROOT=Path(__file__).resolve().parents[1]
@lru_cache(None)
def station(f='isolated'):
    s=build_station(f);return s,compile_station(s)
@lru_cache(None)
def fixture():return read_fixture(ROOT/'station_fixtures/release.json')
@lru_cache(None)
def case(f='isolated',sc='nominal',pairs=2):
    config=dict(fixture());config['pairs']=pairs
    vs,kw=scenario(config,sc)
    s,c=station(f);r=schedule_station(c,vs,**kw)
    r['independent_check']=check_result(c,vs,r)
    return vs,r

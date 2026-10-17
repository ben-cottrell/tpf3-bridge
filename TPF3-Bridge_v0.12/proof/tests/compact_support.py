from functools import lru_cache
from pathlib import Path
from dataclasses import replace
from railcompact.composition import build_compact,CompactSpec
from railcompact.compiler import compile_assembly
from railcompact.demo import read_fixture,scenario
from railstation.operations import schedule_station
from railstation.checks import check_result
ROOT=Path(__file__).resolve().parents[1]

@lru_cache(None)
def model(family='scissors'):
    s=build_compact(family,CompactSpec(first_fan_toe_x_m=205.));return s,compile_assembly(s.assembly)

def fixture():return read_fixture(ROOT/'compact_fixtures/release.json')

def executed(name='nominal',family='scissors',pairs=2):
    f=fixture();f['pairs']=pairs;v,kw=scenario(f,name);s,c=model(family)
    r=schedule_station(c,v,**kw);r['independent_check']=check_result(c,v,r)
    return s,c,v,r

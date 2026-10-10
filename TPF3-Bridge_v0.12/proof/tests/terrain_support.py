from copy import deepcopy
from pathlib import Path
from railclear.catalogue import read_json
from railterrain.planning import load_inputs,spec_for,bind
from railterrain.geometry import build_placed
ROOT=Path(__file__).resolve().parents[1]
def inputs():
 f=read_json(ROOT/'terrain_fixtures/release.json');c,b=load_inputs(f);return f,c,b
def model(mode='flyover',offset=280,layout_index=1):
 f,c,b=inputs();layout=f['layouts'][layout_index]
 j=build_placed(spec_for(b,c,layout),mode,offset,layout['main_restore_x_m'])
 return f,c,b,j

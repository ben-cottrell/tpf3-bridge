"""Validate authored package links, JSON, executed-input hashes and manifest.

With --baseline PATH, compare frozen earlier source/tests and deterministic
outputs. --refresh is a release-maintainer operation: validate first, then write
release_validation.json and manifest.json. It never reruns or forges test results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from urllib.parse import urlsplit, unquote
import zipfile

ROOT=Path(__file__).resolve().parent
SELF_EXCLUSIONS={'manifest.json','release_validation.json'}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def files():return sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
def reject(x):raise ValueError('Nonfinite JSON: '+x)
def load(p):return json.loads(p.read_text(encoding='utf-8'),parse_constant=reject)


def anchors(path):
    text=path.read_text(encoding='utf-8')
    found=set(re.findall(r'<a\s+id=[\"\']([^\"\']+)',text));counts={}
    in_code=False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):in_code=not in_code;continue
        if in_code:continue
        m=re.match(r'^#{1,6}\s+(.*?)(?:\s+#+)?$',line)
        if not m:continue
        title=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',m.group(1)).lower()
        key=re.sub(r'[^\w\-\s]','',title).replace(' ','-')
        n=counts.get(key,0);counts[key]=n+1;found.add(key+('-'+str(n) if n else ''))
    return found


def validate(baseline=None,refresh=False):
    errors=[];linkcount=0;jsoncount=0;manifest_checked=0
    for p in files():
        if p.suffix=='.json':
            try:load(p);jsoncount+=1
            except Exception as exc:errors.append(f'JSON {p.relative_to(ROOT)}: {exc}')
        if p.suffix=='.md':
            for target in re.findall(r'(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)',p.read_text(encoding='utf-8')):
                target=target.strip().strip('<>');u=urlsplit(target)
                if u.scheme or u.netloc:continue
                dest=(p.parent/unquote(u.path)).resolve() if u.path else p.resolve()
                try:dest.relative_to(ROOT)
                except ValueError:errors.append(f'Escaping local link: {p.name}: {target}');continue
                linkcount+=1
                if not dest.exists():errors.append(f'Missing link: {p.relative_to(ROOT)}: {target}')
                elif u.fragment and dest.suffix=='.md' and unquote(u.fragment) not in anchors(dest):
                    errors.append(f'Missing fragment: {p.relative_to(ROOT)}: {target}')
    report=load(ROOT/'proof/results/test_report.json')
    if not report.get('successful') or report.get('failures') or report.get('errors') or report.get('skipped'):errors.append('Test acceptance not fully successful')
    if len(set(report['executed_test_ids']))!=report['tests_run'] or len(report['passed_test_ids'])!=report['tests_run']:errors.append('Test ID counts inconsistent')
    checked=0
    for key,base in (('source_sha256',ROOT/'proof'),('fixture_sha256',ROOT/'proof'),('evidence_input_sha256',ROOT)):
        for name,expected in report[key].items():
            p=base/name;checked+=1
            if not p.exists() or sha(p)!=expected:errors.append(f'Tested byte mismatch: {name}')
    legacy_sources=[];legacy_outputs=[];legacy_diffs=[]
    if baseline:
        with zipfile.ZipFile(baseline) as z:
            if z.testzip() is not None:errors.append('Baseline ZIP corrupt')
            for name in z.namelist():
                if name.endswith('/'):continue
                rel=PurePosixPath(*PurePosixPath(name).parts[1:]);s=str(rel)
                source=s.startswith(('proof/railproof/','proof/railgeom/','proof/railops/','proof/railclear/','proof/railstation/','proof/railcompact/','proof/railinterface/','proof/railcorridor/','proof/railbranch/','proof/tests/')) and s.endswith('.py')
                output=s.startswith(('proof/results/','proof/geometry_results/','proof/sectional_results/','proof/clearance_results/','proof/station_results/','proof/compact_results/','proof/interface_results/','proof/corridor_results/','proof/branch_results/')) and s.endswith(('.json','.md')) and 'test_report' not in s
                if source:legacy_sources.append(s)
                if output:legacy_outputs.append(s)
                if source or output:
                    if not (ROOT/rel).exists() or (ROOT/rel).read_bytes()!=z.read(name):legacy_diffs.append(s)
        if legacy_diffs:errors.append('Legacy byte regressions: '+', '.join(legacy_diffs))
    if not refresh:
        manifest=load(ROOT/'manifest.json')
        actual={str(p.relative_to(ROOT)) for p in files() if str(p.relative_to(ROOT)) not in SELF_EXCLUSIONS}
        if actual!=set(manifest['sha256']):errors.append('Manifest file-set mismatch')
        for name,expected in manifest['sha256'].items():
            p=ROOT/name;manifest_checked+=1
            if not p.exists() or sha(p)!=expected:errors.append('Manifest byte mismatch: '+name)
    record={'release':'0.11.0','validation_date':'2026-09-21','successful':not errors,
          'main_markdown_files':len(list(ROOT.glob('*.md'))),'markdown_files_including_results':sum(p.suffix=='.md' for p in files()),
          'source_records':len(re.findall(r'^### S\d{3}\b',(ROOT/'10_source_register.md').read_text(),re.M)),
          'local_links_checked':linkcount,'json_files_parsed':jsoncount,'tested_byte_records_checked':checked,
          'tests_run':report['tests_run'],'new_terrain_tests':report['v011_tests_run'],
          'manifest_entries_checked':manifest_checked,'baseline_status':'checked' if baseline else 'not_requested',
          'legacy_baseline_archive':Path(baseline).name if baseline else None,
          'legacy_source_and_test_files_compared':len(legacy_sources),'legacy_deterministic_output_files_compared':len(legacy_outputs),
          'legacy_sources_and_outputs_identical':not legacy_diffs if baseline else None,
          'legacy_source_paths':legacy_sources,'legacy_output_paths':legacy_outputs,
          'legacy_exclusions':['current/historical acceptance reports and timing logs; updated run_tests.py'],
          'errors':errors}
    if refresh and not errors:
        (ROOT/'release_validation.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
        m={'release':'0.11.0','hash_algorithm':'SHA-256','self_exclusions':sorted(SELF_EXCLUSIONS),
           'sha256':{str(p.relative_to(ROOT)):sha(p) for p in files() if str(p.relative_to(ROOT)) not in SELF_EXCLUSIONS}}
        (ROOT/'manifest.json').write_text(json.dumps(m,indent=2)+'\n',encoding='utf-8')
    return record

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--refresh',action='store_true')
    a=p.parse_args()
    try:r=validate(a.baseline,a.refresh)
    except Exception as exc:
        print(json.dumps({'successful':False,'error':str(exc)},indent=2));raise SystemExit(1)
    print(json.dumps({k:r[k] for k in ('release','successful','main_markdown_files','local_links_checked','json_files_parsed',
         'tests_run','new_terrain_tests','baseline_status','legacy_source_and_test_files_compared','legacy_deterministic_output_files_compared','errors')},indent=2))
    raise SystemExit(0 if r['successful'] else 1)

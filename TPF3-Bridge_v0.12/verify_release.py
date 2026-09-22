"""Check v0.12 handoff integrity; this never reruns legacy engineering tests.

--refresh records a new manifest only after all other checks pass.
--baseline compares every preceding proof/evidence file against the actual ZIP.
Requires only the Python standard library. Contract tests use a separate dev
requirement and must be rerun explicitly when their inputs change.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from urllib.parse import unquote,urlsplit
import zipfile

ROOT=Path(__file__).resolve().parent
EXCLUDE={'manifest.json','release_validation.json'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def paths():return sorted(p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
def unique(pairs):
    d={}
    for k,v in pairs:
        if k in d:raise ValueError('duplicate key '+k)
        d[k]=v
    return d
def reject(v):raise ValueError('nonfinite value '+v)
def load(p):return json.loads(p.read_text(encoding='utf-8'),object_pairs_hook=unique,parse_constant=reject)
def anchors(path):
    text=path.read_text(encoding='utf-8');out=set(re.findall(r'<a\s+id=[\"\']([^\"\']+)',text));counts={};inside=False
    for line in text.splitlines():
        if line.lstrip().startswith('```'):inside=not inside;continue
        if inside:continue
        m=re.match(r'^#{1,6}\s+(.*?)(?:\s+#+)?$',line)
        if not m:continue
        title=re.sub(r'\[([^\]]+)\]\([^)]*\)',r'\1',m.group(1)).lower()
        key=re.sub(r'[^\w\-\s]','',title).replace(' ','-');n=counts.get(key,0);counts[key]=n+1;out.add(key+('-'+str(n) if n else ''))
    return out

def validate(baseline=None,refresh=False):
    errors=[];njson=0;nlinks=0;ntested=0
    for p in paths():
        if p.suffix=='.json':
            try:
                x=load(p)
                # Re-encoding disallows overflow values such as 1e309, too.
                json.dumps(x,allow_nan=False);njson+=1
            except Exception as exc:errors.append(f'JSON {p.relative_to(ROOT)}: {exc}')
        if p.suffix=='.md':
            for target in re.findall(r'(?<!!)\[[^\]\n]*\]\(([^)\n]+)\)',p.read_text(encoding='utf-8')):
                target=target.strip().strip('<>');u=urlsplit(target)
                if u.scheme or u.netloc:continue
                dest=(p.parent/unquote(u.path)).resolve() if u.path else p.resolve();nlinks+=1
                try:dest.relative_to(ROOT)
                except ValueError:errors.append(f'escaping link {p.name}: {target}');continue
                if not dest.exists():errors.append(f'missing link {p.relative_to(ROOT)}: {target}')
                elif u.fragment and dest.suffix=='.md' and unquote(u.fragment) not in anchors(dest):errors.append(f'missing fragment {p.name}: {target}')
    report=load(ROOT/'validation/contract_test_report.json')
    if not report.get('successful') or any(report.get(k) for k in ('failures','errors','skipped')):errors.append('contract acceptance failed')
    if len(set(report['executed_test_ids']))!=report['tests_run'] or set(report['executed_test_ids'])!=set(report['passed_test_ids']):errors.append('contract method counts inconsistent')
    for name,expected in report['tested_sha256'].items():
        p=ROOT/name;ntested+=1
        if not p.is_file() or sha(p)!=expected:errors.append('current tested byte mismatch '+name)
    if report.get('legacy_suite_rerun') is not False or report.get('game_calls')!=0:errors.append('incorrect v012 execution scope')
    examples=load(ROOT/'validation/example_validation.json')
    if not examples.get('successful') or len(examples['records'])!=len(load(ROOT/'contracts/example_index.json')['examples']):errors.append('example validation inconsistent')
    old=load(ROOT/'proof/results/test_report.json');nold=0
    if old.get('tests_run')!=985 or not old.get('successful'):errors.append('unexpected preserved engineering acceptance')
    for key,base in [('source_sha256',ROOT/'proof'),('fixture_sha256',ROOT/'proof'),('evidence_input_sha256',ROOT)]:
        for name,expected in old[key].items():
            nold+=1;p=base/name
            if not p.is_file() or sha(p)!=expected:errors.append('preserved tested byte mismatch '+name)
    req=load(ROOT/'implementation/requirement_disposition.json')['requirements']
    ids=set(re.findall(r'^\| ((?:BRF|DAT|TOP|GEO|OPS|PAX|OPT|EXE|OBS|EVD)-\d{3}) \|',(ROOT/'06_passenger_engine_specification.md').read_text(),re.M))
    if len(req)!=75 or {r['requirement_id'] for r in req}!=ids:errors.append('requirement coverage mismatch')
    for r in req:
        for path in r['reference_locations']:
            if not (ROOT/path).exists():errors.append('missing requirement reference '+path)
    for w in load(ROOT/'implementation/work_packages.json')['work_packages']:
        for p in w['inputs']:
            if not (ROOT/p).exists():errors.append('missing work input '+p)
    caps=load(ROOT/'contracts/tpf3_unprobed_capabilities.json')['capabilities']
    if any(c['evidence']['level']!='unknown' or c['game_build'] is not None or c['evidence']['native_symbols'] for c in caps):errors.append('unprobed game manifest promoted')
    compared=[];diffs=[];basehash=None
    if baseline:
        basehash=sha(Path(baseline))
        with zipfile.ZipFile(baseline) as z:
            if z.testzip() is not None:errors.append('baseline zip corrupt')
            for name in z.namelist():
                if name.endswith('/'):continue
                pp=PurePosixPath(name)
                if len(pp.parts)<2:continue
                rel=PurePosixPath(*pp.parts[1:]);s=str(rel)
                if '..' in rel.parts or rel.is_absolute():raise ValueError('unsafe baseline member')
                if not s.startswith(('proof/','evidence/')):continue
                compared.append(s);p=ROOT/s
                if not p.exists() or p.read_bytes()!=z.read(name):diffs.append(s)
        if diffs:errors.append('baseline changes: '+', '.join(diffs))
    manifest_checked=0
    if not refresh:
        m=load(ROOT/'manifest.json');actual={str(p.relative_to(ROOT)) for p in paths() if str(p.relative_to(ROOT)) not in EXCLUDE}
        if set(m['sha256'])!=actual:errors.append('manifest file-set mismatch')
        for name,v in m['sha256'].items():
            manifest_checked+=1;p=ROOT/name
            if not p.exists() or sha(p)!=v:errors.append('manifest mismatch '+name)
    record={'release':'0.12.0','validation_date':'2026-09-21','successful':not errors,'main_markdown_documents':len(list(ROOT.glob('*.md'))),'source_records':len(re.findall(r'^### S\d{3}\b',(ROOT/'10_source_register.md').read_text(),re.M)),'local_links_checked':nlinks,'json_files_parsed':njson,'current_contract_tests_run':report['tests_run'],'current_contract_tested_byte_records':ntested,'preserved_engineering_test_methods':old['tests_run'],'preserved_engineering_suite_rerun':False,'preserved_engineering_tested_bytes_checked':nold,'native_game_calls':0,'schema_definitions':len(load(ROOT/'contracts/bridge.schema.json')['$defs']),'agent_tool_descriptors':len(load(ROOT/'contracts/agent_tools.json')['tools']),'example_records_validated':len(examples['records']),'baseline_status':'checked' if baseline else 'not_requested','baseline_archive':Path(baseline).name if baseline else None,'baseline_archive_sha256':basehash,'baseline_files_compared':len(compared),'baseline_python_files_compared':sum(p.endswith('.py') for p in compared),'baseline_proof_files_compared':sum(p.startswith('proof/') for p in compared),'baseline_evidence_files_compared':sum(p.startswith('evidence/') for p in compared),'baseline_preserved_identical':not diffs if baseline else None,'baseline_paths':compared,'baseline_differences':diffs,'manifest_entries_checked':manifest_checked,'errors':errors}
    if refresh and not errors:
        (ROOT/'release_validation.json').write_text(json.dumps(record,indent=2)+'\n')
        (ROOT/'manifest.json').write_text(json.dumps({'release':'0.12.0','hash_algorithm':'SHA-256','self_exclusions':sorted(EXCLUDE),'sha256':{str(p.relative_to(ROOT)):sha(p) for p in paths() if str(p.relative_to(ROOT)) not in EXCLUDE}},indent=2)+'\n')
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--baseline',type=Path);parser.add_argument('--refresh',action='store_true');args=parser.parse_args()
    result=validate(args.baseline,args.refresh);print(json.dumps(result,indent=2));raise SystemExit(0 if result['successful'] else 1)

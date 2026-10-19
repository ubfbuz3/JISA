"""Package integrity and a literal protocol/implementation sensitivity check.

Does not change any manuscript, recorded experiment, or Git reference.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
GIT = Path(r'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe')

def git(*args):
    return subprocess.check_output([str(GIT),'-c',f'safe.directory={ROOT.as_posix()}',*args],cwd=ROOT).decode('utf8').strip()

def load(rel):
    return json.loads((ROOT/rel).read_text(encoding='utf8'))

evidence={'head':git('rev-parse','HEAD'),'v3_local':git('rev-parse','access-resubmission-v3^{}'),
          'remote_verification':'Not performed; local tag equality does not establish remote equality'}
remote=OUT/'remote_refs.json'
if remote.exists():
    evidence['remote_verification']=json.loads(remote.read_text(encoding='utf8'))
evidence['check_commands']={}
jobs=[('letter_numbers',[sys.executable,'-X','utf8',str(ROOT/'03_论文撰写/response_to_reviewers/check_letter_numbers.py')]),
      ('letter_refs',[r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe','-X','utf8',str(ROOT/'03_论文撰写/response_to_reviewers/check_letter_refs.py')]),
      ('cve_validation',[sys.executable,'-X','utf8',str(ROOT/'04_绘图与分析/analysis/test_cve_pair_validation.py')])]
for name,args in jobs:
    res=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    evidence['check_commands'][name]={'returncode':res.returncode,'output':res.stdout+res.stderr}
    (OUT/f'{name}.log').write_text(res.stdout+res.stderr,encoding='utf8')

texts={}
evidence['pdfs']={}
for name,rel in [('clean','03_论文撰写/paper/main.pdf'),
                 ('response','03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'),
                 ('highlighted','03_论文撰写/response_to_reviewers/main_highlighted.pdf'),
                 ('initial','03_论文撰写/response_to_reviewers/baseline/submitted_main.pdf')]:
    path=ROOT/rel;d=PdfReader(path); pages=[p.extract_text() for p in d.pages]
    texts[name]=pages
    annotations=Counter(str(a.get_object().get('/Subtype')) for p in d.pages for a in p.get('/Annots',[]))
    evidence['pdfs'][name]={'pages':len(pages),'annotations':dict(annotations),
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'title_start':pages[0][:950]}
    (OUT/f'{name}_text.txt').write_text('\n'.join(f'\n=== PAGE {i+1} ===\n{p}' for i,p in enumerate(pages)),encoding='utf8')
evidence['clean_highlighted_same_text']=texts['clean']==texts['highlighted']
evidence['hashes']={}
for name in ['RAW_RECORDS_SHA256','OUTPUTS_SHA256']:
    rows=load(f'04_绘图与分析/provenance/{name}.json')['files']
    bad=[r['path'] for r in rows if not (ROOT/r['path']).is_file() or hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']]
    evidence['hashes'][name]={'files':len(rows),'mismatches':bad}

zip_path=ROOT/'03_论文撰写/paper/latex_source_files_submission.zip'
with zipfile.ZipFile(zip_path) as z:
    names=z.namelist()
    evidence['zip']={'files':len(names),'sha256':hashlib.sha256(zip_path.read_bytes()).hexdigest(),
                     'bad_member':z.testzip(),'members':names,
                     'raw_record_files':[p for p in names if p.endswith(('.json','.jsonl'))],
                     'python_generators':[p for p in names if p.endswith('.py')]}

# Counterfactual is explicitly the literal protocol reading mentioned in main §III:
# every modelled triple with no granting channel is unknown instead of deny.
# This is not a claim that unknown is the scientifically preferable policy.
evidence['literal_unknown_sensitivity']={}
for product in ['gitea','gitlab']:
    data=load(f'experiments/real_system/results/temporal/temporal_{product}.json')
    cells=[c for t in data['transitions'] for c in t['cells']]
    # Paper denominator excludes acting owner controls. Locate the field defining this
    # population by matching totals, rather than silently counting all stored cells.
    candidates={'non_owner_role':[c for c in cells if c.get('role')!='owner'],
                'non_acting_credential':[c for c in cells if not c.get('is_acting_credential',False)],
                'all':cells}
    chosen=[(name,rs) for name,rs in candidates.items() if len(rs)==data['totals']['cells']]
    if not chosen:
        raise RuntimeError(f'{product}: cannot locate scored population, inspect schema')
    name,rows=chosen[0]
    by_e=Counter(c['expected_entitlement'] for c in rows)
    deny=[c for c in rows if c['expected_entitlement']=='deny']
    remaining=[c for c in rows if c['expected_entitlement']=='allow']
    evidence['literal_unknown_sensitivity'][product]={
       'population_rule':name,'recorded_scored':len(rows),'recorded_E_counts':dict(by_e),
       'deny_expected_channels':dict(Counter(c.get('expected_channel') for c in deny)),
       'deny_basis_examples':[c.get('expected_basis') for c in deny[:3]],
       'literal_unknown_count':len(deny),'literal_known_E_cells':len(remaining),
       'literal_EY_agreements_on_known_cells':sum(c['observed_effect']==c['expected_entitlement'] for c in remaining),
       'deny_Y_allow':sum(c['observed_effect']=='allow' for c in deny),
       'recorded_totals':data['totals']}

(OUT/'primary_checks.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
compact={k:v for k,v in evidence.items() if k not in ('pdfs','zip')}
compact['pdf_pages']={k:v['pages'] for k,v in evidence['pdfs'].items()}
compact['source_zip']={k:v for k,v in evidence['zip'].items() if k!='members'}
print(json.dumps(compact,ensure_ascii=False,indent=2))

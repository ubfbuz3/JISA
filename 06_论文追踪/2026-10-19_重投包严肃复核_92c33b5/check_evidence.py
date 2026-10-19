"""Read-only checks of the submission; mutations run only in isolated audit copies."""
from pathlib import Path
from collections import Counter, defaultdict
from io import BytesIO
import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
GIT = Path(r'C:\Users\Administrator\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\git\cmd\git.exe')

def git(*args):
    return subprocess.check_output([str(GIT), '-c', f'safe.directory={ROOT.as_posix()}', *args], cwd=ROOT)

def load(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

report = {'head': git('rev-parse', 'HEAD').decode().strip()}
tag_commit = git('rev-parse', 'access-resubmission-v1^{}').decode().strip()
tag_candidates = ['experiments/results/baseline_compare.json', 'experiments/run_baseline.py',
                  '04_绘图与分析/analysis/ingest_baseline.py',
                  '03_论文撰写/response_to_reviewers/response_to_reviewers.pdf']
tag_missing = []
for candidate in tag_candidates:
    result = subprocess.run([str(GIT), '-c', f'safe.directory={ROOT.as_posix()}',
                             'cat-file', '-e', f'{tag_commit}:{candidate}'],
                            cwd=ROOT, capture_output=True)
    if result.returncode:
        tag_missing.append(candidate)
report['revision_tag_local'] = {'commit':tag_commit, 'missing_current_files':tag_missing,
                              'remote_verification':'Not established by this local check'}
letter = (ROOT/'03_论文撰写/response_to_reviewers/response_to_reviewers.tex').read_text(encoding='utf8')
report['response_blocks'] = {name:len(re.findall(r'^\\'+name+r'\{',letter,re.M))
                             for name in ['Concern','Response','Action']}
report['baselines'] = []
for rev in ['bc3752e', '89f3f96', 'HEAD']:
    data = git('show', f'{rev}:03_论文撰写/paper/main.pdf')
    pdf = PdfReader(BytesIO(data))
    txt = '\n'.join(p.extract_text() for p in pdf.pages)
    tex = git('show', f'{rev}:03_论文撰写/paper/main.tex').decode('utf-8')
    report['baselines'].append({
        'rev': rev, 'commit': git('show', '-s', '--format=%H %aI %s', rev).decode().strip(),
        'pages': len(pdf.pages), 'publicly_fixed_defect_in_pdf': 'A publicly fixed defect' in txt,
        'cve_input_in_source': 'cve_pair_numbers' in tex,
        'temporal_input_in_source': 'temporal_numbers' in tex,
        'pdf_sha256': hashlib.sha256(data).hexdigest(),
    })

report['pdfs'] = {}
pdftexts = {}
for name, rel in [('clean','03_论文撰写/paper/main.pdf'), ('response','03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'), ('highlighted','03_论文撰写/response_to_reviewers/main_highlighted.pdf')]:
    reader = PdfReader(ROOT/rel)
    texts = [p.extract_text() for p in reader.pages]
    pdftexts[name] = texts
    annotations = Counter()
    for p in reader.pages:
        for a in p.get('/Annots', []):
            annotations[str(a.get_object().get('/Subtype'))] += 1
    report['pdfs'][name] = {'pages':len(texts), 'annotations':dict(annotations)}
    (OUT/f'{name}_text.txt').write_text('\n'.join(f'\n=== PAGE {i+1} ===\n{t}' for i,t in enumerate(texts)), encoding='utf8')
report['clean_highlighted_same_text'] = pdftexts['clean'] == pdftexts['highlighted']
report['table_pages'] = {str(n): [i+1 for i,p in enumerate(pdftexts['clean']) if re.search(rf'TABLE\s+{n}\.',p)] for n in range(1,23)}
report['hash_manifests'] = {}
for name in ['RAW_RECORDS_SHA256','OUTPUTS_SHA256']:
    rows = load(f'04_绘图与分析/provenance/{name}.json')['files']
    errors = [r['path'] for r in rows if not (ROOT/r['path']).is_file() or hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']]
    report['hash_manifests'][name]={'count':len(rows), 'mismatches':errors}
z = ROOT/'03_论文撰写/paper/latex_source_files_submission.zip'
with zipfile.ZipFile(z) as archive:
    report['source_zip']={'files':len(archive.namelist()), 'bad_zip_member':archive.testzip(), 'sha256':hashlib.sha256(z.read_bytes()).hexdigest()}
report['temporal']={}
for product in ['gitea','gitlab']:
    d = load(f'experiments/real_system/results/temporal/temporal_{product}.json')
    report['temporal'][product]={'transitions':[t['kind'] for t in d['transitions']], 'totals':d['totals']}
d = load('experiments/native_engine/results/native_engine.json')
report['native_mrs']=d['engine']['mrs']
report['native_counters']=d['engine']['counters']
d = load('experiments/results/baseline_compare.json')
recs=d['records']; ours='ours_mr_v3'
positive=sum(r['truth']=='bola' for r in recs)
report['baseline']={'cells':len(recs), 'errors':d['errors'], 'elapsed_sec':d['elapsed_sec'], 'summary':d['summary'], 'probes':sum(r['budget']['probe_requests'] for r in recs), 'ours_additional':sum(r['budget']['ours_extra_requests'] for r in recs), 'extra_cells':Counter(str(r['budget']['ours_extra_requests']) for r in recs), 'positives':positive, 'positive_abstentions':sum(r['truth']=='bola' and r['methods'][ours]['abstain'] for r in recs), 'global_recall':sum(r['methods'][ours]['tp'] for r in recs)/positive}

d=load('experiments/real_system/results/gogs_real_system.json')
groups=defaultdict(Counter)
# Primary-vantage introspection vs independent ledger, snapshot only (48 cells).
# This table is an audit diagnostic, not a replacement for a full channel model.
for c in d['phaseE_cells']:
    if c['reading']!='snapshot': continue
    k=c['expected_channel']; e=c['expected_entitlement']
    if not c['introspection_readable']: o='unknown'
    elif c['introspection_status']==204: o='allow'
    elif c['introspection_status']==404: o='deny'
    else: o='unknown'
    groups[k][f'E={e},O={o}']+=1
report['gogs_groupable_existing_cells']={k:dict(v) for k,v in groups.items()}

original=load('experiments/real_system/results/cve_pair.json')
cases={'unchanged':lambda d:None,
       'missing_own_comment':lambda d:d['runs'][0].__setitem__('probes',[p for p in d['runs'][0]['probes'] if p['label']!='own_comment']),
       'restore_false':lambda d:d['runs'][0]['restore'].__setitem__('restored',False),
       'owner_state_disagrees_with_stored_Y':lambda d:d['runs'][0]['state'].__setitem__('body',d['runs'][0]['ids']['original_body']),
       'wrong_control_status':lambda d:d['runs'][0]['probes'][0].__setitem__('status',403)}
report['isolated_ingester_checks']={}
for label, mutate in cases.items():
    sandbox=OUT/'isolated_ingester'/label
    inp=sandbox/'experiments/real_system/results/cve_pair.json'
    script=sandbox/'04_绘图与分析/analysis/ingest_cve_pair.py'
    inp.parent.mkdir(parents=True,exist_ok=True)
    script.parent.mkdir(parents=True,exist_ok=True)
    (sandbox/'04_绘图与分析/results').mkdir(parents=True,exist_ok=True)
    data=copy.deepcopy(original); mutate(data)
    inp.write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
    shutil.copyfile(ROOT/'04_绘图与分析/analysis/ingest_cve_pair.py',script)
    res=subprocess.run([sys.executable,'-X','utf8',str(script)],capture_output=True,text=True,encoding='utf8')
    report['isolated_ingester_checks'][label]={'returncode':res.returncode, 'stdout':res.stdout, 'stderr':res.stderr}
    (sandbox/'execution.log').write_text(res.stdout+res.stderr,encoding='utf8')

(OUT/'evidence_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k not in ['native_mrs','native_counters']},ensure_ascii=False,indent=2))

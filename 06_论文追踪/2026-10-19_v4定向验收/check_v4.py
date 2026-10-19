"""Read-only acceptance checks. Keep committed v4 separate from live edits."""
from pathlib import Path
from io import BytesIO
from collections import Counter
import hashlib
import json
import re
import subprocess
import sys
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
GIT=r'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'

def git(*args):
    return subprocess.check_output([GIT,'-c',f'safe.directory={ROOT.as_posix()}',*args],cwd=ROOT)

REV=git('rev-parse','access-resubmission-v4^{}').decode().strip()
result={'revision':REV,'head':git('rev-parse','HEAD').decode().strip(),
        'live_worktree_status':git('status','--short').decode('utf8')}

result['committed_pdfs']={}
for label,rel in [('main','03_论文撰写/paper/main.pdf'),
                  ('letter','03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'),
                  ('highlighted','03_论文撰写/response_to_reviewers/main_highlighted.pdf')]:
    data=git('show',f'{REV}:{rel}')
    doc=PdfReader(BytesIO(data))
    result['committed_pdfs'][label]={'pages':len(doc.pages),'author_metadata':str(doc.metadata.author),
       'sha256':hashlib.sha256(data).hexdigest(),
       'Ke_on_first_page':'XIAOYU KE' in doc.pages[0].extract_text().upper(),
       'pending_contribution_in_text':any('to be confirmed' in p.extract_text() for p in doc.pages),
       'highlights':sum(str(a.get_object().get('/Subtype'))=='/Highlight' for p in doc.pages for a in p.get('/Annots',[]))}

ziprel='03_论文撰写/paper/latex_source_files_submission.zip'
data=git('show',f'{REV}:{ziprel}')
with zipfile.ZipFile(BytesIO(data)) as archive:
    names=archive.namelist()
    texts={n:archive.read(n).decode('utf8',errors='replace') for n in names if n.endswith('.tex')}
    result['committed_zip']={'files':len(names),'sha256':hashlib.sha256(data).hexdigest(),
      'bad_member':archive.testzip(),
      'Ke_in_source':any('uppercase{Xiaoyu Ke}' in t for t in texts.values()),
      'pending_contribution_in_source':[n for n,t in texts.items() if 'to be confirmed' in t]}

result['live_source']={}
for rel in ['03_论文撰写/paper/main.tex','03_论文撰写/paper/sections/10_declarations.tex',
            '03_论文撰写/response_to_reviewers/response_to_reviewers.tex']:
    live=(ROOT/rel).read_bytes(); committed=git('show',f'{REV}:{rel}')
    txt=live.decode('utf8')
    result['live_source'][rel]={'same_as_v4':live==committed,'sha256':hashlib.sha256(live).hexdigest(),
        'Ke_mentioned':'Xiaoyu Ke' in txt}

result['checks']={}
jobs=[('numbers',[sys.executable,'-X','utf8',str(ROOT/'03_论文撰写/response_to_reviewers/check_letter_numbers.py')]),
      ('refs',[r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe','-X','utf8',str(ROOT/'03_论文撰写/response_to_reviewers/check_letter_refs.py')]),
      ('pair_validation',[sys.executable,'-X','utf8',str(ROOT/'04_绘图与分析/analysis/test_cve_pair_validation.py')]),
      ('manifest_entry',[sys.executable,'-X','utf8',str(ROOT/'04_绘图与分析/analysis/make_manifests.py'),'--check'])]
for name,args in jobs:
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    result['checks'][name]={'returncode':p.returncode,'output':p.stdout+p.stderr}
    (OUT/f'{name}.log').write_text(p.stdout+p.stderr,encoding='utf8')

result['manifests']={}
for n in ['RAW_RECORDS_SHA256','OUTPUTS_SHA256']:
    rows=json.loads((ROOT/f'04_绘图与分析/provenance/{n}.json').read_text(encoding='utf8'))['files']
    result['manifests'][n]={'count':len(rows),'mismatches':[r['path'] for r in rows if not (ROOT/r['path']).is_file() or hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']]}

rows=[json.loads(l) for l in (ROOT/'experiments/results/raw_matrix.jsonl').read_text(encoding='utf8').splitlines() if l.strip()]
probe=json.loads((ROOT/'experiments/results/ablation_direct.json').read_text(encoding='utf8'))['probe_cache']
tally=Counter()
for r in rows:
    if 'error' in r:continue
    state=probe.get(r['config']['label']+'|'+r['scenario'],{}).get(r['action']['op'],'unavailable')
    if state=='unavailable':tally['abstain']+=1;continue
    truth=r['truth']['truth']=='bola';alarm=state=='none'
    tally['TP' if truth and alarm else 'FN' if truth else 'FP_binary' if alarm else 'TN']+=1
result['direct_only_recomputed']={'counts':dict(tally),'risk':(tally['FP_binary']+tally['FN'])/(len(rows)-tally['abstain'])}

(OUT/'checks.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))

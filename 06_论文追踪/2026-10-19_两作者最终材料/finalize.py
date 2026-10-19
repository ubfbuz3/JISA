"""Finalize metadata, manifests, and same-host isolated working-copy regeneration."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BUILD=OUT/'builds'
LETTER=ROOT/'03_论文撰写/response_to_reviewers'
results=json.loads((OUT/'build_results.json').read_text(encoding='utf8'))
letter_stage=Path(results['build_directories'][2])
shutil.copyfile(LETTER/'response_to_reviewers.tex',letter_stage/'response_to_reviewers.tex')
env=os.environ.copy();env['SOURCE_DATE_EPOCH']='1704067200'
env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8'
for i in range(3):
    p=subprocess.run([shutil.which('pdflatex'),'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','response_to_reviewers.tex'],cwd=letter_stage,env=env,capture_output=True,timeout=90)
    (OUT/f'letter_metadata_pass{i+1}.log').write_bytes(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError('Letter metadata rebuild failed')
doc=PdfReader(letter_stage/'response_to_reviewers.pdf')
if doc.metadata.author!='Qiulong Lin and Nanlei Chen':raise RuntimeError('Letter metadata incorrect')
shutil.copyfile(letter_stage/'response_to_reviewers.pdf',LETTER/'response_to_reviewers.pdf')

commands=[('manifests',[sys.executable,'-X','utf8',str(ROOT/'04_绘图与分析/analysis/make_manifests.py')]),
          ('manifest_check',[sys.executable,'-X','utf8',str(ROOT/'04_绘图与分析/analysis/make_manifests.py'),'--check']),
          ('numbers',[sys.executable,'-X','utf8',str(LETTER/'check_letter_numbers.py')]),
          ('references',[r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe','-X','utf8',str(LETTER/'check_letter_refs.py')])]
checks={}
for name,args in commands:
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    (OUT/f'{name}.log').write_text(p.stdout+p.stderr,encoding='utf8')
    checks[name]={'returncode':p.returncode,'output':p.stdout+p.stderr}
    if p.returncode:raise RuntimeError(f'{name} failed')

# Recompute changed working sources, not git archive HEAD (which omits edits).
stage=Path(tempfile.mkdtemp(prefix='regeneration_',dir=BUILD))
for rel in ['experiments','04_绘图与分析/analysis','01_文献调研/mstwi_artifact','refine-logs']:
    shutil.copytree(ROOT/rel,stage/rel,ignore=shutil.ignore_patterns('__pycache__'))
res=stage/'04_绘图与分析/results';res.mkdir(parents=True)
(stage/'04_绘图与分析/provenance').mkdir(parents=True)
steps=['compute_all.py','ingest_native_engine.py','ingest_gogs.py','ingest_gogs_channel.py',
       'ingest_gitlab.py','ingest_seeded.py','ingest_cve_pair.py','test_cve_pair_validation.py',
       'ingest_temporal.py','ingest_truth.py','ingest_m2_stratum.py','ingest_design.py',
       'ingest_coverage.py','ingest_baseline.py','make_diagrams.py']
analysis=stage/'04_绘图与分析/analysis'
py=r'C:/Users/Administrator/.workbuddy/binaries/python/envs/bolaexp/Scripts/python.exe'
for name in steps:
    p=subprocess.run([py,'-X','utf8',str(analysis/name)],cwd=analysis,env=env,capture_output=True,text=True,encoding='utf8',timeout=120)
    (OUT/f'regeneration_{name}.log').write_text(p.stdout+p.stderr,encoding='utf8')
    if p.returncode:raise RuntimeError(f'Isolated regeneration failed: {name}, rc={p.returncode}')
    print('Regenerated',name,flush=True)
manifest=json.loads((ROOT/'04_绘图与分析/provenance/OUTPUTS_SHA256.json').read_text(encoding='utf8'))['files']
bad=[]
for item in manifest:
    f=stage/item['path']
    if not f.is_file() or hashlib.sha256(f.read_bytes()).hexdigest()!=item['sha256']:bad.append(item['path'])
if bad:raise RuntimeError('Regenerated output mismatch: '+str(bad))

pdfs={};texts={}
for label,rel in [('main','03_论文撰写/paper/main.pdf'),
                  ('letter','03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'),
                  ('highlighted','03_论文撰写/response_to_reviewers/main_highlighted.pdf')]:
    path=ROOT/rel;d=PdfReader(path);t=[p.extract_text() for p in d.pages];texts[label]=t
    normalized=re.sub(r'-\s+','',re.sub(r'\s+',' ',' '.join(t)))
    if 'Xiaoyu Ke' in normalized or 'XIAOYU KE' in normalized or 'to be confirmed' in normalized:
        raise RuntimeError(f'Author or placeholder remains in {label}')
    if d.metadata.author!='Qiulong Lin and Nanlei Chen':raise RuntimeError(f'PDF metadata mismatch: {label}')
    pdfs[label]={'pages':len(d.pages),'author':d.metadata.author,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
if texts['main']!=texts['highlighted']:raise RuntimeError('Highlighted PDF text differs')
archive=ROOT/'03_论文撰写/paper/latex_source_files_submission.zip'
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        if name.endswith('.tex'):
            t=z.read(name).decode('utf8',errors='replace')
            if 'Xiaoyu Ke' in t or 'to be confirmed' in t:raise RuntimeError('ZIP contains old authorship')
    zip_info={'files':len(z.namelist()),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
out={'authors':['Qiulong Lin','Nanlei Chen'],'pdfs':pdfs,'source_zip':zip_info,
     'isolated_regeneration':{'outputs_matched':len(manifest),'mismatches':bad,'stage':str(stage),
          'scope':'same-host working-copy regeneration with version-pinned external MST source; no live experiments rerun'},
     'checks':checks,'git_or_remote_mutated':False}
(OUT/'final_verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('PASS:',len(manifest),'outputs byte-identical; all deliverables have two authors',flush=True)

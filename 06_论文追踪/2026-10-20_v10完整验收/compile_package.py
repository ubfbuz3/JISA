"""Compile actual submitted ZIP and response in fresh audit staging directories."""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
import pymupdf

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BUILD=OUT/'builds';BUILD.mkdir(exist_ok=True)
env=dict(os.environ,SOURCE_DATE_EPOCH='1704067200',PYTHONUTF8='1')
checks={}
for label in ['main','response_to_reviewers']:
    stage=Path(tempfile.mkdtemp(prefix=label+'_',dir=BUILD))
    if label=='main':
        with zipfile.ZipFile(ROOT/'03_论文撰写/paper/latex_source_files_submission.zip') as z:
            for n in z.namelist():
                if not (stage/n).resolve().is_relative_to(stage.resolve()):raise RuntimeError('Unsafe ZIP entry')
            z.extractall(stage)
        target=ROOT/'03_论文撰写/paper/main.pdf'
    else:
        shutil.copyfile(ROOT/'03_论文撰写/response_to_reviewers/response_to_reviewers.tex',stage/'response_to_reviewers.tex')
        for n in ['native_engine_numbers','temporal_numbers','baseline_numbers','gogs_channel_numbers','multiclass_numbers','budget_numbers']:
            shutil.copyfile(ROOT/'04_绘图与分析/results'/(n+'.tex'),stage/(n+'.tex'))
        target=ROOT/'03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'
    pdflatex=[shutil.which('pdflatex'),'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',label+'.tex']
    commands=[pdflatex]
    if label=='main':commands.append([shutil.which('bibtex'),label])
    commands += [pdflatex,pdflatex]
    for i,cmd in enumerate(commands):
        p=subprocess.run(cmd,cwd=stage,env=env,capture_output=True,timeout=120)
        (stage/f'pass{i+1}.log').write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(f'{label} pass {i+1} returned {p.returncode} (see {stage})')
    log=(stage/(label+'.log')).read_text(encoding='utf8',errors='replace')
    unresolved=re.findall(r'undefined references|Reference .* undefined|Citation .* undefined|Undefined control sequence',log)
    built=pymupdf.open(stage/(label+'.pdf'));given=pymupdf.open(target)
    match=[p.get_text() for p in built]==[p.get_text() for p in given]
    checks[label]={'stage':str(stage),'pages':len(built),'text_matches_delivered_pdf':match,'unresolved':unresolved,'overfull_lines':[s for s in log.splitlines() if 'Overfull' in s]}
    if unresolved or not match:raise RuntimeError('Compilation differs or unresolved references')
    print(label,len(built),'pages, delivered text matches, no undefined references',flush=True)
(OUT/'compile_results.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')

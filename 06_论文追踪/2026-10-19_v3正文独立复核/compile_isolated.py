"""Compile source ZIP and response in separate new workspace staging directories."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PDFLATEX=shutil.which('pdflatex')
BIBTEX=shutil.which('bibtex')
if not PDFLATEX or not BIBTEX:
    raise SystemExit('TeX executables unavailable')

def execute(args,cwd,name):
    result=subprocess.run(args,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (OUT/name).write_bytes(result.stdout)
    return result.returncode

results={}
build_root=OUT/'isolated_builds'
build_root.mkdir(exist_ok=True)
for kind in ['manuscript','response']:
    stage=Path(tempfile.mkdtemp(prefix=f'{kind}_',dir=build_root))
    if not stage.is_absolute() or not stage.is_relative_to(build_root.resolve()):
        raise RuntimeError('Unexpected staging path')
    if kind=='manuscript':
        with zipfile.ZipFile(ROOT/'03_论文撰写/paper/latex_source_files_submission.zip') as archive:
            for entry in archive.infolist():
                if not (stage/entry.filename).resolve().is_relative_to(stage.resolve()):
                    raise RuntimeError('Archive contains out-of-stage member')
            archive.extractall(stage)
        main='main'
    else:
        shutil.copyfile(ROOT/'03_论文撰写/response_to_reviewers/response_to_reviewers.tex',stage/'response_to_reviewers.tex')
        for n in ['native_engine_numbers','temporal_numbers','baseline_numbers','gogs_channel_numbers']:
            shutil.copyfile(ROOT/f'04_绘图与分析/results/{n}.tex',stage/f'{n}.tex')
        main='response_to_reviewers'
    args=[PDFLATEX,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',main+'.tex']
    codes=[execute(args,stage,f'{kind}_pass1.log')]
    if kind=='manuscript' and codes[-1]==0:
        codes.append(execute([BIBTEX,main],stage,f'{kind}_bibtex.log'))
    if codes[-1]==0:
        codes.append(execute(args,stage,f'{kind}_pass2.log'))
    if codes[-1]==0:
        codes.append(execute(args,stage,f'{kind}_pass3.log'))
    logfile=stage/(main+'.log')
    log=logfile.read_text(encoding='utf8',errors='replace') if logfile.exists() else ''
    shutil.copyfile(logfile,OUT/f'{kind}_final_tex.log') if logfile.exists() else None
    pdf=stage/(main+'.pdf')
    shipped=ROOT/('03_论文撰写/paper/main.pdf' if kind=='manuscript' else '03_论文撰写/response_to_reviewers/response_to_reviewers.pdf')
    if pdf.exists():
        reader=PdfReader(pdf)
        current=PdfReader(shipped)
        pages=len(reader.pages)
        same_text=[p.extract_text() for p in reader.pages]==[p.extract_text() for p in current.pages]
    else:
        pages=None;same_text=False
    results[kind]={'stage':str(stage),'exit_codes':codes,'pages':pages,'same_text_as_shipped':same_text,
                   'undefined_references':bool(re.search(r'undefined references|Reference .* undefined|Citation .* undefined',log)),
                   'tex_errors':[s for s in log.splitlines() if s.startswith('!')]}
    print(kind,results[kind],flush=True)
(OUT/'isolated_compile.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
# Staging directories retained for inspection. No recursive deletion performed.

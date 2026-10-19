"""Compile only committed v4 sources, irrespective of concurrent working edits."""
from pathlib import Path
from io import BytesIO
import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BUILD=OUT/'isolated_builds'
BUILD.mkdir(exist_ok=True)
GIT=r'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
REV='80d1e0750b420f7127049eae72471c6c09256ae7'

def read(rel):
    return subprocess.check_output([GIT,'-c',f'safe.directory={ROOT.as_posix()}','show',f'{REV}:{rel}'],cwd=ROOT)

results={}
for kind in ['manuscript','letter']:
    stage=Path(tempfile.mkdtemp(prefix=kind+'_',dir=BUILD))
    if kind=='manuscript':
        with zipfile.ZipFile(BytesIO(read('03_论文撰写/paper/latex_source_files_submission.zip'))) as z:
            for entry in z.infolist():
                if not (stage/entry.filename).resolve().is_relative_to(stage.resolve()):
                    raise RuntimeError('Out-of-stage archive member')
            z.extractall(stage)
        name='main';original='03_论文撰写/paper/main.pdf'
    else:
        name='response_to_reviewers';original='03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'
        (stage/(name+'.tex')).write_bytes(read('03_论文撰写/response_to_reviewers/response_to_reviewers.tex'))
        for macro in ['native_engine_numbers','temporal_numbers','baseline_numbers','gogs_channel_numbers']:
            (stage/(macro+'.tex')).write_bytes(read(f'04_绘图与分析/results/{macro}.tex'))
    args=[shutil.which('pdflatex'),'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',name+'.tex']
    codes=[]
    for i in range(3):
        p=subprocess.run(args,cwd=stage,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
        codes.append(p.returncode)
        (OUT/f'{kind}_compile_{i+1}.log').write_bytes(p.stdout)
        if p.returncode:break
        if i==0 and kind=='manuscript':
            p=subprocess.run([shutil.which('bibtex'),name],cwd=stage,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
            codes.append(p.returncode)
            (OUT/'manuscript_bibtex.log').write_bytes(p.stdout)
            if p.returncode:break
    pdf=stage/(name+'.pdf')
    log=(stage/(name+'.log')).read_text(encoding='utf8',errors='replace')
    doc=PdfReader(pdf) if pdf.exists() else None
    shipped=PdfReader(BytesIO(read(original)))
    results[kind]={'stage':str(stage),'exit_codes':codes,'pages':len(doc.pages) if doc else None,
        'same_text_as_committed_pdf':bool(doc) and [p.extract_text() for p in doc.pages]==[p.extract_text() for p in shipped.pages],
        'undefined_references':bool(re.search(r'undefined references|Reference .* undefined|Citation .* undefined',log))}
    print(kind,results[kind],flush=True)
(OUT/'committed_compile.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')

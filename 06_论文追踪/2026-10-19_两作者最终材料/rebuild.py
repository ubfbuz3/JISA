"""Build the approved two-author working sources without changing Git refs."""
from pathlib import Path
import importlib.util
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
BUILDS=OUT/'builds'
BUILDS.mkdir(exist_ok=True)
PAPER=ROOT/'03_论文撰写/paper'
LETTER=ROOT/'03_论文撰写/response_to_reviewers'
RESULTS=ROOT/'04_绘图与分析/results'
ENV=os.environ.copy()
ENV['SOURCE_DATE_EPOCH']='1704067200'
ENGINE=shutil.which('pdflatex')
BIBTEX=shutil.which('bibtex')
if not ENGINE or not BIBTEX:raise SystemExit('TeX tools unavailable')

def compile_tex(stage,name,bibliography):
    commands=[[ENGINE,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',name+'.tex']]
    if bibliography:commands.append([BIBTEX,name])
    commands.extend([[ENGINE,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error',name+'.tex']]*2)
    for i,cmd in enumerate(commands):
        p=subprocess.run(cmd,cwd=stage,env=ENV,capture_output=True,timeout=90)
        (stage/f'pass_{i+1}.stdout.log').write_bytes(p.stdout+p.stderr)
        if p.returncode:raise RuntimeError(f'Compile failed {stage}, pass {i+1}, rc={p.returncode}')
    log=(stage/(name+'.log')).read_text(encoding='utf8',errors='replace')
    if re.search(r'undefined references|Reference .* undefined|Citation .* undefined|Undefined control sequence',log):
        raise RuntimeError(f'Unresolved TeX diagnostic in {stage}')
    return PdfReader(stage/(name+'.pdf'))

def check_authors(doc,label):
    texts=[p.extract_text() for p in doc.pages]
    all_text='\n'.join(texts)
    if 'Xiaoyu Ke' in all_text or 'XIAOYU KE' in all_text or 'to be con-\nfirmed' in all_text:
        raise RuntimeError(f'Unapproved author or placeholder remains in {label}')
    if not all(n in texts[0].upper() for n in ['QIULONG LIN','NANLEI CHEN']):
        raise RuntimeError(f'Expected authors absent from {label}')
    return texts

stage=Path(tempfile.mkdtemp(prefix='main_',dir=BUILDS))
shutil.copyfile(PAPER/'main.tex',stage/'main.tex')
shutil.copyfile(PAPER/'refs.bib',stage/'refs.bib')
shutil.copytree(PAPER/'sections',stage/'sections')
shutil.copytree(ROOT/'04_绘图与分析/figures',stage/'figures')
for path in RESULTS.glob('*.tex'):shutil.copyfile(path,stage/path.name)
for path in (PAPER/'ieeeaccess').iterdir():
    if path.is_file():shutil.copyfile(path,stage/path.name)
main_doc=compile_tex(stage,'main',True)
main_text=check_authors(main_doc,'main PDF')
if main_doc.metadata.author!='Qiulong Lin and Nanlei Chen':
    raise RuntimeError('Incorrect main PDF author metadata')
shutil.copyfile(stage/'main.pdf',PAPER/'main.pdf')
print('Main manuscript:',len(main_doc.pages),'pages; two-author metadata verified',flush=True)

spec=importlib.util.spec_from_file_location('submission_packager',ROOT/'make_submission_zip.py')
packager=importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)
packager.BUILD=stage
packager.main()
package=PAPER/'latex_source_files_submission.zip'

# Compile the actual packaged sources in a second empty directory.
zip_stage=Path(tempfile.mkdtemp(prefix='zip_',dir=BUILDS))
with zipfile.ZipFile(package) as archive:
    for member in archive.infolist():
        if not (zip_stage/member.filename).resolve().is_relative_to(zip_stage.resolve()):
            raise RuntimeError('Unsafe ZIP member')
    archive.extractall(zip_stage)
zip_doc=compile_tex(zip_stage,'main',True)
zip_text=check_authors(zip_doc,'source ZIP')
if main_text!=zip_text:raise RuntimeError('ZIP compilation text differs from main manuscript')
print('Source ZIP compilation matches manuscript',flush=True)

letter_stage=Path(tempfile.mkdtemp(prefix='letter_',dir=BUILDS))
shutil.copyfile(LETTER/'response_to_reviewers.tex',letter_stage/'response_to_reviewers.tex')
for n in ['native_engine_numbers','temporal_numbers','baseline_numbers','gogs_channel_numbers']:
    shutil.copyfile(RESULTS/(n+'.tex'),letter_stage/(n+'.tex'))
letter_doc=compile_tex(letter_stage,'response_to_reviewers',False)
check_authors(letter_doc,'response letter')
shutil.copyfile(letter_stage/'response_to_reviewers.pdf',LETTER/'response_to_reviewers.pdf')
print('Response letter:',len(letter_doc.pages),'pages; two-author signature verified',flush=True)

checks={}
for name,args in [
    ('numbers',[sys.executable,'-X','utf8',str(LETTER/'check_letter_numbers.py')]),
    ('references',[r'C:/Users/Administrator/.workbuddy/binaries/python/envs/default/Scripts/python.exe','-X','utf8',str(LETTER/'check_letter_refs.py')]),
    ('pair_validation',[sys.executable,'-X','utf8',str(ROOT/'04_绘图与分析/analysis/test_cve_pair_validation.py')])]:
    p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    (OUT/(name+'.log')).write_text(p.stdout+p.stderr,encoding='utf8')
    checks[name]={'returncode':p.returncode,'output':p.stdout+p.stderr}
    if p.returncode:raise RuntimeError(f'{name} check failed. See {OUT/(name+".log")}')
print('Numerical, reference and validation checks passed',flush=True)
(OUT/'build_results.json').write_text(json.dumps({'main_pages':len(main_doc.pages),
    'letter_pages':len(letter_doc.pages),'source_zip_compilation_matches':True,
    'authors':['Qiulong Lin','Nanlei Chen'],'checks':checks,
    'build_directories':[str(stage),str(zip_stage),str(letter_stage)]},ensure_ascii=False,indent=2),encoding='utf8')

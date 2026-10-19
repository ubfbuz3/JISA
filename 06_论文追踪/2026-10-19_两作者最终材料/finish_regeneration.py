"""Resume only the diagram step after the isolated provenance-directory repair."""
from pathlib import Path
import hashlib,json,os,re,subprocess,zipfile
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
stage=(OUT/'builds/regeneration_a4msh_zk').resolve()
if not stage.is_relative_to((OUT/'builds').resolve()):raise RuntimeError('Unexpected staging path')
(stage/'04_绘图与分析/provenance').mkdir(exist_ok=True)
env=os.environ.copy();env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8'
analysis=stage/'04_绘图与分析/analysis'
p=subprocess.run([r'C:/Users/Administrator/.workbuddy/binaries/python/envs/bolaexp/Scripts/python.exe','-X','utf8',str(analysis/'make_diagrams.py')],cwd=analysis,env=env,capture_output=True,text=True,encoding='utf8',timeout=120)
(OUT/'regeneration_make_diagrams.py.log').write_text(p.stdout+p.stderr,encoding='utf8')
if p.returncode:raise RuntimeError('Diagram regeneration failed')
manifest=json.loads((ROOT/'04_绘图与分析/provenance/OUTPUTS_SHA256.json').read_text(encoding='utf8'))['files']
bad=[r['path'] for r in manifest if not (stage/r['path']).is_file() or hashlib.sha256((stage/r['path']).read_bytes()).hexdigest()!=r['sha256']]
if bad:raise RuntimeError('Output mismatch: '+str(bad))
pdfs={};texts={}
for name,rel in [('main','03_论文撰写/paper/main.pdf'),('letter','03_论文撰写/response_to_reviewers/response_to_reviewers.pdf'),('highlighted','03_论文撰写/response_to_reviewers/main_highlighted.pdf')]:
    f=ROOT/rel;d=PdfReader(f);texts[name]=[p.extract_text() for p in d.pages]
    text=re.sub(r'-\s+','',re.sub(r'\s+',' ',' '.join(texts[name])))
    if 'Xiaoyu Ke' in text or 'XIAOYU KE' in text or 'to be confirmed' in text:raise RuntimeError('Unapproved author or placeholder in '+name)
    if d.metadata.author!='Qiulong Lin and Nanlei Chen':raise RuntimeError('Wrong metadata in '+name)
    pdfs[name]={'pages':len(d.pages),'author':d.metadata.author,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
if texts['main']!=texts['highlighted']:raise RuntimeError('Clean/highlighted text differs')
archive=ROOT/'03_论文撰写/paper/latex_source_files_submission.zip'
with zipfile.ZipFile(archive) as z:
    for name in z.namelist():
        if name.endswith('.tex'):
            t=z.read(name).decode('utf8',errors='replace')
            if 'Xiaoyu Ke' in t or 'to be confirmed' in t:raise RuntimeError('ZIP authorship not updated')
    zipinfo={'files':len(z.namelist()),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}
checks={}
for name in ['numbers','references','manifest_check']:
    log=(OUT/(name+'.log')).read_text(encoding='utf8');checks[name]=log
raw=json.loads((ROOT/'04_绘图与分析/provenance/RAW_RECORDS_SHA256.json').read_text(encoding='utf8'))['files']
if any(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256'] for r in raw):raise RuntimeError('Input integrity failed')
result={'authors':['Qiulong Lin','Nanlei Chen'],'pdfs':pdfs,'source_zip':zipinfo,
        'isolated_regeneration':{'outputs_matched':len(manifest),'mismatches':bad,'stage':str(stage),'scope':'same-host working-copy regeneration with pinned external MST source; live experiments not rerun'},
        'raw_inputs_verified':len(raw),'checks':checks,'git_or_remote_mutated':False}
(OUT/'final_verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))

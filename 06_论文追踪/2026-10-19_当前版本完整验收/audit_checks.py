"""Read-only checks of the current manuscript package; writes audit evidence only."""
from pathlib import Path
import difflib
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import Counter, defaultdict
import pymupdf

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PAPER = ROOT/'03_论文撰写/paper'
LETTER = ROOT/'03_论文撰写/response_to_reviewers'
PY = Path(sys.executable)
GIT = r'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
env = dict(os.environ, PYTHONUTF8='1', PYTHONIOENCODING='utf-8')
results = {}
commands = {
    'git_head': [GIT, '-c', 'safe.directory='+ROOT.as_posix(), 'rev-parse', 'HEAD'],
    'git_status_start': [GIT, '-c', 'safe.directory='+ROOT.as_posix(), 'status', '--short'],
    'manifest_check': [str(PY), '-X', 'utf8', str(ROOT/'04_绘图与分析/analysis/make_manifests.py'), '--check'],
    'letter_numbers': [str(PY), '-X', 'utf8', str(LETTER/'check_letter_numbers.py')],
    'letter_refs': [str(PY), '-X', 'utf8', str(LETTER/'check_letter_refs.py')],
    'pair_validation': [str(PY), '-X', 'utf8', str(ROOT/'04_绘图与分析/analysis/test_cve_pair_validation.py')],
    'skill_consistency': [str(PY), '-X', 'utf8', r'C:/Users/Administrator/.codex/skills/nature-response/scripts/check_package_consistency.py', '--manuscript', str(PAPER/'main.tex'), '--response', str(LETTER/'response_to_reviewers.tex'), '--json'],
}
for name, command in commands.items():
    p = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf8', timeout=90)
    (OUT/(name+'.log')).write_text(p.stdout+p.stderr, encoding='utf8')
    results[name] = {'returncode':p.returncode, 'output':p.stdout+p.stderr}

texts = {}
for name, file in {'main':PAPER/'main.pdf', 'letter':LETTER/'response_to_reviewers.pdf', 'highlighted':LETTER/'main_highlighted.pdf', 'baseline':LETTER/'baseline/submitted_main.pdf'}.items():
    doc = pymupdf.open(file)
    texts[name] = [p.get_text() for p in doc]
    (OUT/(name+'_text.txt')).write_text('\n'.join(f'\n===== PAGE {i+1} =====\n'+t for i,t in enumerate(texts[name])), encoding='utf8')
    results[name] = {'pages':len(doc), 'author':doc.metadata.get('author'), 'sha256':hashlib.sha256(file.read_bytes()).hexdigest(), 'annotations':sum(sum(1 for _ in p.annots()) for p in doc)}
results['clean_highlighted_text_identical'] = texts['main'] == texts['highlighted']

tables = []
for i,t in enumerate(texts['main'],1):
    for m in re.finditer(r'TABLE\s+(\d+)\.\s*', t):
        tables.append({'table':int(m.group(1)), 'page':i, 'caption_start':re.sub(r'\s+', ' ',t[m.end():m.end()+240])})
results['tables'] = tables
letter = (LETTER/'response_to_reviewers.tex').read_text(encoding='utf8').split('\\begin{document}',1)[1]
results['response_structure'] = {'concerns':len(re.findall(r'\\Concern\{',letter)), 'responses':len(re.findall(r'\\Response\{',letter)), 'actions':len(re.findall(r'\\Action\{',letter))}
results['letter_table_mentions'] = [{'line':i, 'text':s.strip()} for i,s in enumerate(letter.splitlines(),1) if re.search(r'Tables?~\d',s)]
with zipfile.ZipFile(PAPER/'latex_source_files_submission.zip') as z:
    results['source_zip'] = {'members':len(z.namelist()), 'sha256':hashlib.sha256((PAPER/'latex_source_files_submission.zip').read_bytes()).hexdigest(), 'bad_crc_member':z.testzip()}
    mismatch=[]
    for p in [PAPER/'main.tex', PAPER/'refs.bib', *sorted((PAPER/'sections').glob('*.tex'))]:
        rel=p.relative_to(PAPER).as_posix()
        if rel not in z.namelist() or z.read(rel)!=p.read_bytes():mismatch.append(rel)
    results['source_zip']['source_mismatches']=mismatch

# Audit the actual highlight algorithm without editing or saving either PDF.
spec=importlib.util.spec_from_file_location('highlight_module', LETTER/'highlight_diff.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
old=pymupdf.open(LETTER/'baseline/submitted_main.pdf')
new=pymupdf.open(PAPER/'main.pdf')
old_raw=[t for _,t,_ in h.lines_of(old) if not h.is_header_footer(t)]
old_lines=[h.norm(t) for t in old_raw]
old_pool=Counter(old_lines)
index=defaultdict(list)
for i,s in enumerate(old_lines):
    for w in set(s.split()):index[w].append(i)
miss=[]; changed=0; zero_pool=[]
for pno,t,rect in h.lines_of(new):
    if h.is_header_footer(t):continue
    n=h.norm(t)
    if not n:continue
    if n in old_pool:
        if old_pool[n]<=0:zero_pool.append({'page':pno,'text':t})
        old_pool[n]-=1
        continue
    if len(n.split())>=3:
        cand=set()
        for w in set(n.split()):
            if len(index.get(w,()))<=400:cand.update(index.get(w,()))
        best=0;best_i=-1
        for i in cand:
            if abs(len(old_lines[i].split())-len(n.split()))>.5*len(n.split())+4:continue
            r=difflib.SequenceMatcher(None,n.split(),old_lines[i].split()).ratio()
            if r>best:
                best=r;best_i=i
                if best>=h.SIM:break
        if best>=h.SIM and best_i>=0 and set(n.split())==set(old_lines[best_i].split()):
            miss.append({'page':pno,'old':old_raw[best_i], 'new':t, 'similarity':best})
            old_pool[old_lines[best_i]]-=1
            continue
    changed+=1
counterexamples=[]
for a,b in [('Alice grants Bob read access to the repository','Bob grants Alice read access to the repository'),('The method is sound, conditional on a readable oracle.','The method is sound conditional on a readable oracle.'),('The result holds when x ≤ y','The result holds when x ≥ y')]:
    x,y=h.norm(a),h.norm(b)
    counterexamples.append({'old':a,'new':b,'normalizations_equal':x==y,'sets_equal':set(x.split())==set(y.split()),'similarity':difflib.SequenceMatcher(None,x.split(),y.split()).ratio()})
results['highlight_audit']={'changed_lines_recomputed':changed, 'same_token_set_changed_lines_skipped':miss, 'duplicate_old_pool_reuses':zero_pool, 'counterexamples':counterexamples, 'scope':'Current PDF misses distinguished from synthetic algorithm counterexamples.'}
results['artifact_hashes_match_previous_verification']={}
previous=json.loads((ROOT/'06_论文追踪/2026-10-19_两作者最终材料/final_verification.json').read_text(encoding='utf8'))
for label in ['main','letter','highlighted']:
    results['artifact_hashes_match_previous_verification'][label]=results[label]['sha256']==previous['pdfs'][label]['sha256']
(OUT/'checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in results.items() if k not in commands and k not in ['letter_table_mentions','tables','highlight_audit']},ensure_ascii=False,indent=2))
print('Check return codes:',{k:results[k]['returncode'] for k in commands})
print('Current skipped word-order/repetition changes:',len(miss))
print('Synthetic highlight counterexamples:',json.dumps(counterexamples,ensure_ascii=False))

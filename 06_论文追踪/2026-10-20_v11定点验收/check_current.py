"""Read-only package, record and checker audit of v10."""
from pathlib import Path
import copy,hashlib,importlib.util,json,os,re,subprocess,sys,zipfile
import pymupdf
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PAPER=ROOT/'03_论文撰写/paper';LETTER=ROOT/'03_论文撰写/response_to_reviewers'
results={};texts={}
for name,p in [('main',PAPER/'main.pdf'),('letter',LETTER/'response_to_reviewers.pdf'),('highlighted',LETTER/'main_highlighted.pdf')]:
    d=pymupdf.open(p);texts[name]=[q.get_text() for q in d]
    (OUT/(name+'_text.txt')).write_text('\n'.join(f'===== PAGE {i+1} =====\n'+t for i,t in enumerate(texts[name])),encoding='utf8')
    results[name]={'pages':len(d),'bytes':p.stat().st_size,'author':d.metadata['author'],'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'annotations':sum(sum(1 for _ in q.annots()) for q in d)}
results['text_identity']=texts['main']==texts['highlighted']
results['tables']=[{'number':int(m.group(1)),'page':i,'caption':re.sub(r'\s+',' ',t[m.end():m.end()+190])} for i,t in enumerate(texts['main'],1) for m in re.finditer(r'TABLE\s+(\d+)\.\s*',t)]
body=(LETTER/'response_to_reviewers.tex').read_text(encoding='utf8').split('\\begin{document}',1)[1]
results['response_blocks']={n:len(re.findall(r'\\'+n+r'\{',body)) for n in ['Concern','Response','Action']}
mac={}
for p in (ROOT/'04_绘图与分析/results').glob('*.tex'):
    for m in re.finditer(r'\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}',p.read_text(encoding='utf8')):mac[m.group(1)]=m.group(2)
a=re.search(r'\\begin\{abstract\}([\s\S]*?)\\end\{abstract\}',(PAPER/'main.tex').read_text(encoding='utf8')).group(1)
a=re.sub(r'\\([A-Za-z]+)\{\}',lambda m:mac.get(m.group(1),m.group(0)),a)
a=re.sub(r'\\[A-Za-z]+','',a).replace('{','').replace('}','')
results['abstract']={'words_whitespace':len(a.split()),'paragraphs':len(re.split(r'\n\s*\n',a.strip()))}
p=PAPER/'latex_source_files_submission.zip'
with zipfile.ZipFile(p) as z:
    results['zip']={'files':len(z.namelist()),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bad_crc':z.testzip(),'mismatches':[]}
    for q in [PAPER/'main.tex',PAPER/'refs.bib',*sorted((PAPER/'sections').glob('*.tex'))]:
        rel=q.relative_to(PAPER).as_posix()
        if rel not in z.namelist() or z.read(rel)!=q.read_bytes():results['zip']['mismatches'].append(rel)
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
for name,path,args in [('numbers',LETTER/'check_letter_numbers.py',[]),('references',LETTER/'check_letter_refs.py',[]),('manifests',ROOT/'04_绘图与分析/analysis/make_manifests.py',['--check']),('macros',ROOT/'04_绘图与分析/analysis/check_macro_use.py',[]),('pair_validator',ROOT/'04_绘图与分析/analysis/test_cve_pair_validation.py',[])]:
    r=subprocess.run([sys.executable,'-X','utf8',str(path),*args],env=env,cwd=ROOT,capture_output=True,text=True,encoding='utf8')
    (OUT/(name+'.log')).write_text(r.stdout+r.stderr,encoding='utf8');results[name]={'returncode':r.returncode,'output':r.stdout+r.stderr}

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
bgt=module('budget_check',ROOT/'04_绘图与分析/analysis/ingest_budget.py')
mc=module('multiclass_check',ROOT/'04_绘图与分析/analysis/ingest_multiclass.py')
b=json.loads((ROOT/'experiments/results/baseline_budget.json').read_text(encoding='utf8'))
mult=json.loads((ROOT/'experiments/real_system/results/seeded_multiclass.json').read_text(encoding='utf8'))
result_budget={}
for cap,s in b['sweeps'].items():
    cap=int(cap);rows=s['records'];fresh=bgt.cross_check(cap,s['summary'],rows)
    errors=[]
    for r in rows:
        own=r['methods']['ours_mr_v3'];bud=r['budget']
        for name,m in r['methods'].items():
            pos=r['truth']=='bola';alarm=m['alarm'];abstain=m['abstain']
            expected={'tp':pos and alarm and not abstain,'fp':not pos and alarm and not abstain,'fn':pos and not alarm and not abstain,'tn':not pos and not alarm and not abstain,'abstain':abstain}
            if any(bool(m[k])!=v for k,v in expected.items()):errors.append('score: '+name)
            cost=bud['probe_requests']+(bud['ours_extra_requests'] if name=='ours_mr_v3' else bud['reach_extra_requests'] if name=='B3r_diff_reach' else 0)
            if cost>cap:errors.append('cost: '+name)
        if own['verdict']=='pass' and (bud['oracle_read'] or bud['ours_extra_requests']):errors.append('pass read oracle')
    result_budget[str(cap)]={'records':len(rows),'summary':fresh,'per_cell_errors':errors}
results['budget']=result_budget
results['multiclass_cross_check']=mc.cross_check(mult)
results['leave_one_out_by_method']={name:{c:{meth:sum(bool(r['alarms'][meth]) for r in run['instances'] if r['class']==c) for meth in ['v3','v3_channel','direct_observe_channel']} for c in ['C1','C2','C3','C4']} for name,run in mult['runs'].items()}
checks=[]
for kind in ['budget_cache','multiclass_cache']:
    try:
        if kind=='budget_cache':
            d=copy.deepcopy(b['sweeps']['3']);d['summary']['ours_mr_v3']['tp']+=1;bgt.cross_check(3,d['summary'],d['records'])
        else:
            d=copy.deepcopy(mult);d['summary']['per_class']['C1']['mr_read']+=1;mc.cross_check(d)
        rejected=False
    except SystemExit:rejected=True
    checks.append({'perturbation':kind,'rejected':rejected})
results['summary_perturbation_checks']=checks
results['negative_denials']={ch:[{'subject':r['subject'],'object':r['object'],'status':r['probe_status'],'effect':r['effect']} for r in rows if not r['effect']] for ch,rows in mult['runs']['all']['negatives'].items()}
protocol=ROOT/'experiments/real_system/prereg/R1.4_oracle_admission_v1.md'
results['protocol_sha256']=hashlib.sha256(protocol.read_bytes()).hexdigest()
results['manifests_counts']={name:len(json.loads((ROOT/'04_绘图与分析/provenance'/name).read_text(encoding='utf8'))['files']) for name in ['RAW_RECORDS_SHA256.json','OUTPUTS_SHA256.json']}
(OUT/'checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
print('PDF pages:',{k:results[k]['pages'] for k in ['main','letter','highlighted']})
print('Author metadata:',results['main']['author']);print('ZIP',results['zip'])
print('Abstract',results['abstract']);print('Reply blocks',results['response_blocks'])
print('Check codes',{k:results[k]['returncode'] for k in ['numbers','references','manifests','macros','pair_validator']})
print('Cap 2',result_budget['2']['summary']['ours_mr_v3']);print('Cap 3',result_budget['3']['summary']['ours_mr_v3'])
print('Negatives',results['multiclass_cross_check'][1]);print('Mutation checks',checks)

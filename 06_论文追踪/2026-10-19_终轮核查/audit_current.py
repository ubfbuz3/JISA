"""Read-only review checks; regeneration is isolated under this audit folder."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def read(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    result = {'source_revision': '36090b7', 'live_experiments_rerun': False}
    matrix=[json.loads(s) for s in (ROOT/'experiments/results/raw_matrix.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    cells=Counter((r['config']['label'],r['scenario']) for r in matrix)
    result['synthetic']={'records':len(matrix), 'design_cells':len(cells), 'records_per_cell':dict(Counter(cells.values())), 'gui_modes':dict(Counter(r['gui_mode'] for r in matrix))}
    representative=[r for r in matrix if r['config']['mode']=='e3' and r['precond_variant']=='raw' and r['gui_mode']=='aware']
    original=[r for r in representative if r['scenario'] in ('S3','S4','S5','S6','S7')]
    reconciliation=[r for r in representative if r['scenario'] in ('S1','S2','S3','S4','S5')]
    rid=lambda r:(r['config']['label'],r['scenario'],r['mr'],r['precond_variant'],r['gui_mode'])
    oa,ob=set(map(rid,original)),set(map(rid,reconciliation))
    result['representative_reconciliation']={'original_n':len(original),'reconciliation_n':len(reconciliation),'shared':len(oa&ob),'only_original':len(oa-ob),'only_new':len(ob-oa),'original_v2_false_proofs':sum(r['truth']['truth']=='normal' and r['verdicts']['v2']['verdict']=='violation-proven' for r in original),'new_v2_false_proofs':sum(r['truth']['truth']=='normal' and r['verdicts']['v2']['verdict']=='violation-proven' for r in reconciliation)}
    probe=read('experiments/results/ablation_direct.json')['probe_cache']
    pair_diff=[]
    for r in matrix:
        s=probe.get(f"{r['config']['label']}|{r['scenario']}",{}).get(r['action']['op'],'unavailable')
        v3=r['verdicts']['v3']['verdict']=='violation-proven'
        d=s=='none' and r['truth']['app_allowed']
        if v3 != d:
            pair_diff.append({k:r[k] for k in ('scenario','mr','gui_mode','precond_variant','truth')})
    result['v3_direct_differences']=pair_diff
    result['direct_semantics']={'unreadable_rows':sum(probe.get(f"{r['config']['label']}|{r['scenario']}",{}).get(r['action']['op'],'unavailable')=='unavailable' for r in matrix)}
    result['direct_semantics']['coverage_if_unreadable_is_abstention']=(len(matrix)-result['direct_semantics']['unreadable_rows'])/len(matrix)
    result['equality_counterexamples']=[{'y':y,'m':m,'o':o,'A':int(y and not m),'D':int(y and not o)} for y in (0,1) for m in (0,1) for o in (0,1) if ((bool(y and not m)==bool(y and not o)) != (m==o))]
    temporal={}
    for name in ('gitea','gitlab'):
        d=read(f'experiments/real_system/results/temporal/temporal_{name}.json')
        rows=[c for t in d['transitions'] for c in t['cells'] if c['role']=='cross' and c.get('abstain_reason') is None]
        recalc={'cells':len(rows),'E_eq_Y':sum((c['expected_entitlement']=='allow')==(c['observed_effect']=='allow') for c in rows),
                'stale_false_proofs':sum(c['H_stale'] and c['expected_entitlement']=='allow' for c in rows),
                'live_false_proofs':sum(c['H_live'] and c['expected_entitlement']=='allow' for c in rows),
                'recrawl_fixed':sum(c['stale_missing_legit'] and not c['live_missing_legit'] for c in rows),
                'true_positives':sum(c['H_live'] and c['expected_entitlement']=='deny' and c['observed_effect']=='allow' for c in rows)}
        snapshots=[]
        for t in d['transitions']:
            for typ in ('M0','M1'):
                desc=t[typ]
                path=ROOT/'experiments/real_system/results/temporal'/Path(desc['file']).name
                snapshots.append({'file':path.name,'exists':path.exists(),'matches':path.exists() and sha(path)==desc['sha256']})
        temporal[name]={'stored_totals':d['totals'],'recomputed':recalc,'mismatched_totals':{k:[v,d['totals'][k]] for k,v in recalc.items() if d['totals'][k]!=v},'snapshot_checks':snapshots,'base_protocol_hash_matches':sha(ROOT/'experiments/real_system/c_protocol.json')==d['meta']['protocol_sha256']}
    result['temporal']=temporal
    gl=read('experiments/real_system/results/temporal/temporal_gitlab.json')
    result['protocol_chronology']={'gitlab_first_freeze':gl['transitions'][0]['t_freeze'],'gitlab_last_probe':gl['transitions'][-1]['t_probe'], 'amendments':[]}
    for i,filename in enumerate(('c_protocol_amendment_a1.json','c_protocol_amendment_a2.json')):
        p=ROOT/'experiments/real_system'/filename
        d=json.loads(p.read_text(encoding='utf-8'))
        result['protocol_chronology']['amendments'].append({'file':filename,'written_at':d['written_at'],'hash_matches_run':sha(p)==gl['meta']['amendment_sha256'][i]})
    result['native_split']=read('experiments/native_engine/results/native_split.json')['counts']
    pair=read('experiments/real_system/results/cve_pair.json')
    result['real_pair']=[{'version':r['version'],'E':r['main']['E_object'],'Y':r['main']['Y_allow'],'category':r['main']['category'],'owner_read_status':r['state']['status'],'restored':r['restore']['restored']} for r in pair['runs']]
    manifests=[]
    for n in ('RAW_RECORDS_SHA256.json','OUTPUTS_SHA256.json'):
        d=read('04_绘图与分析/provenance/'+n)['files']
        manifests.append({'manifest':n,'entries':len(d),'missing':[x['path'] for x in d if not (ROOT/x['path']).exists()],'mismatched':[x['path'] for x in d if (ROOT/x['path']).exists() and sha(ROOT/x['path'])!=x['sha256']]})
    result['manifests']=manifests
    zpath=ROOT/'03_论文撰写/paper/latex_source_files_submission.zip'
    with zipfile.ZipFile(zpath) as z:
        differences=[]
        for name in z.namelist():
            src=None
            if name=='main.tex' or name.startswith('sections/'):
                src=ROOT/'03_论文撰写/paper'/name
            elif name.endswith('.tex') and '/' not in name:
                src=ROOT/'04_绘图与分析/results'/name
            if src and src.is_file() and z.read(name)!=src.read_bytes():differences.append(name)
        result['submission_zip']={'entries':len(z.namelist()),'source_differences':differences}
    from pypdf import PdfReader
    pdf=PdfReader(ROOT/'03_论文撰写/paper/main.pdf')
    result['pdf']={'pages':len(pdf.pages),'title':pdf.metadata.title}
    (OUT/'pdf_text.txt').write_text('\n\n'.join(f'PAGE {i+1}\n'+p.extract_text() for i,p in enumerate(pdf.pages)),encoding='utf-8')
    # Re-run five self-contained ingests in a minimal isolated mirror.
    mirror=OUT/'recompute_copy'
    for sub in ('04_绘图与分析/analysis','04_绘图与分析/results','experiments/results','experiments/real_system/results/temporal'):
        (mirror/sub).mkdir(parents=True,exist_ok=True)
    inputs=['experiments/results/raw_matrix.jsonl','experiments/results/ablation_direct.json',
            'experiments/real_system/results/cve_pair.json','experiments/real_system/results/temporal/temporal_gitea.json',
            'experiments/real_system/results/temporal/temporal_gitlab.json']
    for f in inputs:shutil.copy2(ROOT/f,mirror/f)
    for p in (ROOT/'04_绘图与分析/results').glob('*.tex'):shutil.copy2(p,mirror/'04_绘图与分析/results'/p.name)
    regen=[]
    for script in ('ingest_truth.py','ingest_design.py','ingest_coverage.py','ingest_temporal.py','ingest_cve_pair.py'):
        relative='04_绘图与分析/analysis/'+script
        shutil.copy2(ROOT/relative,mirror/relative)
        p=subprocess.run([sys.executable,'-X','utf8',str(mirror/relative)],capture_output=True,text=True,encoding='utf-8',timeout=60)
        (OUT/(script+'.log')).write_text(p.stdout+p.stderr,encoding='utf-8')
        regen.append({'script':script,'exit_code':p.returncode})
    differences=[]
    for p in (mirror/'04_绘图与分析/results').glob('*.tex'):
        original=ROOT/'04_绘图与分析/results'/p.name
        if original.exists() and p.read_bytes()!=original.read_bytes():differences.append(p.name)
    result['isolated_ingests']=regen
    result['regenerated_tex_differences']=differences
    script=(ROOT/'reproduce.sh').read_text(encoding='utf-8')
    result['reproduce_missing_ingests']=[s for s in ('ingest_design.py','ingest_coverage.py','ingest_m2_stratum.py') if s not in script]
    (OUT/'audit_evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'matrix':result['synthetic'],'paired_differences':len(pair_diff),'temporal':{k:v['recomputed'] for k,v in temporal.items()},'manifests':manifests,'pdf':result['pdf'],'zip':result['submission_zip'],'isolated_ingests':regen,'regenerated_tex_differences':differences,'reproduce_missing_ingests':result['reproduce_missing_ingests']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()

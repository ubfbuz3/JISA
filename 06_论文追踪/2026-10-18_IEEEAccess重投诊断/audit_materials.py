"""Read-only audit of supplied manuscript evidence; writes only beside this script."""
from pathlib import Path
import json
from collections import Counter, defaultdict
import zipfile
import xml.etree.ElementTree as ET
import hashlib
import csv

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent

def read_json(relative):
    return json.loads((ROOT / relative).read_text(encoding='utf-8'))

def counts(records, method):
    return dict(Counter(r['verdicts'][method]['verdict'] for r in records))

def main():
    records = [json.loads(x) for x in (ROOT/'experiments/results/raw_matrix.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    valid = [r for r in records if 'error' not in r]
    probes = read_json('experiments/results/ablation_direct.json')['probe_cache']
    configs = {}
    config_scenario = Counter()
    strata = defaultdict(list)
    disagreements = []
    for r in valid:
        label = r['config']['label']
        configs[label] = r['config']
        config_scenario[(label,r['scenario'])] += 1
        state = probes.get(f"{label}|{r['scenario']}",{}).get(r['action']['op'],'unavailable')
        strata['readable' if state != 'unavailable' else 'unreadable'].append(r)
        v3 = r['verdicts']['v3']['verdict'] == 'violation-proven'
        direct = state == 'none' and r['truth']['app_allowed']
        if v3 != direct:
            disagreements.append({k:r[k] for k in ('config','scenario','mr','gui_mode','precond_variant','truth','mr_result','verdicts')})
    selective = {}
    for name, rs in [('all', valid), *strata.items()]:
        n = len(rs)
        vc = counts(rs,'v3')
        decided = [r for r in rs if r['verdicts']['v3']['verdict'] != 'indeterminate']
        errors = sum((r['verdicts']['v3']['verdict']=='violation-proven') != (r['truth']['truth']=='bola') for r in decided)
        selective[name] = {'n':n, 'truth_counts':dict(Counter(r['truth']['truth'] for r in rs)), 'verdict_counts':vc,
                           'coverage_if_pass_is_negative':len(decided)/n,
                           'selective_risk_if_pass_is_negative': errors/len(decided) if decided else None,
                           'unknown_oracle_abstentions': sum(r['verdicts']['v3'].get('witness',{}).get('sut_introspection')=='unavailable' for r in rs if r['verdicts']['v3'].get('witness')),
                           'legitimate_covering_abstentions': sum(bool(r['verdicts']['v3'].get('witness',{}).get('share_records')) for r in rs if r['verdicts']['v3'].get('witness'))}
    native = read_json('experiments/native_engine/results/native_engine.json')
    native_summary = {'top_keys':list(native), 'elapsed_s':native.get('elapsed_s')}
    for k,v in native.items():
        if isinstance(v,list) and len(v)<30 and k!='log_tail': native_summary[k]=v
        elif isinstance(v,dict): native_summary[k+'_keys']=list(v)
    reals = {}
    for fn in ('real_system.json','gogs_real_system.json','gitlab_real_system.json','seeded.json'):
        d=read_json('experiments/real_system/results/'+fn)
        summary={'keys':list(d)}
        cells=d.get('phaseE_cells',[])
        summary['cells']=len(cells)
        summary['cell_keys']=list(cells[0]) if cells else []
        if 'meta' in d: summary['meta']=d['meta']
        if 'M6_provenance' in d: summary['channels']=dict(Counter(x.get('channel') for x in d['M6_provenance']))
        for key in ('seeded_bola','seeds','seed_list','positive_control','seeded_truth','seeded_bfla'):
            if key in d: summary[key]=d[key]
        reals[fn]=summary
    result={'records':len(records), 'errors':len(records)-len(valid), 'configs':list(configs.values()),
            'design_cells':len(config_scenario),'config_scenario_counts':[{'config':c,'scenario':s,'n':n} for (c,s),n in sorted(config_scenario.items())],
            'factor_counts':{k:dict(Counter(r[k] for r in valid)) for k in ('scenario','mr','gui_mode','precond_variant')},
            'selective_metrics':selective,'v3_vs_direct_disagreements':len(disagreements),
            'ablation':read_json('experiments/results/ablation_direct_observe.json'),
            'native':native_summary,'real_systems':reals,
            'request_count_caveat':'http_requests is a shared run total including setup and several adjudicators, not a matched per-method cost.'}
    (OUT/'evidence_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'v3_direct_disagreements.json').write_text(json.dumps(disagreements,ensure_ascii=False,indent=2),encoding='utf-8')
    for p in (OUT/'编辑部附件').glob('*.docx'):
        with zipfile.ZipFile(p) as z:
            xml=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        lines=[''.join(t.text or '' for t in para.findall('.//w:t',ns)) for para in xml.findall('.//w:p',ns)]
        p.with_suffix('.extracted.txt').write_text('\n'.join(lines),encoding='utf-8')
    files=['03_论文撰写/paper/main.tex','03_论文撰写/paper/main.pdf','experiments/results/raw_matrix.jsonl','experiments/boundary_aware.py','experiments/run_matrix.py','experiments/real_system/run_real.py']
    hashes={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files}
    (OUT/'inspected_source_sha256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2),encoding='utf-8')
    hash_checks=[]
    for name in ('RAW_RECORDS_SHA256.json','OUTPUTS_SHA256.json'):
        manifest=read_json('04_绘图与分析/provenance/'+name)['files']
        hash_checks.append({'manifest':name,'n':len(manifest),
                            'missing':[x['path'] for x in manifest if not (ROOT/x['path']).exists()],
                            'mismatched':[x['path'] for x in manifest if (ROOT/x['path']).exists() and hashlib.sha256((ROOT/x['path']).read_bytes()).hexdigest()!=x['sha256']]})
    (OUT/'hash_check.json').write_text(json.dumps(hash_checks,ensure_ascii=False,indent=2),encoding='utf-8')
    report=(OUT/'修改判断与执行方案.md').read_text(encoding='utf-8')
    rows=[]
    for line in report.splitlines():
        parts=[x.strip() for x in line.strip().strip('|').split('|')]
        if len(parts)==4 and parts[0].startswith(('R1.','R2.')):
            item, action, location, rerun=parts
            rows.append({'id':item.split()[0],'concern':item,'severity':'major','proposed_action':action,'work_status':'PROPOSED_NOT_IMPLEMENTED','required_input_or_work':rerun,'expected_output':location,'blocks_finalization':'yes','audience':'internal/editor only'})
    assert len(rows)==21, len(rows)
    with (OUT/'reviewer_tracker.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
    print(json.dumps({'records':len(records),'errors':result['errors'],'design_cells':len(config_scenario), 'factor_counts':result['factor_counts'], 'selective':selective,'ablation':result['ablation']['tally'], 'disagreements':len(disagreements),'native':native_summary},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()

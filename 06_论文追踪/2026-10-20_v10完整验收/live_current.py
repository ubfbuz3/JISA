"""Fresh controlled runs; do not alter submitted records."""
from pathlib import Path
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
RS=ROOT/'experiments/real_system'
sys.path.insert(0,str(RS))
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
mc=module('audited_current_multiclass',RS/'run_multiclass.py')
mc.RESULTS=OUT/'builds/live_multiclass';mc.RESULTS.mkdir(parents=True,exist_ok=True)
mc.BASE_PORT=13431
counter={'n':0};crawl_cost=[]
original_req=mc.R.L.Client.req if hasattr(mc.R,'L') else None
# Client is imported by the target and runner from the same module.
import gitea_lab
original_req=gitea_lab.Client.req
def req(self,*args,**kwargs):
    counter['n']+=1
    return original_req(self,*args,**kwargs)
gitea_lab.Client.req=req
original_crawl=mc.R.crawl
def crawl(*args,**kwargs):
    before=counter['n'];result=original_crawl(*args,**kwargs)
    crawl_cost.append({'client':getattr(args[0],'label','?'),'requests':counter['n']-before,'objects':len(result['urls'])})
    return result
mc.R.crawl=crawl
mc.main()
new=json.loads((mc.RESULTS/'seeded_multiclass.json').read_text(encoding='utf8'))
old=json.loads((RS/'results/seeded_multiclass.json').read_text(encoding='utf8'))
assert new['summary']==old['summary'],'multiclass summary differs'
(OUT/'live_crawl_requests.json').write_text(json.dumps(crawl_cost,indent=2),encoding='utf8')
print('LIVE MULTICLASS SUMMARY MATCH',flush=True)
sys.path.insert(0,str(ROOT/'experiments'))
bl=module('audited_current_baseline',ROOT/'experiments/run_baseline.py')
bl.RESULTS=OUT/'builds/live_budget';bl.RESULTS.mkdir(parents=True,exist_ok=True)
budget=bl.run_budget_sweep()
oldb=json.loads((ROOT/'experiments/results/baseline_budget.json').read_text(encoding='utf8'))
for cap in ['2','3']:
    assert budget['sweeps'][cap]['errors']==0
    assert budget['sweeps'][cap]['summary']==oldb['sweeps'][cap]['summary'],cap
print('LIVE BUDGET BOTH SUMMARIES MATCH',flush=True)
(OUT/'live_results.json').write_text(json.dumps({'multiclass_summary_match':True,'budget_caps_2_3_match':True,'budget_records':84,'crawl_costs':crawl_cost},indent=2),encoding='utf8')

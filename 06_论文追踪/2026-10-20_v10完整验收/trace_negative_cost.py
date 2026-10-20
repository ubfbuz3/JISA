"""Count actual HTTP calls in each negative-control block, audit output only."""
from pathlib import Path
import importlib.util,sys,json
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/real_system'))
spec=importlib.util.spec_from_file_location('cost_audit_mc',ROOT/'experiments/real_system/run_multiclass.py')
mc=importlib.util.module_from_spec(spec);spec.loader.exec_module(mc)
import gitea_lab
orig=gitea_lab.Client.req
calls={'read':[],'write':[],'grant':[],'grant_shared_crawl':[]}
def req(self,method,path,*args,**kwargs):
    f=sys._getframe(1)
    while f:
        if f.f_code.co_name=='_measure' and f.f_code.co_filename==str(ROOT/'experiments/real_system/run_multiclass.py'):
            line=f.f_lineno
            ch='read' if 211<=line<=239 else 'write' if 240<=line<=266 else 'grant' if 267<=line<=293 else 'grant_shared_crawl' if line==294 else None
            if ch:calls[ch].append({'method':method,'path':path,'caller_line':line})
            break
        f=f.f_back
    return orig(self,method,path,*args,**kwargs)
gitea_lab.Client.req=req
srv,clients,_=mc._setup(13531,{'C1','C2','C3','C4'})
try:result=mc._measure(13531,clients,{'C1','C2','C3','C4'})
finally:srv.shutdown();srv.server_close()
summary={ch:len(rows) for ch,rows in calls.items()}
assert summary=={'read':69,'write':64,'grant':21,'grant_shared_crawl':21},summary
(OUT/'negative_cost_trace.json').write_text(json.dumps({'actual_http_counts':summary,'recorded_counts':mc._summarise({'all':result,**{f'without_{c}':result for c in ['C1','C2','C3','C4']}})['negatives'],'calls':calls},indent=2),encoding='utf8')
print(json.dumps(summary))

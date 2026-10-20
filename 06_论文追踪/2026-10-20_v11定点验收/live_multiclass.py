"""Fresh v11 controlled runs; archived inputs stay unchanged."""
from pathlib import Path
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/real_system'))
spec=importlib.util.spec_from_file_location('v11_live_multiclass',ROOT/'experiments/real_system/run_multiclass.py')
mc=importlib.util.module_from_spec(spec);spec.loader.exec_module(mc)
mc.RESULTS=OUT/'builds/live_multiclass';mc.RESULTS.mkdir(parents=True,exist_ok=True)
mc.BASE_PORT=13631
mc.main()
fresh=json.loads((mc.RESULTS/'seeded_multiclass.json').read_text(encoding='utf8'))
old=json.loads((ROOT/'experiments/real_system/results/seeded_multiclass.json').read_text(encoding='utf8'))
assert fresh['summary']==old['summary']
actual=fresh['summary']['negatives']
assert [actual[ch]['requests'] for ch in ['read','write','grant']]==[69,64,42]
assert actual['grant']['shared_requests']==21
(OUT/'live_results.json').write_text(json.dumps({'fresh_summary_matches':True,'negatives':actual,'leave_one_out_by_method':fresh['summary']['leave_one_out_by_method']},ensure_ascii=False,indent=2),encoding='utf8')
print('PASS: all five runs match; negative costs 69/64/42, shared crawl 21',flush=True)

"""Rerun the controlled target and reproduce cap=2 semantics, saving audit data only."""
from pathlib import Path
import importlib.util
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
RS=ROOT/'experiments/real_system'
sys.path.insert(0,str(RS))
spec=importlib.util.spec_from_file_location('audited_multiclass',RS/'run_multiclass.py')
mc=importlib.util.module_from_spec(spec);spec.loader.exec_module(mc)
mc.RESULTS=OUT/'builds/multiclass';mc.RESULTS.mkdir(parents=True,exist_ok=True)
mc.BASE_PORT=13331
mc.main()
new=json.loads((mc.RESULTS/'seeded_multiclass.json').read_text(encoding='utf8'))
old=json.loads((RS/'results/seeded_multiclass.json').read_text(encoding='utf8'))
assert new['summary']==old['summary'],'multiclass summary changed'

sys.path.insert(0,str(ROOT/'experiments'))
spec=importlib.util.spec_from_file_location('audited_baseline',ROOT/'experiments/run_baseline.py')
bl=importlib.util.module_from_spec(spec);spec.loader.exec_module(bl)
cfg=bl.BASE_CONFIGS[0]
cap_two=bl.run_cell(cfg,'S1',budget_cap=2)
normal=bl.run_cell(cfg,'S1',budget_cap=None)
case={'config':cfg.as_dict(),'scenario':'S1',
      'cap_two':cap_two,'original_method':normal,
      'finding':'Identical non-triggering case is pass in the original method but forced indeterminate by the cap=2 wrapper.'}
(OUT/'cap_two_semantics.json').write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf8')
assert normal['methods']['ours_mr_v3']['verdict']=='pass'
assert cap_two['methods']['ours_mr_v3']['verdict']=='indeterminate'
print('Verified: non-triggering S1 is pass normally, forced abstain at cap=2',flush=True)
print('Multiclass live rerun summary matches archived results',flush=True)

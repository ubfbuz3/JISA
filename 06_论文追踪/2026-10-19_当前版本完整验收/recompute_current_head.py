"""Regenerate outputs from a read-only git archive of the audited HEAD."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
BUILD=OUT/'builds';BUILD.mkdir(exist_ok=True)
GIT=r'C:/Users/Administrator/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/git/cmd/git.exe'
PY=r'C:/Users/Administrator/.workbuddy/binaries/python/envs/bolaexp/Scripts/python.exe'
archive=BUILD/'head.zip'
subprocess.run([GIT,'-c','safe.directory='+ROOT.as_posix(),'archive','--format=zip','--output='+str(archive),'HEAD','experiments','04_绘图与分析/analysis','04_绘图与分析/provenance','01_文献调研/mstwi_artifact','refine-logs'],cwd=ROOT,check=True,capture_output=True)
stage=Path(tempfile.mkdtemp(prefix='head_',dir=BUILD))
with zipfile.ZipFile(archive) as z:z.extractall(stage)
manifest=json.loads((ROOT/'04_绘图与分析/provenance/OUTPUTS_SHA256.json').read_text(encoding='utf8'))['files']
for item in manifest:
    p=stage/item['path']
    if p.is_file():p.unlink()
(stage/'04_绘图与分析/results').mkdir(exist_ok=True)
env=dict(os.environ,PYTHONUTF8='1',PYTHONIOENCODING='utf-8')
steps=['compute_all.py','ingest_native_engine.py','ingest_gogs.py','ingest_gogs_channel.py','ingest_gitlab.py','ingest_seeded.py','ingest_cve_pair.py','test_cve_pair_validation.py','ingest_temporal.py','ingest_truth.py','ingest_m2_stratum.py','ingest_design.py','ingest_coverage.py','ingest_baseline.py','make_diagrams.py']
checks=[]
for name in steps:
    p=subprocess.run([PY,'-X','utf8',name],cwd=stage/'04_绘图与分析/analysis',env=env,capture_output=True,text=True,encoding='utf8',timeout=150)
    (OUT/('recompute_'+name+'.log')).write_text(p.stdout+p.stderr,encoding='utf8')
    checks.append({'step':name,'returncode':p.returncode})
    print(name,p.returncode,flush=True)
    if p.returncode:raise RuntimeError(name+' failed')
bad=[]
for item in manifest:
    p=stage/item['path']
    if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=item['sha256']:bad.append(item['path'])
result={'stage':str(stage),'checks':checks,'outputs':len(manifest),'mismatches':bad,'scope':'same-host regeneration from committed tree, with the pinned external MST source dependency; no live system rerun'}
(OUT/'regeneration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
if bad:raise RuntimeError(str(bad))
print('PASS',len(manifest),'byte-identical outputs',flush=True)

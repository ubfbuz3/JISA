"""
受控脆弱性靶机 · 阳性对照实验驱动器
====================================
复用 run_real.py 的**拓扑构建 / 带外变更 / 爬取 / 自省 / 裁决**代码（直接 import），
只把被测端点从真实 Gitea 换成 seeded_target.py 这个受控靶机，并加上**已知真值**
（SEED_FLAWS）来算 TP / FN / FP。这样检测器在"真有越权时能否检出"这一逻辑被公平
测量，且不引入任何新的判定公式（与真实系统实验同代码路径）。

测量项（与论文一致）：
  M5 方法对照：mr_bookkeeping / v3(自省) / direct_only / direct_observe
  + 阳性对照指标：对已知植入缺陷的 TP / FN / FP（每个方法各算一套）

用法：python run_seeded.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import run_real as R                       # 复用拓扑/变更/爬取/自省代码
import seeded_target as ST

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
PORT = int(__import__("os").environ.get("SEED_PORT", "3319"))
BASE = f"http://127.0.0.1:{PORT}"

ADMIN_USER = R.ADMIN_USER
OBJ_CREDENTIAL = R.OBJ_CREDENTIAL
ALL_OBJS = R.ALL_OBJS
USERS = R.USERS
ORG = R.ORG
PASS = R.PASS


# --------------------------------------------------------------------------
# 极简 HTTP 客户端（与 gitea_lab.Client 同契约：get/post/put/patch -> (st, body)）
# --------------------------------------------------------------------------
class Client:
    def __init__(self, user=None, password=None, label="anonymous"):
        self.label = label
        self._hdr = {"Accept": "application/json", "Content-Type": "application/json"}
        if user is not None and password is not None:
            import base64
            raw = base64.b64encode(f"{user}:{password}".encode()).decode()
            self._hdr["Authorization"] = f"Basic {raw}"

    def req(self, method, path, body=None, timeout=25):
        url = BASE + path
        data = json.dumps(body).encode() if body is not None else None
        r = Request(url, data=data, method=method, headers=dict(self._hdr))
        try:
            with urlopen(r, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return resp.status, _mj(raw)
        except Exception as e:                       # noqa: BLE001
            code = getattr(e, "code", 0)
            return code, {}

    def get(self, p, **k):
        return self.req("GET", p, **k)

    def post(self, p, body=None, **k):
        return self.req("POST", p, body, **k)

    def put(self, p, body=None, **k):
        return self.req("PUT", p, body, **k)

    def patch(self, p, body=None, **k):
        return self.req("PATCH", p, body, **k)


def _mj(raw):
    s = raw.strip()
    if s.startswith(("{", "[")):
        try:
            return json.loads(s)
        except Exception:
            return {"_raw": s[:200]}
    return s[:200]


def clients():
    out = {"anonymous": Client()}
    out[ADMIN_USER] = Client(user=ADMIN_USER, password="AdminPass123!", label=ADMIN_USER)
    for u in USERS:
        out[u] = Client(user=u, password=PASS, label=u)
    return out


# --------------------------------------------------------------------------
# 主流程
# --------------------------------------------------------------------------
def main():
    t0 = time.time()
    srv = ST.make_server(PORT)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    time.sleep(1.0)

    cl = clients()
    rep = {"meta": {
        "experiment": "seeded vulnerable control (positive control)",
        "target": "seeded_target.py (faithful Gitea API emulator, NOT production Gitea)",
        "gitea_version_emulated": ST.GITEA_VERSION,
        "reused_code": "experiments/real_system/run_real.py (topology/mutation/crawl/introspection/adjudication)",
        "honesty_boundary": (
            "靶机复刻的是引擎实际消费的 API 契约；检测器在'真有越权时能否检出'被公平测量；"
            "不声称能发现 Gitea 真实 CVE。植入缺陷只影响运行期读/写绕过，列表/搜索/自省走正确模型。"),
    }}

    try:
        # ---- 阶段 A：拓扑（复用 run_real.phaseA_topology） ----
        print("[A] 拓扑构建 …", flush=True)
        rep["phaseA_topology"] = R.phaseA_topology(cl)
        # ---- 阶段 C：带外变更（复用 run_real.phaseC_mutations 的真实调用） ----
        team_ids = rep["phaseA_topology"]["team_ids"]
        print("[C] 带外授权变更 …", flush=True)
        rep["phaseC_mutations"] = R.phaseC_mutations(cl, team_ids)

        # ---- 阶段 B/D：爬取快照（复用 run_real.crawl） ----
        print("[B/D] 爬取 …", flush=True)
        snap = {u: R.crawl(c, [ORG]) for u, c in cl.items()}

        # ---- 阶段 E：四方法裁决（复用 run_real 的单元格公式） ----
        print("[E] 裁决 …", flush=True)
        acting = {}
        for obj in ALL_OBJS:
            o, n = obj.split("/")
            st, b = cl[OBJ_CREDENTIAL[obj]].get(f"/api/v1/repos/{o}/{n}")
            acting[obj] = {"granted": st == 200,
                           "out": R._norm_repo(b) if isinstance(b, dict) else None}
        subjects = list(USERS) + [ADMIN_USER]
        truth_map = {}
        cells = []
        for obj in ALL_OBJS:
            o, n = obj.split("/")
            for subj in subjects:
                if subj == OBJ_CREDENTIAL[obj]:
                    continue
                st, b = cl[subj].get(f"/api/v1/repos/{o}/{n}")
                granted = st == 200
                out_subj = R._norm_repo(b) if isinstance(b, dict) else None
                truth_map[f"{obj}|{subj}"] = granted
                can_snap = obj not in set(snap[subj]["urls"])
                out_equal = bool(granted and acting[obj]["granted"]
                                and out_subj == acting[obj]["out"])
                ins = R.introspect(cl, obj, subj)
                ins_self = R.introspect_self(cl, obj, subj)
                log_has = subj in R.FRAMEWORK_LOG.get(obj, {})
                fires = can_snap and (subj != ADMIN_USER) and out_equal
                cells.append({
                    "object": obj, "subject": subj,
                    "cannotReachThroughGUI": can_snap,
                    "output_equal": out_equal, "mr_fires": fires,
                    "framework_log_has_record": log_has,
                    "introspection_status": ins["status"],
                    "introspection_permission": ins["permission"],
                    "introspection_readable": ins["readable"],
                    "introspection_says_none": ins["says_none"],
                    "authorized": granted,
                    "alarms": {
                        "mr_bookkeeping": fires and not log_has,
                        "v3": fires and ins["readable"] and ins["says_none"],
                        "v3_self": fires and ins_self["readable"] and ins_self["says_none"],
                        "direct_only": ins["readable"] and ins["says_none"],
                        "direct_observe": (ins["readable"] and ins["says_none"] and granted),
                        "direct_observe_self": (ins_self["readable"] and ins_self["says_none"]
                                                and granted),
                    },
                })
        for c_ in cells:
            c_["false_proofs"] = {m: bool(c_["alarms"][m] and c_["authorized"])
                                 for m in c_["alarms"]}
        rep["phaseE_cells"] = cells

        # ---- 阳性对照：已知真值 → TP / FN / FP ----
        seeded_bola = {(s, o) for (k, s, o) in ST.SEED_FLAWS if k == "BOLA"}
        rep["seeded_truth"] = {"bola": [list(x) for x in sorted(seeded_bola)],
                               "bfla": list(ST.BFLA_FLAW)}
        methods = ["mr_bookkeeping", "v3", "v3_self", "direct_only",
                   "direct_observe", "direct_observe_self"]
        perf = {m: {"TP": 0, "FN": 0, "FP": 0, "TN": 0} for m in methods}
        for c_ in cells:
            is_vuln = (c_["subject"], c_["object"]) in seeded_bola
            for m in methods:
                fired = bool(c_["alarms"][m])
                if is_vuln and fired:
                    perf[m]["TP"] += 1
                elif is_vuln and not fired:
                    perf[m]["FN"] += 1
                elif (not is_vuln) and fired:
                    perf[m]["FP"] += 1
                else:
                    perf[m]["TN"] += 1
        rep["positive_control_TP_FN_FP"] = perf

        # ---- BFLA 定性：非特权 actor 越权写是否成功（引擎读向设计不覆盖） ----
        _, actor, bobj = ST.BFLA_FLAW
        st_bfla, _ = cl[actor].put(
            f"/api/v1/repos/{bobj.replace('/', '/')}/collaborators/carol",
            {"permission": "read"})
        rep["bfla_probe"] = {
            "actor": actor, "target_object": bobj,
            "unauthorized_grant_status": st_bfla,
            "vulnerable_present": st_bfla in (200, 201, 204),
            "detector_coverage": ("引擎的读向自省/观察裁决不直接覆盖写向 BFLA；"
                                  "此为已知边界，与论文 §6 的 oracle 保真度边界一致。"),
        }
    finally:
        srv.shutdown()

    rep["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = RESULTS / "seeded.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] -> {out} ({out.stat().st_size} bytes, {rep['meta']['elapsed_s']}s)", flush=True)

    # 终端汇总
    print("\n===== 阳性对照 TP/FN/FP（已知植入 BOLA 缺陷 = %d 个）=====" % len(seeded_bola))
    print(f"{'method':18s}{'TP':>4}{'FN':>4}{'FP':>5}{'TN':>5}")
    for m, d in perf.items():
        print(f"{m:18s}{d['TP']:>4}{d['FN']:>4}{d['FP']:>5}{d['TN']:>5}")
    print("\nBFLA 探针：", rep["bfla_probe"]["actor"],
          "越权授予状态=", rep["bfla_probe"]["unauthorized_grant_status"],
          "漏洞存在=", rep["bfla_probe"]["vulnerable_present"])


if __name__ == "__main__":
    main()

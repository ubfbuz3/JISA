"""
R1.9 · 多类独立授权缺陷 · 逐缺陷召回与误报
==========================================

在同一台受控靶机（seeded_target.py，复刻引擎消费的 Gitea API 契约）上植入四类
**相互独立、可单独开关**的授权缺陷，用**与真实系统实验完全相同的代码路径**
（run_real.crawl / run_real.introspect / 同一套 alarm 公式）测量：

  C1 读越权   ：运行期 GET 放行，正确模型为 none
  C2 写越权   ：运行期 PATCH 放行并**真的改变**对象状态
  C3 继承缺陷 ：错误的组织/团队继承扩展；列表与对象读一致地"看得见"
  C4 提权     ：非 owner/非 admin 的 actor 越权授予，被授予者由此获得访问

测量两类关系：
  · 已研究的关系（read gate）：cannotReachThroughGUI ∧ 输出等价
  · 通道匹配的同族关系（write gate / grant gate）：README 记载，作为"若把同一
    关系族搬到该通道会怎样"的对照，**不**声称是本文已研究的关系

真值：靶机的正确模型（intended_perm），与 E/Y 拆分中的 E 同角色；观测：实际请求。
误报定义与正文一致：在**被授权**（intended != none）的单元格上报警。

归因检验：全量跑一次，再对每一类做 leave-one-out（只关掉该类），确认该类的实例
不再报警、其余类仍报警 —— 证明每个报警可归因到那一个缺陷，而不是共享根因。

用法：python run_multiclass.py
"""
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import run_real as R
import seeded_target as ST
from gitea_lab import ADMIN_PASS, ADMIN_USER, Client as LabClient

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

BASE_PORT = 3331

# 四类缺陷的实例（subject, obj, detail）。C4 的 subject 是**被授予者**：
# 越权访问在它身上兑现；actor 单独记录。
CLASSES = {
    "C1": {"label": "read enforcement",
           "instances": [("eve", "alice/r1"), ("bob", "dave/r5"),
                         ("carol", "acme/t2")]},
    "C2": {"label": "modify enforcement",
           "instances": [("dave", "alice/r2"), ("eve", "dave/r5")]},
    "C3": {"label": "inheritance",
           "instances": [("carol", "acme/t1"), ("eve", "acme/t2")]},
    "C4": {"label": "privilege escalation",
           "instances": [("carol", "alice/r3"), ("frank", "dave/r5")]},
}

# C4：(actor, obj) -> grantee；actor 是被植入的越权者
ESCALATIONS = [("bob", "carol", "alice/r3"), ("carol", "frank", "dave/r5")]


def _clients(port: int):
    base = f"http://127.0.0.1:{port}"
    out = {"anonymous": LabClient(base=base, label="anonymous")}
    out[ADMIN_USER] = LabClient(base=base, user=ADMIN_USER, password=ADMIN_PASS,
                                label=ADMIN_USER)
    for u in ST.USERS:
        out[u] = LabClient(base=base, user=u, password=ST.PASS, label=u)
    return out


def _setup(port: int, active: set[str]):
    """起靶机 + 拓扑 + 带外变更 + C3 所需的组织成员，返回 (srv, cl, rep)。"""
    srv = ST.make_server(port, legacy=False)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    time.sleep(0.6)
    cl = _clients(port)
    rep = {"phaseA": R.phaseA_topology(cl)}
    team_ids = rep["phaseA"]["team_ids"]
    rep["phaseC"] = R.phaseC_mutations(cl, team_ids)

    # C3 需要"组织成员但不在该团队"的主体：carol / eve 加入组织（不加入 dev）
    for u in ("carol", "eve"):
        st, b = cl[ST.ADMIN_USER].put(f"/api/v1/orgs/{ST.ORG}/members/{u}")
        rep.setdefault("c3_setup", []).append({"add_org_member": u, "status": st})

    m = ST.Handler.model
    read = [(s, o) for (s, o) in CLASSES["C1"]["instances"] if "C1" in active]
    write = [(s, o) for (s, o) in CLASSES["C2"]["instances"] if "C2" in active]
    inherit = {k: "read" for k in ((s, o) for (s, o) in CLASSES["C3"]["instances"])
               if "C3" in active}
    escalate = [(a, o) for (a, g, o) in ESCALATIONS if "C4" in active]
    ST.install_multiclass(m, read=read, write=write, inherit=inherit, escalate=escalate)
    return srv, cl, rep


def _measure(port: int, cl, active: set[str]):
    """执行 C4 的越权授予、爬取、逐实例探针与 alarm 计算。"""
    m = ST.Handler.model
    out = {"instances": [], "fp": {}, "port": port}

    # ---- C4：先执行越权授予（被授予者之后才会在列表里看到对象）----
    grants = []
    for actor, grantee, obj in ESCALATIONS:
        if "C4" not in active:
            continue
        o, n = obj.split("/")
        st, _ = cl[actor].put(f"/api/v1/repos/{o}/{n}/collaborators/{grantee}",
                              {"permission": "read"})
        grants.append({"actor": actor, "grantee": grantee, "object": obj, "status": st})
    out["escalation_grants"] = grants

    # ---- 爬取（GUI 等价）：所有主体的可达集 ----
    snap = {u: R.crawl(cl[u], [ST.ORG]) for u in list(ST.USERS) + [ST.ADMIN_USER]}

    def can_snap(subj, obj):
        return obj not in set(snap[subj]["urls"])

    def owner_view(obj):
        o, n = obj.split("/")
        st, b = cl[ST.OBJ_CREDENTIAL[obj]].get(f"/api/v1/repos/{o}/{n}")
        return b if st == 200 and isinstance(b, dict) else {}

    # ---- 逐实例 ----
    for cls, spec in CLASSES.items():
        on = cls in active
        for subj, obj in spec["instances"]:
            o, n = obj.split("/")
            truth = m.intended_perm(subj, obj)
            rec = {"class": cls, "class_label": spec["label"], "subject": subj,
                   "object": obj, "truth_permission": truth,
                   "defect_active": on,
                   "cannot_reach": can_snap(subj, obj)}
            # 自省面（对象拥有者视点，与真实系统实验同一函数）
            ins = R.introspect(cl, obj, subj)
            rec["introspection"] = ins

            if cls in ("C1", "C3"):
                st, b = cl[subj].get(f"/api/v1/repos/{o}/{n}")
                rec["probe"] = {"channel": "read", "status": st}
                same = (st == 200 and isinstance(b, dict)
                        and R._norm_repo(b) == R._norm_repo(owner_view(obj)))
                rec["channel_effect"] = bool(same)
            elif cls == "C2":
                pre = owner_view(obj).get("description")
                st, _ = cl[subj].patch(f"/api/v1/repos/{o}/{n}",
                                       {"description": f"written-by-{subj}"})
                post = owner_view(obj).get("description")
                rec["probe"] = {"channel": "write", "status": st,
                                "pre": pre, "post": post}
                rec["channel_effect"] = bool(st in (200, 204) and post != pre)
            else:  # C4：测被授予者
                st, _ = cl[subj].get(f"/api/v1/repos/{o}/{n}")
                rec["probe"] = {"channel": "grant", "status": st}
                rec["channel_effect"] = bool(st == 200)

            # 已研究的关系：read gate（同一公式，所有类都用它评一次）
            read_st, read_b = cl[subj].get(f"/api/v1/repos/{o}/{n}")
            read_ok = (read_st == 200 and isinstance(read_b, dict)
                       and R._norm_repo(read_b) == R._norm_repo(owner_view(obj)))
            mr_read = bool(rec["cannot_reach"] and read_ok)
            # 通道匹配的同族关系
            mr_channel = bool(rec["cannot_reach"] and rec["channel_effect"])
            rec["mr_read"] = mr_read
            rec["mr_channel"] = mr_channel

            says_none = bool(ins.get("says_none"))
            readable = bool(ins.get("readable"))
            log_has = subj in R.FRAMEWORK_LOG.get(obj, {})
            rec["alarms"] = {
                "mr_bookkeeping": bool(mr_read and not log_has),
                "v3": bool(mr_read and readable and says_none),
                "v3_channel": bool(mr_channel and readable and says_none),
                "direct_observe": bool(readable and says_none and read_st == 200),
                "direct_observe_channel": bool(readable and says_none
                                               and rec["probe"]["status"] in (200, 204)),
                "direct_only": bool(readable and says_none),
            }
            out["instances"].append(rec)

    # ---- 误报：被授权单元格（intended != none）上的报警 ----
    fp = {k: 0 for k in ("mr_bookkeeping", "v3", "v3_channel", "direct_observe",
                         "direct_observe_channel", "direct_only")}
    safe = 0
    for subj in list(ST.USERS) + [ST.ADMIN_USER]:
        for obj in ST.ALL_OBJS:
            if m.intended_perm(subj, obj) == "none":
                continue
            safe += 1
            o, n = obj.split("/")
            ins = R.introspect(cl, obj, subj)
            st, b = cl[subj].get(f"/api/v1/repos/{o}/{n}")
            read_ok = (st == 200 and isinstance(b, dict)
                       and R._norm_repo(b) == R._norm_repo(owner_view(obj)))
            mr_read = bool(can_snap(subj, obj) and read_ok)
            log_has = subj in R.FRAMEWORK_LOG.get(obj, {})
            if mr_read and not log_has:
                fp["mr_bookkeeping"] += 1
            if mr_read and ins.get("readable") and ins.get("says_none"):
                fp["v3"] += 1
                fp["v3_channel"] += 1
            if ins.get("readable") and ins.get("says_none") and st == 200:
                fp["direct_observe"] += 1
                fp["direct_observe_channel"] += 1
            if ins.get("readable") and ins.get("says_none"):
                fp["direct_only"] += 1
    out["fp"] = fp
    out["fp_denominator"] = safe
    return out


def _summarise(runs: dict[str, dict]):
    """runs: {run_name: measure_result}。返回逐类 TP/FN/recall 与 FP。"""
    full = runs["all"]
    per_class = {}
    for cls, spec in CLASSES.items():
        rows = [r for r in full["instances"] if r["class"] == cls]
        entry = {"label": spec["label"], "n": len(rows), "detected": {},
                 "mr_read": sum(1 for r in rows if r["mr_read"]),
                 "mr_channel": sum(1 for r in rows if r["mr_channel"])}
        for meth in ("mr_bookkeeping", "v3", "v3_channel", "direct_observe",
                     "direct_observe_channel", "direct_only"):
            entry["detected"][meth] = sum(1 for r in rows if r["alarms"][meth])
        per_class[cls] = entry
    # leave-one-out：关掉某类后，该类实例应全部不再报警，其余类保持
    loo = {}
    for cls in CLASSES:
        off = runs[f"without_{cls}"]
        own = [r for r in off["instances"] if r["class"] == cls]
        other = [r for r in off["instances"] if r["class"] != cls]
        loo[cls] = {
            "own_alarms_after_disable": sum(1 for r in own
                                            if r["alarms"]["v3_channel"] or r["mr_read"]),
            "other_alarms_retained": sum(1 for r in other
                                         if r["alarms"]["v3_channel"] or r["mr_read"]),
        }
    return {"per_class": per_class, "leave_one_out": loo,
            "fp": full["fp"], "fp_denominator": full["fp_denominator"]}


def main():
    t0 = time.time()
    runs = {}
    combos = [("all", {"C1", "C2", "C3", "C4"})] + [
        (f"without_{c}", {"C1", "C2", "C3", "C4"} - {c}) for c in ("C1", "C2", "C3", "C4")]
    port = BASE_PORT
    for name, active in combos:
        srv, cl, rep = _setup(port, active)
        try:
            res = _measure(port, cl, active)
        finally:
            srv.shutdown()
            srv.server_close()
        res["setup"] = rep
        runs[name] = res
        print(f"[run] {name}: {sum(1 for r in res['instances'] if r['mr_read'])} mr_read / "
              f"{sum(1 for r in res['instances'] if r['mr_channel'])} mr_channel", flush=True)
        port += 1

    summary = _summarise(runs)
    out = {"meta": {
        "experiment": "R1.9 multi-class seeded authorization defects",
        "target": "seeded_target.py (controlled Gitea API emulator)",
        "active_classes": {k: list(v) for k, v in
                           [("all", {"C1", "C2", "C3", "C4"})]},
        "classes": {k: {"label": v["label"], "instances": [list(x) for x in v["instances"]]}
                    for k, v in CLASSES.items()},
        "truth_source": "ST.Model.intended_perm (tainted grants excluded)",
        "fp_definition": "alarm on a cell whose intended permission is not none",
        "elapsed_s": None,
    }, "summary": summary, "runs": runs}
    out["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    p = RESULTS / "seeded_multiclass.json"
    p.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n===== 逐类召回（全量缺陷开启）=====")
    hdr = f"{'class':6s}{'n':>3}{'mr_read':>9}{'mr_ch':>7}{'v3':>5}{'v3_ch':>7}{'d_obs':>7}{'d_only':>8}"
    print(hdr)
    for cls, e in summary["per_class"].items():
        print(f"{cls:6s}{e['n']:>3}{e['mr_read']:>9}{e['mr_channel']:>7}"
              f"{e['detected']['v3']:>5}{e['detected']['v3_channel']:>7}"
              f"{e['detected']['direct_observe']:>7}{e['detected']['direct_only']:>8}")
    print("\n误报（被授权单元格）：", summary["fp"], "分母", summary["fp_denominator"])
    print("leave-one-out：", json.dumps(summary["leave_one_out"], ensure_ascii=False))
    print(f"[done] -> {p} ({out['meta']['elapsed_s']}s)")


if __name__ == "__main__":
    main()

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
误报定义与正文一致：在**被授权**（intended != none）的单元格上报警。负例按通道
分组（read / write / grant），因为读格不能代替写格与授予格：写通道的成功以
**实际状态变化**判定（不是状态码），授予通道要求协作者记录真的出现。

归因检验：全量跑一次，再对每一类做 leave-one-out（只关掉该类），确认该类的实例
不再报警、其余类仍报警 —— 证明该报警可归因到那一个缺陷，而不是共享根因。
归因量**按方法分开记**（leave_one_out_by_method）：复合量（三条链路的 OR）四类
都有可归因的报警，但读关系只对 C1、渠道匹配关系只对 C1/C2 有"有→无"，
C3/C4 的关系自始至终不报警，可归因的是渠道匹配的直接裁决。

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

# ---- 真实 HTTP 计数 -----------------------------------------------------
# 负例成本必须来自实际发出的请求，不能是每格一个常数：读格每格 3 次、写格 4 次、
# 授予格 3 次，另有一次**共享**的授予后枚举（3 条列表 + 每个列表结果的对象访问）。
# 计数器包在 Client.req 上，所以 crawl/introspect/探针都算在内；每格测前后取差。
_ORIG_REQ = LabClient.req


class _Counter:
    def __init__(self) -> None:
        self.n = 0

    def reset(self) -> int:
        prev, self.n = self.n, 0
        return prev


COUNT = _Counter()


def _counting_req(self, *a, **kw):                              # noqa: ANN001
    COUNT.n += 1
    return _ORIG_REQ(self, *a, **kw)


LabClient.req = _counting_req

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
    grant_st: dict[str, int] = {}
    for actor, grantee, obj in ESCALATIONS:
        if "C4" not in active:
            continue
        o, n = obj.split("/")
        st, _ = cl[actor].put(f"/api/v1/repos/{o}/{n}/collaborators/{grantee}",
                              {"permission": "read"})
        grants.append({"actor": actor, "grantee": grantee, "object": obj, "status": st})
        grant_st[obj] = st
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
                gst = grant_st.get(obj)
                rec["probe"] = {"channel": "grant", "status": st, "grant_status": gst}
                # 效果判定：越权授予被接受 **且** 被授予者真的读到了对象；
                # 只看被授予者的状态码会把"本来就能读"误计为提权生效。
                rec["channel_effect"] = bool(st == 200 and gst in (200, 204))

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
                # 与效果合同对齐：写通道以**实际状态变化**判定成功，不看状态码。
                "direct_observe_channel": bool(readable and says_none
                                               and rec["channel_effect"]),
                "direct_only": bool(readable and says_none),
            }
            out["instances"].append(rec)

    # ---- 误报对照：**逐通道**的授权负例 --------------------------------
    # 每个通道各自一组"正确模型说该主体有权做该操作"的格。在这些格上：关系触发、
    # 或 oracle 回答 none、或（写通道）状态码成功但状态没变，都是误报。
    # 逐条保存 E（正确模型）、Y（该通道的实际效果）、方法输出与请求成本；分母按
    # 通道分别记。读通道的 23 格同时充当 C1/C3 的负例（复用，不重复发请求）；
    # 写通道与授予通道各自独立，不能用读格代替。
    users = list(ST.USERS) + [ST.ADMIN_USER]
    neg: dict[str, list] = {"read": [], "write": [], "grant": []}

    def _alarms(mr: bool, readable: bool, says_none: bool, effect: bool) -> dict:
        return {
            "relation": bool(mr),
            "relation_oracle": bool(mr and readable and says_none),
            "oracle_only": bool(readable and says_none and effect),
            "bookkeeping": bool(mr and effect),   # 只用于读通道的 log 变体，见下
        }

    # (a) 读通道 ------------------------------------------------------
    for subj in users:
        for obj in ST.ALL_OBJS:
            perm = m.intended_perm(subj, obj)
            if perm == "none":
                continue
            o, n = obj.split("/")
            COUNT.reset()
            ins = R.introspect(cl, obj, subj)
            st, b = cl[subj].get(f"/api/v1/repos/{o}/{n}")
            read_ok = (st == 200 and isinstance(b, dict)
                       and R._norm_repo(b) == R._norm_repo(owner_view(obj)))
            nreq = COUNT.n
            cannot = bool(can_snap(subj, obj))
            log_has = subj in R.FRAMEWORK_LOG.get(obj, {})
            a = _alarms(cannot and read_ok, ins.get("readable", False),
                        ins.get("says_none", False), bool(read_ok))
            a["bookkeeping"] = bool(cannot and read_ok and not log_has)
            neg["read"].append({
                "channel": "read", "subject": subj, "object": obj,
                "truth_permission": perm, "truth": "authorized",
                "cannot_reach": cannot, "log_has": log_has,
                "effect": bool(read_ok), "probe_status": st,
                "E_says": perm, "Y_effect": bool(read_ok),
                "oracle_readable": bool(ins.get("readable")),
                "oracle_says_none": bool(ins.get("says_none")),
                "alarms": a, "requests": nreq,
            })

    # (b) 写通道（PATCH）—— 成功以**实际状态变化**判定，不看状态码 --------
    for subj in users:
        for obj in ST.ALL_OBJS:
            perm = m.intended_perm(subj, obj)
            if perm not in ("write", "admin"):
                continue
            o, n = obj.split("/")
            COUNT.reset()
            pre = owner_view(obj).get("description")
            st, _ = cl[subj].patch(f"/api/v1/repos/{o}/{n}",
                                   {"description": f"neg-write-{subj}-{n}"})
            post = owner_view(obj).get("description")
            effect = bool(st in (200, 204) and post != pre)
            ins = R.introspect(cl, obj, subj)
            nreq = COUNT.n
            cannot = bool(can_snap(subj, obj))
            neg["write"].append({
                "channel": "write", "subject": subj, "object": obj,
                "truth_permission": perm, "truth": "authorized",
                "cannot_reach": cannot,
                "effect": effect, "probe_status": st,
                "E_says": perm, "Y_effect": effect,
                "pre": pre, "post": post,
                "oracle_readable": bool(ins.get("readable")),
                "oracle_says_none": bool(ins.get("says_none")),
                "alarms": _alarms(cannot and effect, ins.get("readable", False),
                                  ins.get("says_none", False), effect),
                "requests": nreq,   # 写前状态 + PATCH + 写后状态 + 自省面（实测）
            })

    # (c) 授予通道（PUT collaborators）—— 只有 owner/admin 是合法授予者 ------
    # 注意：授予会改变可达性，所以不能拿授予前的爬取快照判 cannot_reach；
    # 先做完所有授予，再对同一个被授予者重新爬一次（1 次共享枚举），然后判。
    grantee = "eve"
    grant_cells: list[dict] = []
    shared_req = 0
    for subj in users:
        for obj in ST.ALL_OBJS:
            if not (subj == ST.ADMIN_USER or m.repos[obj]["owner"] == subj):
                continue
            if m.intended_perm(grantee, obj) != "none":
                continue          # 被授予者本就有权：该格不是"授予产生访问"的负例
            o, n = obj.split("/")
            COUNT.reset()
            st, _ = cl[subj].put(f"/api/v1/repos/{o}/{n}/collaborators/{grantee}",
                                 {"permission": "read"})
            lst = cl[subj].get(f"/api/v1/repos/{o}/{n}/collaborators")[1] or []
            in_collab = any(isinstance(c, dict) and c.get("login") == grantee for c in lst)
            ins = R.introspect(cl, obj, grantee)
            nreq = COUNT.n
            grant_cells.append({
                "channel": "grant", "subject": subj, "grantee": grantee, "object": obj,
                "truth_permission": "admin", "truth": "authorized",
                "effect": bool(st in (200, 204) and in_collab), "probe_status": st,
                "E_says": "admin", "Y_effect": bool(st in (200, 204) and in_collab),
                "oracle_readable": bool(ins.get("readable")),
                "oracle_says_none": bool(ins.get("says_none")),
                "requests": nreq,   # PUT + 协作者列表复核 + 自省面（实测）
            })
    if grant_cells:                       # 授予后的新鲜可达集（1 次共享枚举）
        COUNT.reset()
        urls = set(R.crawl(cl[grantee], [ST.ORG])["urls"])
        shared_req = COUNT.n
        for c in grant_cells:
            c["cannot_reach"] = c["object"] not in urls
            c["alarms"] = _alarms(c["cannot_reach"] and c["effect"],
                                  c["oracle_readable"], c["oracle_says_none"],
                                  c["effect"])
        neg["grant"] = grant_cells

    out["negatives"] = neg
    out["neg_denominator"] = {k: len(v) for k, v in neg.items()}
    # 通道级共享成本：授予通道要在授予后重新枚举一次被授予者的可达集，
    # 这次枚举本身也是 HTTP 请求（3 条列表 + 每个列表结果的对象访问），实测计数。
    out["neg_shared_requests"] = {"read": 0, "write": 0,
                                  "grant": shared_req if grant_cells else 0}
    # 兼容旧字段：合并读通道计数（与正文既有 8/23、0 同一口径）
    fp = {k: 0 for k in ("mr_bookkeeping", "v3", "v3_channel", "direct_observe",
                         "direct_observe_channel", "direct_only")}
    for r in neg["read"]:
        a = r["alarms"]
        fp["mr_bookkeeping"] += int(a["bookkeeping"])
        fp["v3"] += int(a["relation_oracle"])
        fp["v3_channel"] += int(a["relation_oracle"])
        fp["direct_observe"] += int(a["oracle_only"])
        fp["direct_observe_channel"] += int(a["oracle_only"])
        fp["direct_only"] += int(r["oracle_readable"] and r["oracle_says_none"])
    out["fp"] = fp
    out["fp_denominator"] = len(neg["read"])
    return out


CLASS_CHANNEL = {"C1": "read", "C2": "write", "C3": "read", "C4": "grant"}


METHODS = ("mr_read", "v3_channel", "direct_observe_channel")


def _alarm_of(rec: dict, meth: str) -> bool:
    """单条链路的告警，不带复合。留一法必须分开报，否则会把"oracle 能归因"
    误读成"关系能归因"——C3/C4 的关系自始至终不报警。"""
    if meth == "mr_read":
        return bool(rec["mr_read"])
    return bool(rec["alarms"][meth])


def _any_alarm(rec: dict) -> bool:
    """该实例上"有没有任何一条被检验的链路报警"（复合量）。

    取三条：已研究的关系（mr_read）、渠道匹配的关系（v3_channel）、渠道匹配的
    oracle 裁决（direct_observe_channel 已在测量里用效果判定）。复合量四类都有
    可归因的报警；但**不能**由此推出每个组成方法都能归因四类，正文引用归因时
    必须用 leave_one_out_by_method 的分方法数字。
    """
    a = rec["alarms"]
    return bool(rec["mr_read"] or a["v3_channel"] or a["direct_observe_channel"])


def _summarise(runs: dict[str, dict]):
    """runs: {run_name: measure_result}。返回逐类 TP/FN/recall 与逐通道 FP。"""
    full = runs["all"]
    per_class = {}
    # 逐通道误报：分母 = 该通道的授权负例数
    neg_fp = {}
    shared = full.get("neg_shared_requests", {})
    for ch, rows in full["negatives"].items():
        n = len(rows)
        d = {"n": n,
             "relation": sum(1 for r in rows if r["alarms"]["relation"]),
             "relation_oracle": sum(1 for r in rows if r["alarms"]["relation_oracle"]),
             "oracle_only": sum(1 for r in rows if r["alarms"]["oracle_only"]),
             "requests": sum(r["requests"] for r in rows) + shared.get(ch, 0),
             "shared_requests": shared.get(ch, 0)}
        d["fpr_relation_oracle"] = round(d["relation_oracle"] / n, 4) if n else None
        d["fpr_oracle_only"] = round(d["oracle_only"] / n, 4) if n else None
        neg_fp[ch] = d
    for cls, spec in CLASSES.items():
        rows = [r for r in full["instances"] if r["class"] == cls]
        entry = {"label": spec["label"], "n": len(rows), "detected": {},
                 "mr_read": sum(1 for r in rows if r["mr_read"]),
                 "mr_channel": sum(1 for r in rows if r["mr_channel"])}
        for meth in ("mr_bookkeeping", "v3", "v3_channel", "direct_observe",
                     "direct_observe_channel", "direct_only"):
            entry["detected"][meth] = sum(1 for r in rows if r["alarms"][meth])
        ch = CLASS_CHANNEL[cls]
        entry["neg_channel"] = ch
        entry["neg_n"] = neg_fp[ch]["n"]
        entry["neg_fp_channel"] = neg_fp[ch]["relation_oracle"]
        entry["neg_fp_oracle"] = neg_fp[ch]["oracle_only"]
        entry["neg_fpr_channel"] = neg_fp[ch]["fpr_relation_oracle"]
        entry["neg_fpr_oracle"] = neg_fp[ch]["fpr_oracle_only"]
        per_class[cls] = entry
    # leave-one-out：关掉某类后，该类实例不再报警，其余类保持
    loo = {}
    for cls in CLASSES:
        off = runs[f"without_{cls}"]
        own = [r for r in off["instances"] if r["class"] == cls]
        other = [r for r in off["instances"] if r["class"] != cls]
        loo[cls] = {
            "own_alarms_after_disable": sum(1 for r in own if _any_alarm(r)),
            "other_alarms_retained": sum(1 for r in other if _any_alarm(r)),
            "own_total_when_active": sum(1 for r in full["instances"]
                                         if r["class"] == cls and _any_alarm(r)),
        }
    # 逐方法留一法：复合量覆盖四类，不代表每个组成方法都能覆盖四类。
    loo_m = {}
    for cls in CLASSES:
        off = runs[f"without_{cls}"]
        own_off = [r for r in off["instances"] if r["class"] == cls]
        own_on = [r for r in full["instances"] if r["class"] == cls]
        loo_m[cls] = {meth: {"active": sum(1 for r in own_on if _alarm_of(r, meth)),
                             "disabled": sum(1 for r in own_off if _alarm_of(r, meth))}
                      for meth in METHODS}
        # 关掉该类后，其余类的实例在每条链路上是否仍然报警（共享根因检查）
        other_off = [r for r in off["instances"] if r["class"] != cls]
        for meth in METHODS:
            loo_m[cls][meth]["other_retained"] = sum(
                1 for r in other_off if _alarm_of(r, meth))
    return {"per_class": per_class, "leave_one_out": loo,
            "leave_one_out_by_method": loo_m,
            "negatives": neg_fp,
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
    print("\n误报（合并读通道）：", summary["fp"], "分母", summary["fp_denominator"])
    print("逐通道负例：", json.dumps(summary["negatives"], ensure_ascii=False))
    print("leave-one-out：", json.dumps(summary["leave_one_out"], ensure_ascii=False))
    print("leave-one-out（逐方法）：")
    for cls, m in summary["leave_one_out_by_method"].items():
        print("  ", cls, json.dumps(m, ensure_ascii=False))
    print(f"[done] -> {p} ({out['meta']['elapsed_s']}s)")


if __name__ == "__main__":
    main()

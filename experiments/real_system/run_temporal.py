"""
B · 真时序实验（Gitea 1.22.6）
===============================

每轮一个授权转移，严格按预注册顺序执行：

    S0/E0 → crawl → 冻结 M0（写盘 + 摘要）→ 授权事务提交（hv+1）
          → 同权限 recrawl M1 → 请求 + 效果复读 Y → oracle O → 判定 A/H/T

为什么要这样：`cannotReachThroughGUI` 与 `userCanRetrieveContent` 都是相对
**采集期记录**定义的。旧实验把"采集"和"变更"压在同一阶段，无法回答
"错判是时间陈旧造成的，还是新采集仍然看不见这条通道"。本运行器把两者分开：

  * `stale` 读法 = M0（变更前冻结）
  * `live`  读法 = M1（变更后、同一主体凭证重新采集）
  * 真值 E 始终取**判定时刻**的台账（hv_e），绝不取任何响应

诚实边界（写死在脚本里）
  1. `hv` 是 harness 逻辑版本，不是服务端原子快照号。
  2. oracle 与 enforcement 同源，`oracle_independence = shared`；O 只作交叉核对。
  3. 主体自身视点读不到的 deny 格记 unknown，不记 deny（校准里也这样验）。
  4. 撤销后旧模型仍"可达"但 enforcement 拒绝 ⇒ 不是真实违规，不算漏检。
  5. 只报本拓扑的格数与分母，不外推部署发生率。

用法: python run_temporal.py [--keep]
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_ID = time.strftime("%Y%m%d_%H%M%S")

# 必须在 import gitea_lab 之前设好：模块在导入时读取这两个环境变量
os.environ.setdefault(
    "BOLA_LAB_DIR",
    str(Path(r"C:\Users\Administrator\WorkBuddy") / f"gitea_temporal_{RUN_ID}"))
os.environ.setdefault("BOLA_LAB_PORT", "3313")

sys.path.insert(0, str(HERE))
import gitea_lab as gl                                        # noqa: E402
from entitlement import PolicyModel, classify                 # noqa: E402
from gitea_lab import (ADMIN_PASS, ADMIN_USER, Client, Server,  # noqa: E402
                       ensure_migrated, write_config)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PASS = "LabPass123!"
PROTO = HERE / "c_protocol.json"
RESULTS = HERE / "results" / "temporal"
RESULTS.mkdir(parents=True, exist_ok=True)

ORG = "acme"
USERS = ["alice", "bob", "carol", "dave", "erin"]
SUBJECTS = USERS + ["anonymous"]

# (object, owner, private)
REPOS = [
    ("alice/priv1", "alice", True),    # T1 直接授权
    ("alice/priv2", "alice", True),    # T2 直接撤销
    ("alice/pub1",  "alice", False),   # T6 公开 -> 私有
    ("acme/t1",     "acme",  True),    # T4 移除团队后仍保留直授（替代通道）
    ("acme/t2",     "acme",  True),    # T3 团队继承授权
    ("dave/r1",     "dave",  True),    # T5 私有 -> 公开
    ("dave/r2",     "dave",  True),    # T7 角色 read -> write
]
OBJECTS = [r[0] for r in REPOS]
OBJ_CRED = {o: (owner if owner != "acme" else "dave") for o, owner, _ in REPOS}
PRIVATE = {o: p for o, _, p in REPOS}


# ---------------------------------------------------------------------------
# 基础工具
# ---------------------------------------------------------------------------
def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def canon(x) -> bytes:
    return json.dumps(x, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":")).encode("utf-8")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def call(c: Client, method: str, path: str, body=None, retries: int = 2):
    """status 0 = 传输失败；按协议重试两次后再放弃。"""
    st, b = 0, None
    for _ in range(retries + 1):
        st, b = c.req(method, path, body)
        if st != 0:
            return st, b
        time.sleep(0.25)
    return st, b


def clients() -> dict[str, Client]:
    out = {"anonymous": Client(label="anonymous")}
    out[ADMIN_USER] = Client(user=ADMIN_USER, password=ADMIN_PASS, label=ADMIN_USER)
    for u in USERS:
        out[u] = Client(user=u, password=PASS, label=u)
    return out


# ---------------------------------------------------------------------------
# 阶段 A · 基线拓扑（每条成功事务都是台账的一行）
# ---------------------------------------------------------------------------
def setup(cl: dict[str, Client]) -> dict:
    steps: list[dict] = []

    def rec(label, st, body):
        ok = 200 <= st < 300
        steps.append({"step": label, "status": st, "ok": ok,
                      "error": None if ok else str(body)[:200]})
        return ok

    admin = cl[ADMIN_USER]
    for u in USERS:
        rec(f"user:{u}", *call(admin, "POST", "/api/v1/admin/users", {
            "username": u, "password": PASS, "email": f"{u}@lab.local",
            "must_change_password": False, "restricted": False}))

    rec("org:acme", *call(cl["dave"], "POST", "/api/v1/orgs", {
        "username": ORG, "visibility": "private", "full_name": "Acme"}))

    st, team = call(cl["dave"], "POST", f"/api/v1/orgs/{ORG}/teams", {
        "name": "dev", "permission": "read",
        "units": ["repo.code", "repo.issues", "repo.pulls", "repo.wiki", "repo.releases"],
        "includes_all_repositories": False})
    rec("team:dev", st, team)
    team_id = team.get("id") if isinstance(team, dict) else None

    for obj, owner, priv in REPOS:
        if owner == "acme":
            path, body = f"/api/v1/orgs/{ORG}/repos", {
                "name": obj.split("/")[1], "private": priv,
                "auto_init": True, "description": "temporal lab"}
            st, b = call(cl["dave"], "POST", path, body)
        else:
            st, b = call(cl[owner], "POST", "/api/v1/user/repos", {
                "name": obj.split("/")[1], "private": priv,
                "auto_init": True, "description": "temporal lab"})
        rec(f"repo:{obj}", st, b)

    # 基线授权（都发生在第一次采集之前）
    rec("baseline: alice/priv2 <- bob (read)",
        *call(cl["alice"], "PUT", "/api/v1/repos/alice/priv2/collaborators/bob",
              {"permission": "read"}))
    rec("baseline: team dev <- bob",
        *call(cl["dave"], "PUT", f"/api/v1/teams/{team_id}/members/bob"))
    rec("baseline: team dev <- acme/t1",
        *call(cl["dave"], "PUT", f"/api/v1/teams/{team_id}/repos/{ORG}/t1"))
    rec("baseline: acme/t1 <- bob (read, alt channel)",
        *call(cl["dave"], "PUT", "/api/v1/repos/acme/t1/collaborators/bob",
              {"permission": "read"}))
    rec("baseline: dave/r2 <- carol (read)",
        *call(cl["dave"], "PUT", "/api/v1/repos/dave/r2/collaborators/carol",
              {"permission": "read"}))

    # 校准对象：一次性，不进正式分母
    rec("cal: dave/cal private", *call(cl["dave"], "POST", "/api/v1/user/repos", {
        "name": "cal", "private": True, "auto_init": True, "description": "calibration"}))
    rec("cal: dave/cal <- carol (read)",
        *call(cl["dave"], "PUT", "/api/v1/repos/dave/cal/collaborators/carol",
              {"permission": "read"}))

    failures = [s for s in steps if not s["ok"]]
    if failures:
        raise RuntimeError("setup 有失败步骤: "
                           + json.dumps(failures[:3], ensure_ascii=False))
    return {"steps": steps, "team_id": team_id}


def baseline_policy(team_id: int) -> PolicyModel:
    """只由 setup 事务构造，不读任何探针响应。"""
    m = PolicyModel()
    m.add_org(ORG, "dave", "setup: org created by dave")
    for obj, owner, priv in REPOS:
        m.add_repo(obj, owner, priv, "setup: repo creation")
    m.add_site_admin(ADMIN_USER, "lab admin bootstrap")
    m.add_team("dev", "read", "setup: team dev")
    m.add_team_member("dev", "bob", "setup: team dev <- bob")
    m.add_team_repo("dev", "acme/t1", "setup: team dev <- acme/t1")
    m.add_collaborator("alice/priv2", "bob", "read", "setup: alice/priv2 <- bob")
    m.add_collaborator("acme/t1", "bob", "read", "setup: acme/t1 <- bob (alt)")
    m.add_collaborator("dave/r2", "carol", "read", "setup: dave/r2 <- carol")
    return m


# ---------------------------------------------------------------------------
# 采集（GUI 等价记录）与冻结
# ---------------------------------------------------------------------------
def crawl(c: Client) -> dict:
    urls: set[str] = set()
    sources: dict[str, int] = {}

    def add_many(st, body, key=None):
        if st != 200:
            return
        rows = body.get("data", []) if isinstance(body, dict) else body
        if isinstance(rows, list):
            for r in rows:
                if isinstance(r, dict) and r.get("name") and r.get("owner"):
                    urls.add(f"{r['owner']['login']}/{r['name']}")

    st, b = call(c, "GET", "/api/v1/user/repos?limit=50")
    sources["user_repos"] = st
    add_many(st, b)

    st, b = call(c, "GET", f"/api/v1/orgs/{ORG}/repos?limit=50")
    sources["org_repos"] = st
    add_many(st, b)

    st, b = call(c, "GET", "/api/v1/repos/search?limit=50")
    sources["search"] = st
    add_many(st, b)

    return {"urls": sorted(urls), "sources": sources}


def freeze_snapshot(tag: str, payload: dict) -> dict:
    """把模型写盘并立即复读摘要；返回 {file, sha256}。"""
    raw = canon(payload)
    p = RESULTS / f"{tag}.json"
    p.write_bytes(raw)
    h = sha(raw)
    if sha(p.read_bytes()) != h:                       # 同一次调用内自检
        raise RuntimeError(f"冻结文件复读摘要不一致: {p}")
    return {"file": str(p), "sha256": h, "bytes": len(raw)}


def snapshot_still_frozen(rec: dict) -> bool:
    return sha(Path(rec["file"]).read_bytes()) == rec["sha256"]


# ---------------------------------------------------------------------------
# 观测量
# ---------------------------------------------------------------------------
def read_sha(c: Client, obj: str, path: str = "README.md"):
    st, b = call(c, "GET", f"/api/v1/repos/{obj}/raw/{path}")
    if st == 200 and isinstance(b, str):
        return st, sha(b.encode("utf-8"))
    return st, None


def oracle(cl, obj: str, subject: str, vantage: str) -> dict:
    """vantage = 凭证用户名；anonymous 无 oracle 视点。"""
    if subject == "anonymous" or vantage == "anonymous":
        return {"status": None, "permission": None, "answer": "unknown",
                "vantage": None, "abstain_reason": "oracle_unreadable",
                "independence": "shared",
                "note": "permission endpoint requires a credential"}
    st, b = call(cl[vantage], "GET",
                 f"/api/v1/repos/{obj}/collaborators/{subject}/permission")
    perm = b.get("permission") if isinstance(b, dict) else None
    answer = ("allow" if perm in ("owner", "read", "write", "admin")
              else "deny" if perm == "none" else "unknown")
    return {"status": st, "permission": perm, "answer": answer,
            "vantage": vantage, "independence": "shared",
            "abstain_reason": None if answer != "unknown" else "oracle_unreadable"}


def write_file(cl, obj, subject, path, text) -> int:
    body = {"files": [{"operation": "create", "path": path,
                       "content": base64.b64encode(text.encode()).decode()}]}
    st, _ = call(cl[subject], "POST", f"/api/v1/repos/{obj}/contents", body)
    return st


def write_probe(cl, obj: str, subject: str) -> dict:
    """内容级写探针：主体写，拥有者复读，拥有者删除并复读 404。"""
    owner = OBJ_CRED[obj]
    marker = f"wb-probe-{uuid.uuid4().hex[:10]}"
    path = f"{marker}.txt"
    _, sha_before = read_sha(cl[owner], obj)
    st0, _ = call(cl[owner], "GET", f"/api/v1/repos/{obj}/raw/{path}")
    if st0 == 200:
        return {"object": obj, "subject": subject, "error": "probe path exists"}
    st = write_file(cl, obj, subject, path, marker)
    st_v, txt = call(cl[owner], "GET", f"/api/v1/repos/{obj}/raw/{path}")
    changed = bool(st_v == 200 and isinstance(txt, str) and txt == marker)
    restored = False
    if changed:
        st_m, meta = call(cl[owner], "GET", f"/api/v1/repos/{obj}/contents/{path}")
        if st_m == 200 and isinstance(meta, dict):
            call(cl[owner], "DELETE", f"/api/v1/repos/{obj}/contents/{path}",
                 {"sha": meta.get("sha"), "message": "temporal probe cleanup"})
            st_d, _ = call(cl[owner], "GET", f"/api/v1/repos/{obj}/raw/{path}")
            restored = st_d == 404
    _, sha_after = read_sha(cl[owner], obj)
    return {"object": obj, "subject": subject, "write_status": st,
            "content_changed": changed, "restored": restored,
            "readme_unchanged": bool(sha_before and sha_before == sha_after),
            "observed_effect": "allow" if changed else "deny",
            "note": "" if changed else ("transport-error" if st == 0 else "denied")}


# ---------------------------------------------------------------------------
# 一轮：冻结 → 变更 → recrawl → 观测 → 判定
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, cl, team_id: int, proto_digest: str):
        self.cl = cl
        self.pm = baseline_policy(team_id)
        self.hv = 0
        self.event_seq = 0
        self.proto_digest = proto_digest
        self.policy_events: list[dict] = []
        self.cycles: list[dict] = []

    def _commit(self, kind: str, actor: str, obj: str, subject: str,
                st: int, body, ledger_fn) -> bool:
        """成功才递增 hv 并改台账；失败原样留痕。"""
        ok = 200 <= st < 300
        ev = {"event_seq": self.event_seq + (1 if ok else 0),
              "mutation": kind, "actor": actor, "object": obj, "subject": subject,
              "http_status": st, "committed": ok, "committed_at": now(),
              "hv_before": self.hv, "hv_after": self.hv + (1 if ok else 0),
              "error": None if ok else str(body)[:240]}
        if ok:
            self.event_seq += 1
            self.hv += 1
            ledger_fn()
        self.policy_events.append(ev)
        return ok

    def cycle(self, seq: int, kind: str, obj: str, subject: str,
              mutate, ledger_fn, actor: str = "unknown",
              extra_probe=None) -> dict:
        t0 = now()
        hv_before = self.hv
        subs = SUBJECTS
        m0 = {s: crawl(self.cl[s]) for s in subs}
        rec0 = freeze_snapshot(f"M0_{seq:02d}_{kind}",
                               {"seq": seq, "kind": kind, "hv": self.hv,
                                "subjects": m0})
        t_freeze = now()
        frozen_ok = snapshot_still_frozen(rec0)

        pre = extra_probe("pre") if extra_probe else None

        st, body = mutate()
        committed = self._commit(kind, actor, obj, subject, st, body, ledger_fn)
        t_mut = now()
        hv_e = self.hv

        m1 = {s: crawl(self.cl[s]) for s in subs}
        rec1 = freeze_snapshot(f"M1_{seq:02d}_{kind}",
                               {"seq": seq, "kind": kind, "hv": hv_e, "subjects": m1})
        t_recrawl = now()

        # 探针前最后一次复核：M0 必须仍未改变，hv 必须未再变
        m0_intact = snapshot_still_frozen(rec0)
        version_ok = (self.hv == hv_e)
        cycle_abstain = (None if (m0_intact and version_ok and committed and frozen_ok)
                         else "snapshot_mutated" if not (m0_intact and frozen_ok)
                         else "version_mismatch" if not version_ok
                         else "mutation_failed")

        owner_sha = {}
        for o in OBJECTS:
            st_o, h = read_sha(self.cl[OBJ_CRED[o]], o)
            owner_sha[o] = h
            if h is None:
                cycle_abstain = cycle_abstain or "owner_read_failed"

        cells = []
        for o in OBJECTS:
            for s in subs:
                # 静止窗口内：oracle 先于探针（两者都是只读 GET，顺序不影响状态）
                o_owner = oracle(self.cl, o, s, OBJ_CRED[o])
                o_self = oracle(self.cl, o, s, s if s != "anonymous" else "anonymous")
                st_r, h = read_sha(self.cl[s], o)
                y_allow = bool(st_r == 200 and h is not None and h == owner_sha[o])
                dec = self.pm.expected(o, s, "read")
                role = "owner" if s == OBJ_CRED[o] else "cross"
                m0r = o in set(m0[s]["urls"])
                m1r = o in set(m1[s]["urls"])
                a_stale = bool((not m0r) and y_allow and role == "cross")
                a_live = bool((not m1r) and y_allow and role == "cross")
                v_stale = classify(dec.value, y_allow, a_stale, a_stale)
                v_live = classify(dec.value, y_allow, a_live, a_live)
                cells.append({
                    "run_id": RUN_ID,
                    "case_id": f"{seq:02d}:{o}:{s}:read",
                    "system_version": gl.GITEA_VERSION,
                    "object": o, "subject": s, "action": "read", "role": role,
                    "event_seq": self.event_seq,
                    "timestamp": now(),
                    "M0_hash": rec0["sha256"], "M1_hash": rec1["sha256"],
                    "policy_version": hv_e,
                    "policy_version_kind": "harness-logical",
                    "expected_entitlement": dec.value,
                    "expected_channel": dec.channel,
                    "expected_basis": list(dec.basis),
                    "oracle_answer": o_owner["answer"],
                    "oracle_status": o_owner["status"],
                    "oracle_vantage": o_owner["vantage"],
                    "oracle_permission": o_owner["permission"],
                    "oracle_independence": o_owner["independence"],
                    "oracle_self_answer": o_self["answer"],
                    "oracle_self_status": o_self["status"],
                    "oracle_abstain_reason": o_owner["abstain_reason"],
                    "observed_effect": "allow" if y_allow else "deny",
                    "observed_status": st_r,
                    "read_order": "oracle_then_probe",
                    "A_stale": a_stale, "H_stale": a_stale,
                    "T_stale": v_stale["category"],
                    "A_live": a_live, "H_live": a_live,
                    "T_live": v_live["category"],
                    "abstain_reason": cycle_abstain or (
                        "transport_error" if st_r == 0 else None),
                    "M0_reachable": m0r, "M1_reachable": m1r,
                    "stale_missing_legit": bool(dec.value == "allow" and not m0r and y_allow),
                    "live_missing_legit": bool(dec.value == "allow" and not m1r and y_allow),
                })

        post = extra_probe("post") if extra_probe else None
        t_probe = now()

        cross = [c for c in cells if c["role"] == "cross" and c["abstain_reason"] is None]
        stale_fp = [c for c in cross if c["T_stale"] == "false_proof"]
        live_fp = [c for c in cross if c["T_live"] == "false_proof"]
        fixed = [c for c in cross
                 if c["stale_missing_legit"] and not c["live_missing_legit"]]
        still = [c for c in cross
                 if c["live_missing_legit"]]
        tp = [c for c in cross if c["T_live"] == "true_positive"]
        over = [c for c in cross
                if c["M0_reachable"] and not c["M1_reachable"]
                and c["expected_entitlement"] == "deny"
                and c["observed_effect"] == "deny"]

        cyc = {
            "seq": seq, "kind": kind, "object": obj, "subject": subject,
            "committed": committed, "mutation_status": st, "actor": actor,
            "hv_before": hv_before,
            "hv_after": hv_e,
            "t_freeze": t_freeze, "t_mutation": t_mut,
            "t_recrawl": t_recrawl, "t_probe": t_probe,
            "M0": rec0, "M1": rec1,
            "M0_verified_unchanged": m0_intact,
            "version_consistent": version_ok,
            "abstain_reason": cycle_abstain,
            "cells": cells,
            "write_pre": pre, "write_post": post,
            "summary": {
                "cells_total": len(cells),
                "cells_cross_scored": len(cross),
                "E_allow": sum(1 for c in cross if c["expected_entitlement"] == "allow"),
                "E_deny": sum(1 for c in cross if c["expected_entitlement"] == "deny"),
                "E_unknown": sum(1 for c in cross if c["expected_entitlement"] == "unknown"),
                "Y_allow": sum(1 for c in cross if c["observed_effect"] == "allow"),
                "E_eq_Y": sum(1 for c in cross
                              if (c["expected_entitlement"] == "allow")
                              == (c["observed_effect"] == "allow")),
                "stale_false_proofs": len(stale_fp),
                "live_false_proofs": len(live_fp),
                "stale_missing_legit": sum(1 for c in cross if c["stale_missing_legit"]),
                "live_missing_legit": sum(1 for c in cross if c["live_missing_legit"]),
                "recrawl_fixed": len(fixed),
                "recrawl_still_misses": len(still),
                "stale_over_after_revoke": len(over),
                "true_positives": len(tp),
                "oracle_readable": sum(1 for c in cross if c["oracle_answer"] in ("allow", "deny")),
                "oracle_self_readable": sum(1 for c in cross
                                            if c["oracle_self_answer"] in ("allow", "deny")),
            },
        }
        self.cycles.append(cyc)
        s = cyc["summary"]
        print(f"  [{seq:02d}] {kind:52s} hv={self.hv} "
              f"staleFP={s['stale_false_proofs']} liveFP={s['live_false_proofs']} "
              f"fixed={s['recrawl_fixed']} miss={s['recrawl_still_misses']} "
              f"TP={s['true_positives']}", flush=True)
        return cyc


# ---------------------------------------------------------------------------
# 校准
# ---------------------------------------------------------------------------
def calibrate(cl) -> dict:
    """6 个已知格，6/6 才继续；校准格不进正式分母。

    副视点（主体自己的凭证）在 Gitea 1.22.6 上对 read 协作者返回 403、
    对无权限者返回 404 ⇒ 只能记 unreadable，不能把不可读当 deny。
    """
    cal_obj = "dave/cal"
    checks = []

    def chk(case, subject, vantage, expect):
        o = oracle(cl, cal_obj, subject, vantage)
        if expect == "unreadable":
            ok = (o["answer"] == "unknown" and o["status"] in (403, 404))
        else:
            ok = (o["answer"] == expect)
        checks.append({"case": case, "subject": subject, "vantage": vantage,
                       "expected": expect, "observed": o["answer"],
                       "status": o["status"], "permission": o["permission"], "ok": ok})
        return ok

    chk("owner_on_own_private", "dave", "dave", "allow")
    chk("collaborator_read_on_private", "carol", "dave", "allow")
    chk("non_collaborator_on_private", "erin", "dave", "deny")
    chk("owner_self_vantage", "dave", "dave", "allow")
    chk("collaborator_self_vantage", "carol", "carol", "unreadable")
    chk("non_collaborator_self_vantage", "erin", "erin", "unreadable")
    return {"object": cal_obj, "checks": checks,
            "passed": all(c["ok"] for c in checks),
            "secondary_vantage_admissible": False,
            "note": ("副视点：read 协作者 403、外人 404 ⇒ 既不能确认也不能否认，"
                     "只作诊断列，不充当 oracle")}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    proto_raw = PROTO.read_bytes()
    proto_digest = sha(proto_raw)
    proto = json.loads(proto_raw.decode("utf-8"))

    cfg = write_config()
    print(f"[B] lab={gl.LAB} port={gl.PORT} version={gl.GITEA_VERSION}")
    print("[A] migrate/admin:", ensure_migrated(cfg), flush=True)

    with Server(cfg) as srv:
        print(f"[A] ready version={gl.version()} ready_ms={srv.ready_ms}", flush=True)
        cl = clients()
        topo = setup(cl)
        print(f"    setup steps={len(topo['steps'])} all_ok=True", flush=True)

        cal = calibrate(cl)
        print(f"[C] calibration {sum(c['ok'] for c in cal['checks'])}/"
              f"{len(cal['checks'])} passed={cal['passed']}", flush=True)
        for c in cal["checks"]:
            print(f"      {c['case']:34s} expected={c['expected']:8s} "
                  f"observed={c['observed']:8s} status={c['status']}", flush=True)
        if not cal["passed"]:
            raise RuntimeError("oracle 校准未通过，按预注册协议中止，不产生正式格")

        team_id = topo["team_id"]
        r = Runner(cl, team_id, proto_digest)

        def ledger(kind, obj, subject):
            def fn():
                if kind == "grant_collaborator":
                    r.pm.add_collaborator(obj, subject, "read", f"hv{r.hv}:{kind}")
                elif kind == "revoke_collaborator":
                    r.pm.collaborators.pop((obj, subject), None)
                    r.pm._log("revoke_collaborator", f"{obj} -= {subject}", f"hv{r.hv}")
                elif kind == "team_repo_attach":
                    r.pm.add_team_repo("dev", obj, f"hv{r.hv}:{kind}")
                elif kind == "team_member_remove":
                    r.pm.team_members["dev"].discard(subject)
                    r.pm._log("team_member_remove", f"dev -= {subject}", f"hv{r.hv}")
                elif kind == "visibility_public":
                    r.pm.set_visibility(obj, False, f"hv{r.hv}:{kind}")
                elif kind == "visibility_private":
                    r.pm.set_visibility(obj, True, f"hv{r.hv}:{kind}")
                elif kind == "role_write":
                    r.pm.add_collaborator(obj, subject, "write", f"hv{r.hv}:{kind}")
                elif kind == "site_admin":
                    r.pm.add_site_admin(subject, f"hv{r.hv}:{kind}")
            return fn

        # ---- T1 直接授权 ---------------------------------------------------
        r.cycle(1, "grant_collaborator", "alice/priv1", "carol",
                lambda: call(cl["alice"], "PUT",
                             "/api/v1/repos/alice/priv1/collaborators/carol",
                             {"permission": "read"}),
                ledger("grant_collaborator", "alice/priv1", "carol"),
                actor="alice")

        # ---- T2 直接撤销 ---------------------------------------------------
        r.cycle(2, "revoke_collaborator", "alice/priv2", "bob",
                lambda: call(cl["alice"], "DELETE",
                             "/api/v1/repos/alice/priv2/collaborators/bob"),
                ledger("revoke_collaborator", "alice/priv2", "bob"),
                actor="alice")

        # ---- T3 团队继承授权 -----------------------------------------------
        r.cycle(3, "team_repo_attach", "acme/t2", "bob",
                lambda: call(cl["dave"], "PUT",
                             f"/api/v1/teams/{team_id}/repos/{ORG}/t2"),
                ledger("team_repo_attach", "acme/t2", "bob"),
                actor="dave")

        # ---- T4 移除团队成员，但直授仍在 -----------------------------------
        r.cycle(4, "team_member_remove", "acme/t1", "bob",
                lambda: call(cl["dave"], "DELETE",
                             f"/api/v1/teams/{team_id}/members/bob"),
                ledger("team_member_remove", "acme/t1", "bob"),
                actor="dave")

        # ---- T5 私有 -> 公开 -----------------------------------------------
        r.cycle(5, "visibility_public", "dave/r1", "erin",
                lambda: call(cl["dave"], "PATCH", "/api/v1/repos/dave/r1",
                             {"private": False}),
                ledger("visibility_public", "dave/r1", "erin"),
                actor="dave")

        # ---- T6 公开 -> 私有 -----------------------------------------------
        r.cycle(6, "visibility_private", "alice/pub1", "erin",
                lambda: call(cl["alice"], "PATCH", "/api/v1/repos/alice/pub1",
                             {"private": True}),
                ledger("visibility_private", "alice/pub1", "erin"),
                actor="alice")

        # ---- T7 角色 read -> write（先测写前拒绝，再测写后允许） -------------
        r.cycle(7, "role_write", "dave/r2", "carol",
                lambda: call(cl["dave"], "PUT",
                             "/api/v1/repos/dave/r2/collaborators/carol",
                             {"permission": "write"}),
                ledger("role_write", "dave/r2", "carol"),
                actor="dave",
                extra_probe=lambda when: write_probe(cl, "dave/r2", "carol"))

        # ---- T8 站点管理员授予 ---------------------------------------------
        r.cycle(8, "site_admin", "(all)", "erin",
                lambda: call(cl[ADMIN_USER], "PATCH", "/api/v1/admin/users/erin",
                             {"login_name": "erin", "source_id": 0, "admin": True}),
                ledger("site_admin", "(all)", "erin"),
                actor=ADMIN_USER)

    # ---- 汇总 --------------------------------------------------------------
    cross = [c for cy in r.cycles for c in cy["cells"]
             if c["role"] == "cross" and c["abstain_reason"] is None]
    totals = {
        "cycles": len(r.cycles),
        "cycles_scored": sum(1 for cy in r.cycles if cy["abstain_reason"] is None),
        "cells": len(cross),
        "E_allow": sum(1 for c in cross if c["expected_entitlement"] == "allow"),
        "E_deny": sum(1 for c in cross if c["expected_entitlement"] == "deny"),
        "E_unknown": sum(1 for c in cross if c["expected_entitlement"] == "unknown"),
        "Y_allow": sum(1 for c in cross if c["observed_effect"] == "allow"),
        "E_eq_Y": sum(1 for c in cross
                      if (c["expected_entitlement"] == "allow")
                      == (c["observed_effect"] == "allow")),
        "stale_false_proofs": sum(1 for c in cross if c["T_stale"] == "false_proof"),
        "live_false_proofs": sum(1 for c in cross if c["T_live"] == "false_proof"),
        "stale_missing_legit": sum(1 for c in cross if c["stale_missing_legit"]),
        "live_missing_legit": sum(1 for c in cross if c["live_missing_legit"]),
        "recrawl_fixed": sum(1 for c in cross
                             if c["stale_missing_legit"] and not c["live_missing_legit"]),
        "recrawl_still_misses": sum(1 for c in cross if c["live_missing_legit"]),
        "true_positives": sum(1 for c in cross if c["T_live"] == "true_positive"),
        "oracle_readable": sum(1 for c in cross
                               if c["oracle_answer"] in ("allow", "deny")),
        "oracle_self_readable": sum(1 for c in cross
                                    if c["oracle_self_answer"] in ("allow", "deny")),
        "abstained_cells": sum(1 for cy in r.cycles for c in cy["cells"]
                               if c["abstain_reason"] is not None),
    }

    rep = {
        "meta": {
            "run_id": RUN_ID,
            "system": "Gitea",
            "version": gl.GITEA_VERSION,
            "exe_sha256": sha(gl.GITEA_EXE.read_bytes()),
            "lab_dir": str(gl.LAB),
            "port": gl.PORT,
            "started_at": now(),
            "elapsed_s": round(time.time() - t_start, 1),
            "generated_by": "experiments/real_system/run_temporal.py",
            "protocol_id": proto["protocol_id"],
            "protocol_sha256": proto_digest,
            "policy_version_kind": "harness-logical",
            "policy_version_note": proto["versioning"]["honesty_note"],
            "order": "freeze -> mutate -> recrawl -> oracle -> probe",
            "honesty_boundary": (
                "E 来自台账；Y 来自内容复读；O 与 enforcement 同源，不参与 TP/FP；"
                "只报本拓扑格数，不外推部署发生率；撤销后旧模型仍可达但被拒绝不算漏检。"),
        },
        "setup": topo,
        "calibration": cal,
        "transitions": r.cycles,
        "policy_events": r.policy_events,
        "policy_ledger": r.pm.ledger,
        "totals": totals,
    }
    out = RESULTS / "temporal_gitea.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== totals ===")
    for k, v in totals.items():
        print(f"  {k:26s} {v}")
    print(f"[done] {out} ({out.stat().st_size} bytes, {rep['meta']['elapsed_s']}s)")


if __name__ == "__main__":
    main()

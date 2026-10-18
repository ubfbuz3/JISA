"""
B · 真时序实验（GitLab CE 17.11.7）
====================================

与 `run_temporal.py`（Gitea）同一套预注册协议、同一套 E/Y/O 定义，
只替换产品适配层。目的不是"再跑一遍"，而是回答单产品无法回答的问题：
**同一套协议在另一个产品的授权机制上是否给出同样的结论**，以及
产品之间在 oracle 可读性上的差异有多大。

协议
----
`c_protocol.json`（sha256 d09d9047…，逐字节复用 Gitea 那次）
+ `c_protocol_amendment_a1.json`（在观察任何 GitLab 响应之前写下：
  校准门槛改为 primary vantage 4/4，副视点只作诊断列）。

八类转移（与 Gitea 一一对应，机制按 GitLab 的表达实现）
------------------------------------------------------
  T1 直接授权   POST /projects/:id/members {access_level:20}
  T2 直接撤销   DELETE /projects/:id/members/:uid
  T3 组继承     POST /projects/:id/share {group_id, group_access:20}
  T4 移除组成员 DELETE /groups/:id/members/:uid（替代通道在**组外**的 dave/r4）
  T5 私有→公开  PUT /projects/:id {visibility:"public"}
  T6 公开→私有  PUT /projects/:id {visibility:"private"}
  T7 read→write PUT /projects/:id/members/:uid {access_level:30} + 写探针
  T8 站点管理员 PUT /users/:id {admin:true}

诚实边界（写死在脚本里，与 Gitea 版一致）
  1. hv 是 harness 逻辑版本，不是服务端原子快照号。
  2. oracle 与 enforcement 同源，`independence = shared`，O 不参与 TP/FP。
  3. 副视点对 deny 格 404 是**歧义**（可能无权限，也可能看不见对象）⇒ unknown。
  4. GitLab 的 `members/all` 不建模站点管理员 ⇒ admin 格上 O 与 E 会分歧，
     这是 oracle 保真度差异，如实记录，不用它改 E。
  5. 只报本拓扑格数，不外推部署发生率。

用法:
  GL_LAB_CONTAINER=gitlab-temporal GL_LAB_PORT=3321 \
  GL_LAB_DIR=C:/Users/Administrator/WorkBuddy/gitlab_temporal_lab \
  python run_temporal_gitlab.py [--keep]
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.parse
import uuid
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUN_ID = time.strftime("%Y%m%d_%H%M%S")

os.environ.setdefault("GL_LAB_CONTAINER", "gitlab-temporal")
os.environ.setdefault("GL_LAB_PORT", "3321")
os.environ.setdefault(
    "GL_LAB_DIR",
    str(Path(r"C:\Users\Administrator\WorkBuddy") / f"gitlab_temporal_{RUN_ID}"))

sys.path.insert(0, str(HERE))
import gitlab_lab as gl                                      # noqa: E402
from entitlement import PolicyModel, classify                # noqa: E402
from gitlab_lab import ADMIN_USER, API, Client                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PROTO = HERE / "c_protocol.json"
AMEND = HERE / "c_protocol_amendment_a1.json"
AMEND2 = HERE / "c_protocol_amendment_a2.json"
RESULTS = HERE / "results" / "temporal"
RESULTS.mkdir(parents=True, exist_ok=True)

ORG = "acme"
USERS = ["alice", "bob", "carol", "dave", "eve", "frank"]
SUBJECTS = USERS + ["anonymous"]

# access_level：Guest 10 < Reporter 20 < Developer 30 < Maintainer 40 < Owner 50
READ = 20      # Reporter：可读代码
WRITE = 30     # Developer：可写（新分支）

# (object, private, credential that owns it)
REPOS = [
    ("alice/priv1", True,  "alice"),   # T1 直接授权
    ("alice/priv2", True,  "alice"),   # T2 直接撤销
    ("alice/pub1",  False, "alice"),   # T6 公开 -> 私有
    ("acme/t1",     True,  "dave"),    # T4 组员移除后直授仍在
    ("acme/t2",     True,  "dave"),    # T4 的对照：无直授 ⇒ 应失去
    ("dave/r1",     True,  "dave"),    # T5 私有 -> 公开
    ("dave/r2",     True,  "dave"),    # T7 read -> write
    ("dave/r3",     True,  "dave"),    # T3 共享给组（继承授权）
    ("dave/r4",     True,  "dave"),    # T4 的替代通道：组外直授，不受组变更影响
]
OBJECTS = [r[0] for r in REPOS]
OBJ_CRED = {o: cr for o, _, cr in REPOS}
PRIVATE = {o: p for o, p, _ in REPOS}

PIDS: dict[str, int] = {}
UIDS: dict[str, int] = {}
GID: int | None = None
BRANCH: dict[str, str] = {}


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


def q(s: str) -> str:
    return urllib.parse.quote(s, safe="")


def call(c: Client, method: str, path: str, body=None, retries: int = 2):
    """status 0 = 传输失败；按协议重试两次后再放弃。"""
    st, b = 0, None
    for _ in range(retries + 1):
        st, b = c.req(method, path, body)
        if st != 0:
            return st, b
        time.sleep(0.25)
    return st, b


def enc(obj: str) -> str:
    return urllib.parse.quote(obj, safe="")


# ---------------------------------------------------------------------------
# 阶段 A · 基线拓扑
# ---------------------------------------------------------------------------
def setup(cl: dict[str, Client]) -> dict:
    steps: list[dict] = []
    global GID

    def rec(label, st, body, **extra):
        ok = 200 <= st < 300
        steps.append({"step": label, "status": st, "ok": ok,
                      "error": None if ok else str(body)[:200], **extra})
        return ok

    dave = cl["dave"]
    rec("group:acme", *call(dave, "POST", f"{API}/groups", {
        "name": ORG, "path": ORG, "visibility": "private"}))
    st, b = call(dave, "GET", f"{API}/groups/{ORG}")
    GID = b.get("id") if isinstance(b, dict) else None

    for obj, priv, creator in REPOS:
        owner, name = obj.split("/")
        body = {"name": name, "path": name,
                "visibility": "private" if priv else "public",
                "initialize_with_readme": True, "description": "temporal lab"}
        if owner == ORG:
            body["namespace_id"] = GID
        rec(f"repo:{obj}", *call(cl[creator], "POST", f"{API}/projects", body))

    # 解析数字 id（成员端点要 uid/pid，不要 username/path）
    for u, meta in gl.users().items():
        st, b = call(cl[ADMIN_USER], "GET", f"{API}/users?username={u}")
        UIDS[u] = b[0]["id"] if (st == 200 and isinstance(b, list) and b) else None
    for obj in OBJECTS:
        st, b = call(cl[OBJ_CRED[obj]], "GET", f"{API}/projects/{enc(obj)}")
        PIDS[obj] = b.get("id") if isinstance(b, dict) else None
        BRANCH[obj] = (b.get("default_branch") or "main") if isinstance(b, dict) else "main"

    # 基线授权（全部发生在第一次采集之前）
    rec("baseline: group acme <- bob (Reporter)",
        *call(dave, "POST", f"{API}/groups/{GID}/members",
              {"user_id": UIDS["bob"], "access_level": READ}))
    # 替代通道必须落在组外：GitLab 在移除组成员时会连带删除该组项目的
    # 项目级成员记录（修正案 A2 的实测证据），若把直授放在 acme/t1，
    # 测到的就不是"多通道"，而是这条连带规则本身。
    rec("baseline: dave/r4 <- bob (Reporter, alt channel outside the group)",
        *call(dave, "POST", f"{API}/projects/{PIDS['dave/r4']}/members",
              {"user_id": UIDS["bob"], "access_level": READ}))
    rec("baseline: alice/priv2 <- bob (Reporter)",
        *call(cl["alice"], "POST", f"{API}/projects/{PIDS['alice/priv2']}/members",
              {"user_id": UIDS["bob"], "access_level": READ}))
    rec("baseline: dave/r2 <- carol (Reporter)",
        *call(dave, "POST", f"{API}/projects/{PIDS['dave/r2']}/members",
              {"user_id": UIDS["carol"], "access_level": READ}))

    # 校准对象：一次性，不进正式分母
    rec("cal: dave/cal private", *call(dave, "POST", f"{API}/projects", {
        "name": "cal", "path": "cal", "visibility": "private",
        "initialize_with_readme": True, "description": "calibration"}))
    st, b = call(dave, "GET", f"{API}/projects/{enc('dave/cal')}")
    PIDS["dave/cal"] = b.get("id") if isinstance(b, dict) else None
    BRANCH["dave/cal"] = (b.get("default_branch") or "main") if isinstance(b, dict) else "main"
    rec("cal: dave/cal <- carol (Reporter)",
        *call(dave, "POST", f"{API}/projects/{PIDS['dave/cal']}/members",
              {"user_id": UIDS["carol"], "access_level": READ}))

    failures = [s for s in steps if not s["ok"]]
    if failures:
        raise RuntimeError("setup 有失败步骤: "
                           + json.dumps(failures[:3], ensure_ascii=False))
    return {"steps": steps, "group_id": GID,
            "pids": dict(PIDS), "uids": dict(UIDS)}


def baseline_policy() -> PolicyModel:
    """只由 setup 事务构造，不读任何探针响应。"""
    m = PolicyModel()
    m.add_org(ORG, "dave", "setup: group created by dave")
    for obj, priv, _ in REPOS:
        owner = obj.split("/")[0] if not obj.startswith(f"{ORG}/") else ORG
        m.add_repo(obj, owner, priv, "setup: project creation")
    m.add_site_admin(ADMIN_USER, "lab admin bootstrap")
    m.add_team(ORG, "read", "setup: group acme (Reporter)")
    m.add_team_member(ORG, "bob", "setup: group acme <- bob")
    # GitLab：组项目对组员自动可见 = "team repo" 全组挂载
    m.add_team_repo(ORG, "acme/t1", "setup: group project")
    m.add_team_repo(ORG, "acme/t2", "setup: group project")
    m.add_collaborator("dave/r4", "bob", "read", "setup: dave/r4 <- bob (alt, outside group)")
    m.add_collaborator("alice/priv2", "bob", "read", "setup: alice/priv2 <- bob")
    m.add_collaborator("dave/r2", "carol", "read", "setup: dave/r2 <- carol")
    return m


# ---------------------------------------------------------------------------
# 采集 / 冻结 / 观测量
# ---------------------------------------------------------------------------
def crawl(c: Client) -> dict:
    urls: set[str] = set()
    sources: dict[str, int] = {}

    def add(st, body):
        if st != 200:
            return
        rows = body if isinstance(body, list) else []
        for r in rows:
            if isinstance(r, dict) and r.get("path_with_namespace"):
                urls.add(r["path_with_namespace"])

    st, b = call(c, "GET", f"{API}/projects?membership=true&per_page=100")
    sources["membership"] = st
    add(st, b)

    st, b = call(c, "GET", f"{API}/groups/{ORG}/projects?per_page=100")
    sources["group_projects"] = st
    add(st, b)

    st, b = call(c, "GET", f"{API}/projects?per_page=100")
    sources["visible"] = st
    add(st, b)

    return {"urls": sorted(urls), "sources": sources}


def freeze_snapshot(tag: str, payload: dict) -> dict:
    raw = canon(payload)
    p = RESULTS / f"{tag}.json"
    p.write_bytes(raw)
    h = sha(raw)
    if sha(p.read_bytes()) != h:
        raise RuntimeError(f"冻结文件复读摘要不一致: {p}")
    return {"file": str(p), "sha256": h, "bytes": len(raw)}


def snapshot_still_frozen(rec: dict) -> bool:
    return sha(Path(rec["file"]).read_bytes()) == rec["sha256"]


def read_sha(c: Client, obj: str, path: str = "README.md", ref: str | None = None):
    st, b = call(c, "GET",
                 f"{API}/projects/{PIDS[obj]}/repository/files/{q(path)}/raw"
                 f"?ref={ref or BRANCH[obj]}")
    if st == 200 and isinstance(b, str):
        return st, sha(b.encode("utf-8"))
    return st, None


def oracle(cl, obj: str, subject: str, vantage: str) -> dict:
    """primary vantage = 对象拥有者；200 = 成员，404 = 非成员。

    ⚠️ 404 只在**视点能看见该项目**时才是"非成员"。项目拥有者总看得见，
    所以 primary 视点的 404 可判 deny；副视点看不见项目时 404 是歧义 ⇒ unknown。
    """
    if subject == "anonymous" or vantage == "anonymous":
        return {"status": None, "permission": None, "answer": "unknown",
                "vantage": None, "abstain_reason": "oracle_unreadable",
                "independence": "shared",
                "note": "members endpoint requires a credential"}
    st, b = call(cl[vantage], "GET",
                 f"{API}/projects/{PIDS[obj]}/members/all/{UIDS[subject]}")
    if st == 200:
        lvl = b.get("access_level") if isinstance(b, dict) else None
        return {"status": st, "permission": {10: "read", 20: "read", 30: "write",
                                             40: "admin", 50: "admin"}.get(lvl, "read"),
                "access_level": lvl, "answer": "allow",
                "vantage": vantage, "independence": "shared",
                "abstain_reason": None}
    if st == 404:
        return {"status": st, "permission": "none", "access_level": None,
                "answer": "deny", "vantage": vantage, "independence": "shared",
                "abstain_reason": None}
    return {"status": st, "permission": None, "access_level": None,
            "answer": "unknown", "vantage": vantage, "independence": "shared",
            "abstain_reason": "oracle_unreadable"}


def write_probe(cl, obj: str, subject: str) -> dict:
    """内容级写探针：主体在**新分支**上建文件 → 拥有者复读 → 删分支 → 复读 404。

    用新分支而不是默认分支，是为了避开 GitLab 默认分支保护：
    默认分支上 Developer 未必能推，但那不是"有无写权限"的证据。
    """
    owner = OBJ_CRED[obj]
    marker = f"wb-probe-{uuid.uuid4().hex[:10]}"
    path = f"{marker}.txt"
    branch = f"wb-probe-{uuid.uuid4().hex[:10]}"
    st = 0
    st, _ = call(cl[subject], "POST",
                 f"{API}/projects/{PIDS[obj]}/repository/files/{q(path)}",
                 {"branch": branch, "start_branch": BRANCH[obj],
                  "content": marker, "commit_message": "temporal write probe"})
    st_v, txt = call(cl[owner], "GET",
                     f"{API}/projects/{PIDS[obj]}/repository/files/{q(path)}/raw"
                     f"?ref={branch}")
    changed = bool(st_v == 200 and isinstance(txt, str) and txt == marker)
    restored = False
    if changed:
        st_d, _ = call(cl[owner], "DELETE",
                       f"{API}/projects/{PIDS[obj]}/repository/branches/{q(branch)}")
        st_c, _ = call(cl[owner], "GET",
                       f"{API}/projects/{PIDS[obj]}/repository/branches/{q(branch)}")
        restored = bool(st_d < 400 and st_c == 404)
    return {"object": obj, "subject": subject, "branch": branch,
            "write_status": st, "content_changed": changed, "restored": restored,
            "observed_effect": "allow" if changed else "deny",
            "note": "" if changed else ("transport-error" if st == 0 else "denied")}


# ---------------------------------------------------------------------------
# 一轮
# ---------------------------------------------------------------------------
class Runner:
    def __init__(self, cl, proto_digest: str, amend_digest: str):
        self.cl = cl
        self.pm = baseline_policy()
        self.hv = 0
        self.event_seq = 0
        self.proto_digest = proto_digest
        self.amend_digest = amend_digest
        self.policy_events: list[dict] = []
        self.cycles: list[dict] = []

    def _commit(self, kind, actor, obj, subject, st, body, ledger_fn) -> bool:
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

    def cycle(self, seq, kind, obj, subject, mutate, ledger_fn,
              actor="unknown", extra_probe=None) -> dict:
        t0 = now()
        hv_before = self.hv
        subs = SUBJECTS
        m0 = {s: crawl(self.cl[s]) for s in subs}
        rec0 = freeze_snapshot(f"GL_M0_{seq:02d}_{kind}",
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
        rec1 = freeze_snapshot(f"GL_M1_{seq:02d}_{kind}",
                               {"seq": seq, "kind": kind, "hv": hv_e,
                                "subjects": m1})
        t_recrawl = now()

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
                    "system": "GitLab", "system_version": gl.GITLAB_VERSION,
                    "object": o, "subject": s, "action": "read", "role": role,
                    "event_seq": self.event_seq, "timestamp": now(),
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
                    "oracle_access_level": o_owner.get("access_level"),
                    "oracle_independence": o_owner["independence"],
                    "oracle_self_answer": o_self["answer"],
                    "oracle_self_status": o_self["status"],
                    "oracle_abstain_reason": o_owner["abstain_reason"],
                    "oracle_matches_E": (None if o_owner["answer"] not in ("allow", "deny")
                                         else (o_owner["answer"] == "allow")
                                         == (dec.value == "allow")),
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
        fixed = [c for c in cross if c["stale_missing_legit"] and not c["live_missing_legit"]]
        still = [c for c in cross if c["live_missing_legit"]]
        tp = [c for c in cross if c["T_live"] == "true_positive"]
        over = [c for c in cross
                if c["M0_reachable"] and not c["M1_reachable"]
                and c["expected_entitlement"] == "deny"
                and c["observed_effect"] == "deny"]

        cyc = {
            "seq": seq, "kind": kind, "object": obj, "subject": subject,
            "committed": committed, "mutation_status": st, "actor": actor,
            "hv_before": hv_before, "hv_after": hv_e,
            "t_freeze": t_freeze, "t_mutation": t_mut,
            "t_recrawl": t_recrawl, "t_probe": t_probe,
            "M0": rec0, "M1": rec1,
            "M0_verified_unchanged": m0_intact,
            "version_consistent": version_ok,
            "abstain_reason": cycle_abstain,
            "cells": cells, "write_pre": pre, "write_post": post,
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
                "oracle_readable": sum(1 for c in cross
                                       if c["oracle_answer"] in ("allow", "deny")),
                "oracle_self_readable": sum(1 for c in cross
                                            if c["oracle_self_answer"] in ("allow", "deny")),
                "oracle_disagrees_with_E": sum(1 for c in cross
                                               if c["oracle_matches_E"] is False),
            },
        }
        self.cycles.append(cyc)
        s = cyc["summary"]
        print(f"  [{seq:02d}] {kind:40s} hv={self.hv} "
              f"staleFP={s['stale_false_proofs']} liveFP={s['live_false_proofs']} "
              f"fixed={s['recrawl_fixed']} miss={s['recrawl_still_misses']} "
              f"TP={s['true_positives']} O!=E={s['oracle_disagrees_with_E']}", flush=True)
        return cyc


# ---------------------------------------------------------------------------
# 校准（修正案 A1：主视点 4/4 才开跑；副视点只记录）
# ---------------------------------------------------------------------------
def calibrate(cl) -> dict:
    cal_obj = "dave/cal"
    checks = []

    def chk(case, subject, vantage, expect, gate=True):
        o = oracle(cl, cal_obj, subject, vantage)
        ok = (o["answer"] == expect)
        checks.append({"case": case, "subject": subject, "vantage": vantage,
                       "expected": expect, "observed": o["answer"],
                       "status": o["status"], "access_level": o.get("access_level"),
                       "gate": gate, "ok": ok})
        return ok

    chk("owner_on_own_private", "dave", "dave", "allow")
    chk("collaborator_read_on_private", "carol", "dave", "allow")
    chk("non_collaborator_on_private", "eve", "dave", "deny")
    chk("owner_self_vantage", "dave", "dave", "allow")
    # 修正案 A1：以下两格只记录，不设门槛（副视点已被协议判为不可作 oracle）
    chk("collaborator_self_vantage", "carol", "carol", "unknown", gate=False)
    chk("non_collaborator_self_vantage", "eve", "eve", "unknown", gate=False)

    gated = [c for c in checks if c["gate"]]
    return {"object": cal_obj, "checks": checks,
            "passed": all(c["ok"] for c in gated),
            "gate": "primary_vantage_4_of_4 (amendment A1)",
            "secondary_vantage_admissible": False,
            "note": ("GitLab 的 members/all 对项目成员可读 ⇒ 副视点能确认 allow，"
                     "但 404 对看不见项目的人有歧义，仍不能确认 deny")}


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main():
    t_start = time.time()
    proto_raw = PROTO.read_bytes()
    proto_digest = sha(proto_raw)
    amend_raw = AMEND.read_bytes()
    amend_digest = sha(amend_raw)
    amend2_raw = AMEND2.read_bytes()
    amend2_digest = sha(amend2_raw)
    proto = json.loads(proto_raw.decode("utf-8"))
    amend = json.loads(amend_raw.decode("utf-8"))
    amend2 = json.loads(amend2_raw.decode("utf-8"))
    if amend["base_protocol_sha256"] != proto_digest:
        raise RuntimeError("修正案 A1 的 base_protocol_sha256 与当前协议不符")
    if amend2["base_protocol_sha256"] != proto_digest:
        raise RuntimeError("修正案 A2 的 base_protocol_sha256 与当前协议不符")

    print(f"[B] container={gl.CONTAINER} port={gl.PORT} lab={gl.LAB}")
    gl.LAB.mkdir(parents=True, exist_ok=True)
    gl.ensure_container()
    ready_s = gl.wait_healthy(timeout_s=900)
    print(f"[B] ready in {ready_s}s", flush=True)

    boot = gl.bootstrap_root()
    admin = gl.admin_client()
    users = gl.ensure_users(admin)
    print(f"[A] users: {len(users['steps'])} steps, failures={len(users['failures'])}",
          flush=True)
    gl.mint_user_tokens()
    cl = gl.clients()

    topo = setup(cl)
    print(f"    setup steps={len(topo['steps'])} all_ok=True", flush=True)

    cal = calibrate(cl)
    print(f"[C] calibration gate={cal['gate']} passed={cal['passed']}", flush=True)
    for c in cal["checks"]:
        print(f"      {c['case']:34s} expected={c['expected']:8s} "
              f"observed={c['observed']:8s} status={c['status']} gate={c['gate']}",
              flush=True)
    if not cal["passed"]:
        raise RuntimeError("oracle 校准未通过，按预注册协议中止，不产生正式格")

    r = Runner(cl, proto_digest, amend_digest)

    def ledger(kind, obj, subject):
        def fn():
            if kind == "grant_collaborator":
                r.pm.add_collaborator(obj, subject, "read", f"hv{r.hv}:{kind}")
            elif kind == "revoke_collaborator":
                r.pm.collaborators.pop((obj, subject), None)
                r.pm._log("revoke_collaborator", f"{obj} -= {subject}", f"hv{r.hv}")
            elif kind == "group_share":
                r.pm.add_team_repo(ORG, obj, f"hv{r.hv}:{kind}")
            elif kind == "group_member_remove":
                r.pm.team_members[ORG].discard(subject)
                r.pm._log("group_member_remove", f"{ORG} -= {subject}", f"hv{r.hv}")
            elif kind == "visibility_public":
                r.pm.set_visibility(obj, False, f"hv{r.hv}:{kind}")
            elif kind == "visibility_private":
                r.pm.set_visibility(obj, True, f"hv{r.hv}:{kind}")
            elif kind == "role_write":
                r.pm.add_collaborator(obj, subject, "write", f"hv{r.hv}:{kind}")
            elif kind == "site_admin":
                r.pm.add_site_admin(subject, f"hv{r.hv}:{kind}")
        return fn

    # ---- T1 直接授权 -------------------------------------------------------
    r.cycle(1, "grant_collaborator", "alice/priv1", "carol",
            lambda: call(cl["alice"], "POST",
                         f"{API}/projects/{PIDS['alice/priv1']}/members",
                         {"user_id": UIDS["carol"], "access_level": READ}),
            ledger("grant_collaborator", "alice/priv1", "carol"), actor="alice")

    # ---- T2 直接撤销 -------------------------------------------------------
    r.cycle(2, "revoke_collaborator", "alice/priv2", "bob",
            lambda: call(cl["alice"], "DELETE",
                         f"{API}/projects/{PIDS['alice/priv2']}/members/{UIDS['bob']}"),
            ledger("revoke_collaborator", "alice/priv2", "bob"), actor="alice")

    # ---- T3 组继承（项目共享给组） -----------------------------------------
    r.cycle(3, "group_share", "dave/r3", "bob",
            lambda: call(cl["dave"], "POST", f"{API}/projects/{PIDS['dave/r3']}/share",
                         {"group_id": GID, "group_access": READ}),
            ledger("group_share", "dave/r3", "bob"), actor="dave")

    # ---- T4 移除组成员（直授仍在 ⇒ 替代通道） ------------------------------
    r.cycle(4, "group_member_remove", "acme/t1", "bob",
            lambda: call(cl["dave"], "DELETE",
                         f"{API}/groups/{GID}/members/{UIDS['bob']}"),
            ledger("group_member_remove", "acme/t1", "bob"), actor="dave")

    # ---- T5 私有 -> 公开 ---------------------------------------------------
    r.cycle(5, "visibility_public", "dave/r1", "eve",
            lambda: call(cl["dave"], "PUT", f"{API}/projects/{PIDS['dave/r1']}",
                         {"visibility": "public"}),
            ledger("visibility_public", "dave/r1", "eve"), actor="dave")

    # ---- T6 公开 -> 私有 ---------------------------------------------------
    r.cycle(6, "visibility_private", "alice/pub1", "eve",
            lambda: call(cl["alice"], "PUT", f"{API}/projects/{PIDS['alice/pub1']}",
                         {"visibility": "private"}),
            ledger("visibility_private", "alice/pub1", "eve"), actor="alice")

    # ---- T7 read -> write --------------------------------------------------
    r.cycle(7, "role_write", "dave/r2", "carol",
            lambda: call(cl["dave"], "PUT",
                         f"{API}/projects/{PIDS['dave/r2']}/members/{UIDS['carol']}",
                         {"access_level": WRITE}),
            ledger("role_write", "dave/r2", "carol"), actor="dave",
            extra_probe=lambda when: write_probe(cl, "dave/r2", "carol"))

    # ---- T8 站点管理员 -----------------------------------------------------
    r.cycle(8, "site_admin", "(all)", "frank",
            lambda: call(cl[ADMIN_USER], "PUT", f"{API}/users/{UIDS['frank']}",
                         {"admin": True}),
            ledger("site_admin", "(all)", "frank"), actor=ADMIN_USER)

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
        "oracle_disagrees_with_E": sum(1 for c in cross
                                       if c["oracle_matches_E"] is False),
        "abstained_cells": sum(1 for cy in r.cycles for c in cy["cells"]
                               if c["abstain_reason"] is not None),
    }

    rep = {
        "meta": {
            "run_id": RUN_ID, "system": "GitLab",
            "version": gl.GITLAB_VERSION,
            "image": gl.IMAGE,
            "container": gl.CONTAINER,
            "lab_dir": str(gl.LAB), "port": gl.PORT,
            "started_at": now(),
            "elapsed_s": round(time.time() - t_start, 1),
            "generated_by": "experiments/real_system/run_temporal_gitlab.py",
            "protocol_id": proto["protocol_id"],
            "protocol_sha256": proto_digest,
            "amendment_id": [amend["amendment_id"], amend2["amendment_id"]],
            "amendment_sha256": [amend_digest, amend2_digest],
            "policy_version_kind": "harness-logical",
            "policy_version_note": proto["versioning"]["honesty_note"],
            "order": "freeze -> mutate -> recrawl -> oracle -> probe",
            "honesty_boundary": (
                "E 来自台账；Y 来自内容复读；O 与 enforcement 同源，不参与 TP/FP；"
                "GitLab 的 members/all 不建模站点管理员 ⇒ admin 格上 O 与 E 分歧，"
                "如实记录；只报本拓扑格数，不外推部署发生率。"),
        },
        "setup": topo,
        "calibration": cal,
        "transitions": r.cycles,
        "policy_events": r.policy_events,
        "policy_ledger": r.pm.ledger,
        "totals": totals,
    }
    out = RESULTS / "temporal_gitlab.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print("\n=== totals ===")
    for k, v in totals.items():
        print(f"  {k:26s} {v}")
    print(f"[done] {out} ({out.stat().st_size} bytes, {rep['meta']['elapsed_s']}s)")


if __name__ == "__main__":
    main()

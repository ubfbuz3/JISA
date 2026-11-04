"""R1.5 配对实验：同一实例、同一主体、同一操作、同一预算，只改授权通道。

三臂（都发生在快照之后，均由主体以外的凭证执行）：
  S · 直接协作者    alice/rS ← bob            （用户库，私有）
  T · 团队继承      acme/tT → team dev，bob ∈ dev（组织库，私有）
  C · 公开可见      alice/rC 以 public 新建    （用户库；Gogs 0.14.3 无 visibility 翻转路由）

每臂观察四件事：
  (1) 快照爬取里是否列出对象（应为否）；
  (2) 重爬（同一界面、同一预算）是否列出对象；
  (3) 主体直接请求是否真的被允许（状态码 + 内容哈希，确认权限生效）；
  (4) 固定升格策略 P1 下，报警/错误证明在快照与重爬后各是多少。

"不可枚举"只由界面实际响应建立：重爬结果里没有该对象，且同一界面在 S/T 臂能列出对象
（正对照），才判定为覆盖盲点。C 臂另测一次"按名字查询"（?q=rC），用来划清边界——
它说明盲点是遍历方式的属性，不是对象的属性。

Gogs 0.14.3 的三个接口就是论文 §V 用的那个爬取面：
  GET /api/v1/user/repos          （主体自己的仪表盘列表）
  GET /api/v1/orgs/{org}/repos    （组织页）
  GET /api/v1/repos/search        （站内搜索，不带 q）
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

LAB = r"C:\Users\Administrator\WorkBuddy\gogs_lab\inst_r15_pair"
os.environ["BOLA_GOGS_DIR"] = LAB
os.environ["BOLA_GOGS_PORT"] = "3314"
shutil.rmtree(LAB, ignore_errors=True)
Path(LAB).mkdir(parents=True, exist_ok=True)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import gogs_lab as gl  # noqa: E402

RESULTS = HERE / "results"
PASS = "LabPass123!"
ORG = "acme"
LOG: list[dict] = []


def step(name: str, st: int, body=None, **extra):
    err = None if 200 <= st < 300 else (json.dumps(body, ensure_ascii=False)[:180]
                                        if isinstance(body, (dict, list)) else str(body)[:180])
    LOG.append({"step": name, "status": st, "error": err, **extra})
    print(f"  {name:56s} {st}{'' if not err else '  ' + err[:90]}")


def crawl(c: gl.Client, orgs: list[str], limit: int = 50) -> dict:
    """论文 §V 的爬取面，原样：三个接口、同一预算、逐仓跟一次 GET。"""
    urls: set[str] = set()
    outputs: dict[str, str] = {}
    sources: dict[str, int] = {}

    def visit(owner: str, name: str):
        st, b = c.get(f"/api/v1/repos/{owner}/{name}")
        urls.add(f"{owner}/{name}")
        if st == 200 and isinstance(b, dict):
            outputs[f"{owner}/{name}"] = hashlib.sha256(
                json.dumps(b, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]

    st, body = c.get(f"/api/v1/user/repos?limit={limit}")
    sources["user_repos"] = st
    if st == 200 and isinstance(body, list):
        for r in body:
            visit(r["owner"]["login"], r["name"])
    for org in orgs:
        st, body = c.get(f"/api/v1/orgs/{org}/repos?limit={limit}")
        sources[f"org:{org}"] = st
        if st == 200 and isinstance(body, list):
            for r in body:
                visit(r["owner"]["login"], r["name"])
    st, body = c.get(f"/api/v1/repos/search?limit={limit}")
    sources["search"] = st
    if isinstance(body, dict):
        for r in body.get("data", []) or []:
            visit(r["owner"]["login"], r["name"])
    return {"urls": sorted(urls), "outputs": outputs, "sources": sources}


def probe_read(c: gl.Client, owner: str, name: str) -> dict:
    st, b = c.get(f"/api/v1/repos/{owner}/{name}")
    st2, f = c.get(f"/api/v1/repos/{owner}/{name}/contents/README.md")
    content = None
    if isinstance(f, dict) and f.get("content"):
        try:
            import base64
            content = hashlib.sha256(base64.b64decode(f["content"])).hexdigest()[:16]
        except Exception:                                            # noqa: BLE001
            content = "decode-error"
    return {"repo_status": st, "file_status": st2, "file_sha": content,
            "allowed": st == 200 and st2 == 200}


cfg = gl.write_config()
adm = gl.ensure_admin(cfg)
report: dict = {"meta": {
    "generated_by": "experiments/real_system/run_r15_pair.py",
    "system": "Gogs", "gogs_version": gl.version(), "lab_dir": LAB,
    "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "crawl_surface": ["GET /api/v1/user/repos?limit=50",
                      f"GET /api/v1/orgs/{ORG}/repos?limit=50",
                      "GET /api/v1/repos/search?limit=50"],
    "promotion_policy": "P1 (alarm -> violation), fixed for all cells",
    "design_note": ("同一实例/主体/操作/爬取预算；只有授权通道不同。"
                    "C 臂的对象在快照后才存在（Gogs 0.14.3 无 visibility 翻转路由），"
                    "这一点不对称必须披露：它使 C 臂同时是'新对象'与'新通道'。"),
}}

with gl.Server(cfg) as srv:
    report["meta"]["server_ready_ms"] = srv.ready_ms
    root = gl.Client(token=gl.create_token(gl.ADMIN_USER, gl.ADMIN_PASS, name="r15-root")["token"], label="root")
    for u in ("alice", "bob"):
        step(f"user:{u}", *root.post("/api/v1/admin/users",
             {"username": u, "password": PASS, "email": f"{u}@lab.local"}))
    alice = gl.Client(token=gl.create_token("alice", PASS, name="r15-alice")["token"], label="alice")
    bob = gl.Client(token=gl.create_token("bob", PASS, name="r15-bob")["token"], label="bob")
    for c, who in ((root, "root"), (alice, "alice"), (bob, "bob")):
        st, me = c.get("/api/v1/user")
        assert st == 200 and me.get("login") == who, f"身份校验失败 {who}: {st} {me}"
    report["meta"]["identity_verified"] = True

    # ---- 拓扑：组织 + 团队（团队由站点管理员代建，Gogs 无 org 自建团队路由）----
    step("org:acme", *alice.post("/api/v1/user/orgs", {"username": ORG, "full_name": "Acme"}))
    st, team = root.post(f"/api/v1/admin/orgs/{ORG}/teams",
                         {"name": "dev", "description": "", "permission": "read"})
    step("team:acme/dev", st, team)
    tid = team.get("id")

    # ---- 快照前就存在的两个私有对象 ----
    for owner_path, name in (("/api/v1/user/repos", "rS"), (f"/api/v1/org/{ORG}/repos", "tT")):
        step(f"repo:{name}", *alice.post(owner_path,
             {"name": name, "private": True, "auto_init": True, "readme": "Default",
              "description": "r15-pair", "default_branch": "master"}))

    # ---- 阶段 B：快照爬取 ----
    snap = crawl(bob, [ORG])
    report["phaseB_snapshot"] = snap
    print("  snapshot urls:", snap["urls"], "| sources", snap["sources"])

    # ---- 阶段 C：三条授予（全部由非框架凭证执行，均在快照之后）----
    step("grant S: alice/rS <- bob (collaborator)",
         *root.put("/api/v1/repos/alice/rS/collaborators/bob", {"permission": "read"}))
    step("grant T: acme/tT -> team dev",
         *root.put(f"/api/v1/admin/teams/{tid}/repos/tT"))
    step("grant T: bob -> team dev",
         *root.put(f"/api/v1/admin/teams/{tid}/members/bob"))
    step("grant C: alice/rC created public",
         *alice.post("/api/v1/user/repos",
                     {"name": "rC", "private": False, "auto_init": True, "readme": "Default",
                      "description": "r15-pair-public", "default_branch": "master"}))

    # ---- 阶段 D：同界面、同预算重爬 ----
    after = crawl(bob, [ORG])
    report["phaseD_recrawl"] = after
    print("  recrawl urls:", after["urls"], "| sources", after["sources"])

    # ---- 阶段 E：实际请求（确认权限生效）+ 按名字查询（划清边界）----
    probes = {"S": probe_read(bob, "alice", "rS"),
              "T": probe_read(bob, ORG, "tT"),
              "C": probe_read(bob, "alice", "rC")}
    report["probes"] = probes
    st, q = bob.get("/api/v1/repos/search?q=rC&limit=50")
    named = [r.get("full_name") for r in (q.get("data") or [])] if isinstance(q, dict) else []
    report["name_query"] = {"status": st, "q": "rC", "found": named}

    # ---- 判定表 ----
    arms = [("S", "direct collaborator", "alice/rS"),
            ("T", "team-derived", f"{ORG}/tT"),
            ("C", "public visibility", "alice/rC")]
    rows = []
    for key, channel, obj in arms:
        p = probes[key]
        listed_snap = obj in snap["urls"]
        listed_after = obj in after["urls"]
        # 论文的报警谓词：快照不可达 ∧ 实际可读 ∧ 主体非所有者
        alarm_snap = (not listed_snap) and p["allowed"]
        # 重爬后：以重爬结果替换可达性，其余不变
        alarm_after = (not listed_after) and p["allowed"]
        rows.append({
            "arm": key, "channel": channel, "object": obj,
            "in_snapshot_crawl": listed_snap, "in_recrawl": listed_after,
            "readable": p["allowed"], "repo_status": p["repo_status"],
            "file_status": p["file_status"], "file_sha": p["file_sha"],
            "alarm_snapshot": alarm_snap, "alarm_after_recrawl": alarm_after,
            # P1：报警即升格为 violation；该主体对每个对象都有合法授权 ⇒ 报警即错误证明
            "false_proof_snapshot": alarm_snap, "false_proof_after_recrawl": alarm_after,
            "repaired_by_recrawl": bool(alarm_snap and not alarm_after),
        })
    report["arms"] = rows
    report["totals"] = {
        "cells": len(rows),
        "alarms_snapshot": sum(r["alarm_snapshot"] for r in rows),
        "alarms_after_recrawl": sum(r["alarm_after_recrawl"] for r in rows),
        "repaired": sum(r["repaired_by_recrawl"] for r in rows),
        "persisting": sum(r["alarm_after_recrawl"] for r in rows),
    }
    report["steps"] = LOG
    report["elapsed_s"] = round(time.time() - float(adm.get("t0", time.time())), 1)

print("\n=== 判定表 ===")
for r in report["arms"]:
    print(f"  {r['arm']} {r['channel']:20s} {r['object']:10s} "
          f"snap={r['in_snapshot_crawl']!s:5s} recrawl={r['in_recrawl']!s:5s} "
          f"read={r['readable']!s:5s} alarm_snap={r['alarm_snapshot']!s:5s} "
          f"alarm_after={r['alarm_after_recrawl']!s:5s} repaired={r['repaired_by_recrawl']}")
print("totals:", report["totals"])
print("name query 'rC':", report["name_query"])

RESULTS.mkdir(parents=True, exist_ok=True)
out = RESULTS / "r15_pair.json"
out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved ->", out)

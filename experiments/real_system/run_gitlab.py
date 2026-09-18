"""跨厂商复核 · **GitLab CE 17.11.7** 上的三阶段测量（run_real.py / run_gogs.py 的独立副本）
=================================================================================
动机：Block 10（Gitea 1.22.6）与 Block 12（Gogs 0.14.3）之后，缺一个**非血缘**
厂商。GitLab 与 Gitea/Gogs 无 fork 关系（独立代码库、独立权限模型：
projects × members × roles × group 继承），是本实验能提供的最强独立性。
（诚实披露：三者也同为 git-forge 域模型，非跨领域。）

三阶段协议与谓词定义与 run_gogs.py 完全一致（采集 → 带外授权变更 → 执行 MR）；
M1 共享同一张模式表（m1_census.SHARED_PATTERNS 追加 GitLab 形状条目，
Gitea/Gogs 条目原样保留，保证既有数字不受影响）。

方法学差异（全部记录进产物 meta）
  - M1 分母 = **钉死的运行实例**的 Grape 路由枚举（`API::API.routes`，1357 条）。
    GitLab 自带 OpenAPI 规范（doc/api/openapi/openapi_v2.yaml，819 路径）但是
    **部分规范**（/admin/users 等核心授予端点缺失）⇒ 不可作分母；meta 里如实记录。
  - 站点管理员判定：归一化后路径以 /admin 开头 ⇒ True；另有一条**策展覆盖**：
    POST /users（建用户）在 GitLab 是管理员专用（文档明确），标 True。
  - 认证：`PRIVATE-TOKEN` 头；用户建局走 root 的管理员 API；用户 PAT 走
    gitlab-rails runner（PAT 明文不可从存量记录恢复，按名 revoke 重签）。
  - GUI 模型两种读法（snapshot / live）都报，失效只在前者出现——与 Gogs/Gitea 同。

用法: python run_gitlab.py
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitlab_lab as gl
import m1_census as mc
from gitlab_lab import ADMIN_USER, API, BASE, Client, clients, user_ids

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

USERS = gl.users()
ORG = "acme"
ORG_MEMBER_LEVEL = 20          # Reporter：可读组内私有项目（对应 Gogs team dev=read）

# (owner, name, private, is_org, creator) —— 与 Gogs 完全同构的 8 对象
REPOS = [
    ("alice", "r1",   True,  False, "alice"),
    ("alice", "r2",   True,  False, "alice"),
    ("alice", "r3",   True,  False, "alice"),
    ("alice", "r4",   True,  False, "alice"),
    ("alice", "pub1", False, False, "alice"),
    ("acme",  "t1",   True,  True,  "dave"),
    ("acme",  "t2",   True,  True,  "dave"),
    ("dave",  "r5",   True,  False, "dave"),
]
ALL_OBJS = [f"{o}/{n}" for o, n, _, _, _ in REPOS]
PRIV_OF = {f"{o}/{n}": priv for o, n, priv, _, _ in REPOS}

# 框架自己的动作日志：**只含框架用自己凭证做的共享**（与 Gitea/Gogs 版同口径）
FRAMEWORK_LOG = {"alice/r1": {"bob": "read"}}

# 采集期基线（阶段 A 里、B 之前授予，= "采集记录里本来就有"）
BASELINES = ["group:acme<-bob(Reporter)", "project:alice/r1<-bob(Reporter)"]

# 自省面候选（顺序 = 优先级）。GitLab v4 的成员端点用**数字 id**：
#   /projects/{id}/members/all/{user_id}  —— 含组继承（"all" 的本义）
#   /projects/{id}/members/{user_id}      —— 仅直接成员
#   /projects/{id}                        —— permissions 字段是**请求者自己的**，
#                                            与主体无关 ⇒ object_read 陷阱
# ⚠️ 模板必须带 /api/v4 前缀（初版漏了前缀，成员端点全部 302 到 Web UI 恒 404，
#    差点把「GitLab 无 oracle」的假象当结果收进论文——A2 的正确性探针恰好挡住了）。
INTROSPECT_ENDPOINTS = [
    ("members_all_get", "/api/v4/projects/{pid}/members/all/{uid}"),
    ("members_get", "/api/v4/projects/{pid}/members/{uid}"),
    ("object_read", "/api/v4/projects/{pid}"),
]


def enc(obj: str) -> str:
    """owner/name → URL 编码的命名空间路径（GitLab v4 接受 %2F 形式）。"""
    return urllib.parse.quote(obj, safe="")


# ==========================================================================
# 阶段 A0+A · 用户/组/项目拓扑（含采集前基线授权）
# ==========================================================================
def phaseA_topology(cl: dict[str, Client], uids: dict[str, int]) -> dict:
    log: list[dict] = []
    ids: dict[str, int] = {}

    def rec(step, st, body, **extra):
        err = None
        if not (200 <= st < 300):
            err = (json.dumps(body, ensure_ascii=False)[:240]
                   if isinstance(body, (dict, list)) else str(body)[:240])
        log.append({"step": step, "status": st, "error": err, **extra})

    dave = cl["dave"]
    # 组织由 dave 自建（GitLab：任何用户可建组；与 Gitea/Gogs 的"组织由
    # owner/admin 建"同口径——dave 是 acme 的组 Owner）
    rec(f"group:{ORG}", *dave.post(f"{API}/groups", {
        "name": ORG, "path": ORG, "visibility": "private"}))
    st, b = dave.get(f"{API}/groups/{ORG}")
    gid = b.get("id") if isinstance(b, dict) else None
    ids[f"group:{ORG}"] = gid

    for owner, name, priv, isorg, creator in REPOS:
        vis = "private" if priv else "public"
        body = {"name": name, "path": name, "visibility": vis,
                "initialize_with_readme": True,
                "description": "lab"}
        if isorg:
            body["namespace_id"] = gid
        # GitLab：个人项目默认落 creator 的个人命名空间
        rec(f"repo:{owner}/{name}", *cl[creator].post(f"{API}/projects", body))

    # 解析每对 (owner,name) 的数字 id（自省面端点需要）
    for obj in ALL_OBJS:
        st, b = cl[PRIV_OWNER[obj]].get(f"{API}/projects/{enc(obj)}")
        ids[obj] = b.get("id") if isinstance(b, dict) else None

    # 基线（采集**之前**就存在）的授权：
    # ① dave 把 bob 加进组 acme（GitLab 的组-成员通道，Gogs 无此路由）
    rec("baseline group acme <- bob(Reporter)",
        *dave.post(f"{API}/groups/{gid}/members",
                   {"user_id": uids["bob"], "access_level": ORG_MEMBER_LEVEL}))
    # ② alice/r1 <- bob（框架自己的 in-band 共享，用 alice 的凭证）
    rec("baseline in-band share alice/r1 <- bob(Reporter)",
        *cl["alice"].post(f"{API}/projects/{enc('alice/r1')}/members",
                          {"user_id": uids["bob"], "access_level": ORG_MEMBER_LEVEL}))

    return {"steps": log, "ids": {k: v for k, v in ids.items()},
            "failures": [s for s in log if not (200 <= s["status"] < 300)]}


# obj → 其拥有者凭证（组项目由组拥有者 dave 代持；与 Gogs 的 OBJ_CREDENTIAL 同义）
PRIV_OWNER = {f"{o}/{n}": cr for o, n, _, _, cr in REPOS}


# ==========================================================================
# 自省面发现（A2）
# ==========================================================================
def discover_introspection(cl, uids: dict[str, int], pids: dict[str, int],
                           cells: list[tuple[str, str]]) -> dict:
    """在若干 (对象, 主体) 上探测候选自省端点。

    判据与 run_gogs.discover_introspection 相同（两条缺一不可）：
      ① 拥有者视点可读（确定答案，不是被拒）；
      ② 能区分主体（答案与真值一致）。
    另记 best_effort_readable（只满足 ① 的最优先端点）。
    """
    truth: dict[str, bool] = {}
    for obj, subj in cells:
        st, _ = cl[subj].get(f"{API}/projects/{enc(obj)}")
        truth[f"{obj}|{subj}"] = st == 200

    per: dict[str, dict] = {}
    for name, _ in INTROSPECT_ENDPOINTS:
        rows: dict[str, dict] = {}
        readable_all, correct_all = True, True
        for obj, subj in cells:
            rr = introspect_with(cl, obj, subj, PRIV_OWNER[obj], name,
                                 uids=uids, pids=pids)
            auth = truth[f"{obj}|{subj}"]
            ok = bool(rr["readable"] and (rr["says_none"] == (not auth)))
            rows[f"{obj}|{subj}"] = {
                "authorized": auth, "status": rr["status"],
                "readable": rr["readable"], "says_none": rr["says_none"],
                "correct_as_oracle": ok}
            readable_all &= rr["readable"]
            correct_all &= ok
        per[name] = {"probes": rows,
                     "readable_on_all_probes": readable_all,
                     "correct_on_all_probes": correct_all}

    chosen = next((n for n, _ in INTROSPECT_ENDPOINTS
                   if per[n]["correct_on_all_probes"]), None)
    best_effort = next((n for n, _ in INTROSPECT_ENDPOINTS
                        if per[n]["readable_on_all_probes"]), None)
    return {"chosen": chosen, "best_effort_readable": best_effort,
            "per_endpoint": per,
            "probes": [f"{o}|{s}" for o, s in cells],
            "truth": truth,
            "note": ("chosen 为空 = 没有候选端点能同时满足「拥有者可读」与"
                     "「能区分主体」⇒ 本系统上不存在可用的授权 oracle。")}


def introspect_with(cl, obj: str, subject: str, vantage: str,
                    endpoint: str | None, *, uids: dict, pids: dict) -> dict:
    """以指定视点读授权面。GitLab 的成员端点是 200/404 语义：
      200 ⇒ 该 (uid) 在该项目的（含继承的）成员列表里；
      404 ⇒ 不在。两者都是"可读"。403 = 被拒（不可读）。
    object_read 的 permissions 字段是**请求者自己的** ⇒ 对谁都"可读"，
    但与主体无关（正是 Gogs 版初版踩过的陷阱，这里作为候选记录在案）。
    """
    if endpoint is None:
        return {"vantage_credential": vantage, "endpoint": None, "status": 0,
                "permission": None, "readable": False, "says_none": False}
    pid = pids.get(obj)
    uid = uids.get(subject)
    if endpoint == "object_read":
        st, b = cl[vantage].get(f"{API}/projects/{enc(obj)}")
        perm = None
        if isinstance(b, dict):
            p = b.get("permissions") or {}
            perm = p.get("project_access") or p.get("group_access")
        return {"vantage_credential": vantage, "endpoint": endpoint,
                "status": st, "permission": bool(perm) if perm else None,
                "readable": st == 200, "says_none": st == 200 and not perm}
    if pid is None or uid is None:
        return {"vantage_credential": vantage, "endpoint": endpoint, "status": 0,
                "permission": None, "readable": False, "says_none": False}
    tpl = dict(INTROSPECT_ENDPOINTS)[endpoint]
    st, b = cl[vantage].get(tpl.format(pid=pid, uid=uid))
    readable = st in (200, 404)
    says_none = st == 404
    return {"vantage_credential": vantage, "endpoint": endpoint, "status": st,
            "permission": None, "readable": readable, "says_none": says_none}


def introspect(cl, obj, subject, endpoint, *, uids, pids):
    return introspect_with(cl, obj, subject, PRIV_OWNER[obj], endpoint,
                           uids=uids, pids=pids)


def introspect_self(cl, obj, subject, endpoint, *, uids, pids):
    if subject not in cl:
        return {"vantage_credential": subject, "endpoint": endpoint, "status": 0,
                "permission": None, "readable": False, "says_none": False}
    return introspect_with(cl, obj, subject, subject, endpoint,
                           uids=uids, pids=pids)


def m2_vantage_matrix(cl, uids, pids, obj: str, subject: str) -> dict:
    out = {}
    for v in cl:
        row = {}
        for name, _ in INTROSPECT_ENDPOINTS:
            rr = introspect_with(cl, obj, subject, v, name, uids=uids, pids=pids)
            row[name] = {"status": rr["status"], "readable": rr["readable"],
                         "says_none": rr["says_none"]}
        out[v] = row
    return {"object": obj, "subject": subject, "vantages": out}


# ==========================================================================
# 阶段 C · 带外授权变更（GitLab 机制空间）
# ==========================================================================
def phaseC_mutations(cl: dict[str, Client], uids: dict, pids: dict) -> dict:
    admin, dave, alice = cl[ADMIN_USER], cl["dave"], cl["alice"]
    muts: list[dict] = []

    def rec(kind, who, st, body, **extra):
        err = None
        if not (200 <= st < 300):
            err = (json.dumps(body, ensure_ascii=False)[:240]
                   if isinstance(body, (dict, list)) else str(body)[:240])
        muts.append({"mutation": kind, "executed_by": who, "status": st,
                     "error": err, "observed_by_framework_log": False, **extra})

    # M1 管理员把 carol 加为 alice/r2 成员（= Gogs 版的 admin_grant_collaborator）
    rec("admin_grant_member:alice/r2<-carol(Reporter)", ADMIN_USER,
        *admin.post(f"{API}/projects/{pids['alice/r2']}/members",
                    {"user_id": uids["carol"], "access_level": ORG_MEMBER_LEVEL}),
        object="alice/r2", subject="carol")
    # M2 管理员把 eve 加为 alice/r3 成员
    rec("admin_grant_member:alice/r3<-eve(Reporter)", ADMIN_USER,
        *admin.post(f"{API}/projects/{pids['alice/r3']}/members",
                    {"user_id": uids["eve"], "access_level": ORG_MEMBER_LEVEL}),
        object="alice/r3", subject="eve")
    # M3 组拥有者（非站点管理员）把 frank 加进组 acme ⇒ t1、t2 同时授权
    #    （Gogs 上这条通道不存在：组/团队加人只在 /admin/** 下）
    rec("org_owner_grant_group:acme<-frank(Reporter)", "dave",
        *dave.post(f"{API}/groups/{pids['group:acme']}/members",
                   {"user_id": uids["frank"], "access_level": ORG_MEMBER_LEVEL}),
        object="group:acme", subject="frank")
    # M4 仓库拥有者把 frank 加为 dave/r5 成员
    rec("owner_grant_member:dave/r5<-frank(Reporter)", "dave",
        *dave.post(f"{API}/projects/{pids['dave/r5']}/members",
                   {"user_id": uids["frank"], "access_level": ORG_MEMBER_LEVEL}),
        object="dave/r5", subject="frank")
    # M5 可见性翻转 alice/r4 → public（Gogs 无此通道；Gitea 有）。
    # ⚠️ GitLab 编辑项目是 **PUT**（不是 Gitea 的 PATCH）——route 枚举里
    #    /projects/{id} 的写方法 = {PUT, DELETE}；PATCH 实测 404。
    rec("visibility_flip:alice/r4->public", "alice",
        *alice.put(f"{API}/projects/{enc('alice/r4')}", {"visibility": "public"}),
        object="alice/r4", subject="(everyone)")

    return {"mutations": muts,
            "absent_channels": [],
            "note": ("GitLab 机制空间是三者最富的：组加人（M3）、可见性翻转（M5）"
                     "在 Gogs 均不存在，组共享仓库（POST /projects/{id}/share）"
                     "三条都存在。此处只执行与 Gogs 版变更集**语义对应**的子集，"
                     "多余通道不执行以免扰动真值。"),
            "failures": [m for m in muts if not (200 <= m["status"] < 300)]}


# ==========================================================================
# 爬取（GUI 等价记录）——三入口与 Gogs 版同构
# ==========================================================================
def _norm_repo(b: dict) -> str:
    """项目体指纹。⚠️ GitLab 的 `permissions` 字段是**请求者相对的**，必须剔除；
    `license`/`statistics`/`container_registry_*` 等也随视点波动，一律不取。"""
    keys = ("id", "name", "path", "path_with_namespace", "visibility",
            "created_at", "default_branch", "empty_repo", "archived")
    return json.dumps({k: b.get(k) for k in keys if k in b}, sort_keys=True,
                      ensure_ascii=False)


def crawl(c: Client, org: str, limit: int = 50) -> dict:
    urls: set[str] = set()
    outputs: set[str] = set()
    sources: dict[str, int] = {}

    def visit(b: dict):
        if not isinstance(b, dict):
            return
        ns = b.get("path_with_namespace") or \
             f"{(b.get('namespace') or {}).get('path', '?')}/{b.get('path')}"
        urls.add(ns)
        st2, full = c.get(f"{API}/projects/{enc(ns)}")
        if st2 == 200 and isinstance(full, dict):
            outputs.add(_norm_repo(full))

    st, body = c.get(f"{API}/projects?membership=true&per_page={limit}")
    sources["membership_projects"] = st
    if st == 200 and isinstance(body, list):
        for r in body:
            visit(r)

    st, body = c.get(f"{API}/groups/{org}/projects?per_page={limit}")
    sources[f"group_projects:{org}"] = st
    if st == 200 and isinstance(body, list):
        for r in body:
            visit(r)

    st, body = c.get(f"{API}/projects?per_page={limit}")
    sources["visible_projects"] = st
    if st == 200 and isinstance(body, list):
        for r in body:
            visit(r)

    return {"urls": sorted(urls), "outputs": sorted(outputs), "sources": sources}


# ==========================================================================
# M1 · 授权授予机制空间普查（钉死实例的 Grape 路由枚举）
# ==========================================================================
def enumerate_routes() -> dict:
    """rails runner 枚举 API::API.routes。分母 = 运行实例的 Grape 路由。"""
    rb = r"""
require 'json'
rows = API::API.routes.map do |r|
  { 'path' => r.pattern.origin.to_s, 'method' => r.request_method.to_s }
end
File.write('/tmp/wb_routes.json', JSON.generate(rows))
puts 'written'
"""
    out = gl.rails_runner(rb, result_name="wb_routes.json")
    if "written" not in out:
        raise RuntimeError(f"路由枚举 runner 异常：\n{out[-2000:]}")
    rows = json.loads((gl.LAB / "wb_routes.json").read_text(encoding="utf-8"))
    (gl.LAB / "wb_routes.json").unlink(missing_ok=True)
    routes, wildcards = [], 0
    for r in rows:
        p = r["path"]
        if "*" in p:                       # 通配兜底路由不是端点
            wildcards += 1
            continue
        p = p.removeprefix("/api/:version")
        p = re.sub(r":([A-Za-z_]+)", r"{\1}", p)
        routes.append({"path": p, "methods": [r["method"].upper()]})
    return {"routes": routes, "route_entries_raw": len(rows),
            "wildcard_excluded": wildcards}


# GitLab 特有的站点管理员判定（策展覆盖；/admin 前缀之外唯一已知的
# 授予相关管理员专用端点是 POST /users）
CURATED_ADMIN = {"/users": True, "/users/{}": True}


def m1_route_census(parsed: dict) -> dict:
    pwm: dict[str, list[str]] = {}
    adm: dict[str, bool] = {}
    for r in parsed["routes"]:
        p = r["path"]
        pwm.setdefault(p, [])
        pwm[p] = sorted(set(pwm[p]) | set(r["methods"]))
        flag = p.startswith("/admin") or CURATED_ADMIN.get(p, False)
        adm[p] = adm.get(p, False) or flag
    return mc.census(
        pwm, adm,
        source_label=("GitLab 17.11.7 · 钉死运行实例的 Grape 路由枚举 "
                      "(API::API.routes；自带 OpenAPI 规范是部分规范，不可作分母)"),
        denominator_label="Grape 路由条目数（实例枚举，含只读端点；通配兜底已剔除）") | {
        "route_entries_raw": parsed["route_entries_raw"],
        "unique_paths": len(pwm),
        "admin_flag_rule": ("/admin 前缀 + 策展覆盖 {POST /users: 管理员专用}；"
                            "Grape 层无逐路由的 admin 谓词可静态枚举"),
    }


# ==========================================================================
# 主流程
# ==========================================================================
def main():
    t0 = time.time()
    rep: dict = {"meta": {
        "system": "GitLab",
        "gitlab_version": gl.GITLAB_VERSION,
        "image": gl.IMAGE,
        "container": gl.CONTAINER,
        "generated_by": "experiments/real_system/run_gitlab.py",
        "positioning": ("非血缘厂商复核（independent-vendor replication）：GitLab 与 "
                        "Gitea/Gogs 无 fork 关系。披露：三者同为 git-forge 域模型。"),
        "phases": ["A 基线拓扑", "A2 自省面发现", "B 采集爬取", "C 带外授权变更",
                   "D 变更后爬取", "E MR 执行与四方法裁决", "F M1/M2/M3", "G M6"],
        "methodological_differences_vs_gitea_gogs": [
            "M1 分母 = 钉死运行实例的 Grape 路由枚举（API::API.routes）",
            "自带 OpenAPI 规范(doc/api/openapi/openapi_v2.yaml, 819 路径)是部分规范"
            "（/admin/users 等缺失）⇒ 不作分母",
            "站点管理员判定 = /admin 前缀 + 策展覆盖 POST /users",
            "认证 PRIVATE-TOKEN 头；用户 PAT 经 gitlab-rails runner 重签"
            "（PAT 明文不可从存量记录恢复）",
            "组-成员通道（POST /groups/{id}/members）存在 ⇒ Gogs 上缺席的"
            "组织级带外通道在 GitLab 存在",
            "GitLab 的 GET /projects 体含请求者相对的 permissions 字段 ⇒ "
            "_norm_repo 指纹剔除之",
        ],
        "honesty_boundary": (
            "GitLab 是正确系统，不含对象级授权漏洞 ⇒ 只测假确证侧与发生率，"
            "不测检出率；不声称实验证明 MST-wi 失效；GUI 模型的 snapshot / live "
            "两种读法都报。"),
    }}

    gl.ensure_container()
    ready_s = gl.wait_healthy()
    root_info = gl.bootstrap_root()
    print(f"[bootstrap] 容器就绪 {ready_s}s；root PAT 已签发 "
          f"(len={root_info['token_len']}, v={root_info['gitlab_version']})", flush=True)

    admin = gl.admin_client()
    # 陈旧状态守卫：上次运行若中途失败，实例里会残留拓扑/变更 ⇒ snapshot 基线
    # 将被污染（真实踩过：M1–M4 已生效而 M5 失败中止）。发现即拒绝继续。
    st_probe, _ = admin.get(f"{API}/projects/{enc('alice/r1')}")
    if st_probe == 200:
        raise SystemExit(
            "实例不是空的（alice/r1 已存在）——上次运行残留状态会污染 snapshot 基线。\n"
            "请重置容器：docker rm -f gitlab-lab && docker volume rm gitlab_lab_vol\n"
            "并按 gitlab_lab/bootstrap.md 重建后重跑。")
    a0 = gl.ensure_users(admin)
    print("     用户创建", len(a0["steps"]), "失败", len(a0["failures"]), flush=True)
    for s in a0["failures"]:
        print("       ! ", s["step"], s["status"], s.get("error"), flush=True)
    mint = gl.mint_user_tokens()
    print("     用户 PAT", mint["users"], flush=True)
    rep["meta"]["bootstrap"] = {"ready_s": ready_s, "users": a0["steps"],
                                "token_minted": mint["users"]}

    cl = clients()
    uids = dict(user_ids())
    uids[ADMIN_USER] = root_info["root_id"]

    # ---------------- A：基线拓扑 ----------------
    print("[A] 基线拓扑 …", flush=True)
    report_A = phaseA_topology(cl, uids)
    rep["phaseA_topology"] = report_A
    pids = report_A["ids"]
    print("     拓扑步骤", len(report_A["steps"]), "失败",
          len(report_A["failures"]), flush=True)
    for s in report_A["failures"]:
        print("       ! ", s["step"], s["status"], s.get("error"), flush=True)
    if report_A["failures"]:
        raise SystemExit("拓扑有失败步骤，中止（网格真值依赖完整拓扑）")

    # ---------------- A2：自省面发现 ----------------
    print("[A2] 自省面发现 …", flush=True)
    probe_cells = [("alice/r1", "bob"),    # 有权限（直接成员，in-band 基线）
                   ("acme/t1", "bob"),     # 有权限（**组继承**）
                   ("alice/r2", "carol"),  # 无权限
                   ("acme/t1", "eve"),     # 无权限
                   ("dave/r5", "frank")]   # 无权限
    disc = discover_introspection(cl, uids, pids, probe_cells)
    rep["A2_introspection_discovery"] = disc
    oracle = disc["chosen"] or disc["best_effort_readable"]
    rep["A2_oracle_used"] = {
        "endpoint": oracle,
        "is_correct_oracle": oracle is not None and oracle == disc["chosen"],
        "reason": ("无端点同时满足「拥有者可读」与「能区分主体」⇒ 退化为仅可读的那面，"
                   "其判定错误由 M3/M5 直接量出。"
                   if oracle and oracle != disc["chosen"] else
                   ("完全不存在可读的自省面。" if oracle is None else "严格 oracle 可用。")),
    }
    print("     严格 oracle:", disc["chosen"],
          "| 仅可读的那面:", disc["best_effort_readable"],
          "| 实际使用:", oracle, flush=True)
    for n, d in disc["per_endpoint"].items():
        print(f"       {n:16s} 拥有者全可读={d['readable_on_all_probes']!s:5s}"
              f" 可作合法 oracle={d['correct_on_all_probes']}", flush=True)

    # ---------------- B：采集爬取（snapshot 基准） ----------------
    print("[B] 采集期爬取 …", flush=True)
    snap_before = {u: crawl(c, ORG) for u, c in cl.items()}
    rep["phaseB_crawl_snapshot"] = {
        u: {"urls": d["urls"], "n_outputs": len(d["outputs"]), "sources": d["sources"]}
        for u, d in snap_before.items()}

    # ---------------- C：带外授权变更 ----------------
    print("[C] 带外授权变更 …", flush=True)
    rc = phaseC_mutations(cl, uids, pids)
    rep["phaseC_mutations"] = rc
    print("     变更", len(rc["mutations"]), "失败", len(rc["failures"]), flush=True)
    for m in rc["failures"]:
        print("       ! ", m["mutation"], m["status"], m.get("error"), flush=True)
    if rc["failures"]:
        raise SystemExit("带外变更失败，中止")

    # ---------------- D：变更后爬取 ----------------
    print("[D] 变更后爬取 …", flush=True)
    snap_after = {u: crawl(c, ORG) for u, c in cl.items()}
    rep["phaseD_crawl_after"] = {u: {"urls": d["urls"]} for u, d in snap_after.items()}

    # ---------------- E：MR 执行 + 四方法裁决 ----------------
    print("[E] MR 执行 …", flush=True)
    acting = {}
    for obj in ALL_OBJS:
        st, b = cl[PRIV_OWNER[obj]].get(f"{API}/projects/{enc(obj)}")
        acting[obj] = {"granted": st == 200,
                       "out": _norm_repo(b) if isinstance(b, dict) else None}

    subjects = list(USERS) + [ADMIN_USER]
    cells = []
    truth_map = {}
    for obj in ALL_OBJS:
        for subj in subjects:
            if subj == PRIV_OWNER[obj]:
                continue
            st, b = cl[subj].get(f"{API}/projects/{enc(obj)}")
            granted = st == 200
            out_subj = _norm_repo(b) if isinstance(b, dict) else None
            truth_map[f"{obj}|{subj}"] = granted

            can_snap = obj not in set(snap_before[subj]["urls"])
            can_live = obj not in set(snap_after[subj]["urls"])
            out_equal = bool(granted and acting[obj]["granted"]
                             and out_subj == acting[obj]["out"])
            ins = introspect(cl, obj, subj, oracle, uids=uids, pids=pids)
            ins_self = introspect_self(cl, obj, subj, oracle, uids=uids, pids=pids)
            log_has = subj in FRAMEWORK_LOG.get(obj, {})

            for reading, can_reach in (("snapshot", can_snap), ("live", can_live)):
                fires = can_reach and (subj != ADMIN_USER) and out_equal
                cells.append({
                    "object": obj, "subject": subj, "reading": reading,
                    "cannotReachThroughGUI": can_reach,
                    "output_equal": out_equal, "mr_fires": fires,
                    "framework_log_has_record": log_has,
                    "introspection_status": ins["status"],
                    "introspection_permission": ins["permission"],
                    "introspection_readable": ins["readable"],
                    "introspection_self_status": ins_self["status"],
                    "introspection_self_permission": ins_self["permission"],
                    "introspection_self_readable": ins_self["readable"],
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

    # ---------------- F：M1/M2/M3 ----------------
    print("[F] M1/M2/M3 …", flush=True)
    parsed = enumerate_routes()
    if not parsed["routes"]:
        raise SystemExit("路由枚举为空")
    rep["M1_grant_mechanism_census"] = m1_route_census(parsed)
    print("     路由条目", rep["M1_grant_mechanism_census"]["denominator_entries"],
          "授予端点", rep["M1_grant_mechanism_census"]["grant_endpoints_total"],
          "其中非站点管理员",
          rep["M1_grant_mechanism_census"]["grant_endpoints_without_site_admin"],
          flush=True)

    rep["M2_vantage_readability"] = {
        obj: m2_vantage_matrix(cl, uids, pids, obj, "bob")
        for obj in ["alice/r1", "acme/t1"]}
    rep["M3_introspection_fidelity"] = []
    for obj in ALL_OBJS:
        for s in subjects:
            o = introspect(cl, obj, s, oracle, uids=uids, pids=pids)
            sf = introspect_self(cl, obj, s, oracle, uids=uids, pids=pids)
            rep["M3_introspection_fidelity"].append({
                "object": obj, "subject": s,
                "authorized": truth_map.get(f"{obj}|{s}"),
                "is_acting_credential": s == PRIV_OWNER[obj],
                "vantage_credential": o["vantage_credential"],
                "status": o["status"], "permission": o["permission"],
                "readable": o["readable"], "says_none": o["says_none"],
                "status_self": sf["status"], "permission_self": sf["permission"],
                "readable_self": sf["readable"], "says_none_self": sf["says_none"],
            })

    # ---------------- G：授权通道定性 ----------------
    print("[G] 授权通道定性 …", flush=True)
    # ⚠️ 通道归因用**测量时刻的最终可见性**（r4 已被 M5 翻转为 public），
    #    不是建局时的初始值——否则 5 个公开格会被错记成 out_of_band。
    final_vis: dict[str, bool] = {}
    for obj in ALL_OBJS:
        stv, bv = admin.get(f"{API}/projects/{enc(obj)}")
        final_vis[obj] = (stv == 200 and isinstance(bv, dict)
                          and bv.get("visibility") == "public")
    prov = []
    for obj in ALL_OBJS:
        priv = not final_vis[obj]           # True = 仍私有
        for s in subjects:
            if not truth_map.get(f"{obj}|{s}"):
                kind = "none"
            elif s == ADMIN_USER:
                kind = "implicit_site_admin"
            elif s == PRIV_OWNER[obj]:
                kind = "implicit_owner"
            elif not priv:
                kind = "implicit_public"
            elif obj == "alice/r1" and s == "bob":
                kind = "in_band_share"
            else:
                kind = "out_of_band"
            prov.append({"cell": obj, "subject": s, "channel": kind})
    rep["M6_provenance"] = prov

    rep["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = RESULTS / "gitlab_real_system.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] -> {out} ({out.stat().st_size} bytes, {rep['meta']['elapsed_s']}s)",
          flush=True)


if __name__ == "__main__":
    main()

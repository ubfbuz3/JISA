"""
实验 B · 真实系统对照（Gitea 1.22.6）· 三阶段版
================================================
动机：第七轮追问判决后选 B ——「在真实系统上做 `MR` vs `直接请求` 对照」。
见 02_Idea与架构/Idea苏格拉底追问与判断.md 与 refine-logs/EXPERIMENT_RESULTS.md §Block 9。

★ 本版依据是 MST-wi 论文**原文对谓词的定义**（mstwi_paper_text.txt §4.4）：

  cannotReachThroughGUI(User u, String URL)
      "Returns true if a URL cannot be reached by the given user by
       exploring the user interface of the system (e.g., by traversing anchors)."

  userCanRetrieveContent(User u, Object out)
      "Returns true if the output data has ever been received in response to
       any of the input sequences executed by the given user during data collection."

  设计意图（原文）：
      "if the system does not provide a URL to a user through its GUI,
       then she should not access the URL. Also, to avoid false alarms, the user
       who cannot access the URL from the GUI ... should not be a supervisor
       with access to all the resources of the other user."

⇒ 两个谓词都是相对**采集期爬取记录**定义的，不是相对系统的授权状态。
⇒ 因此忠实实例化必须是三阶段：**采集 → 授权变更 → 执行 MR**（本版重写的原因：
   旧版把"API 完整枚举"当作 GUI 模型，那是**实时且完备**的读法，对 MST-wi 不公平）。

⚠️ 诚实边界（写死在脚本里）
  1. Gitea 是**正确**系统，不含对象级授权漏洞 ⇒ 本实验**只测假确证侧与发生率**，
     **不测检出率**。检出侧仍以合成 SUT（576 条记录）为准。
  2. 不声称"实验证明 MST-wi 失效"（未跑其原生引擎），只声称
     "该 MR 家族的结构在真实系统上被实例化后的行为"。
  3. GUI 模型有**两种读法**，本实验**两种都报**：
       snapshot 读法 = 用采集期的爬取记录（默认读法，原文 userCanRetrieveContent 的措辞支持）
       live     读法 = 在执行 MR 时重新爬取
     失效只在 snapshot 读法下出现 ⇒ 结论必须带上这个条件。

测量项
  M1 授权授予机制空间普查（读 Gitea 自带 swagger.v1.json）—— 实例无关
  M2 自省面**视点可读性**矩阵
  M3 自省面**保真度**（所报 vs 有效访问）
  M4 采集期爬取记录 vs 变更后有效访问（GUI 代理的失配面）
  M5 方法对照：mr_bookkeeping / v3(自省) / direct_only / direct_observe
  M6 授权通道定性与带外占比

用法: python run_real.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import gitea_lab as gl
from gitea_lab import ADMIN_PASS, ADMIN_USER, Client, Server, ensure_migrated, write_config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
PASS = "LabPass123!"

USERS = {
    "alice": dict(email="alice@lab.local", restricted=False),
    "bob":   dict(email="bob@lab.local",   restricted=False),
    "carol": dict(email="carol@lab.local", restricted=False),
    "dave":  dict(email="dave@lab.local",  restricted=False),
    "eve":   dict(email="eve@lab.local",   restricted=False),
    "frank": dict(email="frank@lab.local", restricted=False),
}
ORG = "acme"
TEAMS = {"dev": "read", "ops": "write"}

# (owner, name, private, org, creator)
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
OBJ_CREDENTIAL = {f"{o}/{n}": cr for o, n, _, _, cr in REPOS}
ALL_OBJS = [f"{o}/{n}" for o, n, _, _, _ in REPOS]

# 框架自己的动作日志：**只含框架用自己凭证做的共享**
FRAMEWORK_LOG = {"alice/r1": {"bob": "read"}}


def clients() -> dict[str, Client]:
    out = {"anonymous": Client(label="anonymous")}
    out[ADMIN_USER] = Client(user=ADMIN_USER, password=ADMIN_PASS, label=ADMIN_USER)
    for u in USERS:
        out[u] = Client(user=u, password=PASS, label=u)
    return out


# ==========================================================================
# 阶段 A · 基线拓扑
# ==========================================================================
def phaseA_topology(cl: dict[str, Client]) -> dict:
    log: list[dict] = []

    def rec(step, st, body):
        err = None
        if not (200 <= st < 300):
            err = (json.dumps(body, ensure_ascii=False)[:200]
                   if isinstance(body, (dict, list)) else str(body)[:200])
        log.append({"step": step, "status": st, "error": err})

    admin = cl[ADMIN_USER]
    for u, meta in USERS.items():
        rec(f"user:{u}", *admin.post("/api/v1/admin/users", {
            "username": u, "password": PASS, "email": meta["email"],
            "must_change_password": False, "restricted": meta["restricted"]}))

    rec(f"org:{ORG}", *cl["dave"].post("/api/v1/orgs", {
        "username": ORG, "visibility": "private", "full_name": "Acme"}))

    team_ids = {}
    for tname, perm in TEAMS.items():
        st, b = cl["dave"].post(f"/api/v1/orgs/{ORG}/teams", {
            "name": tname, "permission": perm,
            "units": ["repo.code", "repo.issues", "repo.pulls", "repo.wiki", "repo.releases"],
            "includes_all_repositories": False})
        rec(f"team:{tname}", st, b)
        if isinstance(b, dict) and b.get("id"):
            team_ids[tname] = b["id"]

    for owner, name, priv, isorg, creator in REPOS:
        path = f"/api/v1/orgs/{owner}/repos" if isorg else "/api/v1/user/repos"
        rec(f"repo:{owner}/{name}", *cl[creator].post(path, {
            "name": name, "private": priv, "auto_init": True, "description": "lab"}))

    # 基线（采集**之前**就存在）的授权
    if team_ids.get("dev"):
        rec("baseline team dev += bob", *cl["dave"].put(f"/api/v1/teams/{team_ids['dev']}/members/bob"))
        rec("baseline team dev += repo acme/t1",
            *cl["dave"].put(f"/api/v1/teams/{team_ids['dev']}/repos/{ORG}/t1"))
    # 框架自己的 in-band 共享（用 alice 的凭证 = 框架运行的凭证）
    rec("baseline in-band share alice/r1 <- bob",
        *cl["alice"].put("/api/v1/repos/alice/r1/collaborators/bob", {"permission": "read"}))

    return {"steps": log, "team_ids": team_ids,
            "failures": [s for s in log if not (200 <= s["status"] < 300)]}


# ==========================================================================
# 阶段 C · 带外授权变更（全部由**非框架**凭证执行，且发生在采集之后）
# ==========================================================================
def phaseC_mutations(cl: dict[str, Client], team_ids: dict) -> dict:
    admin, dave = cl[ADMIN_USER], cl["dave"]
    muts: list[dict] = []

    def rec(kind, who, st, body, **extra):
        err = None
        if not (200 <= st < 300):
            err = (json.dumps(body, ensure_ascii=False)[:240]
                   if isinstance(body, (dict, list)) else str(body)[:240])
        muts.append({"mutation": kind, "executed_by": who, "status": st,
                     "error": err, "observed_by_framework_log": False, **extra})

    # M1 管理员把 carol 加为 alice/r2 协作者
    rec("admin_grant_collaborator:alice/r2<-carol", ADMIN_USER,
        *admin.put("/api/v1/repos/alice/r2/collaborators/carol", {"permission": "read"}),
        object="alice/r2", subject="carol")
    # M2 管理员把 eve 加为 alice/r3 协作者
    rec("admin_grant_collaborator:alice/r3<-eve", ADMIN_USER,
        *admin.put("/api/v1/repos/alice/r3/collaborators/eve", {"permission": "read"}),
        object="alice/r3", subject="eve")
    # M3 组织拥有者把 acme/t2 加入团队 dev（carol/frank 属该团队后自动获得读）
    if team_ids.get("dev"):
        rec("team_grant_repo:acme/t2 -> team dev", "dave",
            *dave.put(f"/api/v1/teams/{team_ids['dev']}/repos/{ORG}/t2"),
            object="acme/t2", subject="(team dev members)")
    # M4 管理员把 alice/r4 由私有改为公开（可见性变更 = 对所有人授权）
    rec("admin_flip_visibility:alice/r4 -> public", ADMIN_USER,
        *admin.patch("/api/v1/repos/alice/r4", {"private": False}),
        object="alice/r4", subject="(everyone)")
    # M5 管理员把 frank 加入组织并设为团队 dev 成员
    rec("admin_add_org_member:acme<-frank", ADMIN_USER,
        *admin.put(f"/api/v1/orgs/{ORG}/members/frank"), object="acme", subject="frank")
    if team_ids.get("dev"):
        rec("admin_add_team_member:dev<-frank", ADMIN_USER,
            *admin.put(f"/api/v1/teams/{team_ids['dev']}/members/frank"),
            object=f"team:{team_ids['dev']}", subject="frank")

    return {"mutations": muts,
            "failures": [m for m in muts if not (200 <= m["status"] < 300)]}


# ==========================================================================
# 爬取（GUI 等价记录）
# ==========================================================================
def _norm_repo(b: dict) -> str:
    keys = ("id", "name", "full_name", "private", "created_at", "updated_at",
            "size", "empty", "default_branch")
    return json.dumps({k: b.get(k) for k in keys if k in b}, sort_keys=True, ensure_ascii=False)


def crawl(c: Client, orgs: list[str], limit: int = 50) -> dict:
    """一次 GUI 等价爬取，返回 {urls, outputs, sources}。

    "urls"     = 该视点在本次爬取中**可达的对象 URL 集合**（对象 URL 记作 owner/repo）
    "outputs"  = 本次爬取中**观察到的输出表征集合**（对应 userCanRetrieveContent）
    """
    urls: set[str] = set()
    outputs: set[str] = set()
    sources: dict[str, int] = {}

    def visit(owner: str, name: str):
        urls.add(f"{owner}/{name}")
        st, b = c.get(f"/api/v1/repos/{owner}/{name}")
        if st == 200 and isinstance(b, dict):
            outputs.add(_norm_repo(b))

    st, body = c.get(f"/api/v1/user/repos?limit={limit}")
    sources["user_repos"] = st
    if st == 200 and isinstance(body, list):
        for r in body:
            visit(r["owner"]["login"], r["name"])

    for org in orgs:
        st, body = c.get(f"/api/v1/orgs/{org}/repos?limit={limit}")
        sources[f"org_repos:{org}"] = st
        if st == 200 and isinstance(body, list):
            for r in body:
                visit(r["owner"]["login"], r["name"])

    st, body = c.get(f"/api/v1/repos/search?limit={limit}")
    sources["search"] = st
    if st == 200 and isinstance(body, dict):
        for r in body.get("data", []):
            visit(r["owner"]["login"], r["name"])

    return {"urls": sorted(urls), "outputs": sorted(outputs), "sources": sources}


# ==========================================================================
# 授权自省面
# ==========================================================================
INTROSPECT_ENDPOINTS = [
    ("object_read", "/api/v1/repos/{o}/{r}"),
    ("introspect_list", "/api/v1/repos/{o}/{r}/collaborators"),
    ("introspect_perm", "/api/v1/repos/{o}/{r}/collaborators/{u}/permission"),
]


def introspect(cl, obj: str, subject: str) -> dict:
    """以**本实验规定的自省视点**读授权面。

    第七轮 v3 的规定视点是「以对象拥有者身份读」（组织仓库由组织拥有者代持）。
    可读性本身也是被测量对象（M2），此处返回状态码供 M5 判定。
    """
    owner, repo = obj.split("/")
    cred = OBJ_CREDENTIAL[obj]
    return _introspect_with(cl[cred], obj, subject, vantage=cred)


def introspect_self(cl, obj: str, subject: str) -> dict:
    """以**被测主体自己的凭证**读授权面 —— 这是黑箱测试者的自然视点。

    与 introspect 的差别只有"谁在读"。若该视点读不到，则任何依赖自省面的
    判定器都必须弃权 ⇒ 检出力为 0。这是判断"可容许条件是否只能由特权凭证满足"的关键。
    """
    if subject not in cl:
        return {"vantage_credential": subject, "status": 0, "permission": None,
                "readable": False, "says_none": False}
    return _introspect_with(cl[subject], obj, subject, vantage=subject)


def _introspect_with(c: Client, obj: str, subject: str, vantage: str) -> dict:
    owner, repo = obj.split("/")
    st, body = c.get(f"/api/v1/repos/{owner}/{repo}/collaborators/{subject}/permission")
    perm = body.get("permission") if (st == 200 and isinstance(body, dict)) else None
    return {"vantage_credential": vantage, "status": st, "permission": perm,
            "readable": st == 200 and perm not in (None, ""),
            # Gitea 对"确实没有权限"也在 200 里明确回答 none；只有被拒才不可读
            "says_none": st == 200 and perm == "none"}


def m2_vantage_matrix(cl, obj: str, subject: str) -> dict:
    owner, repo = obj.split("/")
    out = {}
    for v, c in cl.items():
        row = {}
        for name, tpl in INTROSPECT_ENDPOINTS:
            st, b = c.get(tpl.format(o=owner, r=repo, u=subject))
            row[name] = {"status": st,
                         "perm": b.get("permission") if isinstance(b, dict) else None}
        out[v] = row
    return {"object": obj, "subject": subject, "vantages": out}


# ==========================================================================
# M1 · 授权授予机制空间普查
# ==========================================================================
_GRANT_PATTERNS = [
    (r"^/repos/\{owner\}/\{repo\}/collaborators/\{collaborator\}$", "仓库级：协作者（PUT 授予 / DELETE 撤销）"),
    (r"^/teams/\{id\}/repos/", "组织级：仓库挂到团队"),
    (r"^/teams/\{id\}/members/", "组织级：用户加入团队"),
    (r"^/orgs/\{org\}/members/\{username\}$", "组织级：用户移出组织（**仅 DELETE**）"),
    (r"^/orgs/\{org\}/teams$", "组织级：新建团队（授权单位）"),
    (r"^/orgs$", "组织级：新建组织"),
    (r"^/repos/\{owner\}/\{repo\}/transfer$", "仓库级：转移所有权"),
    (r"^/repos/\{owner\}/\{repo\}$", "仓库级：切换可见性（私有→公开即向所有人授予）"),
    (r"^/repos/\{owner\}/\{repo\}/keys$", "部署密钥：授予仓库读写"),
    (r"^/admin/users", "站点级：建/改用户（含受限标志、加入组织）"),
]
# 方向**不写死**，由该端点实际可用的 HTTP 方法推出：方法集 ⊆ {DELETE} ⇒ 撤销，否则 ⇒ 授予。
# （初版把 `/orgs/{org}/members/{username}` 标成"加入组织"，实测 PUT 返回 405、该端点只有
#   DELETE ⇒ 它是**移除**，已更正。）


def m1_swagger_census(cl) -> dict:
    st, sw = cl[ADMIN_USER].get("/swagger.v1.json", timeout=60)
    if st != 200 or not isinstance(sw, dict):
        return {"error": f"swagger 不可读 status={st}"}
    paths = sw.get("paths", {})
    methods = {p: sorted(m.upper() for m in ops
                         if m.lower() in ("post", "put", "patch", "delete"))
               for p, ops in paths.items()}
    hits, seen = [], set()
    for pat, kind in _GRANT_PATTERNS:
        for p in paths:
            ms = methods[p]
            if not ms or not re.match(pat, p) or (p, kind) in seen:
                continue
            seen.add((p, kind))
            hits.append({"endpoint": p, "methods": ms, "kind": kind,
                         "direction": "revoke" if set(ms) <= {"DELETE"} else "grant",
                         "requires_site_admin": p.startswith("/admin")})
    grants = [h for h in hits if h["direction"] == "grant"]
    return {
        "swagger_total_paths": len(paths),
        "grant_endpoints_total": len(grants),
        "revoke_endpoints_total": len(hits) - len(grants),
        "grant_endpoints_without_site_admin": sum(
            1 for h in grants if not h["requires_site_admin"]),
        "endpoints": hits,
        "predicate": ("端点计入当且仅当：在不修改被测系统代码的前提下，"
                      "能使某 (主体, 对象) 的访问权限从否变为是；"
                      "方向由该端点实际可用的 HTTP 方法推出（仅 DELETE ⇒ 撤销，不算授予）。"),
    }


# ==========================================================================
# 主流程
# ==========================================================================
def main():
    t0 = time.time()
    rep: dict = {"meta": {
        "gitea_version": gl.GITEA_VERSION,
        "lab_dir": str(gl.LAB),
        "generated_by": "experiments/real_system/run_real.py",
        "phases": ["A 基线拓扑", "B 采集爬取", "C 带外授权变更", "D 变更后爬取",
                   "E MR 执行与四方法裁决", "F M1/M2/M3", "G M6"],
        "honesty_boundary": (
            "Gitea 是正确系统，不含对象级授权漏洞 ⇒ 只测假确证侧与发生率，不测检出率；"
            "不声称实验证明 MST-wi 失效（未跑其原生引擎）；"
            "GUI 模型的 snapshot / live 两种读法都报，失效只在前者出现。"),
    }}

    cfg = write_config()
    print("[A] migrate/admin:", ensure_migrated(cfg), flush=True)

    with Server(cfg) as srv:
        print(f"[A] 服务就绪 version={gl.version()} ready_ms={srv.ready_ms}", flush=True)
        cl = clients()
        report_A = phaseA_topology(cl)
        rep["phaseA_topology"] = report_A
        print("     拓扑步骤", len(report_A["steps"]), "失败", len(report_A["failures"]), flush=True)

        # ---------------- 阶段 B：采集爬取（snapshot 基准） ----------------
        print("[B] 采集期爬取 …", flush=True)
        snap_before = {u: crawl(c, [ORG]) for u, c in cl.items()}
        rep["phaseB_crawl_snapshot"] = {
            u: {"urls": d["urls"], "n_outputs": len(d["outputs"]), "sources": d["sources"]}
            for u, d in snap_before.items()}

        # ---------------- 阶段 C：带外授权变更 ----------------
        print("[C] 带外授权变更 …", flush=True)
        rc = phaseC_mutations(cl, report_A["team_ids"])
        rep["phaseC_mutations"] = rc
        print("     变更", len(rc["mutations"]), "失败", len(rc["failures"]), flush=True)
        for m in rc["failures"]:
            print("       ! ", m["mutation"], m["status"], m.get("error"), flush=True)

        # ---------------- 阶段 D：变更后再爬一次（live 读法用） ----------------
        print("[D] 变更后爬取 …", flush=True)
        snap_after = {u: crawl(c, [ORG]) for u, c in cl.items()}
        rep["phaseD_crawl_after"] = {u: {"urls": d["urls"]} for u, d in snap_after.items()}

        # ---------------- 阶段 E：MR 执行 + 四方法裁决 ----------------
        print("[E] MR 执行 …", flush=True)
        acting = {obj: {"granted": False, "out": None} for obj in ALL_OBJS}
        for obj in ALL_OBJS:
            owner, name = obj.split("/")
            st, b = cl[OBJ_CREDENTIAL[obj]].get(f"/api/v1/repos/{owner}/{name}")
            acting[obj] = {"granted": st == 200, "out": _norm_repo(b) if isinstance(b, dict) else None}

        subjects = list(USERS) + [ADMIN_USER]
        cells = []
        truth_map = {}
        for obj in ALL_OBJS:
            owner, name = obj.split("/")
            for subj in subjects:
                if subj == OBJ_CREDENTIAL[obj]:
                    continue                       # 执行者自身不作为"换凭证"主体
                st, b = cl[subj].get(f"/api/v1/repos/{owner}/{name}")
                granted = st == 200
                out_subj = _norm_repo(b) if isinstance(b, dict) else None
                truth_map[f"{obj}|{subj}"] = granted

                can_snap = obj not in set(snap_before[subj]["urls"])
                can_live = obj not in set(snap_after[subj]["urls"])
                out_equal = bool(granted and acting[obj]["granted"]
                                 and out_subj == acting[obj]["out"])
                ins = introspect(cl, obj, subj)
                ins_self = introspect_self(cl, obj, subj)
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
                            # 账本版：谓词来自"框架自己的动作记录"
                            "mr_bookkeeping": fires and not log_has,
                            # 自省面版（拥有者/管理员视点读面）
                            "v3": fires and ins["readable"] and ins["says_none"],
                            # 自省面版（被测主体自身视点读面）——黑箱测试者的自然视点
                            "v3_self": fires and ins_self["readable"] and ins_self["says_none"],
                            # 只看面的稻草人对照
                            "direct_only": ins["readable"] and ins["says_none"],
                            # 第七轮的决定性对照
                            "direct_observe": (ins["readable"] and ins["says_none"] and granted),
                            "direct_observe_self": (ins_self["readable"] and ins_self["says_none"]
                                                    and granted),
                        },
                    })
        for c_ in cells:
            c_["false_proofs"] = {m: bool(c_["alarms"][m] and c_["authorized"])
                                  for m in c_["alarms"]}
        rep["phaseE_cells"] = cells

        # ---------------- 阶段 F：M1/M2/M3 ----------------
        print("[F] M1/M2/M3 …", flush=True)
        rep["M1_grant_mechanism_census"] = m1_swagger_census(cl)
        rep["M2_vantage_readability"] = {
            obj: m2_vantage_matrix(cl, obj, "bob") for obj in ["alice/r1", "acme/t1"]}
        rep["M3_introspection_fidelity"] = []
        for obj in ALL_OBJS:
            for s in subjects:
                o = introspect(cl, obj, s)
                sf = introspect_self(cl, obj, s)
                rep["M3_introspection_fidelity"].append({
                    "object": obj, "subject": s,
                    "authorized": truth_map.get(f"{obj}|{s}"),
                    "is_acting_credential": s == OBJ_CREDENTIAL[obj],
                    "vantage_credential": o["vantage_credential"],
                    "status": o["status"], "permission": o["permission"],
                    "readable": o["readable"], "says_none": o["says_none"],
                    "status_self": sf["status"], "permission_self": sf["permission"],
                    "readable_self": sf["readable"], "says_none_self": sf["says_none"],
                })

        # ---------------- 阶段 G：授权通道定性 ----------------
        print("[G] 授权通道定性 …", flush=True)
        prov = []
        for obj in ALL_OBJS:
            owner, name = obj.split("/")
            priv = next(r[2] for r in REPOS if f"{r[0]}/{r[1]}" == obj)
            for s in subjects:
                if not truth_map.get(f"{obj}|{s}"):
                    kind = "none"
                elif s == ADMIN_USER:
                    kind = "implicit_site_admin"
                elif s == OBJ_CREDENTIAL[obj]:
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
    out = RESULTS / "real_system.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] -> {out} ({out.stat().st_size} bytes, {rep['meta']['elapsed_s']}s)", flush=True)


if __name__ == "__main__":
    main()

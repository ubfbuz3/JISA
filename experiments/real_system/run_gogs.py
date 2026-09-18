"""
跨实现复核 · **Gogs 0.14.3** 上的三阶段测量（run_real.py 的独立代码库副本）
=========================================================================
动机：Block 10 的全部结论取自 **Gitea 1.22.6 一个系统**。审稿人最可能的一击是
「这是 Gitea 的 API 细节，不是 MST-wi 谓词的性质」。本脚本把同一套三阶段协议
（采集 → 带外授权变更 → 执行 MR）在**另一套独立代码库**上原样重做。

★ 依据仍是 MST-wi 论文原文对两个谓词的定义（见 run_real.py 顶部引文）：
  `cannotReachThroughGUI` 相对 **exploring the user interface** 定义；
  `userCanRetrieveContent` 相对 **during data collection** 定义。
  ⇒ 两者都相对**采集期爬取记录**，不是相对系统授权状态。

⚠️ 诚实边界（写死在脚本里）
  1. **血缘必须披露**：Gitea 2016 年 fork 自 Gogs。本实验定位为
     「独立代码库复核」，**不**声称厂商级独立。
  2. Gogs 是**正确**系统 ⇒ 仍只测**假确证侧与发生率**，不测检出率。
  3. GUI 模型两种读法（snapshot / live）都报，失效只在前者出现。
  4. Gogs 的授权面**天然比 Gitea 窄**（团队授权只在 `/admin/**` 下、无可见性
     PATCH、无 transfer）⇒ **R1/R3 的分母不可与 Gitea 版直接比**，必须各自标注。

与 run_real.py 的**方法学差异**（全部记录在产物 meta 里，不隐藏）
  - Gogs 无 `/api/v1/version`、无 swagger ⇒ M1 的端点普查改用**钉死版本的
    路由表源码** `internal/route/api/v1/api.go@v0.14.3`（程序化解析，见
    `parse_routes`），并在运行时逐条实测方法可用性。
  - Gogs 大量路由要求 **token**（`reqToken()` 查 `IsTokenAuth`）⇒ 每个视点先
    用 Basic 兑换一枚 access token，再用 `Authorization: token <sha1>` 访问。
  - Gogs 无 `PUT /orgs/{org}/members/{u}`（加组织成员）、无 `PATCH /repos/…`
    （改可见性）、无 `POST /orgs/{org}/teams`（组织者建团队）⇒ 带外变更集
    按**该系统的实际机制空间**重写，并在 M1 里如实报出这些缺口。

用法: python run_gogs.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gogs_lab as gl
import m1_census as mc
from gogs_lab import ADMIN_PASS, ADMIN_USER, Client, Server, ensure_admin, write_config

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)
PASS = "LabPass123!"

# 钉死版本的 Gogs 路由表源码（由 gogs_lab 之外的步骤下载，见 meta.route_source）
ROUTE_SOURCE = Path(r"C:\Users\Administrator\WorkBuddy\gogs_lab\gogs_api_routes.go")
ROUTE_SOURCE_REF = "internal/route/api/v1/api.go@gogs/v0.14.3"

USERS = {
    "alice": dict(email="alice@lab.local"),
    "bob":   dict(email="bob@lab.local"),
    "carol": dict(email="carol@lab.local"),
    "dave":  dict(email="dave@lab.local"),
    "eve":   dict(email="eve@lab.local"),
    "frank": dict(email="frank@lab.local"),
}
ORG = "acme"
TEAMS = {"dev": "read", "ops": "write"}

# (owner, name, private, is_org, creator)
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

# 框架自己的动作日志：**只含框架用自己凭证做的共享**（与 Gitea 版同口径）
FRAMEWORK_LOG = {"alice/r1": {"bob": "read"}}


# ==========================================================================
# 客户端（Gogs：每个视点一枚 token）
# ==========================================================================
def clients(admin_token: str | None = None) -> dict[str, Client]:
    out = {"anonymous": Client(label="anonymous")}
    if admin_token is None:
        tk = gl.create_token(ADMIN_USER, ADMIN_PASS, name="lab-root")
        if not tk["token"]:
            raise RuntimeError(f"root token 失败: {tk}")
        admin_token = tk["token"]
    out[ADMIN_USER] = Client(token=admin_token, label=ADMIN_USER)
    for u in USERS:
        tk = gl.create_token(u, PASS, name=f"lab-{u}")
        if not tk["token"]:
            raise RuntimeError(f"{u} token 失败（用户可能还没建）: {tk}")
        out[u] = Client(token=tk["token"], label=u)
    return out


# ==========================================================================
# 阶段 A0 · 只建用户（建用户后才能为各用户兑换 token）
# ==========================================================================
def phaseA0_users(admin: Client) -> dict:
    log: list[dict] = []

    def rec(step, st, body, **extra):
        err = None
        if not (200 <= st < 300):
            err = (json.dumps(body, ensure_ascii=False)[:200]
                   if isinstance(body, (dict, list)) else str(body)[:200])
        log.append({"step": step, "status": st, "error": err, **extra})

    for u, meta in USERS.items():
        rec(f"user:{u}", *admin.post("/api/v1/admin/users", {
            "username": u, "password": PASS, "email": meta["email"]}))
    return {"steps": log, "failures": [s for s in log if not (200 <= s["status"] < 300)]}


# ==========================================================================
# 阶段 A · 基线拓扑（用户已在 A0 建好）
# ==========================================================================
def phaseA_topology(cl: dict[str, Client]) -> dict:
    log: list[dict] = []

    def rec(step, st, body, **extra):
        err = None
        if not (200 <= st < 300):
            err = (json.dumps(body, ensure_ascii=False)[:200]
                   if isinstance(body, (dict, list)) else str(body)[:200])
        log.append({"step": step, "status": st, "error": err, **extra})

    admin = cl[ADMIN_USER]

    # 组织由 dave 自建（Gogs: POST /user/orgs，reqToken，非站点管理员可用）
    rec(f"org:{ORG}", *cl["dave"].post("/api/v1/user/orgs", {
        "username": ORG, "full_name": "Acme"}))

    # ⚠️ Gogs **没有** `POST /orgs/{org}/teams`：建团队只在
    #    `POST /admin/orgs/{orgname}/teams`（reqAdmin）⇒ 本次由 root 代建，
    #    该事实本身计入 M1（"组织自建团队"这条通道在 Gogs 不存在）。
    team_ids = {}
    for tname, perm in TEAMS.items():
        st, b = admin.post(f"/api/v1/admin/orgs/{ORG}/teams", {
            "name": tname, "description": "", "permission": perm})
        rec(f"team:{tname}", st, b, executed_by="root(site admin)")
        if isinstance(b, dict) and b.get("id"):
            team_ids[tname] = b["id"]

    for owner, name, priv, isorg, creator in REPOS:
        path = f"/api/v1/org/{owner}/repos" if isorg else "/api/v1/user/repos"
        # ⚠️ Gogs 的坑：`auto_init: true` **必须同时给 `readme`**，否则建仓 500，
        #    日志为 `getRepoInitFile[]: read readme: is a directory`
        #    （tp 为空 ⇒ 它去读 `conf/init/readme` 这个**目录**）。
        #    实测对照（probe_gogs_repoinit.py）：auto_init+readme=Default ⇒ 201；
        #    只给 auto_init ⇒ 500；auto_init=false ⇒ 201。
        rec(f"repo:{owner}/{name}", *cl[creator].post(path, {
            "name": name, "private": priv, "auto_init": True, "readme": "Default",
            "description": "lab", "default_branch": "master"}))

    # 基线（采集**之前**就存在）的授权：团队 dev += bob，且 dev 挂上 acme/t1
    if team_ids.get("dev"):
        rec("baseline team dev += bob",
            *admin.put(f"/api/v1/admin/teams/{team_ids['dev']}/members/bob"),
            executed_by="root(site admin)")
        rec("baseline team dev += repo t1",
            *admin.put(f"/api/v1/admin/teams/{team_ids['dev']}/repos/t1"),
            executed_by="root(site admin)")
    # 框架自己的 in-band 共享（用 alice 的凭证 = 框架运行的凭证）
    rec("baseline in-band share alice/r1 <- bob",
        *cl["alice"].put("/api/v1/repos/alice/r1/collaborators/bob",
                         {"permission": "read"}))

    return {"steps": log, "team_ids": team_ids,
            "failures": [s for s in log if not (200 <= s["status"] < 300)]}


# ==========================================================================
# 自省面发现（Gogs 无 `/permission` 后缀 ⇒ 必须先问清楚哪个端点可读）
# ==========================================================================
INTROSPECT_ENDPOINTS = [
    # ⚠️ 顺序 = 优先级。`object_read` 必须排在最后：它**与主体无关**
    #    （`GET /repos/{o}/{r}` 里根本没有主体的位置），只看"拥有者能不能读"会把它
    #    误选为自省面（初版就跑出了这个错：选中的是 object_read）。
    ("perm_suffix", "/api/v1/repos/{o}/{r}/collaborators/{u}/permission"),
    ("collab_get", "/api/v1/repos/{o}/{r}/collaborators/{u}"),
    ("collab_list", "/api/v1/repos/{o}/{r}/collaborators"),
    ("object_read", "/api/v1/repos/{o}/{r}"),
]


def discover_introspection(cl, cells: list[tuple[str, str]]) -> dict:
    """在若干 (对象, 主体) 上逐视点探测候选自省端点，选出**真正能判定授权状态**的那个。

    判定标准有两条，缺一不可：
      ① **拥有者视点上可读**：所有探针都返回"确定答案"（不是被拒）；
      ② **能区分主体**：把它的答案当作 oracle 时，对每个探针都给出正确答案
         —— 即 `says_none == (not 该主体实际有权限)`。
    第 ② 条排除了两类假自省面：
      * 与主体无关的读数（`object_read` 对谁都 200）；
      * 只覆盖**直接协作者**、看不到**团队派生**权限的读数
        （Gogs 的 `IsCollaborator` 正是这种 —— 这本身就是本实验要报的结果）。

    另外记录 `best_effort_readable`（只满足 ① 的最优先端点），
    因为"唯一可读的那面不是合法 oracle"是一个**比"完全不可读"更细**的结论。
    """
    truth: dict[str, bool] = {}
    for obj, subj in cells:
        o, r = obj.split("/")
        st, _ = cl[subj].get(f"/api/v1/repos/{o}/{r}")
        truth[f"{obj}|{subj}"] = st == 200

    per: dict[str, dict] = {}
    for name, _ in INTROSPECT_ENDPOINTS:
        rows: dict[str, dict] = {}
        readable_all, correct_all = True, True
        for obj, subj in cells:
            rr = introspect_with(cl, obj, subj, OBJ_CREDENTIAL[obj], name)
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
                    endpoint: str | None) -> dict:
    """以指定视点读授权面。返回 {status, readable, says_none, perm}。

    Gogs 的 `GET …/collaborators/{u}`（IsCollaborator）是 **204/404/422** 语义：
      204 ⇒ 是协作者；404 ⇒ 不是协作者；422 ⇒ 该用户不存在。
      204 与 404 **都是"可读"**（能给出确定答案），但含义相反；
      `/permission` 后缀不存在（恒 404），**不可**与"不是协作者"混同 ⇒ 分开记。

    `endpoint is None`（= 没发现任何可读的自省面）时返回 0/不可读，
    而不是抛异常：**"没有自省面"本身就是本实验要报的结果之一**。
    """
    if endpoint is None:
        return {"vantage_credential": vantage, "endpoint": None, "status": 0,
                "permission": None, "readable": False, "says_none": False}
    owner, repo = obj.split("/")
    tpl = dict(INTROSPECT_ENDPOINTS)[endpoint]
    st, b = cl[vantage].get(tpl.format(o=owner, r=repo, u=subject))
    perm = b.get("permission") if isinstance(b, dict) else None
    if endpoint == "collab_get":
        readable = st in (200, 204, 404)
        says_none = st == 404
    else:
        readable = st == 200 and perm not in (None, "")
        says_none = st == 200 and perm == "none"
    return {"vantage_credential": vantage, "endpoint": endpoint, "status": st,
            "permission": perm, "readable": readable, "says_none": says_none}


def introspect(cl, obj: str, subject: str, endpoint: str | None) -> dict:
    """实验规定的自省视点 = 对象拥有者（组织仓库由组织拥有者代持）。"""
    return introspect_with(cl, obj, subject, OBJ_CREDENTIAL[obj], endpoint)


def introspect_self(cl, obj: str, subject: str, endpoint: str | None) -> dict:
    """被测主体自己的凭证 —— 黑箱测试者的自然视点。"""
    if subject not in cl:
        return {"vantage_credential": subject, "endpoint": endpoint, "status": 0,
                "permission": None, "readable": False, "says_none": False}
    return introspect_with(cl, obj, subject, subject, endpoint)


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
# 阶段 C · 带外授权变更（按 Gogs 的**实际机制空间**重写）
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

    # M1 管理员把 carol 加为 alice/r2 协作者（Gogs 支持，reqRepoAdmin）
    rec("admin_grant_collaborator:alice/r2<-carol", ADMIN_USER,
        *admin.put("/api/v1/repos/alice/r2/collaborators/carol", {"permission": "read"}),
        object="alice/r2", subject="carol")
    # M2 管理员把 eve 加为 alice/r3 协作者
    rec("admin_grant_collaborator:alice/r3<-eve", ADMIN_USER,
        *admin.put("/api/v1/repos/alice/r3/collaborators/eve", {"permission": "read"}),
        object="alice/r3", subject="eve")
    # M3 组织仓库挂到团队（Gogs 只在 /admin/teams/{id}/repos/{reponame}）
    if team_ids.get("dev"):
        rec("team_grant_repo:acme/t2 -> team dev", ADMIN_USER,
            *admin.put(f"/api/v1/admin/teams/{team_ids['dev']}/repos/t2"),
            object="acme/t2", subject="(team dev members)")
    # M4 frank 加入团队 dev（Gogs 只在 /admin/teams/{id}/members/{username}）
    if team_ids.get("dev"):
        rec("admin_add_team_member:dev<-frank", ADMIN_USER,
            *admin.put(f"/api/v1/admin/teams/{team_ids['dev']}/members/frank"),
            object=f"team:{team_ids['dev']}", subject="frank")
    # M5 仓库拥有者把 frank 加为 dave/r5 的协作者（非站点管理员的带外通道）
    rec("owner_grant_collaborator:dave/r5<-frank", "dave",
        *dave.put("/api/v1/repos/dave/r5/collaborators/frank", {"permission": "read"}),
        object="dave/r5", subject="frank")

    # ⚠️ 记录 Gitea 侧存在、Gogs 侧**不存在**的带外通道（正面证据，不静默略过）
    absent = []
    for kind, method, path, body in [
        ("org_add_member:acme<-frank", "PUT", f"/api/v1/orgs/{ORG}/members/frank", None),
        ("visibility_flip:alice/r4->public", "PATCH", "/api/v1/repos/alice/r4",
         {"private": False}),
        ("org_owner_create_team", "POST", f"/api/v1/orgs/{ORG}/teams",
         {"name": "tmp", "permission": "read"}),
    ]:
        st, b = admin.req(method, path, body)
        absent.append({"mutation": kind, "status": st, "note": "Gogs 无此路由（预期 404）",
                       "response": (json.dumps(b, ensure_ascii=False)[:160]
                                    if isinstance(b, (dict, list)) else str(b)[:160])})

    return {"mutations": muts, "absent_channels": absent,
            "failures": [m for m in muts if not (200 <= m["status"] < 300)]}


# ==========================================================================
# 爬取（GUI 等价记录）
# ==========================================================================
def _norm_repo(b: dict) -> str:
    keys = ("id", "name", "full_name", "private", "created_at", "updated_at",
            "size", "empty", "default_branch")
    return json.dumps({k: b.get(k) for k in keys if k in b}, sort_keys=True,
                      ensure_ascii=False)


def crawl(c: Client, orgs: list[str], limit: int = 50) -> dict:
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
    if isinstance(body, dict):
        for r in body.get("data", []) or []:
            visit(r["owner"]["login"], r["name"])

    return {"urls": sorted(urls), "outputs": sorted(outputs), "sources": sources}


# ==========================================================================
# M1 · 授权授予机制空间普查（**路由表源码**驱动，因为 Gogs 没有 swagger）
# ==========================================================================
def m1_route_census(parsed: dict, cl=None) -> dict:
    """M1 普查（Gogs 侧）。分母 = 钉死版本的路由表条目数。

    ★ 模式表与 Gitea 侧**共用** `m1_census.SHARED_PATTERNS`（结构化归一化：
    把每个路径参数名整体抹掉），否则两边各用各的正则写法，数字**不可比**，
    也容易被质疑"挑了对自己有利的写法"。
    """
    pwm: dict[str, list[str]] = {}
    adm: dict[str, bool] = {}
    for r in parsed["routes"]:
        pwm.setdefault(r["path"], [])
        pwm[r["path"]] = sorted(set(pwm[r["path"]]) | set(r["methods"]))
        adm[r["path"]] = adm.get(r["path"], False) or r["requires_site_admin"]
    return mc.census(
        pwm, adm,
        source_label="Gogs 0.14.3 · 钉死版本的路由表源码（Gogs 无 swagger 端点）",
        denominator_label="路由表条目数（源码解析，含只读端点）") | {
        "route_entries_raw": parsed["route_entries"],
        "unique_paths": len(pwm),
    }


def parse_routes(go_src: Path) -> dict:
    """程序化解析 Gogs 路由表源码（`m.Group` / `m.Get|Post|Put|Patch|Delete` / `m.Combo`）。

    返回 {routes, route_entries, groups}。这是 M1 的**分母来源**：钉死版本的路由表
    条目数（因为 Gogs 没有 swagger 端点可读）。

    ⚠️ **两遍式，不能边扫边判**：`reqAdmin()` / `reqToken()` 写在**组的收尾行**上
    （形如 `}, reqAdmin())`），而组内路由在收尾行**之前**就被记录了
    ⇒ 必须先收完所有组的 (open_i, close_i, handlers)，再对每条路由判断
    "有没有一个包住它的组要求管理员/令牌"。
    （初版是边扫边判：会把整个 `/admin/**` 误判成"不需要站点管理员"。）
    """
    lines = go_src.read_text(encoding="utf-8").splitlines()
    groups: list[dict] = []
    raw_routes: list[dict] = []
    stack: list[dict] = []
    pending: dict | None = None

    def flush_pending():
        nonlocal pending
        if pending is not None:
            raw_routes.append({"path": pending["path"],
                               "methods": sorted(set(pending["methods"])),
                               "i": pending["i"], "inline": pending["inline"]})
            pending = None

    for i, raw in enumerate(lines):
        line = raw.strip()
        if not line:
            continue

        m = re.match(r'^m\.Group\("([^"]*)"', line)
        if m:
            flush_pending()
            stack.append({"prefix": m.group(1), "open_i": i})
            continue

        m = re.match(r'^m\.Combo\("([^"]*)"', line)
        if m:
            flush_pending()
            pending = {"path": "".join(g["prefix"] for g in stack) + m.group(1),
                       "methods": [], "i": i, "inline": line}
            continue

        m = re.match(r'^m\.(Get|Post|Put|Patch|Delete)\("([^"]*)"', line)
        if m:
            flush_pending()
            raw_routes.append({
                "path": "".join(g["prefix"] for g in stack) + m.group(2),
                "methods": [m.group(1).upper()], "i": i, "inline": line})
            continue

        m = re.match(r'^\.?(Get|Post|Put|Patch|Delete)\(', line)
        if m and pending is not None:
            pending["methods"].append(m.group(1).upper())
            pending["inline"] += " " + line
            continue

        # 组的收尾行：`})` / `}, reqToken())` / `}, reqToken(), orgAssignment(true))`
        if re.match(r'^\}\s*[\.,\);]', line):
            flush_pending()
            if stack:
                g = stack.pop()
                g["close_i"] = i
                g["req_admin"] = "reqAdmin()" in line
                g["req_token"] = "reqToken()" in line
                groups.append(g)
            continue

    flush_pending()

    # 归一化：① Gogs 的 `:param` → `{param}`；② 去掉顶层 `/v1` 前缀。
    # 进一步的"参数名抹平"与模式匹配统一交给 `m1_census.normalize_path`，
    # 这里只做 Gogs 自己的语法转换。
    for r in raw_routes:
        r["path"] = re.sub(r":([A-Za-z_]+)", r"{\1}", r["path"]).removeprefix("/v1")

    routes = []
    for r in raw_routes:
        enclosing = [g for g in groups if g["open_i"] < r["i"] < g["close_i"]]
        routes.append({
            "path": r["path"], "methods": r["methods"],
            "requires_site_admin": any(g["req_admin"] for g in enclosing),
            "requires_token": (any(g["req_token"] for g in enclosing)
                               or "reqToken()" in r["inline"]),
        })
    return {"routes": routes, "route_entries": len(routes),
            "groups": [{"prefix": g["prefix"], "req_admin": g["req_admin"],
                        "req_token": g["req_token"]} for g in groups]}




# ==========================================================================
# 主流程
# ==========================================================================
def main():
    t0 = time.time()
    rep: dict = {"meta": {
        "system": "Gogs",
        "gogs_version": gl.GOGS_VERSION,
        "lab_dir": str(gl.LAB),
        "generated_by": "experiments/real_system/run_gogs.py",
        "route_source": ROUTE_SOURCE_REF,
        "positioning": ("独立代码库复核（independent codebase replication）。"
                        "Gitea 2016 年 fork 自 Gogs ⇒ **不**声称厂商级独立，"
                        "该血缘在正文脚注中披露。"),
        "phases": ["A 基线拓扑", "A2 自省面发现", "B 采集爬取", "C 带外授权变更",
                   "D 变更后爬取", "E MR 执行与四方法裁决", "F M1/M2/M3", "G M6"],
        "methodological_differences_vs_gitea": [
            "Gogs 无 /api/v1/version、无 swagger ⇒ M1 分母改为钉死版本的路由表源码条目数",
            "Gogs 受保护路由要求 access token（reqToken 查 IsTokenAuth）；query/Basic 均 401",
            "Gogs 无 PUT /orgs/{org}/members/{u}（加组织成员）",
            "Gogs 无 PATCH /repos/{o}/{r}（改可见性）",
            "Gogs 无 POST /orgs/{org}/teams（组织拥有者建团队）⇒ 建团队需站点管理员",
            "Gogs 无 /repos/{o}/{r}/collaborators/{u}/permission 后缀",
        ],
        "honesty_boundary": (
            "Gogs 是正确系统，不含对象级授权漏洞 ⇒ 只测假确证侧与发生率，不测检出率；"
            "不声称实验证明 MST-wi 失效；GUI 模型的 snapshot / live 两种读法都报，"
            "失效只在前者出现。"),
    }}

    cfg = write_config()
    adm = ensure_admin(cfg)
    print(f"[bootstrap] {adm['steps']} admin ok={adm['ok']} rc={adm['rc']}",
          flush=True)
    if not adm["ok"]:
        raise SystemExit(f"bootstrap 失败：\n{adm['raw_tail_2k']}")
    rep["meta"]["bootstrap"] = {k: adm[k] for k in
                                ("rc", "ok", "idempotent", "tail", "schema_tables", "steps")}

    with Server(cfg) as srv:
        print(f"[A] 服务就绪 gogs={gl.version()} ready_ms={srv.ready_ms}", flush=True)
        admin_tok = gl.create_token(ADMIN_USER, ADMIN_PASS, name="lab-root")
        if not admin_tok["token"]:
            raise SystemExit(f"root token 失败: {admin_tok}")
        admin_cl = Client(token=admin_tok["token"], label=ADMIN_USER)
        a0 = phaseA0_users(admin_cl)
        print("     用户创建", len(a0["steps"]), "失败", len(a0["failures"]), flush=True)
        for s in a0["failures"]:
            print("       ! ", s["step"], s["status"], s.get("error"), flush=True)

        cl = clients(admin_token=admin_tok["token"])   # 现在可以给每个用户兑换 token 了
        report_A = phaseA_topology(cl)
        report_A["steps"] = a0["steps"] + report_A["steps"]
        report_A["failures"] = a0["failures"] + report_A["failures"]
        rep["phaseA_topology"] = report_A
        print("     拓扑步骤", len(report_A["steps"]), "失败", len(report_A["failures"]),
              flush=True)
        for s in report_A["failures"]:
            print("       ! ", s["step"], s["status"], s.get("error"), flush=True)

        # ---------------- A2：自省面发现 ----------------
        print("[A2] 自省面发现 …", flush=True)
        probe_cells = [("alice/r1", "bob"),    # 有权限（直接协作者，in-band 基线）
                       ("acme/t1", "bob"),     # 有权限（**团队派生**）
                       ("alice/r2", "carol"),  # 无权限
                       ("acme/t1", "eve"),     # 无权限
                       ("dave/r5", "frank")]   # 无权限
        disc = discover_introspection(cl, probe_cells)
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
            print(f"       {n:12s} 拥有者全可读={d['readable_on_all_probes']!s:5s}"
                  f" 可作合法 oracle={d['correct_on_all_probes']}", flush=True)

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
        print("     变更", len(rc["mutations"]), "失败", len(rc["failures"]),
              "；记录到的 Gitea-有/Gogs-无 通道", len(rc["absent_channels"]), flush=True)
        for m in rc["failures"]:
            print("       ! ", m["mutation"], m["status"], m.get("error"), flush=True)

        # ---------------- 阶段 D：变更后再爬一次（live 读法用） ----------------
        print("[D] 变更后爬取 …", flush=True)
        snap_after = {u: crawl(c, [ORG]) for u, c in cl.items()}
        rep["phaseD_crawl_after"] = {u: {"urls": d["urls"]} for u, d in snap_after.items()}

        # ---------------- 阶段 E：MR 执行 + 四方法裁决 ----------------
        print("[E] MR 执行 …", flush=True)
        acting = {}
        for obj in ALL_OBJS:
            owner, name = obj.split("/")
            st, b = cl[OBJ_CREDENTIAL[obj]].get(f"/api/v1/repos/{owner}/{name}")
            acting[obj] = {"granted": st == 200,
                           "out": _norm_repo(b) if isinstance(b, dict) else None}

        subjects = list(USERS) + [ADMIN_USER]
        cells = []
        truth_map = {}
        for obj in ALL_OBJS:
            owner, name = obj.split("/")
            for subj in subjects:
                if subj == OBJ_CREDENTIAL[obj]:
                    continue
                st, b = cl[subj].get(f"/api/v1/repos/{owner}/{name}")
                granted = st == 200
                out_subj = _norm_repo(b) if isinstance(b, dict) else None
                truth_map[f"{obj}|{subj}"] = granted

                can_snap = obj not in set(snap_before[subj]["urls"])
                can_live = obj not in set(snap_after[subj]["urls"])
                out_equal = bool(granted and acting[obj]["granted"]
                                 and out_subj == acting[obj]["out"])
                ins = introspect(cl, obj, subj, oracle)
                ins_self = introspect_self(cl, obj, subj, oracle)
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

        # ---------------- 阶段 F：M1/M2/M3 ----------------
        print("[F] M1/M2/M3 …", flush=True)
        parsed = parse_routes(ROUTE_SOURCE) if ROUTE_SOURCE.exists() else {
            "routes": [], "route_entries": 0, "groups": []}
        if not parsed["routes"]:
            raise SystemExit(f"路由表源码不可读或解析为空：{ROUTE_SOURCE}")
        rep["M1_grant_mechanism_census"] = m1_route_census(parsed, cl)
        rep["M1b_route_groups"] = parsed["groups"]
        print("     路由表条目", rep["M1_grant_mechanism_census"]["denominator_entries"],
              "授予端点", rep["M1_grant_mechanism_census"]["grant_endpoints_total"],
              "其中非站点管理员",
              rep["M1_grant_mechanism_census"]["grant_endpoints_without_site_admin"],
              flush=True)

        rep["M2_vantage_readability"] = {
            obj: m2_vantage_matrix(cl, obj, "bob") for obj in ["alice/r1", "acme/t1"]}
        rep["M3_introspection_fidelity"] = []
        for obj in ALL_OBJS:
            for s in subjects:
                o = introspect(cl, obj, s, oracle)
                sf = introspect_self(cl, obj, s, oracle)
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

        # 端点可用性实测（只针对本次真实存在的对象）
        rep["api_surface_probe"] = gl.probe_api_surface(
            token=cl[ADMIN_USER].token)

    rep["meta"]["elapsed_s"] = round(time.time() - t0, 1)
    out = RESULTS / "gogs_real_system.json"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[done] -> {out} ({out.stat().st_size} bytes, {rep['meta']['elapsed_s']}s)",
          flush=True)


if __name__ == "__main__":
    main()

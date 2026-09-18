"""
受控脆弱性靶机（Controlled Vulnerable Authorization Target, CVAT）
================================================================

为回答审稿人 "why are all three real systems non-vulnerable?" 而设的**阳性对照**：
在本地起一个忠实复刻 Gitea 1.22.6 对象级授权 API 面的 HTTP 服务，内部维护一份
**正确**的授权模型，并在少数端点上植入**确定性的 BOLA / BFLA 缺陷**（运行期绕过，
不写进授权模型）。自省面（/collaborators/{u}/permission）始终回报**正确**的授权，
因此检测器在"面说 none 但实则可读"时应报警 ⇒ 测 TP/FN/FP。

设计要点（诚实边界，写死在代码里）：
  1. 这是**受控靶机**，不是生产 Gitea 二进制。它复刻的是引擎实际消费的 API 契约
     （run_real.py 探测的那些端点与字段），所以检测器在"真有越权时能否检出"这一
     逻辑被公平测量；它**不**声称能发现 Gitea 的真实 CVE。
  2. 植入缺陷只影响运行期 GET /repos/{o}/{r}（BOLA）与一处 PUT 协作者授予（BFLA）；
     列表/搜索/自省/变更类端点一律走**正确**模型 ⇒ 爬取快照反映真实可见性，
     从而 cannotReachThroughGUI 正确为 True（攻击者爬不到被植入对象）。
  3. 同一套 SEED_FLAWS 同时被靶机与 run_seeded.py 消费，保证真值单一来源。

为什么不用 Go 重建 Gitea 源码：本机无 Go / MinGW 工具链，从源码编译带 CGO sqlite
的 Gitea 既慢又易失败；阳性对照只需 API 契约等价，靶机即可满足，且 100% 可复现。

用法：python seeded_target.py [port]   （run_seeded.py 会直接 import 并在线程内启动）
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

GITEA_VERSION = "1.22.6-seeded-control"

# --------------------------------------------------------------------------
# 拓扑（与 run_real.py 完全一致，保证爬取/自省逻辑可复用）
# --------------------------------------------------------------------------
USERS = ["alice", "bob", "carol", "dave", "eve", "frank"]
ADMIN_USER = "root"
PASS = "LabPass123!"
ORG = "acme"
TEAMS = {"dev": "read", "ops": "write"}

# (owner, name, private, org, creator)
REPOS = [
    ("alice", "r1", True, False, "alice"),
    ("alice", "r2", True, False, "alice"),
    ("alice", "r3", True, False, "alice"),
    ("alice", "r4", True, False, "alice"),
    ("alice", "pub1", False, False, "alice"),
    ("acme", "t1", True, True, "dave"),
    ("acme", "t2", True, True, "dave"),
    ("dave", "r5", True, False, "dave"),
]
OBJ_CREDENTIAL = {f"{o}/{n}": cr for o, n, _, _, cr in REPOS}
ALL_OBJS = [f"{o}/{n}" for o, n, _, _, _ in REPOS]

# 基线（采集前就存在的）授权 —— 即"正确模型"的初始授权状态
#   alice/r1 <- bob (read)            （in-band 共享）
#   acme/t1 <- team dev（含 bob）     （团队授权）
# 阶段 C 的带外变更也写进正确模型：
#   alice/r2 <- carol, alice/r3 <- eve, acme/t2 <- team dev,
#   alice/r4 -> public, acme <- frank, team dev <- frank
BASELINE_GRANT = [("alice/r1", "bob", "read")]

# 植入缺陷（运行期绕过，**不**进入正确模型）：
#   BOLA：特定 (subject, obj) 在 GET /repos/{o}/{r} 被非法放行（返回 200）。
#   BFLA：特定 (actor, action) 的写操作被非法放行（返回 200）。
# 注意：自省面回报的是正确模型（none），所以检测器应当报警。
SEED_FLAWS = [
    # (kind, subject, obj) —— BOLA 读越权（subject 对 obj 在正确模型里权限严格为 none）
    ("BOLA", "eve", "alice/r1"),    # eve 仅持有 alice/r3，与 r1 无任何关系
    ("BOLA", "bob", "dave/r5"),     # bob 与 dave/r5 无任何关系（r5 不入任何团队）
    ("BOLA", "carol", "acme/t2"),   # carol 非 acme 组织成员、不在 dev 团队
]
# BFLA：非特权 actor 成功对他人仓库执行"授予协作者"写操作
BFLA_FLAW = ("BFLA", "bob", "alice/r4")  # bob 非 admin/owner，却成功 PUT 协作者


# --------------------------------------------------------------------------
# 授权模型（正确状态）
# --------------------------------------------------------------------------
class Model:
    def __init__(self):
        self.users = {u: dict(password=PASS, email=f"{u}@lab.local",
                              restricted=False, is_admin=False) for u in USERS}
        self.users[ADMIN_USER] = dict(password="AdminPass123!", email="root@lab.local",
                                     restricted=False, is_admin=True)
        self.orgs = {ORG: dict(owner="dave", members=set())}
        self.teams = {}            # id -> dict(name, org, perm, members, repos)
        self.next_team_id = 1
        self.repos = {}            # "o/r" -> dict(owner, name, private, org, creator)
        for o, n, priv, isorg, cr in REPOS:
            self.repos[f"{o}/{n}"] = dict(owner=o, name=n, private=priv,
                                          org=(o if isorg else None), creator=cr,
                                          collab={})  # user -> perm
        # 基线授权
        for obj, subj, perm in BASELINE_GRANT:
            self.repos[obj]["collab"][subj] = perm

    # ---- 正确授权判定 ----
    def intended_perm(self, user: str, obj: str) -> str:
        """返回 none/read/write/admin（基于正确模型）。"""
        if user == ADMIN_USER:
            return "admin"
        r = self.repos.get(obj)
        if r is None:
            return "none"
        if r["owner"] == user or r["creator"] == user:
            return "admin"
        if user in r["collab"]:
            return r["collab"][user]
        # 组织团队授权
        if r["org"]:
            for tid, t in self.teams.items():
                if t["org"] == r["org"] and obj in t["repos"]:
                    if user in t["members"]:
                        return t["perm"]
                    if user in self.orgs[r["org"]]["members"]:
                        # 组织成员对私有团队仓库默认无权限，除非在团队
                        return "none"
        return "none"

    def can_see_list(self, user: str, obj: str) -> bool:
        """列表/搜索端点用：用户在 user/repos、org/repos、search 中能否看到该仓库。"""
        r = self.repos.get(obj)
        if r is None:
            return False
        if not r["private"]:
            return True
        if r["owner"] == user or r["creator"] == user:
            return True
        if user in r["collab"]:
            return True
        if r["org"] and user in self.orgs[r["org"]]["members"]:
            for tid, t in self.teams.items():
                if t["org"] == r["org"] and obj in t["repos"] and user in t["members"]:
                    return True
        return False

    # ---- 阶段 C 带外变更（写进正确模型） ----
    def apply_mutations(self):
        # M1 admin 把 carol 加为 alice/r2 协作者
        self.repos["alice/r2"]["collab"]["carol"] = "read"
        # M2 admin 把 eve 加为 alice/r3 协作者
        self.repos["alice/r3"]["collab"]["eve"] = "read"
        # M3 acme/t2 -> team dev（含 carol/frank 后自动获得读）
        if "dev" in (t for t in self.teams.values() if t["name"] == "dev"):
            for tid, t in self.teams.items():
                if t["name"] == "dev":
                    t["repos"].add("acme/t2")
        # M4 alice/r4 -> public
        self.repos["alice/r4"]["private"] = False
        # M5 frank 加入组织 + dev 团队
        self.orgs[ORG]["members"].add("frank")
        for tid, t in self.teams.items():
            if t["name"] == "dev":
                t["members"].add("frank")


# --------------------------------------------------------------------------
# HTTP 处理器
# --------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    model = None
    seeded = {}          # (subject, obj) -> True  （BOLA 植入）
    bfla_actor = None    # BFLA：谁可越权写
    bfla_obj = None
    _lock = threading.Lock()

    def log_message(self, *a):  # 静默
        pass

    # ---- 工具 ----
    def _send(self, code, body=None):
        self.send_response(code)
        if body is None:
            self.end_headers()
            return
        data = json.dumps(body).encode("utf-8")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth_user(self):
        h = self.headers.get("Authorization", "")
        if not h.startswith("Basic "):
            return None
        import base64
        try:
            raw = base64.b64decode(h[6:]).decode()
            u, p = raw.split(":", 1)
        except Exception:
            return None
        m = Handler.model
        rec = m.users.get(u)
        if rec and rec["password"] == p:
            return u
        return None

    def _repo_json(self, obj: str) -> dict:
        r = Handler.model.repos[obj]
        return {
            "id": abs(hash(obj)) % 10**6, "name": r["name"],
            "full_name": obj, "private": r["private"],
            "owner": {"login": r["owner"]}, "empty": False,
            "default_branch": "main", "size": 1,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

    # ---- 路由 ----
    def do_GET(self):
        u = Handler._auth_user(self)
        path = urlparse(self.path).path
        m = Handler.model

        if path == "/api/v1/version":
            return self._send(200, {"version": GITEA_VERSION})

        # 自省面：回报**正确**模型（即使被植入绕过，面仍说 none）
        mm = re.match(r"^/api/v1/repos/([^/]+)/([^/]+)/collaborators/([^/]+)/permission$", path)
        if mm:
            o, r, subj = mm.group(1), mm.group(2), mm.group(3)
            obj = f"{o}/{r}"
            if obj not in m.repos:
                return self._send(404, {"message": "Not Found"})
            perm = m.intended_perm(subj, obj)
            return self._send(200, {"user": {"login": subj},
                                    "repo": obj, "permission": perm})

        mm = re.match(r"^/api/v1/repos/([^/]+)/([^/]+)/collaborators$", path)
        if mm:
            o, r = mm.group(1), mm.group(2)
            obj = f"{o}/{r}"
            if obj not in m.repos:
                return self._send(404)
            return self._send(200, [{"login": c} for c in m.repos[obj]["collab"]])

        # 仓库详情：BOLA 植入点
        mm = re.match(r"^/api/v1/repos/([^/]+)/([^/]+)$", path)
        if mm:
            o, r = mm.group(1), mm.group(2)
            obj = f"{o}/{r}"
            if obj not in m.repos:
                return self._send(404, {"message": "Not Found"})
            # 正确鉴权
            perm = m.intended_perm(u, obj) if u else "none"
            if perm != "none":
                return self._send(200, self._repo_json(obj))
            # 植入绕过：特定 (u, obj) 非法放行
            if u and (u, obj) in Handler.seeded:
                return self._send(200, self._repo_json(obj))   # ★ BOLA 缺陷
            # 匿名或无权限
            if u is None:
                return self._send(401, {"message": "Unauthorized"})
            return self._send(404, {"message": "Not Found"})

        if path == "/api/v1/user/repos":
            if u is None:
                return self._send(401)
            out = [self._repo_json(o) for o in ALL_OBJS if m.can_see_list(u, o)]
            return self._send(200, out)

        mm = re.match(r"^/api/v1/orgs/([^/]+)/repos$", path)
        if mm:
            if u is None:
                return self._send(401)
            org = mm.group(1)
            out = [self._repo_json(o) for o, r in m.repos.items()
                   if r["org"] == org and m.can_see_list(u, o)]
            return self._send(200, out)

        if path == "/api/v1/repos/search":
            if u is None:
                return self._send(401)
            q = urlparse(self.path).query
            out = [self._repo_json(o) for o in ALL_OBJS if m.can_see_list(u, o)]
            return self._send(200, {"data": out, "ok": True})

        if path == "/swagger.v1.json":
            return self._send(200, {"paths": {p: {"get": {}} for p in [
                "/repos/{owner}/{repo}",
                "/repos/{owner}/{repo}/collaborators/{collaborator}",
                "/repos/{owner}/{repo}/collaborators/{username}/permission",
                "/teams/{id}/repos/{org}/{repo}",
                "/teams/{id}/members/{username}",
                "/orgs/{org}/members/{username}",
                "/orgs/{org}/teams",
                "/orgs",
                "/repos/{owner}/{repo}/transfer",
                "/repos/{owner}/{repo}",
                "/repos/{owner}/{repo}/keys",
                "/admin/users",
            ]}})

        if path == "/__seeded__":
            return self._send(200, {"bola": [list(x) for x in Handler.seeded_flaws],
                                    "bfla": list(Handler.bfla_flaw)})

        return self._send(404, {"message": "Not Found"})

    def do_POST(self):
        u = Handler._auth_user(self)
        path = urlparse(self.path).path
        m = Handler.model
        body = self._read_body()

        if path == "/api/v1/admin/users":
            uname = body.get("username")
            if uname and uname not in m.users:
                m.users[uname] = dict(password=body.get("password", PASS),
                                      email=body.get("email", ""), restricted=False,
                                      is_admin=False)
            return self._send(201, {"username": uname})

        if path == "/api/v1/orgs":
            return self._send(201, {"username": body.get("username", ORG)})

        mm = re.match(r"^/api/v1/orgs/([^/]+)/teams$", path)
        if mm:
            name = body.get("name")
            tid = m.next_team_id
            m.next_team_id += 1
            m.teams[tid] = dict(name=name, org=mm.group(1),
                                perm=body.get("permission", "read"),
                                members=set(), repos=set())
            return self._send(201, {"id": tid, "name": name})

        mm = re.match(r"^/api/v1/user/repos$|^/api/v1/orgs/([^/]+)/repos$", path)
        if mm:
            name = body.get("name")
            if mm.group(1):
                obj = f"{mm.group(1)}/{name}"
            else:
                obj = f"{u}/{name}"
            m.repos[obj] = dict(owner=(mm.group(1) or u), name=name,
                                private=body.get("private", True),
                                org=(mm.group(1) or None), creator=u, collab={})
            return self._send(201, self._repo_json(obj))

        return self._send(404)

    def do_PUT(self):
        u = Handler._auth_user(self)
        path = urlparse(self.path).path
        m = Handler.model
        body = self._read_body()

        mm = re.match(r"^/api/v1/repos/([^/]+)/([^/]+)/collaborators/([^/]+)$", path)
        if mm:
            o, r, subj = mm.group(1), mm.group(2), mm.group(3)
            obj = f"{o}/{r}"
            # BFLA 植入：非特权 actor（bob，非 admin/owner）成功授予协作者
            if Handler.bfla_actor and u == Handler.bfla_actor and obj == Handler.bfla_obj:
                if obj in m.repos:
                    m.repos[obj]["collab"][subj] = body.get("permission", "read")
                    return self._send(204)   # ★ BFLA 缺陷：越权写成功
            # 正确路径：只有 owner/admin 可授予
            if u == ADMIN_USER or (obj in m.repos and m.repos[obj]["owner"] == u):
                if obj in m.repos:
                    m.repos[obj]["collab"][subj] = body.get("permission", "read")
                    return self._send(204)
            return self._send(403, {"message": "Forbidden"})

        mm = re.match(r"^/api/v1/teams/([^/]+)/members/([^/]+)$", path)
        if mm:
            tid = int(mm.group(1))
            if tid in m.teams:
                m.teams[tid]["members"].add(mm.group(2))
                return self._send(204)
            return self._send(404)

        mm = re.match(r"^/api/v1/teams/([^/]+)/repos/([^/]+)/([^/]+)$", path)
        if mm:
            tid = int(mm.group(1))
            obj = f"{mm.group(2)}/{mm.group(3)}"
            if tid in m.teams:
                m.teams[tid]["repos"].add(obj)
                return self._send(204)
            return self._send(404)

        mm = re.match(r"^/api/v1/orgs/([^/]+)/members/([^/]+)$", path)
        if mm:
            if mm.group(1) in m.orgs:
                m.orgs[mm.group(1)]["members"].add(mm.group(2))
                return self._send(204)
            return self._send(404)

        return self._send(404)

    def do_PATCH(self):
        u = Handler._auth_user(self)
        path = urlparse(self.path).path
        m = Handler.model
        body = self._read_body()
        mm = re.match(r"^/api/v1/repos/([^/]+)/([^/]+)$", path)
        if mm:
            obj = f"{mm.group(1)}/{mm.group(2)}"
            if obj in m.repos and (u == ADMIN_USER or m.repos[obj]["owner"] == u):
                if "private" in body:
                    m.repos[obj]["private"] = bool(body["private"])
                return self._send(200, self._repo_json(obj))
            return self._send(403)
        return self._send(404)

    def do_DELETE(self):
        return self._send(404)

    def _read_body(self):
        try:
            ln = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(ln) if ln else b""
            return json.loads(raw.decode("utf-8")) if raw else {}
        except Exception:
            return {}


# --------------------------------------------------------------------------
# 启动（供 run_seeded.py import 用）
# --------------------------------------------------------------------------
def make_server(port: int = 3319):
    Handler.model = Model()
    Handler.seeded_flaws = SEED_FLAWS
    Handler.bfla_flaw = BFLA_FLAW
    Handler.seeded = {(s, o) for (k, s, o) in SEED_FLAWS if k == "BOLA"}
    Handler.bfla_actor = BFLA_FLAW[1]
    Handler.bfla_obj = BFLA_FLAW[2]
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return srv


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3319
    srv = make_server(port)
    print(f"[CVAT] listening on http://127.0.0.1:{port}  version={GITEA_VERSION}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()

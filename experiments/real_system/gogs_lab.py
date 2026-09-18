"""
真实系统实验台（**Gogs 0.14.3**）· 生命周期与 API 客户端
=======================================================
对应第八轮之后的**跨厂商复核**：把 Block 10 在 Gitea 1.22.6 上做的
「MR vs 直接请求」三阶段测量，在**另一套独立代码库**上重做一遍，
以回答「snapshot-vs-live 失效是不是 Gitea 的 API 细节造成的」。

为什么选 Gogs 而不是 GitLab / Nextcloud：
  1. 本机 Docker **守护进程未运行**（`docker version` 报 dockerDesktopLinuxEngine
     管道不存在），php 不在 PATH；Gogs 与 Gitea 一样是**单文件 Go 二进制 + 内建
     SQLite**，`gogs web` 即起服务 ⇒ 零新增依赖、可复现、无常驻进程树。
  2. 本机实测：Gogs v0.14.3 windows/amd64 单文件 93 MB，`gogs.exe --version` 正常。
  3. ⚠️ **血缘必须披露**：Gitea 于 2016 年从 Gogs fork 出来，两者 API 形近。
     因此本实验的定位是「**独立代码库复核（independent codebase replication）**」，
     **不**声称厂商级独立。Gogs 侧的关键差别在授权自省面（见 results/gogs_lab.json
     的 introspection_surface_probe），该差别是本实验要测的东西之一。

设计约束（沿用 gitea_lab.py）：
  * 进程树会被回收 ⇒ 「启动 + 等就绪 + 采集 + 关闭」单命令闭环。
  * 路径含中文易出问题 ⇒ 工作目录放**纯 ASCII**
    （C:\\Users\\Administrator\\WorkBuddy\\gogs_lab）。
  * 网络请求绕代理 ⇒ 所有 HTTP 走 ProxyHandler({})。
  * Gogs 的工作目录 = 进程 CWD；配置用 `--config` 显式指定。
  * Gogs **没有 `migrate` 子命令**：首次 `admin create-user` / `web` 会自动建表。
"""

from __future__ import annotations

import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
GOGS_EXE = Path(os.environ.get(
    "BOLA_GOGS_EXE", r"C:\Users\Administrator\WorkBuddy\gogs_lab\bin\gogs.exe"))
LAB = Path(os.environ.get("BOLA_GOGS_DIR", r"C:\Users\Administrator\WorkBuddy\gogs_lab\inst1"))
RESULTS = HERE / "results"
PORT = int(os.environ.get("BOLA_GOGS_PORT", "3312"))
BASE = f"http://127.0.0.1:{PORT}"

ADMIN_USER = "root"
ADMIN_PASS = "AdminPass123!"
ADMIN_EMAIL = "root@lab.local"

# 版本必须钉死，否则实验不可复现
GOGS_VERSION = "0.14.3"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# --------------------------------------------------------------------------
# HTTP 客户端
# --------------------------------------------------------------------------
class Client:
    """一个凭证 = 一个视点（vantage）。整个实验的核心变量就是"谁在看"。

    ⚠️ **Gogs 与 Gitea 的认证契约不同**（本实验必须如实反映，不得抹平）：
    Gogs 的 `reqToken()` 要求 `c.IsTokenAuth` —— 即 **必须是 access token**，
    HTTP Basic 会被直接 401（见 `internal/route/api/v1/api.go:107-115`）。
    受影响的路由包括 `/user`、`/user/repos`、`/user/orgs`、`/org/:org/repos`、
    `/orgs/:orgname/**`、`/orgs/:org/repos` 等。⇒ 每个视点需要一枚 token。
    """

    def __init__(self, base: str = BASE, user: str | None = None,
                 password: str | None = None, label: str = "anonymous",
                 token: str | None = None):
        self.base = base.rstrip("/")
        self.label = label
        self.user = user
        self.password = password
        self.token = token
        self._hdr = {"Accept": "application/json", "Content-Type": "application/json"}
        if token is not None:
            # ★ 实测（probe_gogs_auth.py，2026-09-18）Gogs 0.14.3 **只认**
            #   `Authorization: token <sha1>`：
            #     A `?token=<sha1>`   → 401
            #     B `Authorization: token <sha1>` → 200
            #     C `Authorization: Bearer <sha1>` → 401
            #     D `Authorization: Basic …`        → 401（reqToken 要求 IsTokenAuth）
            self._hdr["Authorization"] = f"token {token}"
        elif user is not None and password is not None:
            raw = base64.b64encode(f"{user}:{password}".encode()).decode()
            self._hdr["Authorization"] = f"Basic {raw}"

    def req(self, method: str, path: str, body=None, timeout: int = 25):
        """返回 (status, parsed)。网络/解析异常一律折算为 status 0/…，不抛。"""
        url = self.base + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        r = urllib.request.Request(url, data=data, method=method, headers=dict(self._hdr))
        try:
            with _OPENER.open(r, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return resp.status, _maybe_json(raw)
        except urllib.error.HTTPError as e:
            # ⚠️ Gogs 在部分 404 上会直接把连接关掉 ⇒ `e.read()` 抛
            #    ConnectionResetError(WinError 10054)。状态码本身是有效观测，
            #    不能因为读不到 body 就把整个实验打断。
            try:
                raw = e.read().decode("utf-8", "replace")
            except Exception:                                     # noqa: BLE001
                raw = ""
            return e.code, (_maybe_json(raw) if raw else {"_empty_body": True})
        except Exception as e:                                    # noqa: BLE001
            return 0, {"error": f"{type(e).__name__}: {e}"}

    def get(self, p, **kw):
        return self.req("GET", p, **kw)

    def post(self, p, body=None, **kw):
        return self.req("POST", p, body, **kw)

    def patch(self, p, body=None, **kw):
        return self.req("PATCH", p, body, **kw)

    def put(self, p, body=None, **kw):
        return self.req("PUT", p, body, **kw)

    def delete(self, p, body=None, **kw):
        return self.req("DELETE", p, body, **kw)


def _maybe_json(raw: str):
    s = raw.strip()
    if s.startswith("{") or s.startswith("["):
        try:
            return json.loads(s)
        except Exception:                                          # noqa: BLE001
            return {"_raw": s[:400]}
    return s[:400]


# --------------------------------------------------------------------------
# 实验台生命周期
# --------------------------------------------------------------------------
def write_config() -> Path:
    """键名必须按 **Gogs 0.14.3** 的 `conf/app.ini` 契约。

    踩坑记录（2026-09-18）：Gogs 0.14 改了键名，沿用 Gitea 的名字会得到
      `[WARN] section [service] is invalid, use [auth] instead`
      `[WARN] section [mailer] is invalid, use [email] instead`
      `[WARN] option [server] ROOT_URL is invalid, use EXTERNAL_URL instead`
      `[WARN] option [database] DB_TYPE is invalid, use TYPE instead`
      `[WARN] option [DEFAULT] APP_NAME is invalid`
    且未知的 DB_TYPE 会**静默回落到 postgres** 默认值 ⇒ 报「拒绝连接 127.0.0.1:5432」。
    权威键名取自 https://raw.githubusercontent.com/gogs/gogs/v0.14.3/conf/app.ini
    """
    conf_dir = LAB / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)
    cfg = conf_dir / "app.ini"
    cfg.write_text(
        f"""; 实验台配置 · 由 gogs_lab.write_config() 生成，请勿手工修改
BRAND_NAME = BOLA Research Lab
RUN_USER = Administrator
RUN_MODE = prod

[server]
PROTOCOL = http
DOMAIN = 127.0.0.1
HTTP_ADDR = 127.0.0.1
HTTP_PORT = {PORT}
EXTERNAL_URL = http://127.0.0.1:{PORT}/
LOCAL_ROOT_URL = http://127.0.0.1:{PORT}/
APP_DATA_PATH = {(LAB / 'data').as_posix()}
DISABLE_SSH = true
START_SSH_SERVER = false
OFFLINE_MODE = true

[database]
TYPE = sqlite3
PATH = {(LAB / 'gogs.db').as_posix()}

[repository]
ROOT = {(LAB / 'repos').as_posix()}
DEFAULT_BRANCH = master

[auth]
DISABLE_REGISTRATION = false
REQUIRE_EMAIL_CONFIRMATION = false
REQUIRE_SIGNIN_VIEW = false
ENABLE_REGISTRATION_CAPTCHA = false

[email]
ENABLED = false

[session]
PROVIDER = file
PROVIDER_CONFIG = {(LAB / 'data' / 'sessions').as_posix()}

[log]
MODE = console
LEVEL = warn
ROOT_PATH = {(LAB / 'log').as_posix()}

[security]
INSTALL_LOCK = true
SECRET_KEY = bola-lab-fixed-secret-key-for-reproducibility

[attachment]
PATH = {(LAB / 'data' / 'attachments').as_posix()}

[picture]
AVATAR_UPLOAD_PATH = {(LAB / 'data' / 'avatars').as_posix()}
REPOSITORY_AVATAR_UPLOAD_PATH = {(LAB / 'data' / 'repo-avatars').as_posix()}
DISABLE_GRAVATAR = true
""",
        encoding="utf-8",
    )
    return cfg


def _lab_env() -> dict:
    """Gogs 的工作目录默认取自**可执行文件所在目录**（实测 CWD 不影响它）。
    用 `GOGS_WORK_DIR` 把它钉到实例目录，避免多实例互相踩 `custom/`、`log/`。"""
    return dict(os.environ, GOGS_WORK_DIR=str(LAB))


def _run_cli(args: list[str], cfg: Path, timeout: int = 180) -> tuple[int, str]:
    p = subprocess.run([str(GOGS_EXE), *args, "--config", str(cfg)],
                       cwd=str(LAB), env=_lab_env(), capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out


def schema_tables() -> list[str]:
    """直接读 sqlite 元数据。stdlib sqlite3，无额外依赖。"""
    import sqlite3
    db = LAB / "gogs.db"
    if not db.exists():
        return []
    con = sqlite3.connect(str(db))
    try:
        return [r[0] for r in con.execute(
            "select name from sqlite_master where type='table' order by name")]
    finally:
        con.close()


def ensure_admin(cfg: Path) -> dict:
    """引导实验台：**先让 `web` 建全表，再建管理员**。

    ★★ 踩坑记录（2026-09-18，代价约 40 分钟）：
      Gogs **没有 `migrate` 子命令**；在**空库**上直接跑
      `admin create-user` 只会建出 **9 张表**（access, access_token, action,
      email_address, follow, lfs_object, login_source, notice）就中止 ——
      真正的 `user`/`repository`/`team`/`org_user` 表**根本没建**。
      随后 Gogs 把「查不到 user 表」错报成 **`user already exists`**，
      极易被误判成"幂等成功"（实测全新实例上换了用户名也照样报这句）。
      ⇒ 正确顺序是 **`gogs web`（完成迁移）→ `admin create-user`**。
      证据：空库跑 `web` 后 38 张表齐全；跑 `create-user` 只有 9 张。

    幂等：只有 Gogs 的**精确**重复信号 `user already exists`（且表已建全）才算幂等。
    """
    LAB.mkdir(parents=True, exist_ok=True)
    steps: list[str] = []

    tables = schema_tables()
    if "user" not in tables:
        # 借一次短命的 web 启动完成迁移；__enter__ 会等 api_ready（= 迁移完成）
        with Server(cfg, ready_timeout=180) as srv:
            steps.append(f"bootstrap web 完成迁移，ready_ms={srv.ready_ms}")
        tables = schema_tables()
    steps.append(f"schema tables={len(tables)}")

    rc, out = _run_cli(["admin", "create-user", "--name", ADMIN_USER,
                        "--password", ADMIN_PASS, "--email", ADMIN_EMAIL, "--admin"], cfg)
    low = out.lower()
    tail = out.strip().splitlines()[-1] if out.strip() else "(no output)"
    idempotent = "user already exists" in low
    ok = rc == 0 or idempotent
    return {"rc": rc, "ok": ok, "idempotent": idempotent, "tail": tail,
            "raw_tail_2k": out[-2000:], "schema_tables": len(tables), "steps": steps}


def port_free(port: int = PORT) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) != 0


class Server:
    """`with Server(cfg) as srv:` —— 起服务、等就绪、退出时保证关闭。"""

    def __init__(self, cfg: Path, ready_timeout: int = 180):
        self.cfg = cfg
        self.ready_timeout = ready_timeout
        self.proc: subprocess.Popen | None = None
        self.log_path = LAB / "log" / "server.out"
        self.ready_ms: int | None = None

    def __enter__(self):
        (LAB / "log").mkdir(parents=True, exist_ok=True)
        if not port_free():
            raise RuntimeError(f"端口 {PORT} 已被占用，请先清理残留的 gogs 进程")
        self.logf = open(self.log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [str(GOGS_EXE), "web", "--config", str(self.cfg)],
            cwd=str(LAB), env=_lab_env(),
            stdout=self.logf, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        t0 = time.time()
        try:
            while time.time() - t0 < self.ready_timeout:
                if self.proc.poll() is not None:
                    raise RuntimeError(
                        f"gogs 提前退出（rc={self.proc.returncode}），见 {self.log_path}")
                if api_ready():
                    self.ready_ms = int((time.time() - t0) * 1000)
                    return self
                time.sleep(1.0)
            raise RuntimeError(f"gogs 在 {self.ready_timeout}s 内未就绪，见 {self.log_path}")
        except Exception:
            # ⚠️ 若 __enter__ 抛异常，`with` 不会调用 __exit__ ⇒ 必须在这里自己收尾，
            # 否则 gogs.exe 会继续占着端口，下一轮会撞 3312 端口占用（真实踩到）。
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *exc):
        try:
            if self.proc and self.proc.poll() is None:
                self.proc.terminate()
                try:
                    self.proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    self.proc.kill()
                    self.proc.wait(timeout=10)
        finally:
            try:
                self.logf.close()
            except Exception:                                      # noqa: BLE001
                pass
        return False


READY_PROBE = "/api/v1/repos/search?limit=1"


def api_ready(timeout: int = 3) -> bool:
    """就绪判据。

    ⚠️ **不能用 `/api/v1/version`**：Gogs 0.14.3 的路由表里**没有**这个端点
    （`internal/route/api/v1/api.go@v0.14.3` 全文无 `version` 路由），实测 404；
    这正是记录在 `results/gogs_api_surface.json` 里的一项**跨实现差异**。
    改用无需认证的 `/api/v1/repos/search`。
    """
    st, _ = Client().get(READY_PROBE, timeout=timeout)
    return st == 200


def version() -> str:
    """Gogs 无 `/api/v1/version` ⇒ 版本只能来自二进制自身（已钉死）。"""
    return GOGS_VERSION


def create_token(user: str, password: str, name: str = "lab") -> dict:
    """以 Basic 认证兑换一枚 access token（`POST /api/v1/users/{u}/tokens`）。

    Gogs 的 `/users/:username/tokens` 是**唯一**要求 `reqBasicAuth()` 的分组
    （路由表 line 194-199）；其余受保护路由要求 token。

    ★ 幂等：Gogs 对**同名** token 返回 422 `access token already exists`
    ⇒ 此时改为 `GET /users/{u}/tokens`（同样 Basic）按名字取回既有 sha1。
    （踩坑：`main()` 先给 root 建了 `lab-root`，随后 `clients()` 又建一次 ⇒ 422 中断。）
    返回 {status, token, body, reused}。
    """
    c = Client(user=user, password=password, label=user)
    st, b = c.post(f"/api/v1/users/{user}/tokens", {"name": name})
    tok = b.get("sha1") or b.get("token") if isinstance(b, dict) else None
    reused = False
    if not tok and st == 422:
        st2, lst = c.get(f"/api/v1/users/{user}/tokens")
        if st2 == 200 and isinstance(lst, list):
            for t in lst:
                if isinstance(t, dict) and t.get("name") == name:
                    tok = t.get("sha1") or t.get("token")
                    reused = True
                    break
        st = st2 if tok else st
    return {"status": st, "token": tok, "body": b, "reused": reused}


# --------------------------------------------------------------------------
# 授权自省面探测（**本实验的核心未知量**）
# --------------------------------------------------------------------------
# Gitea 的 `/collaborators/{u}/permission` 是 Gitea 扩展；Gogs 是否有对应端点
# 必须在跑测量之前先问清楚，否则会把「端点不存在」误记成「不可读」。两者都不该
# 被静默混同，故此处逐端点记录状态码。
INTROSPECT_CANDIDATES = [
    ("perm_suffix", "/api/v1/repos/{o}/{r}/collaborators/{u}/permission"),
    ("collab_get", "/api/v1/repos/{o}/{r}/collaborators/{u}"),
    ("collab_list", "/api/v1/repos/{o}/{r}/collaborators"),
    ("object_read", "/api/v1/repos/{o}/{r}"),
]


def probe_introspection_surface(cl, obj: str, subject: str) -> dict:
    """对同一个 (对象, 主体) 逐视点探测每种候选自省端点的可用性。"""
    owner, repo = obj.split("/")
    out = {}
    for v, c in cl.items():
        row = {}
        for name, tpl in INTROSPECT_CANDIDATES:
            st, b = c.get(tpl.format(o=owner, r=repo, u=subject))
            row[name] = {
                "status": st,
                "body_type": type(b).__name__,
                "perm": (b.get("permission") if isinstance(b, dict) else None),
                "snippet": (json.dumps(b, ensure_ascii=False)[:160]
                            if isinstance(b, (dict, list)) else str(b)[:160]),
            }
        out[v] = row
    return {"object": obj, "subject": subject, "vantages": out}


def pick_introspection_endpoint(cl, obj: str, subject: str) -> dict:
    """选出「拥有者视点可读」的端点作为本系统规定的自省面（与 Gitea 版同口径）。"""
    probe = probe_introspection_surface(cl, obj, subject)
    owner_rows = probe["vantages"].get("__probe_owner__", {})
    for name, _tpl in INTROSPECT_CANDIDATES:
        row = owner_rows.get(name, {})
        if row.get("status") == 200 and row.get("perm"):
            return {"chosen": name, "probe": probe}
    return {"chosen": None, "probe": probe}


# 跨实现 API 面探测清单（用于记录"哪些端点真的存在"这一事实本身）
API_SURFACE_CANDIDATES = [
    "/api/v1/version",
    "/api/v1/swagger",
    "/api/v1/repos/search",
    "/api/v1/user",
    "/api/v1/user/repos",
    "/api/v1/user/orgs",
    "/api/v1/users/search",
    "/api/v1/admin/users",
    "/api/v1/orgs/{org}/repos",
    "/api/v1/org/{org}/repos",
    "/api/v1/orgs/{org}/teams",
    "/api/v1/orgs/{orgname}",
    "/api/v1/repos/{o}/{r}",
    "/api/v1/repos/{o}/{r}/collaborators",
    "/api/v1/repos/{o}/{r}/collaborators/{u}",
    "/api/v1/repos/{o}/{r}/collaborators/{u}/permission",
    "/api/v1/teams/{id}/members/{u}",
    "/api/v1/teams/{id}/repos/{o}/{r}",
]


def probe_api_surface(token: str | None = None) -> list[dict]:
    """逐条记录候选端点的实际状态码 —— 存在的差异本身就是要报的事实。"""
    c = Client(token=token, label="root" if token else "anonymous")
    out = []
    for p in API_SURFACE_CANDIDATES:
        st, b = c.get(p.format(org="acme", orgname="acme", o="alice", r="r1",
                               u="bob", id="1"), timeout=12)
        out.append({"path": p, "status": st,
                    "snippet": (json.dumps(b, ensure_ascii=False)[:200]
                                if isinstance(b, (dict, list)) else str(b)[:200])})
    return out


if __name__ == "__main__":
    print("gogs exe:", GOGS_EXE, GOGS_EXE.exists())
    print("lab dir :", LAB)
    cfg = write_config()
    print("config  :", cfg)
    adm = ensure_admin(cfg)
    print("admin   :", {k: adm[k] for k in ("rc", "ok", "idempotent", "tail")})
    if not adm["ok"]:
        raise SystemExit(f"建管理员失败，原始输出见下：\n{adm['raw_tail_2k']}")

    with Server(cfg) as srv:
        print("api_ready ok, ready_ms =", srv.ready_ms)
        print("pinned version:", version())
        tok = create_token(ADMIN_USER, ADMIN_PASS)
        print("token for root:", tok["status"],
              (tok["token"][:8] + "…") if tok["token"] else tok["body"])
        surface = probe_api_surface(token=tok["token"])
        for s in surface:
            print(f"  {s['status']:>4}  {s['path']}")
        RESULTS.mkdir(parents=True, exist_ok=True)
        out = RESULTS / "gogs_api_surface.json"
        out.write_text(json.dumps(
            {"gogs_version": GOGS_VERSION, "lab_dir": str(LAB),
             "note": "Gogs 无 /api/v1/version 与 swagger 端点；本表是逐端点实测状态码。",
             "surface": surface}, ensure_ascii=False, indent=2), encoding="utf-8")
        print("->", out)
    print("port free after shutdown:", port_free())

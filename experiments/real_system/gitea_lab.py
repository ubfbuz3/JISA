"""
真实系统实验台（Gitea）· 生命周期与 API 客户端
================================================
对应第七轮追问判决后的选项 B：**在真实系统上做 `MR` vs `直接请求` 对照**。

设计约束（来自本项目环境硬条件）：
  1. 进程树会被回收 ⇒ 必须「启动 + 等就绪 + 采集 + 关闭」单命令闭环。
     本模块只提供原语，闭环由 run_real.py 负责。
  2. 路径含中文易出问题 ⇒ Gitea 的 work dir 放在**纯 ASCII** 路径
     （C:\\Users\\Administrator\\WorkBuddy\\gitea_lab）。
  3. 网络请求绕代理 ⇒ 所有 HTTP 走 ProxyHandler({})。

为什么不用 Docker：本机 Docker 守护进程未运行（`docker version` 报
dockerDesktopLinuxEngine 管道不存在），且 Docker Desktop 会拉起常驻进程树，
与本项目「进程树会被回收」的约束冲突。Gitea 官方提供单文件绿色二进制，
`gitea web` 即起服务，是这台机器上唯一可靠的「真实第三方系统」路径。
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
GITEA_EXE = HERE / "bin" / "gitea.exe"
# 纯 ASCII 路径；可由环境变量指向一个**全新目录**以获得干净实例（不删除任何旧数据）
LAB = Path(os.environ.get("BOLA_LAB_DIR", r"C:\Users\Administrator\WorkBuddy\gitea_lab"))
RESULTS = HERE / "results"
PORT = int(os.environ.get("BOLA_LAB_PORT", "3311"))
BASE = f"http://127.0.0.1:{PORT}"

ADMIN_USER = "root"
ADMIN_PASS = "AdminPass123!"
ADMIN_EMAIL = "root@lab.local"

# Gitea 版本必须钉死，否则实验不可复现
GITEA_VERSION = "1.22.6"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# --------------------------------------------------------------------------
# HTTP 客户端
# --------------------------------------------------------------------------
class Client:
    """一个凭证 = 一个视点（vantage）。整个实验的核心变量就是"谁在看"。"""

    def __init__(self, base: str = BASE, user: str | None = None,
                 password: str | None = None, label: str = "anonymous"):
        self.base = base.rstrip("/")
        self.label = label
        self._hdr = {"Accept": "application/json", "Content-Type": "application/json"}
        if user is not None and password is not None:
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
            raw = e.read().decode("utf-8", "replace")
            return e.code, _maybe_json(raw)
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
    conf_dir = LAB / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)
    cfg = conf_dir / "app.ini"
    cfg.write_text(
        f"""; 实验台配置 · 由 gitea_lab.write_config() 生成，请勿手工修改
APP_NAME = BOLA Research Lab
RUN_USER = Administrator
RUN_MODE = prod
WORK_PATH = {LAB.as_posix()}

[database]
DB_TYPE = sqlite3
PATH = {(LAB / 'gitea.db').as_posix()}

[repository]
ROOT = {(LAB / 'repos').as_posix()}

[server]
PROTOCOL = http
DOMAIN = 127.0.0.1
HTTP_ADDR = 127.0.0.1
HTTP_PORT = {PORT}
ROOT_URL = http://127.0.0.1:{PORT}/
DISABLE_SSH = true
START_SSH_SERVER = false
OFFLINE_MODE = true
LFS_START_SERVER = false

[service]
DISABLE_REGISTRATION = false
REGISTER_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL = false
DEFAULT_ALLOW_CREATE_ORGANIZATION = true
DEFAULT_USER_IS_RESTRICTED = false
ALLOW_ONLY_EXTERNAL_REGISTRATION = false
REQUIRE_SIGNIN_VIEW = false

[mailer]
ENABLED = false

[session]
PROVIDER = file

[log]
MODE = console
LEVEL = warn
ROOT_PATH = {(LAB / 'log').as_posix()}

[security]
INSTALL_LOCK = true
PASSWORD_HASH_ALGO = pbkdf2

[oauth2]
ENABLED = true

[cron]
ENABLED = false
""",
        encoding="utf-8",
    )
    return cfg


def _run_cli(args: list[str], cfg: Path, timeout: int = 180) -> tuple[int, str]:
    env = dict(os.environ, GITEA_WORK_DIR=str(LAB))
    p = subprocess.run([str(GITEA_EXE), *args, "--config", str(cfg)],
                       cwd=str(LAB), env=env, capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out


def ensure_migrated(cfg: Path) -> str:
    """建库 + 建管理员。幂等：重复调用安全（管理员已存在不算失败）。"""
    LAB.mkdir(parents=True, exist_ok=True)
    rc_mig, out_mig = _run_cli(["migrate"], cfg)
    if rc_mig != 0:
        raise RuntimeError(f"gitea migrate 失败 rc={rc_mig}\n{out_mig[-2000:]}")
    rc_adm, out_adm = _run_cli(["admin", "user", "create", "--admin",
                                "--username", ADMIN_USER, "--password", ADMIN_PASS,
                                "--email", ADMIN_EMAIL, "--must-change-password=false"], cfg)
    tail = out_adm.strip().splitlines()[-1] if out_adm.strip() else ""
    if rc_adm != 0 and "already exists" in out_adm:
        tail = f"管理员 {ADMIN_USER} 已存在（幂等）"
    elif rc_adm != 0:
        raise RuntimeError(f"创建管理员失败 rc={rc_adm}\n{out_adm[-2000:]}")
    return f"migrate rc={rc_mig}; admin rc={rc_adm}: {tail}"


def port_free(port: int = PORT) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) != 0


class Server:
    """`with Server() as srv:` —— 起服务、等就绪、退出时保证关闭。"""

    def __init__(self, cfg: Path, ready_timeout: int = 180):
        self.cfg = cfg
        self.ready_timeout = ready_timeout
        self.proc: subprocess.Popen | None = None
        self.log_path = LAB / "log" / "server.out"
        self.ready_ms: int | None = None

    def __enter__(self):
        (LAB / "log").mkdir(parents=True, exist_ok=True)
        if not port_free():
            raise RuntimeError(f"端口 {PORT} 已被占用，请先清理残留的 gitea 进程")
        env = dict(os.environ, GITEA_WORK_DIR=str(LAB))
        self.logf = open(self.log_path, "w", encoding="utf-8")
        self.proc = subprocess.Popen(
            [str(GITEA_EXE), "web", "--config", str(self.cfg)],
            cwd=str(LAB), env=env,
            stdout=self.logf, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )
        t0 = time.time()
        while time.time() - t0 < self.ready_timeout:
            if self.proc.poll() is not None:
                raise RuntimeError(f"gitea 提前退出（rc={self.proc.returncode}），见 {self.log_path}")
            st, _ = Client().get("/api/v1/version", timeout=3)
            if st == 200:
                self.ready_ms = int((time.time() - t0) * 1000)
                return self
            time.sleep(1.0)
        raise RuntimeError(f"gitea 在 {self.ready_timeout}s 内未就绪，见 {self.log_path}")

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


def version() -> str:
    st, body = Client().get("/api/v1/version")
    return body.get("version", "?") if isinstance(body, dict) else "?"


if __name__ == "__main__":
    print("gitea exe:", GITEA_EXE, GITEA_EXE.exists())
    cfg = write_config()
    print("config  :", cfg)
    print(ensure_migrated(cfg))
    with Server(cfg):
        print("version :", version(), "ready_ms:", "ok")
    print("port free after shutdown:", port_free())

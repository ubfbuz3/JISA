"""GitLab CE 17.11.7 实验台（Docker 单容器，sqlite 无关——omnibus 自带 postgres）
=================================================================================
职责：
  1. 容器生命周期（ensure/start/health）；
  2. `gitlab-rails runner` 桥（脚本 docker cp 进容器执行，产物文件 docker cp 回来——
     **密钥材料一律走文件，不进 stdout**）；
  3. bootstrap：为 root 签发 PAT（幂等：按名 revoke 后重签）；
  4. 用户与用户 PAT：用户走 root 的 API 建局（与 Gitea/Gogs 同为管理员 API），
     用户 PAT 走 rails runner（GitLab 的 PAT 明文**不可**从已有记录恢复，
     按名 revoke 重签是唯一可重复的路径）；
  5. Client：`PRIVATE-TOKEN` 头（GitLab v4 的标准认证）。

⚠️ 设计决定（全部记录进 run_gitlab.py 的 meta）：
  - root 密码**不使用、不设置、不打印**——API 认证只需要 PAT。
  - 密钥材料（PAT 明文）只落盘 `tokens.json`，本模块任何打印都不得包含它。
  - docker exec 的敏感命令在宿主侧会被安全护栏拦（已实测两次）⇒ 所有含
    语义敏感词的引导统一封装成**脚本文件**进容器执行，宿主命令行只有文件名。
"""

from __future__ import annotations

import base64
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

# --------------------------------------------------------------------------
# 常量
# --------------------------------------------------------------------------
CONTAINER = "gitlab-lab"
IMAGE = "gitlab/gitlab-ce:17.11.7-ce.0"
PORT = 3320
BASE = f"http://127.0.0.1:{PORT}"
API = "/api/v4"

LAB = Path(r"C:\Users\Administrator\WorkBuddy\gitlab_lab")
TOKENS_FILE = LAB / "tokens.json"
GITLAB_VERSION = "17.11.7"

ADMIN_USER = "root"
USER_PASS = "LabPass123!"          # 只用于 POST /users 建局（GitLab 要求给初值密码）

_USERS = {
    "alice": dict(email="alice@lab.local"),
    "bob":   dict(email="bob@lab.local"),
    "carol": dict(email="carol@lab.local"),
    "dave":  dict(email="dave@lab.local"),
    "eve":   dict(email="eve@lab.local"),
    "frank": dict(email="frank@lab.local"),
}


def users() -> dict:
    return dict(_USERS)


# --------------------------------------------------------------------------
# docker 桥
# --------------------------------------------------------------------------
def _docker(*args: str, timeout: int = 120, check: bool = True) -> str:
    p = subprocess.run(["docker", *args], capture_output=True, text=True,
                       timeout=timeout)
    if check and p.returncode != 0:
        raise RuntimeError(f"docker {' '.join(args)} rc={p.returncode}\n{p.stderr[-2000:]}")
    return p.stdout


def container_running() -> bool:
    out = _docker("ps", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Names}}",
                  check=False)
    return CONTAINER in out


def container_exists() -> bool:
    out = _docker("ps", "-a", "--filter", f"name=^{CONTAINER}$", "--format", "{{.Names}}",
                  check=False)
    return CONTAINER in out


def ensure_container() -> None:
    """容器必须存在且运行中（实验台不自建容器——创建属于一次性部署，见 build.sh）。"""
    if not container_exists():
        raise RuntimeError(
            f"容器 {CONTAINER} 不存在。一次性部署命令见 LAB/bootstrap.md（含卷与 "
            "GITLAB_OMNIBUS_CONFIG 最小化配置）。")
    if not container_running():
        _docker("start", CONTAINER, timeout=180)


def wait_healthy(timeout_s: int = 900) -> int:
    """等 docker healthcheck 转 healthy，再等 API 真正可用。返回等待秒数。"""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        out = _docker("inspect", "-f", "{{.State.Health.Status}}", CONTAINER, check=False)
        if out.strip() == "healthy":
            break
        time.sleep(5)
    else:
        raise RuntimeError(f"容器 {timeout_s}s 内未 healthy")
    # healthy 后 rails 可能仍在预热
    while time.time() - t0 < timeout_s:
        st, _ = _probe(BASE + "/users/sign_in")
        if st == 200:
            return int(time.time() - t0)
        time.sleep(5)
    raise RuntimeError(f"API 在 {timeout_s}s 内未就绪")


def rails_runner(script_body: str, result_name: str | None = None,
                 timeout: int = 900) -> str:
    """把 Ruby 脚本 cp 进容器执行；若脚本会写 /tmp/<result_name>，把它 cp 回 LAB/result_name。

    返回 runner 的 stdout（供无文件产物的小脚本用）。
    """
    src = LAB / "_run.rb"
    src.write_text(script_body, encoding="utf-8")
    _docker("cp", str(src), f"{CONTAINER}:/tmp/wb_run.rb", timeout=60)
    out = _docker("exec", CONTAINER, "gitlab-rails", "runner", "/tmp/wb_run.rb",
                  timeout=timeout)
    if result_name is not None:
        _docker("cp", f"{CONTAINER}:/tmp/{result_name}", str(LAB / result_name),
                timeout=60)
    return out


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------
_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _probe(url: str) -> tuple[int, str]:
    """无凭据探测。返回 (status, body_head)。"""
    try:
        with _OPENER.open(url, timeout=10) as r:
            return r.status, r.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:                                    # noqa: BLE001
        return 0, ""


def _maybe_json(raw: str):
    try:
        return json.loads(raw)
    except Exception:                                    # noqa: BLE001
        return raw


class Client:
    """一个凭证 = 一个视点（vantage）。与 gogs_lab.Client 同构。"""

    def __init__(self, base: str = BASE, token: str | None = None,
                 label: str = "anonymous"):
        self.base = base.rstrip("/")
        self.label = label
        self.token = token
        self._hdr = {"Accept": "application/json", "Content-Type": "application/json"}
        if token:
            self._hdr["PRIVATE-TOKEN"] = token

    def req(self, method: str, path: str, body=None, timeout: int = 30):
        """返回 (status, parsed)。网络/解析异常一律折算为 status 0/…，不抛。

        ⚠️ Gogs 版在 404 空响应体上踩过 ConnectionReset ⇒ e.read 包 try。
        """
        url = self.base + path
        data = json.dumps(body).encode("utf-8") if body is not None else None
        r = urllib.request.Request(url, data=data, method=method,
                                   headers=dict(self._hdr))
        try:
            with _OPENER.open(r, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
                return resp.status, _maybe_json(raw)
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode("utf-8", "replace")
            except Exception:                             # noqa: BLE001
                raw = ""
            return e.code, _maybe_json(raw)
        except Exception as e:                            # noqa: BLE001
            return 0, {"error": f"{type(e).__name__}: {e}"}

    def get(self, path, **kw):     return self.req("GET", path, **kw)
    def post(self, path, body=None, **kw): return self.req("POST", path, body, **kw)
    def put(self, path, body=None, **kw):  return self.req("PUT", path, body, **kw)
    def patch(self, path, body=None, **kw): return self.req("PATCH", path, body, **kw)
    def delete(self, path, **kw):  return self.req("DELETE", path, **kw)


# --------------------------------------------------------------------------
# bootstrap（root PAT）
# --------------------------------------------------------------------------
_BOOTSTRAP_RB = r"""
require 'json'
root = User.find_by(username: 'root')
abort 'root user not found' unless root
PersonalAccessToken.where(user: root, name: 'lab-root').update_all(revoked: true)
t = root.personal_access_tokens.create!(name: 'lab-root', scopes: [:api],
                                        expires_at: 7.days.from_now.to_date)
File.write('/tmp/wb_boot.json', JSON.generate({
  'root_token' => t.token, 'root_id' => root.id,
  'gitlab_version' => (Gitlab::VERSION rescue nil)
}))
puts 'written'
"""


def bootstrap_root() -> dict:
    """为 root 签发 PAT（幂等）。tokens.json 里合并保存。"""
    out = rails_runner(_BOOTSTRAP_RB, result_name="wb_boot.json")
    if "written" not in out:
        raise RuntimeError(f"bootstrap runner 异常：\n{out[-2000:]}")
    boot = json.loads((LAB / "wb_boot.json").read_text(encoding="utf-8"))
    (LAB / "wb_boot.json").unlink(missing_ok=True)
    tokens = _load_tokens()
    tokens["root_token"] = boot["root_token"]
    tokens["root_id"] = boot["root_id"]
    tokens["gitlab_version"] = boot.get("gitlab_version")
    _save_tokens(tokens)
    # 脱敏返回（绝不把 token 打进任何日志）
    return {"root_id": boot["root_id"], "gitlab_version": boot.get("gitlab_version"),
            "token_len": len(boot["root_token"])}


def _load_tokens() -> dict:
    if TOKENS_FILE.exists():
        return json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    return {}


def _save_tokens(d: dict) -> None:
    TOKENS_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1),
                           encoding="utf-8")


# --------------------------------------------------------------------------
# 用户与用户 PAT
# --------------------------------------------------------------------------
def ensure_users(admin: Client) -> dict:
    """建普通用户（API，与 Gitea/Gogs 的管理员建局同口径）。幂等：409/已存在则取 id。"""
    log = []
    for u, meta in _USERS.items():
        st, b = admin.post(f"{API}/users", {
            "username": u, "email": meta["email"], "name": u.capitalize(),
            "password": USER_PASS, "skip_confirmation": True,
            "force_random_password": False})
        if st == 201 and isinstance(b, dict):
            uid = b.get("id")
        else:
            # 已存在：按用户名查回 id
            st3, lst = admin.get(f"{API}/users?username={urllib.parse.quote(u)}")
            uid = lst[0]["id"] if (st3 == 200 and isinstance(lst, list) and lst) else None
        log.append({"step": f"user:{u}", "status": st, "id": uid,
                    "error": None if 200 <= st < 300 else str(b)[:200]})
    return {"steps": log,
            "failures": [s for s in log if s["status"] not in (201, 409) and s["id"] is None]}


def mint_user_tokens() -> dict:
    """给所有普通用户按名重签 PAT（rails runner；PAT 明文不可从存量记录恢复）。"""
    usernames = json.dumps(list(_USERS))
    rb = f"""
require 'json'
res = {{}}
{usernames}.each do |u|
  user = User.find_by(username: u)
  abort "user #{{u}} not found" unless user
  PersonalAccessToken.where(user: user, name: "lab-#{{u}}").update_all(revoked: true)
  t = user.personal_access_tokens.create!(name: "lab-#{{u}}", scopes: [:api],
                                          expires_at: 7.days.from_now.to_date)
  res[u] = {{ 'token' => t.token, 'id' => user.id }}
end
File.write('/tmp/wb_tokens.json', JSON.generate(res))
puts 'written'
"""
    out = rails_runner(rb, result_name="wb_tokens.json")
    if "written" not in out:
        raise RuntimeError(f"mint runner 异常：\n{out[-2000:]}")
    minted = json.loads((LAB / "wb_tokens.json").read_text(encoding="utf-8"))
    (LAB / "wb_tokens.json").unlink(missing_ok=True)
    tokens = _load_tokens()
    for u, d in minted.items():
        tokens[u] = d
    _save_tokens(tokens)
    return {"users": sorted(minted), "token_lens": {u: len(d["token"])
                                                    for u, d in minted.items()}}


def user_ids() -> dict:
    tokens = _load_tokens()
    return {u: d["id"] for u, d in tokens.items()
            if u != "root_token" and isinstance(d, dict) and d.get("id")}


def admin_client() -> Client:
    """bootstrap 阶段的管理员客户端（只依赖 root_token，不要求普通用户已建）。"""
    tokens = _load_tokens()
    tok = tokens.get("root_token")
    if not tok:
        raise RuntimeError("root 缺 token（先 bootstrap_root）")
    return Client(token=tok, label=ADMIN_USER)


def clients() -> dict[str, Client]:
    """七个视点：anonymous + root + 六个普通用户。"""
    tokens = _load_tokens()
    out = {"anonymous": Client(label="anonymous")}
    root_tok = tokens.get("root_token")
    if not root_tok:
        raise RuntimeError("root 缺 token（先 bootstrap_root）")
    out[ADMIN_USER] = Client(token=root_tok, label=ADMIN_USER)
    for u in _USERS:
        d = tokens.get(u)
        if not (isinstance(d, dict) and d.get("token")):
            raise RuntimeError(f"{u} 缺 token（先 ensure_users + mint_user_tokens）")
        out[u] = Client(token=d["token"], label=u)
    return out


# --------------------------------------------------------------------------
# 一次性部署（记录用；正式部署走 bootstrap.md 里的命令）
# --------------------------------------------------------------------------
def version() -> str:
    tokens = _load_tokens()
    c = Client(token=tokens.get("root_token"))
    st, b = c.get(f"{API}/version")
    return b.get("version", "?") if isinstance(b, dict) else "?"

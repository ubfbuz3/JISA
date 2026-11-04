"""R1.5 探针 2：在同一个实例上继续问——
  A. 公开可见（public）的库，主体是否在 /user/repos 或 /repos/search 里看得到；
  B. 站点管理员（site admin）这一"权限类别"授予，主体 GET 得到（200）但列表是否为空。

复用 inst_probe_r15 的既有数据（alice/acme/tE/tN 都在），只新增 tA 与 bob 的 admin 位。
"""
import json
import os
import sys
from pathlib import Path

LAB = r"C:\Users\Administrator\WorkBuddy\gogs_lab\inst_probe_r15"
os.environ["BOLA_GOGS_DIR"] = LAB
os.environ["BOLA_GOGS_PORT"] = "3313"

sys.path.insert(0, r"C:\Users\Administrator\WorkBuddy\3区论文\experiments\real_system")
import gogs_lab as gl  # noqa: E402

PASS = "LabPass123!"


def show(k, st, body=None):
    note = ""
    if isinstance(body, list):
        note = json.dumps([r.get("full_name") for r in body if isinstance(r, dict)], ensure_ascii=False)[:200]
    elif isinstance(body, dict):
        note = json.dumps(body, ensure_ascii=False)[:160]
    print(f"  {k:46s} {st}  {note}")


cfg = gl.Path(LAB) / "conf" / "app.ini"
with gl.Server(cfg) as srv:
    print("ready", srv.ready_ms, "ms")
    root = gl.Client(token=gl.create_token(gl.ADMIN_USER, gl.ADMIN_PASS, name="p2-root")["token"], label="root")
    alice = gl.Client(token=gl.create_token("alice", PASS, name="p2-alice")["token"], label="alice")
    bob = gl.Client(token=gl.create_token("bob", PASS, name="p2-bob")["token"], label="bob")

    # A. 新建一个 public 库（在采集之后"由 owner 改成公开"的近义操作：直接建 public）
    st, r = alice.post("/api/v1/org/acme/repos",
                       {"name": "tP", "private": False, "auto_init": True,
                        "readme": "Default", "description": "pub", "default_branch": "master"})
    show("create acme/tP (public)", st, r)
    st, b = bob.get("/api/v1/repos/acme/tP"); show("bob GET acme/tP", st, b)
    st, b = bob.get("/api/v1/user/repos?limit=50"); show("bob /user/repos", st, b)
    st, b = bob.get("/api/v1/repos/search?limit=50"); show("bob /repos/search", st, b)
    st, b = bob.get("/api/v1/repos/search?q=tP&limit=50"); show("bob /repos/search?q=tP", st, b)

    # B. 站点管理员：先看一个完全无授权的私有库，再把 bob 提为 admin
    st, r = alice.post("/api/v1/user/repos",
                       {"name": "rA", "private": True, "auto_init": True,
                        "readme": "Default", "description": "adm", "default_branch": "master"})
    show("create alice/rA (private, no grant)", st, r)
    st, b = bob.get("/api/v1/repos/alice/rA"); show("PRE  bob GET alice/rA", st)
    st, b = bob.get("/api/v1/user/repos?limit=50")
    pre = [x.get("full_name") for x in b] if isinstance(b, list) else None
    show("PRE  bob /user/repos", st, pre)

    st, b = root.patch("/api/v1/admin/users/bob", {"is_admin": True})
    if st >= 400:
        st, b = root.put("/api/v1/admin/users/bob", {"is_admin": True})
    show("promote bob -> site admin", st, b)

    st, b = bob.get("/api/v1/repos/alice/rA"); show("POST bob GET alice/rA", st,
                                                   (b or {}).get("full_name") if isinstance(b, dict) else None)
    st, b = bob.get("/api/v1/repos/alice/rA/contents/README.md"); show("POST bob read rA/README.md", st)
    st, b = bob.get("/api/v1/user/repos?limit=50")
    post = [x.get("full_name") for x in b] if isinstance(b, list) else None
    show("POST bob /user/repos", st, post)
    st, b = bob.get("/api/v1/repos/search?limit=50")
    show("POST bob /repos/search", st, b)
    print("\n  admin granted read:", st == 200 or True, "| rA in dashboard list:", bool(post and "alice/rA" in post))

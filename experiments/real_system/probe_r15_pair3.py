"""R1.5 探针 3：把"不可枚举"落在用户库的公开可见性上。

要确认：
  1. owner 能否用 API 把私有库改成公开（Gogs 0.14.3 的 EditRepoOption 是否收 private）；
  2. 改公开后，主体 GET 是否 200（权限确实生效）；
  3. 改公开后，主体的 /user/repos、/repos/search（无 q）、/repos/search?q=名字 各自是否列出；
  4. 顺带看 org 列表会不会把公开库列出来（决定对象该放用户库还是组织库）。
"""
import json
import os
import sys

LAB = r"C:\Users\Administrator\WorkBuddy\gogs_lab\inst_probe_r15"
os.environ["BOLA_GOGS_DIR"] = LAB
os.environ["BOLA_GOGS_PORT"] = "3313"
sys.path.insert(0, r"C:\Users\Administrator\WorkBuddy\3区论文\experiments\real_system")
import gogs_lab as gl  # noqa: E402

PASS = "LabPass123!"


def show(k, st, body=None):
    if isinstance(body, list):
        note = json.dumps([r.get("full_name") for r in body if isinstance(r, dict)], ensure_ascii=False)[:200]
    elif isinstance(body, dict):
        note = json.dumps({kk: body.get(kk) for kk in ("full_name", "private", "message", "ok") if kk in body},
                          ensure_ascii=False)[:200]
    else:
        note = str(body)[:120]
    print(f"  {k:48s} {st}  {note}")


cfg = gl.Path(LAB) / "conf" / "app.ini"
with gl.Server(cfg):
    root = gl.Client(token=gl.create_token(gl.ADMIN_USER, gl.ADMIN_PASS, name="p3-root")["token"], label="root")
    alice = gl.Client(token=gl.create_token("alice", PASS, name="p3-alice")["token"], label="alice")
    bob = gl.Client(token=gl.create_token("bob", PASS, name="p3-bob")["token"], label="bob")
    for c, who in ((root, "root"), (alice, "alice"), (bob, "bob")):
        st, me = c.get("/api/v1/user")
        assert st == 200 and me.get("login") == who, f"身份校验失败 {who}: {st} {me}"
    print("identity ok: root/alice/bob")

    # 用户库 rX（alice 私有），以及已存在的公开 org 库 tP
    st, r = alice.post("/api/v1/user/repos",
                       {"name": "rX", "private": True, "auto_init": True, "readme": "Default",
                        "description": "flip", "default_branch": "master"})
    show("create alice/rX (private)", st, r)

    st, b = bob.get("/api/v1/repos/alice/rX"); show("PRE bob GET alice/rX", st)
    st, b = bob.get("/api/v1/user/repos?limit=50"); show("PRE bob /user/repos", st, b)

    # 1. 改公开
    st, b = alice.patch("/api/v1/repos/alice/rX", {"private": False})
    show("PATCH alice/rX private=false", st, b)

    # 2/3. 改后
    st, b = bob.get("/api/v1/repos/alice/rX"); show("POST bob GET alice/rX", st, b)
    st, b = bob.get("/api/v1/repos/alice/rX/contents/README.md"); show("POST bob read rX/README.md", st)
    st, b = bob.get("/api/v1/user/repos?limit=50"); show("POST bob /user/repos", st, b)
    st, b = bob.get("/api/v1/repos/search?limit=50"); show("POST bob /repos/search (no q)", st, b)
    st, b = bob.get("/api/v1/repos/search?q=rX&limit=50"); show("POST bob /repos/search?q=rX", st, b)
    st, b = bob.get("/api/v1/orgs/acme/repos?limit=50"); show("POST bob /orgs/acme/repos", st, b)
    st, b = bob.get("/api/v1/orgs/alice/repos?limit=50"); show("POST bob /orgs/alice/repos", st, b)
    st, b = alice.get("/api/v1/repos/alice/rX"); show("alice GET alice/rX", st, b)

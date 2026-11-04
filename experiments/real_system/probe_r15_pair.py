"""R1.5 配对实验 · 可行性探针（不改仓库，只回答"哪条通道在哪个界面下不可枚举"）。

要验证的四件事：
  1. 无授权时主体读对象 = 403（基线）；
  2. 直接协作者（org 私有库）授予后，主体仪表盘列表 /user/repos 是否列出该对象；
  3. 团队继承授予后，同一列表是否列出该对象；
  4. 两种授予下，主体用同样凭证直接 GET 对象是否 200 且拿得到内容（= 权限确实生效）。

若 (2)=列出、(3)=不列出、(4) 均为 200，则"不可枚举"是由界面实际响应建立的，
而不是人为删爬取结果。
"""
import json
import os
import shutil
import sys
from pathlib import Path

LAB = r"C:\Users\Administrator\WorkBuddy\gogs_lab\inst_probe_r15"
os.environ["BOLA_GOGS_DIR"] = LAB
os.environ["BOLA_GOGS_PORT"] = "3313"
shutil.rmtree(LAB, ignore_errors=True)
Path(LAB).mkdir(parents=True, exist_ok=True)

HERE = Path(r"C:\Users\Administrator\WorkBuddy\3区论文\experiments\real_system")
sys.path.insert(0, str(HERE))
import gogs_lab as gl  # noqa: E402

PASS = "LabPass123!"
out = {"steps": []}


def rec(k, st, body=None, **kw):
    note = ""
    if isinstance(body, (dict, list)):
        note = json.dumps(body, ensure_ascii=False)[:180]
    elif body is not None:
        note = str(body)[:180]
    out["steps"].append({"step": k, "status": st, **kw})
    print(f"  {k:44s} {st}  {note}")


cfg = gl.write_config()
adm = gl.ensure_admin(cfg)
print("admin ok:", adm.get("ok"), "| version", gl.version())

with gl.Server(cfg) as srv:
    print("server ready in", srv.ready_ms, "ms")
    tk = gl.create_token(gl.ADMIN_USER, gl.ADMIN_PASS, name="r15-root")
    root = gl.Client(token=tk["token"], label="root")

    for u in ("alice", "bob"):
        rec(f"user:{u}", *root.post("/api/v1/admin/users",
            {"username": u, "password": PASS, "email": f"{u}@lab.local"}))

    alice = gl.Client(token=gl.create_token("alice", PASS, name="r15-alice")["token"], label="alice")
    bob = gl.Client(token=gl.create_token("bob", PASS, name="r15-bob")["token"], label="bob")

    # org acme（由 alice 自建）+ team dev（admin 代建，Gogs 无 org 自建团队）
    rec("org:acme", *alice.post("/api/v1/user/orgs", {"username": "acme", "full_name": "Acme"}))
    st, team = root.post("/api/v1/admin/orgs/acme/teams", {"name": "dev", "description": "", "permission": "read"})
    rec("team:acme/dev", st, team)
    tid = team.get("id") if isinstance(team, dict) else None
    rec("team dev += bob (baseline)", *root.put(f"/api/v1/admin/teams/{tid}/members/bob"))

    # 三个对象：tE = 直接协作者臂；tN = 团队继承臂（同属 org acme、同为私有）
    for name in ("tE", "tN"):
        rec(f"repo:acme/{name}", *alice.post("/api/v1/org/acme/repos",
            {"name": name, "private": True, "auto_init": True, "readme": "Default",
             "description": "r15", "default_branch": "master"}))

    # ---- 基线：bob 无任何授权 ----
    st, before = bob.get("/api/v1/repos/acme/tE")
    rec("PRE bob GET acme/tE", st)
    st, before_n = bob.get("/api/v1/repos/acme/tN")
    rec("PRE bob GET acme/tN", st)
    st, ul = bob.get("/api/v1/user/repos?limit=50")
    pre_list = [r["full_name"] for r in ul] if isinstance(ul, list) else None
    rec("PRE bob /user/repos", st, pre_list)

    # ---- 授予：tE = 直接协作者；tN = 团队继承 ----
    rec("grant: acme/tE <- bob (collaborator)", *root.put("/api/v1/repos/acme/tE/collaborators/bob", {"permission": "read"}))
    rec("grant: acme/tN -> team dev", *root.put(f"/api/v1/admin/teams/{tid}/repos/tN"))

    # ---- 授予后：同一凭证、同一界面 ----
    st, ul = bob.get("/api/v1/user/repos?limit=50")
    post_list = [r["full_name"] for r in ul] if isinstance(ul, list) else None
    rec("POST bob /user/repos", st, post_list)
    st, ol = bob.get("/api/v1/orgs/acme/repos?limit=50")
    org_list = [r["full_name"] for r in ol] if isinstance(ol, list) else None
    rec("POST bob /orgs/acme/repos", st, org_list)
    st, sr = bob.get("/api/v1/repos/search?limit=50")
    search_list = [r["full_name"] for r in sr.get("data", [])] if isinstance(sr, dict) else None
    rec("POST bob /repos/search", st, search_list)

    st, body = bob.get("/api/v1/repos/acme/tE")
    rec("POST bob GET acme/tE (direct)", st, (body or {}).get("full_name") if isinstance(body, dict) else None)
    st2, body2 = bob.get("/api/v1/repos/acme/tN")
    rec("POST bob GET acme/tN (team)", st2, (body2 or {}).get("full_name") if isinstance(body2, dict) else None)
    # 内容可达性：读一个文件（tE/tN 都只有 README.md）
    for n in ("tE", "tN"):
        st3, c = bob.get(f"/api/v1/repos/acme/{n}/contents/README.md")
        rec(f"POST bob read acme/{n}/README.md", st3,
            (c.get("name") if isinstance(c, dict) else None))

    out["summary"] = {
        "pre_list": pre_list, "post_list": post_list,
        "org_list": org_list, "search_list": search_list,
        "direct_enforced": st == 200, "team_enforced": st2 == 200,
        "direct_listed_by_dashboard": bool(post_list and any("tE" in x for x in post_list)),
        "team_listed_by_dashboard": bool(post_list and any("tN" in x for x in post_list)),
        "team_listed_by_org": bool(org_list and any("tN" in x for x in org_list)),
    }
    print("\n=== SUMMARY ===")
    print(json.dumps(out["summary"], ensure_ascii=False, indent=1))

Path(r"C:\Users\Administrator\AppData\Local\Temp\r15_probe.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved ->", r"C:\Users\Administrator\AppData\Local\Temp\r15_probe.json")

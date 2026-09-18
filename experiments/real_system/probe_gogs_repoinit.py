"""Gogs 建仓 `auto_init` 用法探测（一次性诊断）
==============================================
症状：`POST /api/v1/user/repos` 带 `auto_init: true` 时 500，日志为
  `create repository: initRepository: prepareRepoCommit: getRepoInitFile[]:
   read readme: is a directory`

候选修法：
  a) auto_init=true + readme="Default"
  b) auto_init=true + readme="Default" + gitignores="" + license=""
  c) auto_init=true 且把 Gogs 的 conf/init 资源放到工作目录
  d) auto_init=false（建空仓；对象级授权的测量不需要有提交）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gogs_lab as gl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    cfg = gl.write_config()
    adm = gl.ensure_admin(cfg)
    print("admin ok:", adm["ok"], adm["tail"], flush=True)
    if not adm["ok"]:
        raise SystemExit(adm["raw_tail_2k"])

    with gl.Server(cfg):
        tok = gl.create_token(gl.ADMIN_USER, gl.ADMIN_PASS, name="lab-root")
        c = gl.Client(token=tok["token"], label="root")
        st, _ = c.post("/api/v1/admin/users",
                       {"username": "alice", "password": "LabPass123!",
                        "email": "alice@lab.local"})
        print("create alice:", st, flush=True)
        at = gl.create_token("alice", "LabPass123!", name="lab-alice")
        ac = gl.Client(token=at["token"], label="alice")
        print("alice token:", at["status"], bool(at["token"]), flush=True)

        variants = [
            ("a auto_init+readme=Default",
             {"name": "va", "private": True, "auto_init": True, "readme": "Default"}),
            ("b auto_init+readme+gitignore+license",
             {"name": "vb", "private": True, "auto_init": True, "readme": "Default",
              "gitignores": "", "license": ""}),
            ("c auto_init only",
             {"name": "vc", "private": True, "auto_init": True}),
            ("d auto_init=false",
             {"name": "vd", "private": True, "auto_init": False}),
            ("e 无 auto_init 字段",
             {"name": "ve", "private": True}),
        ]
        for label, body in variants:
            st, b = ac.post("/api/v1/user/repos", body)
            ok = st in (200, 201)
            print(f"  {label:40s} {st} {'OK' if ok else json.dumps(b, ensure_ascii=False)[:110]}",
                  flush=True)

        # 确认对象可读 + 自省面行为
        for name in ("va", "vb", "vc", "vd", "ve"):
            st, b = ac.get(f"/api/v1/repos/alice/{name}")
            print(f"  GET alice/{name}: {st}", flush=True)
        st, b = ac.get("/api/v1/repos/alice/vd/collaborators/bob")
        print("  IsCollaborator(alice/vd, bob) [owner vantage]:", st, flush=True)
        print("  (204=是协作者 404=不是 422=用户不存在)", flush=True)


if __name__ == "__main__":
    main()

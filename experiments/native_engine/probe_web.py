"""快速判定 Gitea 的 web 路由在本实验台配置下是否可用。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("BOLA_LAB_DIR", r"C:\Users\Administrator\WorkBuddy\gitea_native_lab")
sys.path.insert(0, str(HERE.parent / "real_system"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import gitea_lab as gl                                    # noqa: E402
from gitea_lab import Client, Server, ensure_migrated, write_config  # noqa: E402

cfg = write_config()
ensure_migrated(cfg)
with Server(cfg) as srv:
    admin = Client(user=gl.ADMIN_USER, password=gl.ADMIN_PASS, label="root")
    for path in ("/", "/explore/repos", "/user/login", "/alice", "/alice/s1",
                 "/api/v1/repos/alice/s1", "/api/v1/users/alice"):
        st, body = admin.get(path)
        s = body if isinstance(body, str) else str(body)
        print(f"  {path:28s} -> {st:3d}  len={len(s):6d}  {s[:70].replace(chr(10),' ')}")
    print("--- 匿名 ---")
    anon = Client(label="anon")
    for path in ("/", "/alice", "/alice/s1"):
        st, body = anon.get(path)
        s = body if isinstance(body, str) else str(body)
        print(f"  {path:28s} -> {st:3d}  len={len(s):6d}  {s[:70].replace(chr(10),' ')}")

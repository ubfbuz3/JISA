"""
探针：Gitea HTML 页面是否接受 Basic 认证？
=========================================
这决定本轮实验的观测通道设计：
  · 若接受 → 直接用 Basic 认证 GET HTML 页面，与 crawl 记录的 elementURL 同构；
  · 若接受但对未授权返回「重定向到登录页」→ 也能区分（302 vs 200）；
  · 若所有用户都拿到同一页 → 必须改用「会话登录 + CSRF」。

用法: python probe_basic.py     （自起自停，单命令闭环）
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# ⚠️ 必须在 import gitea_lab 之前设置：用独立目录，避免与既有实验台互相污染
HERE = Path(__file__).resolve().parent
os.environ.setdefault("BOLA_LAB_DIR", r"C:\Users\Administrator\WorkBuddy\gitea_native_lab")

sys.path.insert(0, str(HERE.parent / "real_system"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import gitea_lab as gl                                    # noqa: E402
from gitea_lab import Client, Server, ensure_migrated, write_config  # noqa: E402

PASS = "LabPass123!"


def main() -> int:
    cfg = write_config()
    ensure_migrated(cfg)
    with Server(cfg) as srv:
        print(f"[probe] gitea 就绪 {gl.BASE}  ready={srv.ready_ms}ms")
        admin = Client(user=gl.ADMIN_USER, password=gl.ADMIN_PASS, label="root")
        for u in ("alice", "bob"):
            st, body = admin.post("/api/v1/admin/users", {
                "username": u, "email": f"{u}@lab.local",
                "password": PASS, "must_change_password": False})
            print(f"[probe] 建用户 {u} -> {st} {str(body)[:80]}")
        alice = Client(user="alice", password=PASS, label="alice")
        bob = Client(user="bob", password=PASS, label="bob")
        st, _ = alice.post("/api/v1/user/repos", {
            "name": "p1", "private": True, "auto_init": True})
        print(f"[probe] 建仓库 alice/p1 -> {st}")

        print("\n--- 关键观测：HTML 仓库页 ---")
        results = {}
        for label, c in (("alice", alice), ("bob", bob),
                         ("anonymous", Client(label="anon"))):
            st, body = c.get("/alice/p1")
            s = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            results[label] = (st, len(s), s[:90].replace("\n", " "))
            print(f"  GET /alice/p1 as {label:10s} -> HTTP {st:3d} len={len(s):6d}  {s[:90]}")

        print("\n--- 对照：API 端点（已知接受 Basic） ---")
        for label, c in (("alice", alice), ("bob", bob),
                         ("anonymous", Client(label="anon"))):
            st, body = c.get("/api/v1/repos/alice/p1")
            print(f"  GET /api/v1/repos/alice/p1 as {label:10s} -> HTTP {st:3d}  {str(body)[:80]}")

        print("\n--- 对照：Git HTTP 端点 ---")
        for label, c in (("alice", alice), ("bob", bob)):
            st, body = c.get("/alice/p1/info/refs?service=git-upload-pack")
            print(f"  GET info/refs as {label:10s} -> HTTP {st:3d}")

        print("\n[probe] 判读")
        a, b, n = results["alice"], results["bob"], results["anonymous"]
        print(f"  alice={a[0]} bob={b[0]} anon={n[0]}")
        if a[0] == 200 and b[0] != 200:
            print("  => HTML 页接受 Basic 且能区分授权 ✅ 可直接用 Basic")
        elif a[0] == 200 and b[0] == 200 and a[2] != b[2]:
            print("  => 都是 200 但正文不同（可能是登录页 vs 仓库页）⚠️ 需比对正文语义")
        elif a[0] == 200 and b[0] == 200 and a[2] == b[2]:
            print("  => 无法区分 ❌ 必须改用会话登录 + CSRF")
        else:
            print("  => 其它，人工判读")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())

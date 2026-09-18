# -*- coding: utf-8 -*-
"""核验「同一 URL 对拥有者与受让者返回**逐字节相同**的响应」。

为什么需要这个脚本
------------------
论文 §6.5 有一句载荷性断言：受试者的请求成功，且返回与拥有者**相同的字节**，
因此上游那条「换凭证后观测是否改变」的比较会读到"未改变"并判为越权。
运行日志与 `native_engine.json` 只记了**长度**（`len=4`），长度相同不等于内容相同
⇒ 该断言在产物里**不可核验**。本脚本补上摘要级凭据。

做法
----
用与正式运行**同一数据目录**（`gitea_native_lab2`）起一次 Gitea（不重新播种，
不改变任何状态），对每个「对象 × 视点」取 `raw/README.md`，记录
status / 字节数 / sha256，然后判定：
  * owner 与 grantee 的 sha256 是否相同（断言所需）
  * 无权限者的 status 是否为 404（对照组，证明该端点在授权上是有区分度的）

产出 `results/channel_bytes.json`，供 §6.5 的断言与复核使用。

用法（约 40 秒）：
    BOLA_LAB_DIR="C:\\Users\\Administrator\\WorkBuddy\\gitea_native_lab2" \
      <bolaexp python> verify_channel_bytes.py
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "real_system"))          # noqa: E402

from gitea_lab import Client, Server, ensure_migrated, write_config   # noqa: E402

RESULTS = HERE / "results"
OUT = RESULTS / "channel_bytes.json"

PASS = "LabPass123!"          # 实验台统一口令（与 run_native.py 一致）

# (仓库, 拥有者, 受让者, 无权者)。前两组来自 OOB_GRANTS；第三组是组织仓库，
# 受让者经**团队**获得权限（与 §6.5 提到的组织/团队级授权对应）。
CELLS = [
    ("alice/s1", "alice", "bob", "eve"),
    ("carol/s1", "carol", "eve", "bob"),
    ("acme/t1", "dave", "frank", "eve"),
]


def digest(body) -> str:
    b = body.encode("utf-8") if isinstance(body, str) else json.dumps(
        body, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(b).hexdigest()


def fetch(user: str, url: str) -> dict:
    c = Client(user=user, password=PASS, label=user)
    st, body = c.get(url)
    if isinstance(body, str):
        text, n = body, len(body.encode("utf-8"))
    else:
        text, n = json.dumps(body, ensure_ascii=False), -1
    return {"as": user, "status": st, "bytes": n, "sha256": digest(body),
            "head": text[:24]}


def main() -> int:
    cfg = write_config()
    ensure_migrated(cfg)
    rows, ok_all = [], True
    with Server(cfg) as srv:
        print(f"Gitea 就绪 {srv.ready_ms} ms  workdir={os.environ.get('BOLA_LAB_DIR')}")
        for repo, owner, grantee, outsider in CELLS:
            url = f"/api/v1/repos/{repo}/raw/README.md"
            r_owner, r_grantee, r_out = (fetch(owner, url), fetch(grantee, url),
                                         fetch(outsider, url))
            same = (r_owner["status"] == 200 and r_grantee["status"] == 200
                    and r_owner["sha256"] == r_grantee["sha256"])
            denied = (r_out["status"] == 404)
            ok_all = ok_all and same and denied
            print(f"\n{repo}  {url}")
            for r in (r_owner, r_grantee, r_out):
                print("   %-8s -> %s  bytes=%-5s sha256=%s  %r"
                      % (r["as"], r["status"], r["bytes"], r["sha256"][:16],
                         r["head"]))
            print(f"   [{'ok' if same else 'xx'}] owner 与 grantee 逐字节相同"
                  f"   [{'ok' if denied else 'xx'}] 无权者被拒({outsider})")
            rows.append({"repo": repo, "url": url, "owner": owner,
                         "grantee": grantee, "outsider": outsider,
                         "owner_resp": r_owner, "grantee_resp": r_grantee,
                         "outsider_resp": r_out,
                         "owner_grantee_identical_bytes": same,
                         "outsider_denied": denied})

    payload = {
        "about": "同一 URL 对拥有者与受让者的响应是否逐字节相同（§6.5 断言所需凭据）",
        "workdir": os.environ.get("BOLA_LAB_DIR"),
        "cells": rows,
        "all_owner_grantee_identical": all(
            r["owner_grantee_identical_bytes"] for r in rows),
        "all_outsider_denied": all(r["outsider_denied"] for r in rows),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\n[{'ok' if ok_all else 'xx'}] {OUT}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Gogs 0.14.3 认证方式探测（一次性诊断脚本）
============================================
问题：`POST /api/v1/users/root/tokens` 返回 201 并给出 sha1，但用 `?token=<sha1>`
访问 `/api/v1/user` 仍是 401。需要确定 Gogs 0.14.3 实际接受哪种传法。

候选：
  A. query    `?token=<sha1>`
  B. header   `Authorization: token <sha1>`
  C. header   `Authorization: Bearer <sha1>`
  D. basic    `Authorization: Basic base64(user:pass)`
"""
from __future__ import annotations

import base64
import json
import sys
import urllib.error
import urllib.request

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
import gogs_lab as gl

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def raw(base: str, path: str, headers: dict, timeout: int = 15):
    r = urllib.request.Request(base + path, method="GET", headers=headers)
    try:
        with _OPENER.open(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")[:200]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:200]
    except Exception as e:                                          # noqa: BLE001
        return 0, f"{type(e).__name__}: {e}"


def main():
    cfg = gl.write_config()
    adm = gl.ensure_admin(cfg)
    print("admin:", {k: adm[k] for k in ("rc", "ok", "idempotent", "tail")})
    if not adm["ok"]:
        raise SystemExit(adm["raw_tail_2k"])

    with gl.Server(cfg):
        tk = gl.create_token(gl.ADMIN_USER, gl.ADMIN_PASS)
        print("token status:", tk["status"])
        print("token body  :", json.dumps(tk["body"], ensure_ascii=False)[:300])
        sha = tk["token"]
        print("sha1 len    :", len(sha) if sha else None, repr(sha))

        basic = base64.b64encode(
            f"{gl.ADMIN_USER}:{gl.ADMIN_PASS}".encode()).decode()
        variants = [
            ("A query ?token=", f"/api/v1/user?token={sha}",
             {"Accept": "application/json"}),
            ("B header token", "/api/v1/user",
             {"Accept": "application/json", "Authorization": f"token {sha}"}),
            ("C header Bearer", "/api/v1/user",
             {"Accept": "application/json", "Authorization": f"Bearer {sha}"}),
            ("D basic auth", "/api/v1/user",
             {"Accept": "application/json", "Authorization": f"Basic {basic}"}),
            ("A2 query+user/repos", f"/api/v1/user/repos?token={sha}",
             {"Accept": "application/json"}),
            ("B2 header token+user/repos", "/api/v1/user/repos",
             {"Accept": "application/json", "Authorization": f"token {sha}"}),
        ]
        for label, path, hdrs in variants:
            st, body = raw(gl.BASE, path, hdrs)
            print(f"  {label:28s} {st}  {body[:110].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()

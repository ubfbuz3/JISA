"""
第二实现 · 独立代码路径（EXPERIMENT_PLAN 的 M5 / Block 4 消融 4）
=================================================================
目的：排除"结论依赖特定实现"这一质疑。

独立性手段（相对 mrs/mstwi_mrs.py）：
  1. **不 import** mstwi_mrs / engine 的任何函数 —— 从零重写
  2. 传输层改用 `http.client`，而非 `urllib.request`
  3. 判定表述改为**直白三条件合取**，而非照搬 catalog 的 for/IMPLIES 结构
  4. 真值与混淆判定独立重算

若本实现与主实现在同一批场景上给出**相同结论**，则结论不依赖实现细节；
若出现分歧，分歧点必须写进论文（而不是掩盖）。

诚实声明：本实现仍由同一个模型编写，**不构成跨模型独立复核**。
          它只排除"实现偶然性"，不排除"共同盲点"。
"""

from __future__ import annotations

import json
import sys
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "target_api"))

from app import Config, make_server          # 复用被测系统（这是被测对象，不是实现）

PASSWORDS = {"A": "pw-A", "B": "pw-B", "C": "pw-C"}


# --------------------------------------------------------------------------
# 极简 HTTP 客户端（http.client 路径）
# --------------------------------------------------------------------------

class Bare:
    def __init__(self, port: int):
        self.port = port
        self.tokens: dict[str, str] = {}

    def call(self, method: str, path: str, user: str | None = None, body: dict | None = None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Accept": "application/json", "Connection": "close"}
        payload = None
        if body is not None:
            payload = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        if user:
            headers["Authorization"] = f"Bearer {self.tokens[user]}"
        conn.request(method, path, body=payload, headers=headers)
        r = conn.getresponse()
        raw = r.read().decode("utf-8")
        conn.close()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"_raw": raw}
        return {"status": r.status, "body": parsed}

    def login(self, user: str):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        payload = json.dumps({"username": user, "password": PASSWORDS[user]}).encode()
        conn.request("POST", "/auth/login", body=payload,
                     headers={"Content-Type": "application/json", "Connection": "close"})
        r = conn.getresponse()
        self.tokens[user] = json.loads(r.read().decode())["token"]
        conn.close()


# --------------------------------------------------------------------------
# 直白版 MR 判定
# --------------------------------------------------------------------------

def alt_mr002(owner_call: dict, follower_call: dict) -> bool:
    """换凭证语义的直白表述：

        "拥有者访问成功，且换成访问者后拿到**一模一样**的响应" → 违反

    与主实现的等价性：主实现写成
        precondition_met ∧ ¬isError(Out1) ∧ Out1.equals(Out2)
    本式在 precondition 恒成立（B 非 admin、非 A 下级）时与之一致。
    """
    same = (owner_call["status"] == follower_call["status"]
            and owner_call["body"] == follower_call["body"])
    return owner_call["status"] == 200 and same


def alt_mr004(access_call: dict, visible_ids: set[str], target_id: str) -> bool:
    """参数替换语义的直白表述：

        "访问他人对象既没报错，该对象也不在访问者自己的可见列表里" → 违反
    """
    not_error = access_call["status"] < 400
    not_visible = target_id not in visible_ids
    return not_error and not_visible


# --------------------------------------------------------------------------
# 独立场景构造与运行
# --------------------------------------------------------------------------

def build_and_run(cfg: Config, scenario: str) -> dict:
    srv, state, port = make_server(cfg)
    try:
        c = Bare(port)
        for u in ("A", "B"):
            c.login(u)

        a1 = c.call("POST", "/doc", "A", {"title": "A-main", "content": "content-of-A-main"})["body"]["id"]
        a2 = c.call("POST", "/doc", "A", {"title": "A-second", "content": "content-of-A-second"})["body"]["id"]
        b1 = c.call("POST", "/doc", "B", {"title": "B-main", "content": "content-of-B-main"})["body"]["id"]

        share_log = []
        op = "read"
        if scenario == "S1":
            owner, actor, target = "B", "A", b1
        elif scenario == "S2":
            owner, actor, target = "A", "B", a1
        elif scenario == "S3":
            if cfg.mode == "e3":
                r = c.call("POST", f"/doc/{a1}/share", "A", {"grantee": "B", "permission": "read"})
                share_log.append({"doc_id": a1, "grantee": "B", "permission": "read", "status": r["status"]})
            owner, actor, target = "A", "B", a1
        elif scenario == "S4":
            if cfg.mode == "e3":
                r = c.call("POST", f"/doc/{a1}/share", "A", {"grantee": "B", "permission": "read"})
                share_log.append({"doc_id": a1, "grantee": "B", "permission": "read", "status": r["status"]})
            owner, actor, target = "A", "B", a2
        elif scenario == "S5":
            if cfg.mode == "e3":
                r = c.call("POST", f"/doc/{a1}/share", "A", {"grantee": "B", "permission": "read"})
                share_log.append({"doc_id": a1, "grantee": "B", "permission": "read", "status": r["status"]})
            owner, actor, target = "A", "B", a1
            op = "write"
        else:
            raise ValueError(scenario)

        # --- MR-002 ---
        m = "PUT" if op == "write" else "GET"
        b = {"content": "mutated-by-follower"} if op == "write" else None
        own_call = c.call(m, f"/doc/{target}", owner, b)
        fol_call = c.call(m, f"/doc/{target}", actor, b)
        t002 = alt_mr002(own_call, fol_call)

        # --- MR-004（仅读场景）---
        t004 = None
        if op == "read":
            vis = c.call("GET", "/doc", actor)["body"].get("items", [])
            vis_ids = {i["id"] for i in vis}
            acc = c.call("GET", f"/doc/{target}", actor)
            t004 = alt_mr004(acc, vis_ids, target)

        # --- 独立真值 ---
        should = state.can_access(actor, state.docs[target], op)
        observed_ok = fol_call["status"] == 200
        truth = "bola" if ((not should) and observed_ok) else "normal"

        return {
            "config": cfg.as_dict(), "scenario": scenario, "op": op,
            "target": target, "owner": owner, "actor": actor,
            "share_log": share_log,
            "alt_triggered_MR002": t002,
            "alt_triggered_MR004": t004,
            "truth": truth,
            "confusion_MR002": ("TP" if (truth == "bola" and t002)
                                else "FN" if truth == "bola" else
                                "FP" if t002 else "TN"),
            "confusion_MR004": (None if t004 is None else
                                ("TP" if (truth == "bola" and t004)
                                 else "FN" if truth == "bola" else
                                 "FP" if t004 else "TN")),
        }
    finally:
        srv.shutdown()
        srv.server_close()


ALT_CONFIGS = [
    Config("noe3", 0, "unlisted", "V-noE3-vuln0"),
    Config("noe3", 1, "unlisted", "V-noE3-vuln1"),
    Config("e3", 0, "unlisted", "V-E3-vuln0-unlisted"),
    Config("e3", 1, "unlisted", "V-E3-vuln1-unlisted"),
    Config("e3", 0, "listed", "V-E3-vuln0-listed"),
    Config("e3", 1, "listed", "V-E3-vuln1-listed"),
]


def main():
    out = HERE.parent / "results" / "alt_matrix.jsonl"
    recs = []
    for cfg in ALT_CONFIGS:
        for sc in ("S1", "S2", "S3", "S4", "S5"):
            try:
                recs.append(build_and_run(cfg, sc))
            except Exception as e:
                recs.append({"config": cfg.as_dict(), "scenario": sc,
                             "error": f"{type(e).__name__}: {e}"})
    with out.open("w", encoding="utf-8") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    ok = [r for r in recs if "error" not in r]
    print(f"[alt] {len(ok)}/{len(recs)} 完成 → {out}")
    for r in ok:
        if r["scenario"] in ("S3", "S4") or r["config"]["vulnerable"] == 0:
            print(f"  {r['config']['label']:26s} {r['scenario']} "
                  f"MR002={str(r['alt_triggered_MR002']):5s} "
                  f"MR004={str(r['alt_triggered_MR004']):5s} truth={r['truth']:6s} "
                  f"{r['confusion_MR002']}")


if __name__ == "__main__":
    main()

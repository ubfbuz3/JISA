"""
受控目标系统 · Controlled Target API  (v5 实验 V-noE3 / V-E3)
============================================================
本文件是论文实验的自建被测系统。设计约束（来自 研究方案_v5.md §4.2）:

  * V-noE3 与 V-E3 的端点、请求/响应 schema、OpenAPI **完全一致**,
    唯一差异是 V-E3 额外提供对象级显式授权端点 POST /doc/{id}/share。
  * 授权判定的三个层次必须显式可查:
        E0 归属        doc.owner == user
        E1 主体属性    (由 runner 侧的 MR precondition 使用, 本服务不实现角色)
        E2 主体间关系  (同上)
        E3 对象×主体   shares(doc) 中存在 (grantee=user, permission 覆盖 op)
  * 三个正交开关:
        --mode              {noe3, e3}      是否存在对象级共享能力
        --vulnerable        {0, 1}          是否注入 BOLA 缺陷 (对象级端点只查登录)
        --share-visibility  {listed, unlisted}
              listed   : 共享对列举端点 GET /doc 可见 (≈ GUI 上能看到共享给你的文档)
              unlisted : 共享**只**对 GET /doc/{id} 生效, 列举不体现
                         (≈ 通过 API/分享链接/委派获得的对象级授权, UI 不展示)
              >>> unlisted 是 E3 盲点的真正所在: 用户**合法**有权访问,
                  但 GUI 可达性模型看不到这份授权。

零第三方依赖 (纯 stdlib), 以保证复现性。

诚实声明: 本服务是为受控实验**自建**的最小系统, 不是真实开源应用。
          crAPI 无对象级共享功能、VAmPI 无共享语义, 故 E3 场景必须自建
         ——且必须自建才能获得"我们主动创建共享"这一构造式真值。
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------

ALLOWED_MODES = ("noe3", "e3")
ALLOWED_VISIBILITY = ("listed", "unlisted")
ALLOWED_INTROSPECTION = ("on", "off")


class Config:
    def __init__(self, mode: str = "e3", vulnerable: int = 0,
                 share_visibility: str = "unlisted", label: str | None = None,
                 introspection: str = "on"):
        if mode not in ALLOWED_MODES:
            raise ValueError(f"mode must be one of {ALLOWED_MODES}")
        if share_visibility not in ALLOWED_VISIBILITY:
            raise ValueError(f"share_visibility must be one of {ALLOWED_VISIBILITY}")
        if introspection not in ALLOWED_INTROSPECTION:
            raise ValueError(f"introspection must be one of {ALLOWED_INTROSPECTION}")
        self.mode = mode
        self.vulnerable = int(vulnerable)
        self.share_visibility = share_visibility
        # 授权自省面: 应用是否向拥有者暴露"该对象授权给谁"的查询能力。
        # 这是修正机制 v3 的数据源 —— 不是测试框架自己的账本。
        self.introspection = introspection
        self.label = label or (
            f"V-{mode.upper()}-vuln{self.vulnerable}-{share_visibility}"
            + ("" if introspection == "on" else "-nointro"))

    def as_dict(self) -> dict:
        return {"mode": self.mode, "vulnerable": self.vulnerable,
                "share_visibility": self.share_visibility,
                "introspection": self.introspection, "label": self.label}


# --------------------------------------------------------------------------
# 状态与授权模型
# --------------------------------------------------------------------------

class AppState:
    """单实例的内存态。两个变体各自持有独立实例, 保证不串味。"""

    USERS = {"A": "pw-A", "B": "pw-B", "C": "pw-C"}
    # E2 主体间关系: 方向为 supervisor -> [subordinates]
    # 实验中 B 始终**不是** A 的下级, 以保证 MR 的 !isSupervisorOf 谓词恒为真
    SUPERVISOR_OF = {"C": ["A"], "A": [], "B": []}

    def __init__(self, config: Config):
        self.cfg = config
        self._lock = threading.RLock()
        self.tokens: dict[str, str] = {}
        self.docs: dict[str, dict] = {}
        self.shares: dict[str, list[dict]] = {}   # doc_id -> [{share_id, grantee, permission}]
        self._seq = 0
        self.rpc: dict[str, int] = {}             # 每端点请求计数 (供 specificity 口径复现)

    # ---- 内部 -------------------------------------------------------------

    def _next_id(self, prefix: str) -> str:
        self._seq += 1
        return f"{prefix}{self._seq:04d}"

    def user_of(self, token: str | None) -> str | None:
        if not token:
            return None
        return self.tokens.get(token)

    # ---- E3: 显式授权判定 -------------------------------------------------

    def can_access(self, user: str, doc: dict, op: str) -> bool:
        """E0 归属 → E3 对象级显式授权。op ∈ {read, write}。"""
        if doc["owner"] == user:
            return True                              # E0
        for s in self.shares.get(doc["id"], []):
            if s["grantee"] != user:
                continue
            if op == "read" and s["permission"] in ("read", "write"):
                return True                      # E3: read 被 read/write 覆盖
            if op == "write" and s["permission"] == "write":
                return True                      # E3: write 仅被 write 覆盖
        return False

    def visible_in_listing(self, user: str, doc: dict) -> bool:
        """GUI 可达性模型的代理语义。MST-wi 的 cannotReachThroughGUI /
        userCanRetrieveContent 依赖爬取 GUI, 受控系统无 GUI, 故显式定义之。"""
        if doc["owner"] == user:
            return True
        if self.cfg.mode == "noe3":
            return False                             # 不存在共享能力
        has_share = any(s["grantee"] == user for s in self.shares.get(doc["id"], []))
        if not has_share:
            return False
        # listed → 共享对 UI 可见 (GUI 可达);
        # unlisted → 共享只对对象级端点生效 (GUI 不可达) ← E3 盲点场景
        return self.cfg.share_visibility == "listed"

    # ---- 观测 -------------------------------------------------------------

    def public_doc(self, doc: dict) -> dict:
        return {"id": doc["id"], "owner": doc["owner"],
                "title": doc["title"], "content": doc["content"]}

    def endpoint_catalog(self) -> list[str]:
        """端点全集, 供变体一致性校验 (V-noE3 与 V-E3 除共享端点外必须相同)。"""
        base = ["POST /auth/login", "GET /doc", "POST /doc",
                "GET /doc/{id}", "PUT /doc/{id}", "GET /health"]
        if self.cfg.mode == "e3":
            base += ["POST /doc/{id}/share"]
            if self.cfg.introspection == "on":
                base += ["GET /doc/{id}/shares"]
        return sorted(base)


# --------------------------------------------------------------------------
# HTTP 处理
# --------------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ControlledTargetAPI/1.0"

    # 由 make_server 注入
    state: AppState

    def log_message(self, fmt, *args):        # 静音, 避免污染实验输出
        pass

    # ---- 工具 -------------------------------------------------------------

    def _send(self, code: int, payload: Any):
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Doc-Hash", secrets.token_hex(4))   # 故意加入易变头
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _auth(self) -> str | None:
        h = self.headers.get("Authorization") or ""
        if h.startswith("Bearer "):
            return self.state.user_of(h[7:].strip())
        return None

    def _count(self, ep: str):
        st = self.state
        with st._lock:
            st.rpc[ep] = st.rpc.get(ep, 0) + 1

    # ---- 路由 -------------------------------------------------------------

    def do_GET(self):
        st = self.state
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]

        if path == "/health":
            self._count("GET /health")
            return self._send(200, {"status": "ok", "config": st.cfg.as_dict()})

        if path == "/openapi.json":
            self._count("GET /openapi")
            return self._send(200, {"endpoints": st.endpoint_catalog(),
                                    "config": st.cfg.as_dict()})

        if not parts:
            return self._send(404, {"error": "not_found"})

        user = self._auth()
        if user is None:
            return self._send(401, {"error": "unauthorized"})

        # GET /doc —— 列举当前用户可见的文档
        if parts == ["doc"]:
            self._count("GET /doc")
            with st._lock:
                items = [st.public_doc(d) for d in st.docs.values()
                         if st.visible_in_listing(user, d)]
            return self._send(200, {"items": items})

        # GET /doc/{id}
        if len(parts) == 2 and parts[0] == "doc":
            self._count("GET /doc/{id}")
            with st._lock:
                doc = st.docs.get(parts[1])
                if doc is None:
                    return self._send(404, {"error": "not_found"})
                # vulnerable=1 → 只检查"已登录", 不检查归属 —— 注入的 BOLA 缺陷
                allowed = True if st.cfg.vulnerable else st.can_access(user, doc, "read")
            if not allowed:
                return self._send(403, {"error": "forbidden"})
            return self._send(200, st.public_doc(doc))

        # GET /doc/{id}/shares —— 共享记录查询 (仅 e3 且自省面开启), 供人工核查
        if len(parts) == 3 and parts[0] == "doc" and parts[2] == "shares":
            if st.cfg.mode != "e3" or st.cfg.introspection != "on":
                return self._send(404, {"error": "not_found"})
            self._count("GET /doc/{id}/shares")
            with st._lock:
                doc = st.docs.get(parts[1])
                if doc is None:
                    return self._send(404, {"error": "not_found"})
                if doc["owner"] != user:
                    return self._send(403, {"error": "forbidden"})
                return self._send(200, {"shares": st.shares.get(doc["id"], [])})

        return self._send(404, {"error": "not_found"})

    def do_POST(self):
        st = self.state
        path = urlparse(self.path).path
        parts = [p for p in path.split("/") if p]

        # POST /auth/login （无需认证）
        if parts == ["auth", "login"]:
            self._count("POST /auth/login")
            body = self._read_json()
            u = body.get("username")
            if st.USERS.get(u) != body.get("password"):
                return self._send(401, {"error": "bad_credentials"})
            tok = secrets.token_urlsafe(12)
            with st._lock:
                st.tokens[tok] = u
            return self._send(200, {"token": tok, "user": u})

        user = self._auth()
        if user is None:
            return self._send(401, {"error": "unauthorized"})

        # POST /doc —— 创建文档, owner = 当前用户
        if parts == ["doc"]:
            self._count("POST /doc")
            body = self._read_json()
            with st._lock:
                did = st._next_id("doc")
                st.docs[did] = {"id": did, "owner": user,
                                "title": body.get("title", ""),
                                "content": body.get("content", "")}
                st.shares.setdefault(did, [])
            return self._send(200, st.public_doc(st.docs[did]))

        # POST /doc/{id}/share —— E3 对象级显式授权 (仅 e3)
        if len(parts) == 3 and parts[0] == "doc" and parts[2] == "share":
            if st.cfg.mode != "e3":
                return self._send(404, {"error": "not_found"})
            self._count("POST /doc/{id}/share")
            body = self._read_json()
            grantee = body.get("grantee")
            permission = body.get("permission", "read")
            if grantee not in st.USERS or permission not in ("read", "write"):
                return self._send(400, {"error": "bad_request"})
            with st._lock:
                doc = st.docs.get(parts[1])
                if doc is None:
                    return self._send(404, {"error": "not_found"})
                if doc["owner"] != user:          # 只有拥有者可授予
                    return self._send(403, {"error": "forbidden"})
                rec = {"share_id": st._next_id("sh"), "grantee": grantee,
                       "permission": permission, "by": user, "origin": "api"}
                st.shares.setdefault(doc["id"], []).append(rec)
            return self._send(200, rec)

        return self._send(404, {"error": "not_found"})

    def do_PUT(self):
        st = self.state
        parts = [p for p in urlparse(self.path).path.split("/") if p]
        if len(parts) != 2 or parts[0] != "doc":
            return self._send(404, {"error": "not_found"})
        user = self._auth()
        if user is None:
            return self._send(401, {"error": "unauthorized"})
        self._count("PUT /doc/{id}")
        body = self._read_json()
        with st._lock:
            doc = st.docs.get(parts[1])
            if doc is None:
                return self._send(404, {"error": "not_found"})
            allowed = True if st.cfg.vulnerable else st.can_access(user, doc, "write")
            if not allowed:
                return self._send(403, {"error": "forbidden"})
            if "title" in body:
                doc["title"] = body["title"]
            if "content" in body:
                doc["content"] = body["content"]
            out = st.public_doc(doc)
        return self._send(200, out)


# --------------------------------------------------------------------------
# 服务器工厂
# --------------------------------------------------------------------------

def make_server(config: Config, port: int = 0) -> tuple[ThreadingHTTPServer, AppState, int]:
    """在当前进程内起一个独立实例。返回 (server, state, port)。port=0 → 自动分配。"""
    state = AppState(config)

    class Bound(Handler):
        pass

    Bound.state = state
    srv = ThreadingHTTPServer(("127.0.0.1", port), Bound)
    srv.daemon_threads = True
    actual_port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, state, actual_port


# --------------------------------------------------------------------------
# 带外授权注入 (S6/S7 用)
# --------------------------------------------------------------------------

def seed_share(state: AppState, doc_id: str, grantee: str, permission: str,
               origin: str = "out_of_band") -> dict:
    """**带外**种入一条对象级授权记录。

    语义: 模拟"测试框架从未创建过"的授权——管理员配置、历史委派、第三方共享、
    或任何在测试开始前就已存在的授权数据。

    ★ 与 POST /doc/{id}/share 的关键差异:
      本函数直接写入服务端授权表, **不经过 HTTP 共享端点**,
      因此不会出现在 TargetClient.share_log 中。
      这正是"共享操作对测试框架不可观测"的情形。
      —— 应用自身的授权判定 `can_access` 仍然**完全正确**（它读的是同一张表）。
    """
    with state._lock:
        rec = {"share_id": state._next_id("sh"), "doc_id": doc_id, "grantee": grantee,
               "permission": permission, "by": "out-of-band", "origin": origin,
               "status": 200}
        state.shares.setdefault(doc_id, []).append(rec)
        return rec


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="受控目标 API（实验用）")
    ap.add_argument("--mode", choices=ALLOWED_MODES, default="e3")
    ap.add_argument("--vulnerable", type=int, choices=(0, 1), default=0)
    ap.add_argument("--share-visibility", choices=ALLOWED_VISIBILITY, default="unlisted")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()

    cfg = Config(a.mode, a.vulnerable, a.share_visibility)
    srv, st, p = make_server(cfg, a.port)
    print(f"[target-api] {cfg.label} listening on http://127.0.0.1:{p}")
    print(f"[target-api] endpoints: {st.endpoint_catalog()}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        srv.shutdown()

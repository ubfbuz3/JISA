# -*- coding: utf-8 -*-
"""
Undermind MCP 手动 OAuth 授权（PKCE）

背景：WorkBuddy 的 MCP 客户端不支持传入预登记 client_id，遇到不支持「动态客户端注册(DCR)」
的服务器会在元数据发现阶段直接放弃，浏览器根本不弹。Undermind 正好属于这种情况。

绕过办法：本脚本自己走一遍标准的 authorization_code + PKCE 流程拿到 access_token，
再把 token 以 Bearer 头写进 ~/.workbuddy/mcp.json，从而完全跳过 OAuth 握手。

用法：
    python undermind_auth.py              # 走浏览器授权，写入配置
    python undermind_auth.py --refresh    # 用已保存的 refresh_token 续期
    python undermind_auth.py --check      # 只验证当前 token 是否有效
"""

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import urllib.parse
import urllib.request
import urllib.error
import webbrowser

# CIMD：client_id 直接填元数据文档的 https URL，Undermind 会抓取它读取 redirect_uris。
# 官方说明："CIMD-capable clients identify themselves directly."
CLIENT_ID = "https://a63f667285fd46b59f2bf08546c9488a.app.workbuddy.link/oauth-metadata.json"
REDIRECT_URI = "http://127.0.0.1:8787/callback"
PORT = 8787
RESOURCE = "https://mcp.undermind.ai/mcp"
AS = "https://api.undermind.ai"
TOKEN_URL = AS + "/o/token/"
AUTH_URL = AS + "/o/authorize/"
SCOPE = "mcp"

HOME = os.path.expanduser("~")
MCP_JSON = os.path.join(HOME, ".workbuddy", "mcp.json")
TOKEN_FILE = os.path.join(HOME, ".workbuddy", ".undermind_token.json")


def b64u(raw):
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def http_post(url, fields):
    data = urllib.parse.urlencode(fields).encode()
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"raw": str(e)}


def save_token(tok):
    os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(tok, f, indent=2)


def load_token():
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def patch_mcp_json(access_token):
    cfg = {"mcpServers": {}}
    if os.path.exists(MCP_JSON):
        try:
            with open(MCP_JSON, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except Exception:
            cfg = {"mcpServers": {}}
    cfg.setdefault("mcpServers", {})
    cfg["mcpServers"]["undermind"] = {
        "type": "streamableHttp",
        "url": "https://mcp.undermind.ai/mcp",
        "headers": {"Authorization": "Bearer %s" % access_token},
        "timeout": 120000,
        "disabled": False,
    }
    with open(MCP_JSON, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    print("[ok] 已写入 %s" % MCP_JSON)


def check(access_token):
    req = urllib.request.Request(
        "https://mcp.undermind.ai/mcp",
        data=json.dumps({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                       "clientInfo": {"name": "workbuddy", "version": "1.0"}},
        }).encode(),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer %s" % access_token,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read().decode("utf-8", "ignore")
            print("[ok] MCP 握手成功 (HTTP %s)" % r.status)
            print(body[:500])
            return True
    except urllib.error.HTTPError as e:
        print("[fail] HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))
        return False
    except Exception as e:
        print("[fail] %s" % e)
        return False


def do_authorize():
    verifier = b64u(secrets.token_bytes(32))
    challenge = b64u(hashlib.sha256(verifier.encode()).digest())
    state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": RESOURCE,
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(params)

    result = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.urlparse(self.path).query
            kv = urllib.parse.parse_qs(q)
            if "code" in kv:
                result["code"] = kv["code"][0]
                result["state"] = kv.get("state", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    b"<html><body style='font-family:system-ui;padding:60px'>"
                    b"<h2>Authorization successful</h2>"
                    b"<p>You can close this tab and go back to WorkBuddy.</p>"
                    b"</body></html>"
                )
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"missing code")

        def log_message(self, *a):
            pass

    class Reusable(socketserver.TCPServer):
        allow_reuse_address = True

    httpd = Reusable(("127.0.0.1", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    print("=" * 60)
    print("即将在浏览器中打开 Undermind 登录页：")
    print(url)
    print("=" * 60)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("等待授权回调（最多 10 分钟）...")

    httpd.timeout = 600
    deadline = 600
    while deadline > 0 and "code" not in result:
        httpd.handle_request()
        deadline -= 1
    httpd.shutdown()

    if "code" not in result:
        print("[fail] 未收到回调，超时或用户取消")
        return None
    if result.get("state") != state:
        print("[fail] state 校验失败")
        return None

    print("[ok] 收到 authorization code，正在换取 token ...")
    code, tok = http_post(TOKEN_URL, {
        "grant_type": "authorization_code",
        "code": result["code"],
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "code_verifier": verifier,
        "resource": RESOURCE,
    })
    if "access_token" not in tok:
        print("[fail] token 交换失败 (%s): %s" % (code, json.dumps(tok)[:400]))
        return None
    save_token(tok)
    print("[ok] 已获取 access_token")
    return tok


def do_refresh():
    tok = load_token()
    if not tok or "refresh_token" not in tok:
        print("[fail] 没有可用的 refresh_token，请重新运行授权")
        return None
    code, new = http_post(TOKEN_URL, {
        "grant_type": "refresh_token",
        "refresh_token": tok["refresh_token"],
        "client_id": CLIENT_ID,
        "resource": RESOURCE,
    })
    if "access_token" not in new:
        print("[fail] 续期失败 (%s): %s" % (code, json.dumps(new)[:300]))
        return None
    save_token(new)
    print("[ok] token 已续期")
    return new


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        tok = load_token()
        if not tok:
            print("[fail] 无 token，请先授权")
            sys.exit(1)
        sys.exit(0 if check(tok["access_token"]) else 1)

    tok = do_refresh() if args.refresh else do_authorize()
    if not tok:
        sys.exit(1)

    patch_mcp_json(tok["access_token"])
    print()
    print("验证 MCP 连通性 ...")
    check(tok["access_token"])
    print()
    print("完成。请回到 WorkBuddy 的连接器页面刷新，或重启客户端以重新发现 undermind。")


if __name__ == "__main__":
    main()

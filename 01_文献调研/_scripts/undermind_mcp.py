# -*- coding: utf-8 -*-
"""
Undermind MCP 命令行客户端（Streamable HTTP）

用法:
  python undermind_mcp.py tools                      # 列出所有工具
  python undermind_mcp.py call <tool> [json_args]    # 调用工具
  python undermind_mcp.py call search '{"query":"..."}'

Token 自动从 ~/.workbuddy/.undermind_token.json 读取，过期则用 refresh_token 续期。
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import uuid

BASE = "https://mcp.undermind.ai/mcp"
TOKEN_FILE = os.path.expanduser("~/.workbuddy/.undermind_token.json")
MCP_JSON = os.path.expanduser("~/.workbuddy/mcp.json")


def load_token():
    return json.load(open(TOKEN_FILE, encoding="utf-8"))


def save_token(d):
    json.dump(d, open(TOKEN_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    # 同步到 mcp.json
    try:
        cfg = json.load(open(MCP_JSON, encoding="utf-8"))
        cfg["mcpServers"]["undermind"]["headers"]["Authorization"] = "Bearer " + d["access_token"]
        json.dump(cfg, open(MCP_JSON, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass


def refresh():
    d = load_token()
    rt = d.get("refresh_token")
    if not rt:
        raise RuntimeError("无 refresh_token，请重新运行 undermind_auth.py")
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "client_id": json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 "undermind_auth.py"), encoding="utf-8")) and None or None,
    }) if False else urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": rt,
    })
    # client_id 需与授权时一致（CIMD URL）
    CID = os.environ.get("UNDERMIND_CLIENT_ID") or read_client_id()
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "client_id": CID,
        "resource": BASE,
    })
    req = urllib.request.Request("https://api.undermind.ai/o/token/", data=data.encode(),
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        new = json.loads(r.read().decode("utf-8"))
    merged = dict(d)
    merged.update({k: v for k, v in new.items() if v})
    save_token(merged)
    return merged


def read_client_id():
    """从 undermind_auth.py 中读取 CLIENT_ID 常量"""
    try:
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "undermind_auth.py"),
                   encoding="utf-8").read()
        for line in src.splitlines():
            if line.strip().startswith("CLIENT_ID"):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "cursor"


class MCP:
    def __init__(self):
        self.session = None
        self.tok = load_token()

    def _post(self, payload, retry=True):
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": "Bearer " + self.tok["access_token"],
        }
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        req = urllib.request.Request(BASE, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                sid = r.headers.get("Mcp-Session-Id")
                if sid:
                    self.session = sid
                raw = r.read().decode("utf-8", "ignore")
                return self._parse(raw)
        except urllib.error.HTTPError as e:
            if e.code in (401, 403) and retry:
                self.tok = refresh()
                return self._post(payload, retry=False)
            detail = e.read().decode("utf-8", "ignore")[:400]
            raise RuntimeError("HTTP %s: %s" % (e.code, detail))

    @staticmethod
    def _parse(raw):
        """解析 SSE 或纯 JSON 响应"""
        raw = raw.strip()
        if raw.startswith("{"):
            return json.loads(raw)
        out = []
        for block in raw.split("\n\n"):
            for line in block.splitlines():
                if line.startswith("data:"):
                    try:
                        out.append(json.loads(line[5:].strip()))
                    except Exception:
                        pass
        if not out:
            return {"raw": raw[:600]}
        return out[-1] if len(out) == 1 else out

    def initialize(self):
        r = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "workbuddy-cli", "version": "1.0"},
            },
        })
        if isinstance(r, dict) and "result" in r:
            info = r["result"].get("serverInfo", {})
            print("[ok] 已连接 %s v%s" % (info.get("name"), info.get("version")), file=sys.stderr)
        # notify initialized
        try:
            self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except Exception:
            pass
        return r

    def tools(self):
        r = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        return r.get("result", {}).get("tools", []) if isinstance(r, dict) else []

    def call(self, name, args):
        r = self._post({
            "jsonrpc": "2.0", "id": int(time.time() * 1000) % 10**9,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        })
        if isinstance(r, dict):
            if "error" in r:
                return {"_error": r["error"]}
            return r.get("result", r)
        return r


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    m = MCP()
    m.initialize()
    if cmd == "tools":
        ts = m.tools()
        print(json.dumps(ts, ensure_ascii=False, indent=2))
    elif cmd == "call":
        name = sys.argv[2]
        args = json.loads(sys.argv[3]) if len(sys.argv) > 3 else {}
        print(json.dumps(m.call(name, args), ensure_ascii=False, indent=2))
    else:
        print("未知命令:", cmd)


if __name__ == "__main__":
    import urllib.parse  # noqa
    main()

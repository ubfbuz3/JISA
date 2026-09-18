# -*- coding: utf-8 -*-
"""
把 Undermind 精选的论文写入本地 Zotero 集合。

与 zotero_import.py 同一套踩坑约束：
  - 绕开 http 代理（ProxyHandler({})）
  - If-Unmodified-Since-Version 动态取自 Last-Modified-Version，绝不填 0
  - 建集合后库版本会 +1，必须重新取版本再写条目
  - 401 时走 /api/local/authorize 拿 key（会弹窗，需用户点 Always Allow）
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:23119"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

COLLECTION_NAME = "WebAPI安全与漏洞挖掘_JISA_2026"   # 复用已有集合
KEY_FILE = os.path.join(os.path.expanduser("~"), ".workbuddy", ".zotero_local_key.json")
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STATE = {"server_id": None, "key": None}


def load_key():
    if os.path.exists(KEY_FILE):
        try:
            STATE["key"] = json.load(open(KEY_FILE, encoding="utf-8")).get("key")
        except Exception:
            pass


def save_key():
    os.makedirs(os.path.dirname(KEY_FILE), exist_ok=True)
    json.dump({"key": STATE["key"]}, open(KEY_FILE, "w", encoding="utf-8"))


def authorize():
    body = json.dumps({"appName": "WorkBuddy-LitSurvey",
                       "appVersion": "1.0", "remember": True}).encode()
    req = urllib.request.Request(API + "/api/local/authorize", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    print("  -> 触发 Zotero 授权弹窗，请在 Zotero 窗口点「Always Allow」...")
    with OPENER.open(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    STATE["key"] = d.get("key")
    save_key()
    print("  -> 已获得授权 key: %s" % STATE["key"])
    return STATE["key"]


def call(method, path, payload=None, extra_headers=None):
    headers = {"Zotero-API-Version": "3"}
    if STATE["server_id"]:
        headers["Zotero-Server-ID"] = STATE["server_id"]
    if STATE["key"]:
        headers["Zotero-API-Key"] = STATE["key"]
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(API + path, data=data, method=method, headers=headers)
    with OPENER.open(req, timeout=180) as r:
        raw = r.read().decode("utf-8")
        return r.status, dict(r.headers), (json.loads(raw) if raw.strip() else {})


def library_version():
    st, hd, _ = call("GET", "/api/users/0/items?limit=1")
    STATE["server_id"] = hd.get("Zotero-Server-ID") or STATE["server_id"]
    v = hd.get("Last-Modified-Version")
    if not v:
        raise RuntimeError("取不到 Last-Modified-Version (status=%s)" % st)
    return int(v)


def split_name(full):
    full = (full or "").strip()
    if not full:
        return {"creatorType": "author", "name": "Anonymous"}
    parts = full.split()
    if len(parts) == 1:
        return {"creatorType": "author", "lastName": parts[0], "firstName": ""}
    return {"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]}


def build_items(sel, ckey, existing_dois):
    items, skipped = [], []
    for it in sel["core"]:
        doi = (it.get("doi") or "").replace("https://doi.org/", "")
        if doi and doi.lower() in existing_dois:
            skipped.append((it["cite_key"], doi))
            continue
        venue = it.get("venue") or ""
        vl = venue.lower()
        is_conf = any(k in vl for k in [
            "symposium", "conference", "workshop", "usenix", "ndss", "ccs",
            "icse", "fse", "issta", "ase", "esorics", "acsac", "raid",
            "arxiv", "proceedings", "annual meeting",
        ])
        tags = [{"tag": "#%s" % it["_tag"]},
                {"tag": "WebAPI安全"},
                {"tag": "来源:Undermind"},
                {"tag": "cite_key:%s" % it["cite_key"]},
                {"tag": "cite:%s" % it["citations"]},
                {"tag": "JISA-选题调研"}]
        rec = {
            "itemType": "conferencePaper" if is_conf else "journalArticle",
            "title": it["title"],
            "creators": [split_name(a) for a in it["authors"]],
            "date": str(it["year"] or ""),
            "DOI": doi,
            "url": it["doi"] or "",
            "abstractNote": it["abstract"] or "",
            "language": "en",
            "tags": tags,
            "collections": [ckey],
        }
        if is_conf:
            rec["proceedingsTitle"] = venue
        else:
            rec["publicationTitle"] = venue
        items.append(rec)
    return items, skipped


def main():
    load_key()
    sel = json.load(open(os.path.join(BASE, "_scripts", "und_selection.json"),
                         encoding="utf-8"))

    ver = library_version()
    print("[1] 库版本 = %s ｜ server_id = %s" % (ver, STATE["server_id"]))

    st, _, cols = call("GET", "/api/users/0/collections?limit=100")
    cols = cols if isinstance(cols, list) else []
    ckey = None
    for c in cols:
        if c["data"]["name"] == COLLECTION_NAME:
            ckey = c["key"]
            break
    if not ckey:
        print("!! 找不到集合 %s，请先跑 zotero_import.py" % COLLECTION_NAME)
        sys.exit(2)
    print("[2] 集合 %s -> key=%s" % (COLLECTION_NAME, ckey))

    # 收集集合内已有 DOI，避免重复入库
    st, _, cur = call("GET", "/api/users/0/collections/%s/items?limit=100" % ckey)
    cur = cur if isinstance(cur, list) else []
    existing_dois = set()
    for x in cur:
        d = (x["data"].get("DOI") or "").strip().lower()
        if d:
            existing_dois.add(d)
    print("[3] 集合内现有 %d 条，已知 DOI %d 个" % (len(cur), len(existing_dois)))

    items, skipped = build_items(sel, ckey, existing_dois)
    for ck, d in skipped:
        print("    跳过(DOI 已有): %s  %s" % (ck, d))
    print("[4] 准备写入 %d 条" % len(items))

    ver = library_version()
    try:
        st, _, resp = call("POST", "/api/users/0/items", items,
                           {"If-Unmodified-Since-Version": str(ver)})
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            authorize()
            ver = library_version()
            st, _, resp = call("POST", "/api/users/0/items", items,
                               {"If-Unmodified-Since-Version": str(ver)})
        else:
            body = e.read().decode("utf-8", "ignore")
            print("!! HTTP %s: %s" % (e.code, body[:900]))
            raise

    ok = resp.get("successful") or {}
    failed = resp.get("failed") or {}
    print("[5] 成功 %d 条，失败 %d 条" % (len(ok), len(failed)))
    if failed:
        print("    失败详情:", json.dumps(failed, ensure_ascii=False)[:1200])

    st, _, after = call("GET", "/api/users/0/collections/%s/items?limit=100" % ckey)
    after = after if isinstance(after, list) else []
    print("[6] 校验：集合内现有 %d 条" % len(after))


if __name__ == "__main__":
    main()

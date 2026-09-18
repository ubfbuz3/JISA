# -*- coding: utf-8 -*-
"""
把精选文献写入本地 Zotero。
严格遵循踩坑记录：
  - 绕开 http 代理（ProxyHandler({})）
  - If-Unmodified-Since-Version 动态取自 Last-Modified-Version，绝不能填 0
  - 建集合后库版本会 +1，必须重新取版本再写条目
  - 401 时走 /api/local/authorize 拿 key（会弹窗，需用户点 Always Allow）
不使用 connector/saveItems（会污染 UI 当前选中集合）
"""
import json
import os
import sys
import urllib.error
import urllib.request

API = "http://127.0.0.1:23119"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))

COLLECTION_NAME = "WebAPI安全与漏洞挖掘_JISA_2026"
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
    """触发 Zotero 授权弹窗，用户需点 Always Allow"""
    body = json.dumps({"appName": "WorkBuddy-LitSurvey",
                       "appVersion": "1.0", "remember": True}).encode()
    req = urllib.request.Request(API + "/api/local/authorize", data=body, method="POST",
                                 headers={"Content-Type": "application/json"})
    print("  -> 触发 Zotero 授权弹窗，请在 Zotero 窗口点「Always Allow」...")
    with OPENER.open(req, timeout=180) as r:
        d = json.loads(r.read().decode("utf-8"))
    STATE["key"] = d.get("key")
    save_key()
    print(f"  -> 已获得授权 key: {STATE['key']}")
    return STATE["key"]


def call(method, path, payload=None, extra_headers=None):
    url = API + path
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
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with OPENER.open(req, timeout=180) as r:
        raw = r.read().decode("utf-8")
        return r.status, dict(r.headers), (json.loads(raw) if raw.strip() else {})


def library_version():
    st, hd, _ = call("GET", "/api/users/0/items?limit=1")
    STATE["server_id"] = hd.get("Zotero-Server-ID") or STATE["server_id"]
    v = hd.get("Last-Modified-Version")
    if not v:
        raise RuntimeError(f"取不到 Last-Modified-Version (status={st})")
    return int(v)


def split_name(full):
    full = (full or "").strip()
    if not full:
        return {"creatorType": "author", "name": "Anonymous"}
    parts = full.split()
    if len(parts) == 1:
        return {"creatorType": "author", "lastName": parts[0], "firstName": ""}
    return {"creatorType": "author", "firstName": " ".join(parts[:-1]), "lastName": parts[-1]}


def build_items(selection, ckey):
    items = []
    for it in selection["core"]:
        doi = it["doi"].replace("https://doi.org/", "")
        venue = it.get("venue") or ""
        is_conf = any(k in venue.lower() for k in
                      ["symposium", "conference", "workshop", "usenix", "ndss", "ccs",
                       "icse", "fse", "issta", "ase", "esorics", "acsac", "raid"])
        rec = {
            "itemType": "conferencePaper" if is_conf else "journalArticle",
            "title": it["title"],
            "creators": [split_name(a) for a in it["authors"]],
            "date": str(it["year"] or ""),
            "DOI": doi,
            "url": it["doi"],
            "abstractNote": it["abstract"] or "",
            "language": "en",
            "tags": [{"tag": f"#{it['_tag']}"},
                     {"tag": "WebAPI安全"},
                     {"tag": f"cite:{it['citations']}"},
                     {"tag": "JISA-选题调研"}],
            "collections": [ckey],
        }
        if is_conf:
            rec["proceedingsTitle"] = venue
        else:
            rec["publicationTitle"] = venue
            rec["volume"] = ""
            rec["pages"] = ""
        items.append(rec)
    return items


def main():
    load_key()
    selection = json.load(open(os.path.join(BASE, "_scripts", "final_selection.json"),
                              encoding="utf-8"))

    ver = library_version()
    print(f"[1] 库版本 = {ver} ｜ server_id = {STATE['server_id']}")

    st, _, cols = call("GET", "/api/users/0/collections?limit=100")
    cols = cols if isinstance(cols, list) else []
    print(f"[2] 现有集合 {len(cols)} 个")
    ckey = None
    for c in cols:
        if c["data"]["name"] == COLLECTION_NAME:
            ckey = c["key"]
            print(f"    已存在集合，复用 key={ckey}")
            break

    if not ckey:
        try:
            st, _, resp = call("POST", "/api/users/0/collections",
                               [{"name": COLLECTION_NAME}],
                               {"If-Unmodified-Since-Version": str(ver)})
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                authorize()
                st, _, resp = call("POST", "/api/users/0/collections",
                                   [{"name": COLLECTION_NAME}],
                                   {"If-Unmodified-Since-Version": str(ver)})
            else:
                raise
        ok = resp.get("successful") or {}
        if not ok:
            print("!! 建集合失败:", json.dumps(resp, ensure_ascii=False)[:600])
            sys.exit(2)
        first = list(ok.values())[0]
        ckey = first.get("key") or first.get("data", {}).get("key")
        print(f"[3] 新建集合 {COLLECTION_NAME} -> key={ckey}")

    ver = library_version()
    print(f"[4] 建集合后重新取库版本 = {ver}")

    items = build_items(selection, ckey)
    print(f"[5] 准备写入 {len(items)} 条")
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
            raise

    ok = resp.get("successful") or {}
    failed = resp.get("failed") or {}
    print(f"[6] 成功 {len(ok)} 条，失败 {len(failed)} 条")
    if failed:
        print("    失败详情:", json.dumps(failed, ensure_ascii=False)[:900])

    st, _, v = call("GET", f"/api/users/0/collections/{ckey}/items?format=json&limit=100",
                    extra_headers=None)
    v = v if isinstance(v, list) else []
    print(f"[7] 校验：集合内现有 {len(v)} 条")
    for i, x in enumerate(v, 1):
        print(f"    {i:2d}. {x['data'].get('title','')[:96]}")

    json.dump(ckey, open(os.path.join(BASE, "_scripts", "collection_key.txt"), "w"))
    print(f"\n集合 key 已记录: {ckey}")


if __name__ == "__main__":
    main()

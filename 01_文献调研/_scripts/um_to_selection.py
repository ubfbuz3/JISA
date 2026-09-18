# -*- coding: utf-8 -*-
"""
把 Undermind deep search 结果转成与 final_selection.json 同构的 und_selection.json，
便于复用 zotero_import.py 的入库逻辑。

流程:
  1. 递归遍历 _um_ds_results.json，收集所有 cite_key
  2. get_paper_info(detail_level='full', show_doi=True) 批量补全元数据
  3. 与 final_selection.json 里的已有 15 篇按 DOI / 归一化标题去重
  4. 输出 und_selection.json（结构 {core:[...], reserve:[...]}）
"""
import json
import os
import re
import sys
import time
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from undermind_mcp import MCP  # noqa: E402
from _um import WS, retry_call  # noqa: E402


def norm_title(t):
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def norm_doi(d):
    d = (d or "").lower().strip()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return d.strip()


def collect_cite_keys(obj, out=None, ctx=None):
    """递归收集 (cite_key, 所属search名)"""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        # 找到 cite_key 字段
        ck = obj.get("cite_key") or obj.get("citeKey")
        if isinstance(ck, str) and ck and len(ck) <= 20:
            name = obj.get("name") or obj.get("title") or (ctx or "")
            out.setdefault(ck, name)
        for k, v in obj.items():
            collect_cite_keys(v, out, obj.get("name") or obj.get("title") or ctx)
    elif isinstance(obj, list):
        for x in obj:
            collect_cite_keys(x, out, ctx)
    return out


def main():
    res_path = os.path.join(HERE, "_um_ds_results.json")
    if not os.path.exists(res_path):
        print("!! 缺少 _um_ds_results.json，先跑 `python _um.py results`")
        sys.exit(1)

    raw = json.load(open(res_path, encoding="utf-8"))
    keys = collect_cite_keys(raw)
    print("从深挖结果中收集到 cite_key:", len(keys))
    for k, v in list(keys.items())[:60]:
        print("   ", k, "|", (v or "")[:70])

    if not keys:
        print("!! 没收集到 cite_key，DJ 请检查结果结构")
        sys.exit(2)

    m = MCP()
    m.initialize()

    # 批量取详情（每次最多 50）
    all_keys = list(keys.keys())
    infos = {}
    for i in range(0, len(all_keys), 50):
        batch = all_keys[i:i + 50]
        r = retry_call(m, "get_paper_info", {
            "workspace_id": WS, "cite_keys": batch,
            "detail_level": "full", "show_doi": True, "show_locations": True,
        })
        p = os.path.join(HERE, "_um_paperinfo_%d.json" % i)
        json.dump(r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print("  [batch %d] -> %s" % (i, p), flush=True)
        time.sleep(3)

    print("\n详情已落盘，请人工/脚本解析 _um_paperinfo_*.json 后再生成 und_selection.json")
    print("workspace: https://app.undermind.ai/projects/%s" % WS)


if __name__ == "__main__":
    main()

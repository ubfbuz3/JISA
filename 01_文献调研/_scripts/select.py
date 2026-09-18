# -*- coding: utf-8 -*-
"""定稿精读短名单，并生成 Zotero 导入载荷 + Codex 可读快照"""
import json
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data = json.load(open(os.path.join(BASE, "_scripts", "candidate_pool.json"), encoding="utf-8"))
pool = {}
for it in data["items"]:
    if it["doi"]:
        pool[it["doi"].replace("https://doi.org/", "").lower()] = it


def norm(d):
    return d.replace("https://doi.org/", "").lower()


CORE = [
    # ---- API 安全（本次子方向的核心 gap 区）----
    ("10.1145/3833417", "API-越权", "首个把 BOLA 攻击放到零信任假设下重新审视，指出既有防御的失效边界"),
    ("10.1007/s10207-024-00970-5", "API-越权", "OpenAPI 规格 → 彩色 Petri 网，自动推导并检测 BOLA；规格驱动路线代表"),
    ("10.1016/j.jss.2026.113060", "API-模糊测试", "REST API 模糊测试加入访问策略违规检查 + 注入攻击，扩展了 oracle 维度"),
    ("10.1145/3652157", "API-模糊测试", "REST API 白盒搜索式模糊测试的启发式设计，EvoMaster 系路线"),
    ("10.1145/3731558", "API-模糊测试", "用搜索式 mock 生成处理 Web 服务交互依赖，解决被测服务外部依赖问题"),
    # ---- LLM 辅助漏洞检测（最拥挤的赛道，作为 baseline 与对照）----
    ("10.1016/j.jss.2024.112031", "LLM-检测", "GRACE：图结构 + 上下文学习增强 LLM 漏洞检测，高被引代表"),
    ("10.1016/j.jss.2024.112234", "LLM-检测", "DLAP：深度学习增强的 LLM 提示框架，用 DL 模型产出高质量提示"),
    ("10.1016/j.cose.2024.104151", "LLM-检测", "SecureQwen：面向 Python 代码库的 LLM 漏洞检测，工程落地视角"),
    ("10.1109/tse.2025.3605442", "LLM-检测", "可解释漏洞检测：让 LLM 给出判定依据，直指 LLM 检测可信度痛点"),
    ("10.1109/tse.2024.3470333", "LLM-评测", "多任务评估开源 LLM 在软件漏洞上的能力边界，评测类基准"),
    # ---- 目标期刊 JISA 本体 + 邻近期刊 ----
    ("10.1016/j.jisa.2024.103741", "JISA-本体", "Defendroid：区块链联邦神经网络 + XAI 做 Android 代码漏洞实时检测"),
    ("10.1016/j.jisa.2024.103925", "JISA-本体", "轻量级 LLM + 混合代码特征提升漏洞检测效率，命中 JISA 的选题偏好"),
    # ---- 经典/混合方法（打地基）----
    ("10.1016/j.cose.2022.102823", "经典-GNN", "HyVulDect：图神经网络 + 语义切片做混合语义漏洞挖掘"),
    ("10.1016/j.cose.2024.103802", "经典-NER", "把命名实体识别迁移到 Python 源码漏洞检测"),
    ("10.1007/s10664-023-10346-3", "经典-工具", "AIBugHunter：漏洞预测+分类+修复一体的实用工具，EMSE"),
]

RESERVE = [
    ("10.1109/tifs.2023.3338965", "SPGNN-API：可迁移 GNN 做攻击路径识别与自主缓解（TIFS）"),
    ("10.1007/s10207-026-01307-0", "Hive-AI：面向生成式 AI API 的多服务蜜罐防御框架（IJIS 2026，最新）"),
    ("10.1145/3779222", "Context-Enhanced Vulnerability Detection Based on LLMs（TOSEM 2025）"),
    ("10.1016/j.cose.2022.102831", "XSS 对抗样本攻击（深度强化学习，C&S 2022）"),
]

selected, missing = [], []
for doi, tag, why in CORE:
    it = pool.get(norm(doi))
    if not it:
        missing.append(doi)
        continue
    it = dict(it)
    it["_tag"] = tag
    it["_why"] = why
    selected.append(it)

print(f"命中 {len(selected)}/{len(CORE)}")
if missing:
    print("!! 未在候选池中找到:", missing)

resolved_reserve = []
for doi, desc in RESERVE:
    it = pool.get(norm(doi))
    resolved_reserve.append({"doi": doi, "desc": desc, "found": bool(it),
                             "title": (it or {}).get("title")})

json.dump({"core": selected, "reserve": resolved_reserve},
          open(os.path.join(BASE, "_scripts", "final_selection.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)

# ---------- Codex 可读快照 ----------
cdir = os.path.join(BASE, "for_codex")
os.makedirs(cdir, exist_ok=True)
lines = [
    "# Zotero 文献快照 · Web/API 安全与漏洞挖掘",
    "",
    "> 由 OpenAlex 真实索引检索得到，每条均带 DOI 可溯源。",
    f"> 采集脚本：`01_文献调研/_scripts/openalex_survey.py` ｜ 时间窗 2022-01-01 起",
    f"> 条目数：{len(selected)}",
    "",
    "---",
    "",
]
for i, it in enumerate(selected, 1):
    lines += [
        f"## [{i}] {it['title']}",
        "",
        f"- **作者**：{', '.join(it['authors']) if it['authors'] else 'N/A'}"
        f"{' 等' if it['n_authors'] > len(it['authors']) else ''}",
        f"- **年份**：{it['year']} ｜ **期刊/会议**：{it['venue']} ｜ **被引**：{it['citations']}",
        f"- **DOI**：{it['doi']}",
        f"- **标注**：`{it['_tag']}` — {it['_why']}",
        f"- **命中检索主题**：{', '.join(it['matched_queries'])}",
        "",
        "**摘要**：" + (it["abstract"] or "(OpenAlex 无摘要，需读原文)"),
        "",
        "---",
        "",
    ]
lines += ["## 备用文献（未入选本轮精读，可在需要时加入）", ""]
for r in resolved_reserve:
    lines.append(f"- {'✅' if r['found'] else '❌'} `{r['doi']}` — {r['desc']}")
    if r["found"]:
        lines.append(f"  - {r['title']}")

out = os.path.join(cdir, "zotero_snapshot.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))
print(f"Codex 快照 -> {out}  ({len(''.join(lines))} 字符)")

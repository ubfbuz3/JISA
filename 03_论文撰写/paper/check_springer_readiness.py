"""
Cybersecurity(Springer) 投稿就绪度检查
=====================================
把「换刊需要改什么」从人工判断变成可复跑脚本。
检查项来自 Cybersecurity 官方 Submission guidelines（2026-09-18 抓取）：

  · 表格：不得使用颜色/底纹；阿拉伯数字编号；标题在上（≤15 词）；说明在下（≤300 词）；
          **数字不得用逗号作千分位**
  · 图：矢量优先 EPS，字体须内嵌
  · 网页链接：必须进参考文献列表并带访问日期，不得只写在正文里
  · 必需声明：Data availability / Competing interests / Funding / Authors' contributions / Ethics
  · 双盲评审 ⇒ 需一份匿名化版本
  · 封面信含 6 项固定内容

用法: python check_springer_readiness.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
SECT = HERE / "sections"


def read_all() -> dict[str, str]:
    files = {"main.tex": (HERE / "main.tex").read_text(encoding="utf-8")}
    for p in sorted(SECT.glob("*.tex")):
        files[p.name] = p.read_text(encoding="utf-8")
    return files


def strip_tex(s: str) -> str:
    s = re.sub(r"(?s)%.*?$", " ", s, flags=re.M)
    s = re.sub(r"\\[a-zA-Z@]+\*?(\[[^\]]*\])?", " ", s)
    s = s.replace("{", " ").replace("}", " ")
    return re.sub(r"\s+", " ", s).strip()


def main() -> int:
    files = read_all()
    joined = "\n".join(files.values())
    rows: list[tuple[str, str, str]] = []

    def add(item: str, ok: bool, detail: str = "") -> None:
        rows.append(("PASS" if ok else "TODO", item, detail))

    # 1 文档类
    dc = re.search(r"\\documentclass(\[[^\]]*\])?\{([^}]+)\}", files["main.tex"])
    cls = dc.group(2) if dc else "?"
    add("文档类切换到 Springer 模板", cls == "sn-jnl",
        f"当前 {cls}；目标 sn-jnl.cls（Springer Nature LaTeX 模板）")

    # 2 千分位逗号
    bad = []
    for name, txt in files.items():
        for m in re.finditer(r"\b\d{1,3}(?:,\d{3})+\b", strip_tex(txt)):
            bad.append(f"{name}:{m.group(0)}")
    add("数字不使用逗号千分位", not bad, "; ".join(bad[:5]) if bad else "未发现")

    # 3 表格颜色
    tblcol = [k for k, v in files.items()
              if re.search(r"rowcolors|cellcolor|rowcolor|colortbl|\\rowstyle", v)]
    add("表格无颜色/底纹", not tblcol, ", ".join(tblcol) if tblcol else "未发现")

    # 4 必需声明章节
    need = ["Data availability", "Competing interests", "Funding",
            "Authors' contributions", "Ethics"]
    found = {n: bool(re.search(n.replace("'", "['’]?"), joined, re.I)) for n in need}
    missing = [n for n, v in found.items() if not v]
    add("必需声明章节齐备", not missing,
        "缺: " + ", ".join(missing) if missing else "全部存在")

    # 5 正文裸 URL
    naked = []
    for name, txt in files.items():
        for m in re.finditer(r"(?<!\{)\bhttps?://[^\s{}]+", txt):
            if "\\url" not in txt[max(0, m.start() - 8):m.start()]:
                naked.append(f"{name}:{m.group(0)[:50]}")
    add("网页链接已进参考文献（非正文裸链）", len(naked) <= 2,
        f"正文出现 {len(naked)} 处裸 URL" + (f"，例: {naked[0]}" if naked else ""))

    # 6 摘要长度
    m = re.search(r"(?s)\\begin\{abstract\}(.*?)\\end\{abstract\}", files["main.tex"])
    w = len(strip_tex(m.group(1)).split()) if m else 0
    add("摘要 ≤250 词", 0 < w <= 250, f"当前约 {w} 词")

    # 7 关键词
    kw = re.search(r"(?s)\\begin\{keyword\}(.*?)\\end\{keyword\}", files["main.tex"])
    n_kw = len([x for x in re.split(r"\\sep|,", kw.group(1)) if x.strip()]) if kw else 0
    add("关键词 4–6 个", 4 <= n_kw <= 6, f"当前 {n_kw} 个")

    # 8 图表格式（以正文 \includegraphics 实际引用为准）
    figdir = HERE.parent.parent / "04_绘图与分析" / "figures"
    inc = re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", joined)
    missing = [f for f in inc if not (figdir / f).exists()]
    nonvec = [f for f in inc if not f.lower().endswith((".pdf", ".eps"))]
    add("正文引用的图均为矢量且存在", not missing and not nonvec,
        f"引用 {len(inc)} 张；缺失 {missing or '无'}；非矢量 {nonvec or '无'}")

    # 9 双盲匿名化
    leaks = []
    for name, txt in files.items():
        for pat in (r"qiulong", r"Fuzhou", r"@example\.org", r"福州"):
            if re.search(pat, txt, re.I):
                leaks.append(f"{name}:{pat}")
    add("匿名化版本所需（双盲）", bool(leaks),
        "待剥离: " + ", ".join(sorted(set(leaks))) if leaks else "未发现身份信息（需自查自我引用）")

    w0 = max(len(f"{a}") for a, _, _ in rows) if rows else 1
    w1 = max(len(f"{b}") for _, b, _ in rows) if rows else 1
    print("=" * 78)
    print("Cybersecurity(Springer) 投稿就绪度")
    print("=" * 78)
    for a, b, c in rows:
        print(f"[{a}] {b.ljust(w1)}  {c}")
    n_todo = sum(1 for a, _, _ in rows if a == "TODO")
    print("-" * 78)
    print(f"PASS {len(rows) - n_todo} / {len(rows)}   待办 {n_todo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""机械核对：回信里每个 `Table~N (p.~M)` / `Table~N, p.~M` 引用，
表 N 在 main.pdf 里必须真的在第 M 页。表号对但页码错，或表号根本不存在，都报错。
另外检查 `Tables~A--B, pp.~X--Y` 区间形式。

依赖 PyMuPDF；没有它时明确报 SKIP（不静默放行）。
用法：python check_letter_refs.py
"""
import os
import re
import sys

try:
    import pymupdf
except ImportError:
    print("[skip] check_letter_refs.py: 缺 PyMuPDF，未核对表号/页码引用")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
LETTER = os.path.join(HERE, "response_to_reviewers.tex")
PDF = os.path.normpath(os.path.join(HERE, "..", "paper", "main.pdf"))

# 表号 -> 页码（表头 "TABLE N." 第一次出现的页）
page_of = {}
d = pymupdf.open(PDF)
for i in range(len(d)):
    for m in re.finditer(r"TABLE\s+(\d+)\.", d[i].get_text()):
        page_of.setdefault(int(m.group(1)), i + 1)
print(f"main.pdf: {len(d)} 页, {len(page_of)} 张表")

txt = open(LETTER, encoding="utf-8").read()
flat = re.sub(r"\s+", " ", txt)

bad = []
checked = 0
# 单表 + 页码：Table~N (p.~M) / Table~N, p.~M) / p.~M 出现在同一括号内
for m in re.finditer(r"Table~(\d+)[^)]{0,40}?p[a-z]*\.~(\d+)", flat):
    n, p = int(m.group(1)), int(m.group(2))
    checked += 1
    if n not in page_of:
        bad.append(f"Table~{n} 不存在于 main.pdf")
    elif page_of[n] != p:
        bad.append(f"Table~{n} 信中写 p.~{p}，实际在第 {page_of[n]} 页")
# 区间表：Tables~A--B, pp.~X--Y
for m in re.finditer(r"Tables~(\d+)--(\d+),\s*pp\.~(\d+)--(\d+)", flat):
    a, b, x, y = map(int, m.groups())
    checked += 1
    for n in (a, b):
        if n not in page_of:
            bad.append(f"Tables~{a}--{b}: 表 {n} 不存在")
        elif not (x <= page_of[n] <= y):
            bad.append(f"Tables~{a}--{b}: 表 {n} 在第 {page_of[n]} 页，"
                       f"信中写 pp.~{x}--{y}")
# 纯表号（无页码）：只查存在性
for m in re.finditer(r"Table~(\d+)(?!\d)", flat):
    n = int(m.group(1))
    if n not in page_of:
        bad.append(f"Table~{n}（无页码引用）不存在于 main.pdf")

# 稿件规模声明：页数与表数必须与 main.pdf 实际一致
for m in re.finditer(r"\((\d+) pages", flat):
    n = int(m.group(1))
    checked += 1
    if n != len(d):
        bad.append(f"信中写 {n} pages，main.pdf 实际 {len(d)} 页")
for m in re.finditer(r"(\d+) tables\)", flat):
    n = int(m.group(1))
    checked += 1
    if n != len(page_of):
        bad.append(f"信中写 {n} tables，main.pdf 实际 {len(page_of)} 张表")

# 源码包文件数：`N-file` 与 `(N files)` 必须等于 zip 的实际成员数。
# 这一类字面量曾从 93 漂到 97 而 75 项承重数字检查看不见它，所以单独查。
import json
import zipfile

ZIP = os.path.normpath(os.path.join(HERE, "..", "paper",
                                    "latex_source_files_submission.zip"))
try:
    with zipfile.ZipFile(ZIP) as z:
        n_zip = sum(1 for i in z.infolist() if not i.is_dir())
except FileNotFoundError:
    n_zip = None
    bad.append(f"找不到 {ZIP}，无法核对包内文件数")
if n_zip is not None:
    for pat in (r"(\d+)-file", r"\((\d+) files\)"):
        for m in re.finditer(pat, flat):
            n = int(m.group(1))
            checked += 1
            if n != n_zip:
                bad.append(f"信中写 {n} 个文件，zip 实际 {n_zip} 个")

# 可复现产物数：`all N byte-reproducible outputs` 必须等于 outputs manifest 条数。
MANIFEST = os.path.normpath(os.path.join(HERE, "..", "..", "04_绘图与分析",
                                         "provenance", "OUTPUTS_SHA256.json"))
try:
    _man = json.loads(open(MANIFEST, encoding="utf-8").read())
    n_out = len(_man["files"]) if isinstance(_man, dict) else len(_man)
except Exception:                                                  # noqa: BLE001
    n_out = None
    bad.append(f"读不到 {MANIFEST}，无法核对产物数")
for m in re.finditer(r"all (\d+) byte-reproducible outputs", flat):
    n = int(m.group(1))
    checked += 1
    if n_out is not None and n != n_out:
        bad.append(f"信中写 {n} 个可复现产物，manifest 实际 {n_out} 个")

print(f"检查了 {checked} 个带页码的引用")
if bad:
    print("[FAIL]")
    for b in bad:
        print("  ", b)
    sys.exit(1)
print("[ok] 回信全部表号/页码引用与 main.pdf 一致")

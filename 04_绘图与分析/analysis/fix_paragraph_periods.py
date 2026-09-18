"""去掉 \\paragraph{...} 标题末尾的句点。

原因：elsarticle 在 run-in 标题后已自动加句点，标题内再写一个就渲染成 "X.."。
本脚本只做这一处机械替换，不改动其他内容。
"""
import glob
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PAPER = Path(__file__).resolve().parent.parent.parent / "03_论文撰写" / "paper"
PAT = re.compile(r"\\paragraph\{([^}]*?)\.\}")

files = sorted((PAPER / "sections").glob("*.tex")) + [PAPER / "main.tex"]
tot = 0
for p in files:
    s = p.read_text(encoding="utf-8")
    new, n = PAT.subn(r"\\paragraph{\1}", s)
    if n:
        p.write_text(new, encoding="utf-8")
        tot += n
        print(f"  {p.name}: 修 {n} 处")
print(f"合计 {tot} 处")

left = sum(len(PAT.findall(p.read_text(encoding="utf-8"))) for p in files)
print(f"残留 {left} 处")

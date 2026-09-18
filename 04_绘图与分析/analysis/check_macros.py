#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 03_论文撰写/paper/*.tex 引用的 \\Res* 宏是否都在 numbers.tex 中定义。
用法: python check_macros.py   （退出码 1 表示存在未定义宏）
不产生任何数字，只做一致性检查。
"""
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
PROJ = Path(__file__).resolve().parents[2]
PAPER = PROJ / "03_论文撰写" / "paper"
NUMBERS = PROJ / "04_绘图与分析" / "results" / "numbers.tex"

nums = NUMBERS.read_text(encoding="utf-8")
defined = set(re.findall(r"\\newcommand\{\\([A-Za-z@]+)\}", nums))

# --- 硬检查 1：宏名必须全字母 ---------------------------------------------
# TeX 的控制词只吃字母（catcode 11）。含数字（\ResAbV3FP）会被切成
# \ResAbV + "3FP"；含下划线（\ResVocabshares_of）同样无法调用。
# 实测 xelatex 确认：\newcommand{\FooB1} 报 "Command \FooB already defined"。
name_re = re.compile(r"\\newcommand\{\\([A-Za-z@0-9_\-]+)\}")
illegal = [n for n in name_re.findall(nums) if not n.isalpha()]
if illegal:
    print("!! numbers.tex 中存在非法宏名（TeX 无法调用）:")
    for n in illegal:
        print(f"   \\{n}")
    print("   修法：数字拼写（3→Three）、其余非字母字符删除；见 compute_all.py::tex_name。")
    sys.exit(2)


def strip_comments(src: str) -> str:
    """剥掉未转义的 % 之后的内容（LaTeX 注释），避免注释里的宏名被当成引用。"""
    out = []
    for line in src.splitlines():
        buf = []
        i = 0
        while i < len(line):
            c = line[i]
            if c == "\\" and i + 1 < len(line):
                buf.append(line[i:i + 2])
                i += 2
                continue
            if c == "%":
                break
            buf.append(c)
            i += 1
        out.append("".join(buf))
    return "\n".join(out)


tex_files = sorted(PAPER.glob("*.tex")) + sorted((PAPER / "sections").glob("*.tex"))
used = {}
for f in tex_files:
    src = strip_comments(f.read_text(encoding="utf-8"))
    for m in re.findall(r"\\([A-Za-z@][A-Za-z@0-9]*)", src):
        if len(m) > 3 and m.startswith("Res"):
            used.setdefault(m, []).append(f.name)

missing = sorted(set(used) - defined)
print(f"numbers.tex 定义 {len(defined)} 个宏；被引用的 Res* 宏 {len(used)} 个")
if missing:
    import difflib
    print("\n!! 未定义的宏：")
    for m in missing:
        cand = difflib.get_close_matches(m, defined, n=3, cutoff=0.55)
        print(f"   \\{m}   (出现在 {', '.join(sorted(set(used[m])))})  ~> {cand}")
    sys.exit(1)
print("全部 Res* 宏均已定义。")

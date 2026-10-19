"""上线前自检。

正文引用的 Mii* / Res* / Nt* / Gg* / Gt* / Gl* / Seed* 宏，必须全部在
results/ 下的生成文件中有唯一定义。缺一个即退出非 0——防止出现
"正文一个数、宏文件没有这个数" 的口径漂移。
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent.parent
PAPER = PROJ / "03_论文撰写" / "paper"
RES = PROJ / "04_绘图与分析" / "results"

# 扫描 results/ 下全部生成文件：早期清单只列了 6 个，truth/design/coverage 等
# 后来新增的宏文件因此不被校验（漏检不会报错，只会给假保证）。
GEN_FILES = sorted(p.name for p in RES.glob("*.tex"))

available: dict[str, str] = {}
dup: list[str] = []
for f in GEN_FILES:
    p = RES / f
    if not p.exists():
        print(f"!! 缺少生成文件 {f}")
        sys.exit(1)
    for m in re.findall(r"\\newcommand\{(\\[A-Za-z]+)\}", p.read_text(encoding="utf-8")):
        if m in available:
            dup.append(f"{m} 重复定义于 {available[m]} 与 {f}")
        available[m] = f

used: dict[str, set] = {}
for t in sorted(PAPER.joinpath("sections").glob("*.tex")) + [PAPER / "main.tex"]:
    txt = t.read_text(encoding="utf-8")
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("%"):      # 注释里提到宏名不算引用
            continue
        line = line.split("%")[0] if "%" in line else line
        for m in re.findall(r"\\[A-Z][A-Za-z]+", line):
            used.setdefault("\\" + m[1:], set()).add(t.name)

MACRO_PREFIX = re.compile(r"^(Mii|Res|Nt|Gl|Gg|Gt|Seed|Ssz|Tmp|Cve|Cvg|Tvt|Dsg)")
missing = sorted(k for k in used
                 if MACRO_PREFIX.match(k.lstrip("\\"))
                 and k not in available and k != "\\S")

if dup:
    print("!! 宏重复定义:")
    for d in dup[:10]:
        print("   " + d)
if missing:
    print(f"!! 正文引用但未定义的宏 ({len(missing)}):")
    for k in missing:
        owners = ", ".join(sorted(used[k]))
        print(f"   {k} <- {owners}")
    sys.exit(1)
print(f"ok: 正文引用 {len([k for k in used if MACRO_PREFIX.match(k.lstrip(chr(92)))])} 个宏，"
      f"全部在 {len(GEN_FILES)} 个生成文件中有定义；无重复定义。")

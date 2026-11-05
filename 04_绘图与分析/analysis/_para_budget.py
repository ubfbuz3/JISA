"""Per-paragraph word budget for the manuscript sections (planning aid, not a deliverable)."""
import re
import pathlib
import glob
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
for f in sorted(glob.glob(str(root / "*.tex"))):
    p = pathlib.Path(f)
    s = p.read_text(encoding="utf-8")
    lines = [l for l in s.splitlines() if not l.lstrip().startswith("%")]
    body = "\n".join(lines)
    parts = re.split(r"(\\paragraph\{[^}]*\})", body)
    total = len(body.split())
    print("\n" + "=" * 72)
    print(f"{p.name}   合计 {total} 词")
    pre = parts[0]
    if pre.strip():
        print(f"  {'[章节标题/无段落标题]':<52}{len(pre.split()):>5} 词")
    for i in range(1, len(parts), 2):
        title = re.sub(r"\\paragraph\{|\}", "", parts[i])
        chunk = parts[i + 1] if i + 1 < len(parts) else ""
        print(f"  L{s[:parts[i].find(parts[i])].count(chr(10)) + 1 if False else '':<0}{title[:52]:<54}{len(chunk.split()):>5} 词")

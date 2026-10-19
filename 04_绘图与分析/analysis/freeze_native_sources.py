"""
冻结原生引擎运行的上游源码状态（R1.14 整改）。
====================================================

问题：ingest_native_engine.py / compute_all.py 曾直接读取包外 MST 工作区的
实时 git status / log / diff 与源文件。外部仓库状态一变，"历史运行事实"
就会跟着变——输出不再是归档记录的确定函数。

本脚本把可核实的历史输入**一次性冻结**为
    experiments/native_engine/results/frozen_source_state.json
包含：上游 HEAD 提交与日期、工作区改动清单、每个改动文件的 sha256
（工作区版 + pristine HEAD 版）、pom.xml 的完整 diff 补丁、MR 目录下全部
.java 文件的清单与摘要、compute_all 扫描的三个关键源文件摘要。

之后 ingest_native_engine.py / compute_all.py 只从该冻结文件读历史事实；
实时 git 状态仅作附加诊断（比对不一致时告警，但绝不进宏）。
冻结时间 = 本脚本运行时刻，**不倒填**采集时间；正文引用的历史事实
由冻结内容生成，冻结内容与运行时状态的一致性由"改动计数与运行记录
叙述一致"这一交叉核对佐证（见 stdout 校验段）。

用法:
  python freeze_native_sources.py [--src <MST 仓库路径>]
默认路径 = 环境变量 MST_SRC_PATH，否则 C:/Users/Administrator/WorkBuddy/mst_engine/MST
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "experiments" / "native_engine" / "results" / "frozen_source_state.json"

DEFAULT_SRC = Path(r"C:/Users/Administrator/WorkBuddy/mst_engine/MST")
KEY_FILES = [
    "src/smrl/mr/crawljax/WebProcessor.java",
    "src/smrl/mr/crawljax/WebOperationsProvider.java",
    "src/smrl/mr/language/SystemConfig.java",
]
BUILD_FILES = {"pom.xml", "build.xml", "build.gradle"}


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, timeout=120)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=os.environ.get("MST_SRC_PATH", str(DEFAULT_SRC)))
    a = ap.parse_args()
    src = Path(a.src)
    if not src.exists():
        print(f"[FATAL] 上游源码不存在: {src}")
        return 2

    head = git(src, "log", "-1", "--format=%H%x09%ad%x09%s")
    if head.returncode != 0 or not head.stdout.strip():
        print(f"[FATAL] 无法读取 {src} 的 git 历史（需要 HEAD 提交作为版本锚）")
        return 2
    ch, cdate, csubj = head.stdout.strip().split("\t", 2)

    st = git(src, "status", "--porcelain")
    if st.returncode != 0:
        print(f"[FATAL] git status 失败: {st.stderr.strip()}")
        return 2
    entries = [ln for ln in st.stdout.splitlines() if ln.strip()]

    modified = []
    for ln in entries:
        xy, path = ln[:2], ln[3:].strip()
        rec = {"status": xy, "path": path, "worktree_sha256": None,
               "head_sha256": None}
        p = src / path
        if p.is_file():
            rec["worktree_sha256"] = sha256_bytes(p.read_bytes())
        hv = git(src, "show", f"HEAD:{path}")
        if hv.returncode == 0:
            rec["head_sha256"] = sha256_bytes(hv.stdout.encode("utf-8"))
        modified.append(rec)

    diff = git(src, "diff")
    diff_text = diff.stdout if diff.returncode == 0 else None

    # MR 目录清单（compute_all 扫描输入）
    mr_dir = src / "src-mrs-icst2020"
    mr_files = {}
    if mr_dir.exists():
        for f in sorted(mr_dir.rglob("*.java")):
            mr_files[str(f.relative_to(src)).replace("\\", "/")] = \
                sha256_bytes(f.read_bytes())

    key_files = {}
    for rel in KEY_FILES:
        p = src / rel
        key_files[rel] = sha256_bytes(p.read_bytes()) if p.is_file() else None

    java_mod = sum(1 for m in modified
                   if m["path"].lower().endswith(".java")
                   and m["path"].split("/")[0].lower().startswith("src"))
    build_mod = sum(1 for m in modified
                    if Path(m["path"]).name.lower() in BUILD_FILES)

    doc = {
        "frozen_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "frozen_by": "analysis/freeze_native_sources.py",
        "note": ("Frozen snapshot of the upstream MST workspace used for the "
                 "native-engine run. Historical facts in the paper are "
                 "generated from this file, not from a live checkout; the "
                 "live git state may move on and is used only as a "
                 "diagnostic comparison. frozen_at is the freeze time, not "
                 "the experiment time."),
        "source_root_env": "MST_SRC_PATH",
        "head": {"commit": ch, "date": cdate, "subject": csubj},
        "status_entries": entries,
        "modified_files": modified,
        "counts": {"modified_total": len(modified),
                   "java_modified": java_mod,
                   "build_modified": build_mod,
                   "diff_lines": (len(diff_text.splitlines())
                                  if diff_text is not None else None)},
        "pom_diff": diff_text,
        "mr_dir_files_sha256": mr_files,
        "key_files_sha256": key_files,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    print(f"冻结完成 -> {OUT}")
    print(f"  HEAD          {ch[:12]} ({cdate})")
    print(f"  改动文件      {len(modified)} 个（java {java_mod}，build {build_mod}）")
    for m in modified:
        print(f"    {m['status']} {m['path']}  work={str(m['worktree_sha256'])[:12]} "
              f"head={str(m['head_sha256'])[:12]}")
    print(f"  pom diff      {doc['counts']['diff_lines']} 行")
    print(f"  MR 目录 .java {len(mr_files)} 个；关键文件 {len(key_files)} 个")
    print("\n与既有运行叙述的交叉核对（防倒填）：")
    print(f"  modified_total={len(modified)}（论文记 1）  "
          f"java_modified={java_mod}（论文记 0）  build_modified={build_mod}（论文记 1）")
    ok = len(modified) == 1 and java_mod == 0 and build_mod == 1
    print("  [ok] 与运行时叙述一致" if ok else
          "  !! 与运行时叙述不一致 —— 工作区已变动，冻结前请先核实历史状态")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

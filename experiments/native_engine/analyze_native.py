"""
原生引擎实验结果分析
====================
读 results/native_engine.json，产出可核对的小结（不手敲任何结论）。

用法: python analyze_native.py [results/native_engine.json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent


def main() -> int:
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "results" / "native_engine.json"
    if not p.exists():
        print(f"!! 找不到 {p}")
        return 2
    d = json.loads(p.read_text(encoding="utf-8"))

    print("=" * 76)
    print("原生引擎实验（MST-wi OTG_AUTHZ_*）")
    print("=" * 76)
    g = d.get("gitea", {})
    print(f"被测系统      {g.get('base')}   Gitea {g.get('version')}   ready={g.get('ready_ms')}ms")
    ch = d.get("channel", {})
    print(f"观测通道      {ch.get('channel')}  ← 由通道自检决定，见 channel.evidence")
    for e in ch.get("evidence", []):
        print(f"    [{e['channel']:4s}] /{e['url']} as {e['as']:10s} -> {e['status']}"
              + (f" {e.get('kind')}" if e.get("kind") else ""))

    dat = d.get("data", {})
    print(f"\n数据          base_inputs={dat.get('base_inputs')}  "
          f"pairing={dat.get('pairing_entries')}  store_files={dat.get('store_files')}")
    kc = dat.get("key_cell", {})
    print(f"关键格        {kc.get('repo')} 应收者={kc.get('grantee')}  "
          f"（在受让者采集快照里? {kc.get('in_snapshot_of_grantee')}）")
    for og in dat.get("oob_grants", []):
        print(f"  带外授予    {og['repo']:12s} -> {og['grantee']:9s} ({og['perm']})")

    eng = d.get("engine", {})
    print(f"\n数据视图      view_size={eng.get('input_view_size')}  "
          f"derived={eng.get('derived_inputs')}  failed={eng.get('derive_failed')}  "
          f"chunk=floor(LEN/160)={eng.get('chunk_size_floor_div_160')}")

    print("\n--- 逐条 MR ---")
    print(f"  {'MR':18s} {'status':10s} {'fired':>6s} {'http':>7s} {'ms':>8s}")
    tot_fired = 0
    for r in eng.get("mrs", []):
        nm = r.get("mr", "?").split(".")[-1]
        f = r.get("fired", 0) or 0
        tot_fired += f if isinstance(f, int) else 0
        print(f"  {nm:18s} {str(r.get('status')):10s} {f:>6} "
              f"{r.get('http_calls', 0):>7} {r.get('ms', 0):>8}")
        if r.get("error"):
            print(f"      !! {r.get('error')} @ {r.get('error_at')}")

    print(f"\n  告警总数 = {tot_fired}")

    c = eng.get("counters", {})
    print("\n--- 谓词真实调用统计（纯委托计数，判定权在 MST-wi 原实现） ---")
    for k in ("cannotReachThroughGUI_url_calls", "cannotReachThroughGUI_url_true",
              "cannotReachThroughGUI_input_calls", "cannotReachThroughGUI_input_true",
              "isSupervisorOf_calls", "isSupervisorOf_true",
              "userCanRetrieveContent_calls", "userCanRetrieveContent_true",
              "http_calls_total"):
        print(f"  {k:42s} {c.get(k)}")

    print("\n--- 判读锚点（不替代人工结论） ---")
    n = c.get("cannotReachThroughGUI_url_calls", 0) or 0
    t = c.get("cannotReachThroughGUI_url_true", 0) or 0
    print(f"  1) 引擎是否真的进了谓词：calls={n}  ⇒ {'是' if n > 0 else '否（数据视图为空，未执行）'}")
    print(f"  2) '不可达'为真的比例：{t}/{n}"
          + (f" = {t / n:.3f}" if n else ""))
    print(f"  3) 是否产生了告警：{tot_fired}"
          + ("（若关键格被判成 violation ⇒ 假确证）" if tot_fired else ""))
    print(f"  4) 观测通道：{ch.get('channel')} —— "
          + ("与 crawl 记录的 elementURL 同构" if ch.get("channel") == "html"
             else "⚠️ 为 API 端点，须在正文申报这一偏离"))
    print(f"\n耗时 {d.get('elapsed_s')}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

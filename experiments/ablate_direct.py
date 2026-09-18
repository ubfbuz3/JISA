"""
第七轮追加消融 · direct-authz-probe（无 MR 触发）
=================================================
回答 v7 追问 A 路 Q4 / U9（两个对抗通道都独立提出的最致命方法论攻击）：

> 「v3 = MR 触发 + 自省面比对。若去掉 MR 触发、只保留"查询 SUT 授权面"的直接授权查询，
>   是否在每个 case 上得到相同乃至更多 TP？若是，则 MR 只是冗余触发器，
>   论文贡献塌缩为'用 SUT 授权 API 作 oracle'，不是变形测试贡献。」

本脚本**不新增实验记录**，而是从已有的 raw_matrix.jsonl 出发，
按 (配置, 场景, 操作) 分组重新探测一次 SUT 授权面，得到 direct-only 的裁决，
再与 v1/v2/v3/degrade_all 做**端到端**混淆矩阵对照。

direct-only 的语义（严格定义，先于观察固定）：
    probe_state == "none"        -> violation-proven   （授权面说无授权 ⇒ 报警）
    probe_state == "covering"    -> pass               （授权面说有授权 ⇒ 不报警）
    probe_state == "unavailable" -> indeterminate      （面不可读 ⇒ 弃权）

★ 关键：direct-only **不消费 MR 的任何观测**，因此它检验的正是
  「MR 触发这一步是否必要」。

用法: python ablate_direct.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "mrs"))
sys.path.insert(0, str(HERE / "target_api"))

from app import Config, make_server                      # noqa: E402
from engine import TargetClient, setup_scenario           # noqa: E402
import boundary_aware as ba                               # noqa: E402

RESULTS = HERE / "results"
RAW = RESULTS / "raw_matrix.jsonl"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ADJ = ("v1", "v2", "v3", "degrade_all", "direct")


def probe_state_for(cfg_dict: dict, scenario: str) -> dict:
    """重建场景并探测 SUT 授权面，返回 {op: state}。"""
    cfg = Config(mode=cfg_dict["mode"], vulnerable=cfg_dict["vulnerable"],
                 share_visibility=cfg_dict["share_visibility"],
                 label=cfg_dict.get("label"), introspection=cfg_dict["introspection"])
    srv, state, port = make_server(cfg)
    try:
        client = TargetClient(port)
        setup = setup_scenario(client, cfg, scenario, state)
        out = {}
        for op in ("read", "write"):
            st, _ = ba.probe_e3_sut(client, setup.owner, setup.actor,
                                    setup.target_doc, op)
            out[op] = st
        return out
    finally:
        srv.shutdown()
        srv.server_close()


def direct_verdict(state: str) -> str:
    if state == "none":
        return "violation-proven"
    if state == "covering":
        return "pass"
    return "indeterminate"


def confused(truth: str, alarm: bool) -> str:
    if truth == "bola":
        return "TP" if alarm else "FN"
    return "FP" if alarm else "TN"


def main():
    recs = [json.loads(l) for l in RAW.open(encoding="utf-8") if l.strip()]
    recs = [r for r in recs if "error" not in r]
    print(f"[ablate] loaded {len(recs)} records from {RAW.name}")

    # 1) 重探 SUT 授权面：按 (config.label, scenario) 去重
    groups = sorted({(r["config"]["label"], r["scenario"]) for r in recs})
    print(f"[ablate] probing {len(groups)} (config, scenario) groups ...")
    probe_cache: dict[tuple[str, str], dict] = {}
    for i, (lab, sc) in enumerate(groups, 1):
        cfgd = next(r["config"] for r in recs
                    if r["config"]["label"] == lab and r["scenario"] == sc)
        probe_cache[(lab, sc)] = probe_state_for(cfgd, sc)
        print(f"   [{i}/{len(groups)}] {lab:34s} {sc} -> {probe_cache[(lab, sc)]}")

    # 2) 端到端混淆矩阵
    tally = {a: defaultdict(int) for a in ADJ}
    per_scen = {a: defaultdict(lambda: defaultdict(int)) for a in ADJ}

    for r in recs:
        truth = r["truth"]["truth"]
        sc = r["scenario"]
        label = r["config"]["label"]
        op = r["action"]["op"]

        # 已有裁决器：alarm = 是否升级为 violation-proven
        for a in ("v1", "v2", "v3", "degrade_all"):
            v = r["verdicts"].get(a, {}).get("verdict")
            if v is None:
                continue
            cell = confused(truth, v == "violation-proven")
            tally[a][cell] += 1
            per_scen[a][sc][cell] += 1

        # direct-only
        st = probe_cache[(label, sc)].get(op, "unavailable")
        cell = confused(truth, direct_verdict(st) == "violation-proven")
        tally["direct"][cell] += 1
        per_scen["direct"][sc][cell] += 1

    # 3) 汇报
    def pr(a: str):
        t = tally[a]
        tp, fp, fn, tn = t["TP"], t["FP"], t["FN"], t["TN"]
        n = tp + fp + fn + tn
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        print(f"\n=== {a} ===")
        print(f"  n={n}  TP={tp} FP={fp} FN={fn} TN={tn}")
        print(f"  precision={prec:.4f}  recall={rec:.4f}")

    print("\n" + "=" * 66)
    print("端到端混淆矩阵（alarm 定义为 verdict == violation-proven）")
    print("=" * 66)
    for a in ADJ:
        pr(a)

    print("\n" + "=" * 66)
    print("逐场景（direct-only vs v3）")
    print("=" * 66)
    scens = sorted({r["scenario"] for r in recs})
    print(f"{'scen':6s} | {'v3 TP/FP/FN/TN':>20s} | {'direct TP/FP/FN/TN':>22s}")
    for sc in scens:
        v3 = per_scen["v3"][sc]
        dr = per_scen["direct"][sc]
        print(f"{sc:6s} | {v3['TP']:>4d}/{v3['FP']:>4d}/{v3['FN']:>4d}/{v3['TN']:>4d}"
              f"   | {dr['TP']:>5d}/{dr['FP']:>5d}/{dr['FN']:>5d}/{dr['TN']:>5d}")

    out = {
        "note": "direct-only = 不消费 MR 观测，仅查询 SUT 授权自省面；用于检验 MR 触发步骤是否必要",
        "tally": {a: dict(tally[a]) for a in ADJ},
        "per_scenario": {a: {sc: dict(per_scen[a][sc]) for sc in per_scen[a]}
                         for a in ADJ},
        "probe_cache": {f"{k[0]}|{k[1]}": v for k, v in probe_cache.items()},
    }
    (RESULTS / "ablation_direct.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[done] -> {RESULTS / 'ablation_direct.json'}")


if __name__ == "__main__":
    main()

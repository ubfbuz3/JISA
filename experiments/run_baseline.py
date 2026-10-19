"""
R1.7 竞争基线 · 常规多账户差分 vs 关系感知裁决
================================================

审稿人要求（R1.7）：给出与候选、预算匹配的公平基线，而不是只与自己的消融比。

本实验实现三种**常规差分**做法，并在**同一批 SUT 实例、同一对探测请求**上
与本文方法（MR-002 + v3 裁决）对比：

  B1  status_only        低权账户请求成功（status < 400）即报"疑似越权"。
                          这是 Burp Autorize 一类工具最朴素的模式：只看对方是不是
                          拿到了 2xx，不比对内容、不查授权。
  B2  diff_equal         拥有者的同一请求成功、且低权账户拿到**逐字节相同**的响应
                          才报。即 changeCredentials 重放差分，不含任何授权模型。
  B3  diff_inband        在 B2 之上，用**框架自己创建共享时写下的记录**（in-band
                          share_log）压制告警。这是"最理想的常规差分"：它已经知
                          道测试期间自己授过什么权，但仍看不见带外授权（S6/S7）。
  ours  mr_v3             MR-002 触发后查询**被测系统的授权自省面**；面不可读时
                          弃权（indeterminate），不升级为确证。

★ 公平性要点（必须与结果一起声明）
  1. 预算：四个方法消费**同一对请求**（owner 一次、actor 一次）。B1/B2/B3 的判定
     完全由这两个观测加本地账本推出，不额外发请求。ours 额外发 1 次自省查询，
     成本在表里单列，不隐藏。
  2. 信息：B3 已经拥有"框架可见的全部授权"，是比真实工具更强的对照；真实工具
     连这一层都没有（那更接近 B2）。因此 B3 是**上界式**的常规基线，不是稻草人。
  3. 真值：仍用动作级构造式真值 `ground_truth(...)`，与主实验同一口径。
     真阳性 = E=deny ∧ Y=allow；假确证 = E=allow ∧ 方法仍宣称 violation-proven。
  4. 域：只取具备对象级共享能力的配置（mode == "e3"）与 S1–S7 全部场景，
     共 6 × 7 = 42 个格。无共享能力的配置上 S3–S7 的构造不成立，纳入会污染真值。

用法:  python run_baseline.py
输出:  results/baseline_compare.json
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "mrs"))
sys.path.insert(0, str(HERE / "target_api"))

from app import make_server                                   # noqa: E402
from engine import (TargetClient, setup_scenario, ground_truth,  # noqa: E402
                    action_path, SCENARIOS)
from mstwi_mrs import mr002_evaluate                           # noqa: E402
import boundary_aware as ba                                    # noqa: E402
from run_matrix import CONFIGS                                 # noqa: E402

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

OP_COVERED_BY = {"read": ("read", "write"), "write": ("write",)}

# 只有能创建对象级共享的配置，S3–S7 的构造才有意义
BASE_CONFIGS = [c for c in CONFIGS if c.mode == "e3"]


def inband_covers(client, doc_id: str, actor: str, op: str) -> list[dict]:
    """框架账本里是否存在对该 actor 生效、且覆盖本次操作的共享。"""
    return [s for s in client.shares_of(doc_id)
            if s["grantee"] == actor and s["permission"] in OP_COVERED_BY[op]]


def run_cell(cfg, scenario: str) -> dict:
    srv, state, port = make_server(cfg)
    try:
        client = TargetClient(port)
        setup = setup_scenario(client, cfg, scenario, state)
        method, path = action_path(setup)
        body = {"content": "mutated-by-follower"} if setup.op == "write" else None

        # ---- 同一对探测请求（四个方法共用）-------------------------------
        requests_after_setup = client.request_count
        out1 = client.request(owner := setup.owner, method, path, body)
        out2 = client.request(actor := setup.actor, method, path, body)
        probe_requests = client.request_count - requests_after_setup

        gt = ground_truth(state, cfg, actor, setup.target_doc, setup.op, out2.status)
        equal = out1.equals(out2)
        owner_ok = out1.status < 400
        actor_ok = out2.status < 400
        covering = inband_covers(client, setup.target_doc, actor, setup.op)

        # ---- B1 / B2 / B3 ------------------------------------------------
        b1 = bool(actor_ok)
        b2 = bool(owner_ok and equal)
        b3 = bool(b2 and not covering)

        # ---- ours: MR-002 语义（blind，前置条件恒成立）+ v3 裁决 ---------
        not_sup = not client.is_supervisor_of(actor, owner)
        triggered = bool(not_sup and owner_ok and equal)
        mres = {"mr": "MR-002", "triggered": triggered,
                "owner": owner, "follower": actor, "method": method, "path": path,
                "input1": out1.as_dict(), "input2": out2.as_dict(),
                "ph_notSupervisorOf": not_sup,
                "ph_cannotReachThroughGUI": True,
                "gui_mode": "blind",
                "isError_out1": not owner_ok,
                "out1_equals_out2": equal}
        before = client.request_count
        v3 = ba.adjudicate(mres, client, setup, version="v3")
        ours_extra = client.request_count - before
        claimed = (v3.verdict == "violation-proven")
        abstained = (v3.verdict == "indeterminate")

        def score(alarm: bool, abstain: bool = False) -> dict:
            if abstain:
                return {"tp": False, "fp": False, "fn": False, "tn": False,
                        "abstain": True}
            is_bola = gt["truth"] == "bola"
            return {"tp": bool(is_bola and alarm),
                    "fp": bool(not is_bola and alarm),
                    "fn": bool(is_bola and not alarm),
                    "tn": bool(not is_bola and not alarm),
                    "abstain": False}

        return {
            "config": cfg.as_dict(),
            "scenario": scenario,
            "intent": setup.intent,
            "op": setup.op,
            "owner": owner,
            "actor": actor,
            "target_doc": setup.target_doc,
            "share_origin": setup.share_origin,
            "truth": gt["truth"],
            "truth_detail": gt,
            "out1": out1.as_dict(),
            "out2": out2.as_dict(),
            "signals": {"owner_ok": owner_ok, "actor_ok": actor_ok,
                        "equal": equal, "inband_covering": bool(covering),
                        "inband_records": covering},
            "methods": {
                "B1_status_only": {"alarm": b1, **score(b1)},
                "B2_diff_equal": {"alarm": b2, **score(b2)},
                "B3_diff_inband": {"alarm": b3, **score(b3)},
                "ours_mr_v3": {"alarm": claimed, "verdict": v3.verdict,
                               "reason": v3.reason,
                               **score(claimed, abstained)},
            },
            "budget": {"probe_requests": probe_requests,
                       "ours_extra_requests": ours_extra},
        }
    finally:
        srv.shutdown()
        srv.server_close()


def aggregate(recs: list[dict]) -> dict:
    out = {}
    for name in ("B1_status_only", "B2_diff_equal", "B3_diff_inband", "ours_mr_v3"):
        c = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "abstain": 0}
        for r in recs:
            m = r["methods"][name]
            for k in c:
                c[k] += int(m[k])
        n = len(recs)
        claimed = c["tp"] + c["fp"]
        # 真违规格总数：由每格的 truth 直接数，不依赖任何方法的裁决
        n_viol = sum(1 for r in recs if r.get("truth") == "bola")
        # 被弃权掉的真违规格：召回率的分母必须包含它们
        abstained_viol = sum(
            1 for r in recs
            if r.get("truth") == "bola"
            and r["methods"][name]["abstain"]
        )
        decided = c["tp"] + c["fn"]
        out[name] = {
            **c,
            "cells": n,
            "claimed": claimed,
            "violation_cells": n_viol,
            "abstained_violations": abstained_viol,
            "coverage": round((n - c["abstain"]) / n, 4) if n else None,
            "precision_on_claims": round(c["tp"] / claimed, 4) if claimed else None,
            # 条件召回：只在"作出了裁决"的格子上算。弃权既不算命中也不算漏报，
            # 所以这个数会系统性偏高，引用它必须带上 on_decided 限定。
            "recall_on_decided": round(c["tp"] / decided, 4) if decided else None,
            # 总召回：分母是全部真违规格，含被弃权的那些。
            "recall_all_violations": round(c["tp"] / n_viol, 4) if n_viol else None,
            "false_proof_rate": round(c["fp"] / n, 4) if n else None,
        }
    # 预算口径：匹配的是"探测对"（owner 一次 + actor 一次），不是总请求数。
    shared = 2 * len(recs)
    extra = sum(r["budget"]["ours_extra_requests"] for r in recs)
    out["_budget"] = {
        "probe_requests_per_cell": sorted({r["budget"]["probe_requests"] for r in recs}),
        "ours_extra_per_cell": sorted({r["budget"]["ours_extra_requests"] for r in recs}),
        "shared_probe_requests": shared,
        "ours_extra_requests_total": extra,
        "ours_total_requests": shared + extra,
        "note": ("probe pair matched across methods; total requests are not, "
                 "because only ours adds introspection reads"),
    }
    return out


def main() -> None:
    t0 = time.time()
    recs: list[dict] = []
    for cfg in BASE_CONFIGS:
        for sc in SCENARIOS:
            try:
                recs.append(run_cell(cfg, sc))
                print(f"  {cfg.label:32s} {sc}  ok")
            except Exception as e:                       # 失败入档，不静默跳过
                recs.append({"config": cfg.as_dict(), "scenario": sc,
                             "error": f"{type(e).__name__}: {e}"})
                print(f"  {cfg.label:32s} {sc}  ERROR {type(e).__name__}: {e}")

    ok = [r for r in recs if "error" not in r]
    summary = aggregate(ok)
    payload = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "elapsed_sec": round(time.time() - t0, 1),
        "cells": len(ok),
        "errors": len(recs) - len(ok),
        "design": {
            "domain": "mode == 'e3' 的 6 个配置 × S1–S7（共享能力是 S3–S7 构造的前提）",
            "shared_probe_pair": "owner 与 actor 对同一动作各发一次请求，四个方法共用",
            "b1": "低权账户 status < 400 即告警（Autorize 朴素模式）",
            "b2": "owner 成功且 actor 响应逐字节相同即告警（重放差分，无授权模型）",
            "b3": "b2 之上用框架 in-band share_log 压制；等价于已知测试期全部自建授权的理想差分",
            "ours": "MR-002 + v3（查询 SUT 授权自省面；不可读则弃权）",
        },
        "summary": summary,
        "records": recs,
    }
    (RESULTS / "baseline_compare.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== summary ===")
    for k, v in summary.items():
        if k.startswith("_"):
            continue
        print(f"{k:16s} TP={v['tp']:2d} FP={v['fp']:2d} FN={v['fn']:2d} "
              f"TN={v['tn']:2d} abstain={v['abstain']:2d} "
              f"prec={v['precision_on_claims']} "
              f"recall_decided={v['recall_on_decided']} "
              f"recall_all={v['recall_all_violations']} "
              f"cov={v['coverage']}")
    print(f"\n[done] {len(ok)}/{len(recs)} cells in {time.time()-t0:.1f}s")


if __name__ == "__main__":
    main()

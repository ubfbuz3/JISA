"""
主实验矩阵 runner
=================
编排 (应用配置 × 场景 × MR × 例外谓词变体 × GUI 模型变体) 的全因子矩阵。

★ 每一条记录都自带: 应用配置 / 场景构造 / MR 溯源 / 两次观测全文 /
  前置条件明细 / 动作级构造式真值 / 三项裁决(two versions + degrade-all) / 四项评级。
  → 任何一条数字都能被第三方从记录本身独立复核 (v5 §4.4 第 5 条)。

用法:
    python run_matrix.py            # 全矩阵
    python run_matrix.py --sanity   # 仅 M0 sanity
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "mrs"))
sys.path.insert(0, str(HERE / "target_api"))

from app import Config, make_server                       # noqa: E402
from engine import (TargetClient, setup_scenario, ground_truth,   # noqa: E402
                    action_path, SCENARIOS, SCENARIO_MRS, SCENARIO_INTENT)
from mstwi_mrs import mr002_evaluate, mr004_evaluate, describe_mrs   # noqa: E402
import boundary_aware as ba                               # noqa: E402

RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# --------------------------------------------------------------------------
# 因子
# --------------------------------------------------------------------------

CONFIGS: list[Config] = [
    Config("noe3", 0, "unlisted", "V-noE3-vuln0"),
    Config("noe3", 1, "unlisted", "V-noE3-vuln1"),
    Config("e3", 0, "unlisted", "V-E3-vuln0-unlisted"),
    Config("e3", 1, "unlisted", "V-E3-vuln1-unlisted"),
    Config("e3", 0, "listed", "V-E3-vuln0-listed"),
    Config("e3", 1, "listed", "V-E3-vuln1-listed"),
    # 授权自省面关闭 (第六轮 C8 要求: 检验 v3 在信息不足时是否诚实弃权)
    Config("e3", 0, "unlisted", "V-E3-vuln0-unlisted-nointro", introspection="off"),
    Config("e3", 1, "unlisted", "V-E3-vuln1-unlisted-nointro", introspection="off"),
]

# Block 3 消融: 逐步加上 MST-wi 的例外谓词。
# 语义 = "该例外谓词在当前场景下成立(即不构成例外) → 过滤器放行"。
# 实验中 B 被构造成非管理员、非 A 的下级 → 两个 flag 恒为 True。
PRECOND_VARIANTS: dict[str, dict] = {
    "raw":  {},                                                    # ≈ EvoMaster fault 306 层级 ℒ₁
    "e1":   {"not_admin": True},                                   # MR-E1
    "e1e2": {"not_admin": True, "not_supervisor": True},           # MR-E1E2 = MST-wi 的能力上限 ℒ₂
}

GUI_MODES = ("blind", "aware")
ADJUDICATORS = ("v1", "v2", "v3", "degrade_all")


# --------------------------------------------------------------------------
# 单次运行
# --------------------------------------------------------------------------

def run_one(cfg: Config, scenario: str, mr_id: str, pv: str, gm: str) -> dict:
    srv, state, port = make_server(cfg)
    try:
        client = TargetClient(port)
        setup = setup_scenario(client, cfg, scenario, state)
        method, path = action_path(setup)
        flags = PRECOND_VARIANTS[pv]

        if mr_id == "MR-002":
            body = {"content": "mutated-by-follower"} if setup.op == "write" else None
            mres = mr002_evaluate(client, setup.owner, setup.actor, method, path,
                                  precondition_flags=flags, gui_mode=gm, body=body)
            op = setup.op
        elif mr_id == "MR-004":
            mres = mr004_evaluate(client, setup.actor, setup.owner,
                                  setup.actor_doc, setup.target_doc,
                                  gui_mode=gm, precondition_flags=flags)
            op = "read"
        else:
            raise ValueError(mr_id)

        # 动作级构造式真值：以该 MR 的第二次观测为准
        gt = ground_truth(state, cfg, setup.actor, setup.target_doc, op,
                          mres["input2"]["status"])

        verdicts = {
            "v1": ba.adjudicate(mres, client, setup, version="v1").as_dict(),
            "v2": ba.adjudicate(mres, client, setup, version="v2").as_dict(),
            # v3: 探测数据源改为 SUT 授权自省面；面不可读时强制弃权
            "v3": ba.adjudicate(mres, client, setup, version="v3").as_dict(),
            "degrade_all": ba.adjudicate(mres, client, setup, degrade_all=True).as_dict(),
        }
        grades = {
            k: ba.grade_verdict(gt["truth"], mres["triggered"], verdicts[k]["verdict"])
            for k in ADJUDICATORS
        }

        return {
            "config": cfg.as_dict(),
            "scenario": scenario,
            "scenario_intent": SCENARIO_INTENT[scenario],
            "mr": mr_id,
            "precond_variant": pv,
            "gui_mode": gm,
            "action": {"actor": setup.actor, "method": method, "path": path, "op": op},
            "setup": setup.as_dict(),
            "share_log": client.share_log,
            "http_requests": client.request_count,
            "mr_result": mres,
            "truth": gt,
            "confusion": ba.classify_against_truth(gt["truth"], mres["triggered"]),
            "verdicts": verdicts,
            "grades": grades,
        }
    finally:
        srv.shutdown()
        srv.server_close()


# --------------------------------------------------------------------------
# 矩阵
# --------------------------------------------------------------------------

def iter_cases(sanity: bool = False):
    scenarios = ("S1", "S2") if sanity else SCENARIOS
    for cfg in CONFIGS:
        for scenario in scenarios:
            # S6/S7（预存共享）只有在应用具备对象级共享能力时才有意义
            if scenario in ("S6", "S7") and cfg.mode != "e3":
                continue
            for mr_id in SCENARIO_MRS[scenario]:
                for pv in PRECOND_VARIANTS:
                    for gm in GUI_MODES:
                        yield cfg, scenario, mr_id, pv, gm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sanity", action="store_true", help="仅跑 M0 场景 S1/S2")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    cases = list(iter_cases(a.sanity))
    out = Path(a.out) if a.out else RESULTS / (
        "sanity_matrix.jsonl" if a.sanity else "raw_matrix.jsonl")

    print(f"[run] {'SANITY' if a.sanity else 'FULL'}  cases={len(cases)}  → {out.name}")
    t0 = time.time()
    recs = []
    with out.open("w", encoding="utf-8") as fh:
        for i, (cfg, scenario, mr_id, pv, gm) in enumerate(cases, 1):
            try:
                rec = run_one(cfg, scenario, mr_id, pv, gm)
            except Exception as e:                       # 失败也如实入档
                rec = {"config": cfg.as_dict(), "scenario": scenario, "mr": mr_id,
                       "precond_variant": pv, "gui_mode": gm,
                       "error": f"{type(e).__name__}: {e}"}
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            recs.append(rec)
            if i % 50 == 0 or i == len(cases):
                print(f"  ... {i}/{len(cases)}  ({time.time()-t0:.1f}s)")

    errs = [r for r in recs if "error" in r]
    meta = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "sanity" if a.sanity else "full",
        "cases": len(cases),
        "completed": len(cases) - len(errs),
        "errors": len(errs),
        "elapsed_sec": round(time.time() - t0, 2),
        "mr_provenance": describe_mrs(),
        "configs": [c.as_dict() for c in CONFIGS],
        "precond_variants": PRECOND_VARIANTS,
        "gui_modes": list(GUI_MODES),
        "notes": [
            "MR 为语义移植, 非 MST-wi 原生引擎（本机无 Maven）→ 见 mstwi_mrs.py 表头声明",
            "真值为动作级构造式真值: BOLA ⟺ 应用允许了本不该允许的访问",
            "E3 探测数据源为测试框架主动执行的共享操作记录（构造式真值，非政策推断）",
            "S6/S7 的授权为**带外种入**（app.seed_share 直接写服务端授权表），"
            "框架侧 share_log 为空 → 用于刻画修正机制的有效范围（第五轮硬条件 A1）",
        ],
    }
    (RESULTS / ("run_meta_sanity.json" if a.sanity else "run_meta.json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    if errs:
        print(f"[!] {len(errs)} 条运行出错; 首条: {errs[0].get('error')}")
    print(f"[done] {meta['completed']}/{meta['cases']} in {meta['elapsed_sec']}s → {out}")


if __name__ == "__main__":
    main()

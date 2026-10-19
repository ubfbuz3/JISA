"""回归测试：确认 ingest_cve_pair.validate() 真能拒绝被扰动的配对记录。

扰动都是在**内存中的副本**上做的，不触碰 experiments/ 下的原始 JSON。

四种扰动对应此前的审计发现：
  1. 删掉脆弱版的 own_comment 对照        -> 必须报"缺少必需标签"
  2. 把恢复成功改为 False                 -> 必须报"恢复未成功"
  3. 复读正文改回原文但保留 Y=True/TP      -> 必须报 Y/分类与复算不符
  4. 把现有 own_comment 状态改成 403       -> 必须报对照偏离
外加：未扰动记录必须干净通过。

用法：python test_cve_pair_validation.py
"""
import copy
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import ingest_cve_pair as icp  # noqa: E402

SRC = icp.SRC


def load():
    doc = json.loads(SRC.read_text(encoding="utf-8"))
    return {r["version"]: r for r in doc["runs"]}


def find(run, label):
    return next(p for p in run["probes"] if p["label"] == label)


def case_untouched(runs):
    return [icp.validate(runs[v]) for v in ("1.20.5", "1.20.6")]


def case_drop_control(runs):
    r = copy.deepcopy(runs)
    r["1.20.5"]["probes"] = [p for p in r["1.20.5"]["probes"]
                             if p["label"] != "own_comment"]
    return [icp.validate(r[v]) for v in ("1.20.5", "1.20.6") if v in r]


def case_restore_failed(runs):
    r = copy.deepcopy(runs)
    r["1.20.5"]["restore"]["restored"] = False
    return [icp.validate(r["1.20.5"])]


def case_body_reverted(runs):
    """拥有者复读回到原文，但缓存字段仍写 Y=True / true_positive。"""
    r = copy.deepcopy(runs)
    run = r["1.20.5"]
    run["state"]["body"] = run["ids"]["original_body"]
    run["state"]["contains_bob_mark"] = False
    run["state"]["equals_original"] = True
    # 缓存字段故意不动：Y_allow=True, category=true_positive
    return [icp.validate(run)]


def case_control_403(runs):
    r = copy.deepcopy(runs)
    find(r["1.20.5"], "own_comment")["status"] = 403
    return [icp.validate(r["1.20.5"])]


def case_duplicate_label(runs):
    r = copy.deepcopy(runs)
    run = r["1.20.5"]
    run["probes"].append(copy.deepcopy(find(run, "absent_id")))
    return [icp.validate(run)]


def case_extra_label(runs):
    r = copy.deepcopy(runs)
    run = r["1.20.5"]
    run["probes"].append({"label": "surprise_probe", "status": 200})
    return [icp.validate(run)]


def case_ledger_mismatch(runs):
    r = copy.deepcopy(runs)
    r["1.20.5"]["main"]["E_object"] = "allow"   # 与台账 deny 冲突
    return [icp.validate(r["1.20.5"])]


def main() -> int:
    runs = load()

    cases = [
        ("未扰动记录", case_untouched, True),
        ("删除脆弱版 own_comment 对照", case_drop_control, False),
        ("恢复改为失败", case_restore_failed, False),
        ("复读正文回退但保留 Y=True/TP", case_body_reverted, False),
        ("own_comment 改成 403", case_control_403, False),
        ("标签重复", case_duplicate_label, False),
        ("多出未登记标签", case_extra_label, False),
        ("E 与台账冲突", case_ledger_mismatch, False),
    ]

    failures = 0
    for name, fn, should_pass in cases:
        problems = fn(runs)
        n = sum(len(p) for p in problems)
        ok = (n == 0) if should_pass else (n > 0)
        print(f"  [{'ok' if ok else 'FAIL'}] {name:32s} 问题数={n}")
        if not ok:
            failures += 1
            for group in problems:
                for line in group:
                    print("        " + line)

    if failures:
        print(f"\n[FAIL] {failures} 个用例不符合预期")
        return 1
    print(f"\n[ok] {len(cases)} 个用例全部符合预期")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

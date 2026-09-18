"""
Boundary-aware MR Execution · E3 探测与三级裁决
==============================================
对应 研究方案_v5.md §2.4 的三步:

  步骤 1  执行 MR, 未触发 → pass
  步骤 2  触发 → **探测 E3**: 该对象自创建以来是否被显式共享/委派?
          (数据源: TargetClient.share_log —— 测试框架**主动执行**共享时写下的记录,
           构造式真值, 非政策推断)
  步骤 3  E3 存在 → indeterminate + 产出见证; E3 不存在 → violation-proven

两个版本 (用于 Block 4 的简洁性检查):
  v1  仅做**存在性**探测: 对象有任意共享记录即降级
  v2  存在性 + **权限层级匹配**: 共享记录的 permission 必须覆盖本次触发的操作类型
       (read 仅覆盖读; write 覆盖读与写)
      —— v2 用于消除 S5 类"读合法/写越权"的误降级代价

三级裁决的语义边界（必须写进论文）:
  pass               : MR 未触发。可能是 TN, 也可能是 FN —— 裁决本身不区分。
  violation-proven   : MR 触发, 且该对象**不存在**可覆盖本次操作的 E3 授权
                       → 排除了唯一已知的合法例外解释。
  indeterminate      : MR 触发, 且该对象**存在**可覆盖本次操作的 E3 授权
                       → 观测与"合法共享"假设一致, 无法在 MR 范式内排除, 诚实弃权。
"""

from __future__ import annotations

from dataclasses import dataclass, asdict

VERDICTS = ("pass", "violation-proven", "indeterminate")

# 操作被共享权限覆盖的关系
_OP_COVERED_BY = {"read": ("read", "write"), "write": ("write",)}


@dataclass
class Verdict:
    verdict: str
    reason: str
    witness: dict | None = None

    def as_dict(self):
        return asdict(self)


def probe_e3(client, doc_id: str, op: str, version: str = "v1") -> tuple[bool, list[dict]]:
    """v1/v2 的 E3 探测。**数据源 = 测试框架自己的共享操作记录（share_log）**。

    ⚠️ 这个数据源是"测试者对自己动作的记忆"，不是被测系统的授权状态。
    第六轮追问已确认：它就是 S6 失效的原因。v3 改为查询 SUT 授权面（见 probe_e3_sut）。
    """
    recs = client.shares_of(doc_id)
    if version == "v1":
        # 存在性: 有任意共享即视为存在 E3
        return (len(recs) > 0), recs
    if version == "v2":
        # 存在性 + 权限层级匹配
        covering = [r for r in recs if r["permission"] in _OP_COVERED_BY.get(op, ())]
        return (len(covering) > 0), covering
    raise ValueError("version must be 'v1' or 'v2'")


def probe_e3_sut(client, owner: str, actor: str, doc_id: str, op: str
                 ) -> tuple[str, list[dict]]:
    """v3 的 E3 探测。**数据源 = 被测系统自身的授权自省面**。

    以对象拥有者身份查询 `GET /doc/{id}/shares`（应用自报"该对象授权给了谁"），
    再判断其中是否存在**对当前 actor 生效、且权限覆盖本次操作**的授权。

    返回 (state, records)，state ∈ {"covering", "none", "unavailable"}：
      covering     存在可覆盖本次操作的授权 ⇒ 观测与"合法授权"假设一致 ⇒ 弃权
      none         授权面可读且其中无可覆盖授权 ⇒ 唯一已知合法解释被排除 ⇒ 可确证
      unavailable  应用**未暴露**授权自省面（404/403）⇒ **无法排除不透明授权 ⇒ 必须弃权**
                   —— 这一支是关键：它使修正在信息不足时保持诚实，而不是伪造确证。
    """
    o = client.request(owner, "GET", f"/doc/{doc_id}/shares")
    if o.status != 200:
        return "unavailable", []
    body = o.body if isinstance(o.body, dict) else {}
    recs = body.get("shares") or []
    mine = [r for r in recs if r.get("grantee") == actor]
    covering = [r for r in mine if r.get("permission") in _OP_COVERED_BY.get(op, ())]
    return ("covering" if covering else "none"), (covering or mine)


def adjudicate(mr_result: dict, client, setup, version: str = "v1",
               degrade_all: bool = False) -> Verdict:
    """把 MR 的触发/未触发升级为三级裁决。

    version="v1"/"v2" —— 探测数据源 = 框架账本（share_log）
    version="v3"      —— 探测数据源 = **SUT 授权自省面**；面不可读时强制弃权
    degrade_all=True 时退化为"凡触发即降级"的对照方案 (Block 4 的消融 2)。
    """
    if not mr_result.get("triggered"):
        return Verdict("pass", "MR 未触发，无需裁决")

    if degrade_all:
        return Verdict("indeterminate",
                       "退化方案：凡触发即降级（不区分对象）",
                       witness={"mode": "degrade-all"})

    if version == "v3":
        state, recs = probe_e3_sut(client, setup.owner, setup.actor,
                                   setup.target_doc, setup.op)
        if state == "unavailable":
            return Verdict(
                "indeterminate",
                f"应用未暴露授权自省面（GET /doc/{setup.target_doc}/shares 不可读），"
                f"无法排除不透明的对象级授权 —— 按可容许条件必须弃权，不得升级为确证",
                witness={"probe_version": "v3", "sut_introspection": "unavailable",
                         "op": setup.op, "doc_id": setup.target_doc})
        if state == "covering":
            return Verdict(
                "indeterminate",
                f"SUT 授权面显示对象 {setup.target_doc} 对 {setup.actor} 存在可覆盖 "
                f"'{setup.op}' 的授权，观测与合法授权假设一致",
                witness={"share_records": recs, "probe_version": "v3",
                         "sut_introspection": "readable",
                         "op": setup.op, "doc_id": setup.target_doc})
        return Verdict(
            "violation-proven",
            f"SUT 授权面可读，且其中**不存在**对 {setup.actor} 可覆盖 '{setup.op}' 的授权，"
            f"唯一已知的合法例外解释被排除",
            witness={"share_records": [], "probe_version": "v3",
                     "sut_introspection": "readable",
                     "op": setup.op, "doc_id": setup.target_doc})

    exists, recs = probe_e3(client, setup.target_doc, setup.op, version=version)
    if exists:
        return Verdict(
            "indeterminate",
            f"对象 {setup.target_doc} 存在可覆盖 '{setup.op}' 的显式授权记录，"
            f"观测与合法共享假设一致，MR 范式内无法排除",
            witness={"share_records": recs, "probe_version": version,
                     "op": setup.op, "doc_id": setup.target_doc})
    return Verdict(
        "violation-proven",
        f"对象 {setup.target_doc} 不存在可覆盖 '{setup.op}' 的显式授权记录，"
        f"唯一已知的合法例外解释被排除",
        witness={"share_records": [], "probe_version": version,
                 "op": setup.op, "doc_id": setup.target_doc})


def classify_against_truth(truth: str, triggered: bool) -> str:
    """相对预先声明真值的混淆矩阵归类。"""
    if truth == "bola":
        return "TP" if triggered else "FN"
    return "FP" if triggered else "TN"


def grade_verdict(truth: str, triggered: bool, verdict: str) -> dict:
    """裁决质量的四项标记（用于恢复率/检测力/代价的统计）。"""
    return {
        # 原始 MR 的误报
        "raw_false_alarm": bool(truth == "normal" and triggered),
        # 恢复: 本该是正常, MR 误报, 而裁决正确降级为 indeterminate
        "recovered": bool(truth == "normal" and triggered and verdict == "indeterminate"),
        # 检测力保持: 真 BOLA, MR 触发, 裁决给出 violation-proven
        "detection_kept": bool(truth == "bola" and triggered
                               and verdict == "violation-proven"),
        # 代价: 真 BOLA 却被降级为 indeterminate
        "costly_downgrade": bool(truth == "bola" and triggered
                                 and verdict == "indeterminate"),
        # 漏报: 真 BOLA 但 MR 根本没触发
        "missed": bool(truth == "bola" and not triggered),
    }

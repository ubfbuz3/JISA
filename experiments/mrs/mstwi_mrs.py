"""
MST-wi 授权类 MR · 忠实移植的最小执行器
=======================================
来源: MST-wi (Metamorphic Security Testing for Web Systems, IEEE TSE 2023) 复现包
      Zenodo 10.5281/zenodo.7702754 → `Catalog of MRs.pdf` (129 页 MR 源码)
      本地提取文本: 01_文献调研/mstwi_artifact/catalog_text.txt

★★★ 诚实声明 (必须写入论文 Limitations) ★★★
    本文件是**语义移植**, 不是 MST-wi 原生引擎。
    原因: 原生引擎需要 Maven + chromedriver + Selenium + 被测系统的 OVA 虚拟机,
          本机 Maven 缺失, 无法构建 (见 refine-logs/EXPERIMENT_PLAN.md "Environment Constraints")。
    移植依据: 下面对每条 MR 给出 catalog 行号与**逐行源码片段**,
              第三方可据行号直接比对, 判定逻辑不做任何"改进"或"放宽"。
    已知的移植差异 (全部显式标注, 不隐藏):
      D1. MST-wi 的 GUI 可达性模型由真实浏览器爬取得到; 本实验用被测系统自身的
          列举端点 `GET /doc` 作为代理 (受控系统无 GUI)。为此实现两个代理语义变体
          (gui_blind / gui_aware) 并双向报告 —— 见 Experiments/mrs 说明与结果文件。
      D2. MST-wi 的 `parameterValuesUsedByOtherUsers` 依赖多用户历史输入语料;
          本实验直接以"另一用户实际拥有的对象 ID"充当该值 (语义等价, 来源更确定)。
      D3. 未移植 MST-wi 的 `notTried(...)` 去重优化 (它只影响运行时长, 不影响判定)。

MR 清单:
    MR-002  CWE_266_267_268_269_285_522_529_862_863_OTG_AUTHZ_002   catalog line 579
    MR-004  CWE_15_639_OTG_AUTHZ_004                                catalog line 154
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any


# ==========================================================================
# 0. 观测与判定基元
# ==========================================================================

@dataclass
class Observation:
    """一次 HTTP 交互的可归档观测。"""
    status: int
    body: Any
    headers: dict[str, str] = field(default_factory=dict)
    url: str = ""

    # --- MST-wi 谓词 isError(Output) -------------------------------------
    @property
    def is_error(self) -> bool:
        """catalog 中 `isError(Output(...))` 的代理: 返回错误页/错误响应。

        移植说明: MST-wi 判定的是"是否呈现错误页"。本受控系统以 4xx/5xx
        作为其等价物 (403 是它最关心的"拒绝访问"信号)。
        """
        return self.status >= 400

    # --- MST-wi 谓词 equals(Output, Output) ------------------------------
    def normalized(self) -> str:
        """去除会话级噪音后的可比指纹。

        预注册规则 (v5 §4.4 第 5 条; 先于实验确定, 不得事后调整):
          1. 只保留 status + body;
          2. body 的 JSON key 递归排序;
          3. 去除显式会话噪音头 (X-Doc-Hash 等随机值), 不参与比较;
          4. 不比较 Content-Length / Date / Server。
        注意: owner 字段**保留** —— 它是被测系统的真实输出, 不属于噪音。
        """
        return json.dumps({"status": self.status, "body": self.body},
                          ensure_ascii=False, sort_keys=True)

    def equals(self, other: "Observation") -> bool:
        return self.normalized() == other.normalized()

    def as_dict(self) -> dict:
        return {"status": self.status, "body": self.body, "url": self.url}


# ==========================================================================
# 1. MR-004 · CWE_15_639_OTG_AUTHZ_004          （BOLA 的 CWE 标准定义）
# ==========================================================================
#
# catalog line 154-175 原文:
#
#   MR CWE_15_639_OTG_AUTHZ_004 {
#    {
#   for ( Action action : Input(1).actions() ){                                //(1)
#     for ( var par=0; par < action.getParameters().size() && notTried( action.getUser(),
#           action.url); par++) {                                              //(2)
#
#        for ( usedValue : parameterValuesUsedByOtherUsers(action, par) ){     //(3)
#     var pos = action.getPosition();                                     //(4)
#
#    IMPLIES(
#           CREATE ( Input(2), Input(1) ) &&                               //(5)
#           Input(2).actions().get(pos).setParameterValue(par, usedValue) //(6)
#     ,
#              OR(                                                              //(7)
#     Output(Input(2),pos).isError(),
#     userCanRetrieveContent( action.user, Output(Input(2),pos) ))
#    );//end-IMPLIES
#        }//end-for
#       }//end-for
#      }//end-for
#     }
#    }//end-MR
#
# 语义: 把请求参数替换为"其他用户使用的值"(对我们的场景 = 另一用户拥有的对象 ID),
#       期望得到 错误 或 该用户本就能取到的内容。两者皆不成立 → 违反(疑似 BOLA)。
# ==========================================================================

MR004_META = {
    "id": "MR-004",
    "catalog_id": "MR CWE_15_639_OTG_AUTHZ_004",
    "catalog_line": 154,
    "cwe": "CWE-639 (Authorization Bypass Through User-Controlled Key) — BOLA 的标准 CWE 定义",
    "semantics": "参数替换为其他用户使用的值; 期望 isError ∨ userCanRetrieveContent",
    "violation_condition": "NOT isError(Out2) AND NOT userCanRetrieveContent(user, Out2)",
    "gui_predicates_used": ["userCanRetrieveContent"],
}


def mr004_evaluate(client, actor: str, other: str, doc_own: str, doc_other: str,
                   gui_mode: str = "blind", precondition_flags: dict | None = None) -> dict:
    """执行 MR-004。

    参数
    ----
    actor             : 发起请求的用户 (对应源码中的 action.user), 实验中为"被检查的访问者" B
    other             : 参数值的来源用户 (对应 parameterValuesUsedByOtherUsers), 实验中为 A
    doc_own           : actor 自己的对象 ID (Input(1) 的基线参数值)
    doc_other         : other 拥有的对象 ID —— **Input(2) 替换后的参数值**(来自 line 160)
    gui_mode          : 'blind'  → userCanRetrieveContent 恒 False (仅凭 API 观测)
                        'aware'  → 用 actor 的列举端点 GET /doc 建模 GUI 可达性
    """
    flags = precondition_flags or {}

    # (1)(2)(4) Input(1): actor 用**自己的**参数值访问 —— 基线
    out1 = client.request(actor, "GET", f"/doc/{doc_own}")

    # (5)(6) CREATE(Input(2), Input(1)) + setParameterValue(par, usedValue)
    #        —— 同序列, 但参数换成 other 用户的值
    out2 = client.request(actor, "GET", f"/doc/{doc_other}")

    # (7) OR( isError(Out2), userCanRetrieveContent(action.user, Out2) )
    if gui_mode == "blind":
        # 保守代理: 仅凭 API 观测, 不假设任何 GUI 可达性
        can_retrieve = False
    elif gui_mode == "aware":
        # 用该用户自己的列举端点建模 "GUI 中可见的内容"
        listing = client.request(actor, "GET", "/doc")
        items = listing.body.get("items", []) if isinstance(listing.body, dict) else []
        ids = {i.get("id") for i in items}
        can_retrieve = doc_other in ids
    else:
        raise ValueError("gui_mode must be 'blind' or 'aware'")

    or_satisfied = out2.is_error or can_retrieve
    triggered = (not or_satisfied)                       # IMPLIES 为假 = 违反
    triggered = bool(triggered and _preds_hold(flags))

    return {
        "mr": MR004_META["id"],
        "catalog_line": MR004_META["catalog_line"],
        "actor": actor, "other": other,
        "input1": out1.as_dict(), "input2": out2.as_dict(),
        "isError_out2": out2.is_error,
        "userCanRetrieveContent": can_retrieve,
        "gui_mode": gui_mode,
        "precondition_flags": flags,
        "triggered": triggered,
    }


# ==========================================================================
# 2. MR-002 · CWE_266_267_268_269_285_522_529_862_863_OTG_AUTHZ_002
# ==========================================================================
#
# catalog line 579-594 原文:
#
#    MR CWE_266_267_268_269_285_522_529_862_863_OTG_AUTHZ_002 {
#    {
#      for ( Action action : Input(1).actions() ){                                        //(1)
#
#       IMPLIES(
#         !isSupervisorOf(User(), action.user) &&                   //(2)
#            cannotReachThroughGUI( User(), action.url )&&                     //(3)
#            CREATE( Input(2), changeCredentials(Input(1), User()) )                  //(4)
#      ,
#         OR(                                                                         //(5)
#      isError(Output(Input(1),action.position)),
#      NOT( Output(Input(1),action.position).equals(Output(Input(2),action.position)))
#
#       )); //end-IMPLIES
#     } //end-for
#      }} //end-MR
#
# 语义: 取原用户的动作序列 Input(1); 在**换凭证**后重放为 Input(2)。
#       期望: 原序列本来就报错, 或换人之后输出不同。
#       若原序列成功、且换人后输出**一模一样** → 说明身份对结果无影响 → 违反。
#
# ★ 这是 E3 盲点最干净的一条: 它的判定里**没有任何对象级谓词**。
#   (2) 是 E2 主体间关系, (3) 是 GUI 可达性 —— 恰好是 MST-wi 表达力的两个边界。
# ==========================================================================

MR002_META = {
    "id": "MR-002",
    "catalog_id": "MR CWE_266_267_268_269_285_522_529_862_863_OTG_AUTHZ_002",
    "catalog_line": 579,
    "cwe": "CWE-266/267/268/269/285/522/529/862/863 (含 improper authorization 族)",
    "semantics": "changeCredentials 后重放; 期望 isError(Out1) ∨ NOT(Out1.equals(Out2))",
    "violation_condition": "NOT isError(Out1) AND Out1.equals(Out2)",
    "gui_predicates_used": ["cannotReachThroughGUI"],
    "e2_predicate_used": "!isSupervisorOf(User(), action.user)",
}


def mr002_evaluate(client, owner: str, follower: str, method: str, path: str,
                   precondition_flags: dict | None = None,
                   gui_mode: str = "aware",
                   body: dict | None = None) -> dict:
    """执行 MR-002。

    owner    : 原用户 (源码中的 action.user), 实验中为对象拥有者 A
    follower : changeCredentials 之后执行 Input(2) 的用户 (源码中的 User()),
               实验中为"访问者" B
    method/path : Input(1) 中 action.position 处的那个动作
    gui_mode : 'aware' (忠实 MST-wi) → 用 follower 的列举端点建模 cannotReachThroughGUI
               'blind'               → 保守假设 GUI 不可达 (谓词恒真, 前置条件恒成立)
    body     : 写操作的动作体 (PUT 时使用)

    移植说明 D1: catalog (3) 的 `cannotReachThroughGUI(User(), action.url)` 需要 GUI 爬取。
                 此处用 follower 自己的列举端点建模: 若该 URL 对应的对象出现在
                 follower 的 `GET /doc` 列表里 → GUI 可达 → precondition 为假 (MR 不适用)。
    """
    flags = precondition_flags or {}

    # (1) Input(1): 原用户执行该动作
    out1 = client.request(owner, method, path, body)

    # (2) !isSupervisorOf(User(), action.user)
    is_sup = client.is_supervisor_of(follower, owner)      # follower 是 owner 的上级?
    not_sup = not is_sup

    # (3) cannotReachThroughGUI(User(), action.url)
    target_id = path.rstrip("/").split("/")[-1]
    if gui_mode == "blind":
        gui_reachable = False
        cannot_reach = True
    elif gui_mode == "aware":
        listing = client.request(follower, "GET", "/doc")
        items = listing.body.get("items", []) if isinstance(listing.body, dict) else []
        gui_reachable = any(i.get("id") == target_id for i in items)
        cannot_reach = not gui_reachable
    else:
        raise ValueError("gui_mode must be 'blind' or 'aware'")

    # (4) CREATE(Input(2), changeCredentials(Input(1), User()))
    out2 = client.request(follower, method, path, body)

    precondition_met = not_sup and cannot_reach and _preds_hold(flags)

    # (5) OR( isError(Out1), NOT(Out1.equals(Out2)) ) —— 取反即违反
    implies_false = (not out1.is_error) and out1.equals(out2)
    triggered = bool(precondition_met and implies_false)

    return {
        "mr": MR002_META["id"],
        "catalog_line": MR002_META["catalog_line"],
        "owner": owner, "follower": follower, "method": method, "path": path,
        "input1": out1.as_dict(), "input2": out2.as_dict(),
        "ph_notSupervisorOf": not_sup,
        "ph_cannotReachThroughGUI": cannot_reach,
        "ph_gui_reachable_for_follower": gui_reachable,
        "gui_mode": gui_mode,
        "precondition_met": precondition_met,
        "isError_out1": out1.is_error,
        "out1_equals_out2": out1.equals(out2),
        "precondition_flags": flags,
        "triggered": triggered,
    }


# ==========================================================================
# 3. E1 / E2 例外谓词（Block 3 消融：复现 MST-wi 的例外处理做法）
# ==========================================================================

@dataclass
class ExceptionPredicates:
    """MST-wi DSL 中**全部**可用于授权例外的谓词（穷举自 catalog，见 v5 §1.2）。

    E1 主体属性    : isAdmin(user)
    E2 主体间关系  : isSupervisorOf(user1, user2)

    ★ 关键: 这两个类别的元数分别是 1(主体) 和 2(主体,主体)。
      **没有任何谓词的元数是 2(主体,对象)** —— 即不存在 E3 谓词。
      本实验把 B 构造成"非管理员、非 A 的下级", 于是这两个谓词**恒为真**,
      从而构造性地展示: E1/E2 过滤对 E3 场景不可能起作用。
    """
    use_e1_admin: bool = False
    use_e2_supervisor: bool = False

    def as_dict(self) -> dict:
        return {"use_e1_admin": self.use_e1_admin,
                "use_e2_supervisor": self.use_e2_supervisor}

    def label(self) -> str:
        if self.use_e1_admin and self.use_e2_supervisor:
            return "MR-E1E2"          # = MST-wi 的实际能力上限 (ℒ₂)
        if self.use_e1_admin:
            return "MR-E1"
        return "MR-raw"               # = 无例外谓词 (≈ EvoMaster fault 306 的层级 ℒ₁)


def _preds_hold(flags: dict) -> bool:
    """flags 中的例外谓词是否全部成立（即不构成例外）。

    flags 由实验场景提供, 语义为: "该例外谓词在当前场景下是否成立(=不构成例外)"。
    实验中 B 非 admin、非 supervisor → 两个 flag 均为 True → 过滤器放行 → MR 照常触发。
    """
    return all(bool(v) for v in flags.values()) if flags else True


# ==========================================================================
# 4. 注册表
# ==========================================================================

MR_REGISTRY = {
    "MR-002": {"meta": MR002_META, "fn": mr002_evaluate},
    "MR-004": {"meta": MR004_META, "fn": mr004_evaluate},
}


def describe_mrs() -> list[dict]:
    """供论文附录使用的 MR 溯源表。"""
    out = []
    for k, v in MR_REGISTRY.items():
        m = dict(v["meta"])
        m["local_impl"] = "experiments/mrs/mstwi_mrs.py"
        out.append(m)
    return out


if __name__ == "__main__":
    print(json.dumps(describe_mrs(), ensure_ascii=False, indent=2))

"""
实验执行引擎 · 目标客户端 + 场景构造
====================================
职责:
  1. TargetClient —— 以指定用户身份访问被测系统, 返回可归档 Observation
  2. setup_scenario —— 按 S1..S5 构造受控场景, 并给出**构造式真值**
  3. share_log —— 测试框架**主动执行**的共享操作记录

★ share_log 是 v5 论证"不循环"的关键:
  E3 探测读取的是**我们自己调用共享 API 时写下的记录**,
  而不是"从实现制品推断出的政策"。因此它是构造式真值 (constructive ground truth),
  不是又一层需要验证的假设。
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from mstwi_mrs import Observation

# 组织关系 (E2 的判定来源)。必须与 target_api/app.py 中 AppState.SUPERVISOR_OF 保持一致。
# 实验设计: B **不是** A 的下级, 也不是任何人的上级 → MR-002 的 !isSupervisorOf 恒为真。
SUPERVISOR_OF = {"C": ["A"], "A": [], "B": []}

PASSWORDS = {"A": "pw-A", "B": "pw-B", "C": "pw-C"}


# --------------------------------------------------------------------------
# 客户端
# --------------------------------------------------------------------------

class TargetClient:
    def __init__(self, port: int, timeout: float = 10.0):
        self.base = f"http://127.0.0.1:{port}"
        self.timeout = timeout
        # 显式绕过系统代理 —— 本地回环不应走代理
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self._tokens: dict[str, str] = {}
        self.request_count = 0
        # ★ 构造式真值: 我们主动做的共享操作
        self.share_log: list[dict] = []

    # ---- 底层 -------------------------------------------------------------

    def _raw(self, method: str, path: str, token: str | None, body: dict | None):
        url = self.base + path
        data = None
        headers = {"Accept": "application/json", "Connection": "close"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        self.request_count += 1
        try:
            with self._opener.open(req, timeout=self.timeout) as r:
                raw = r.read().decode("utf-8")
                return r.status, raw
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8")
        except Exception as e:                       # 连接层错误也如实记为观测
            return 599, json.dumps({"error": "transport", "detail": str(e)})

    # ---- 认证 -------------------------------------------------------------

    def login(self, user: str) -> str:
        if user in self._tokens:
            return self._tokens[user]
        code, raw = self._raw("POST", "/auth/login", None,
                              {"username": user, "password": PASSWORDS[user]})
        if code != 200:
            raise RuntimeError(f"login failed for {user}: {code} {raw}")
        tok = json.loads(raw)["token"]
        self._tokens[user] = tok
        return tok

    # ---- 观测 -------------------------------------------------------------

    def request(self, user: str, method: str, path: str, body: dict | None = None) -> Observation:
        tok = self.login(user)
        code, raw = self._raw(method, path, tok, body)
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"_raw": raw}
        return Observation(status=code, body=parsed, url=path)

    # ---- 组织关系 (E2) ----------------------------------------------------

    @staticmethod
    def is_supervisor_of(a: str, b: str) -> bool:
        return b in SUPERVISOR_OF.get(a, [])

    # ---- 对象与共享 -------------------------------------------------------

    def create_doc(self, user: str, title: str, content: str) -> str:
        o = self.request(user, "POST", "/doc", {"title": title, "content": content})
        if o.status != 200:
            raise RuntimeError(f"create_doc failed: {o.status} {o.body}")
        return o.body["id"]

    def share(self, owner: str, doc_id: str, grantee: str, permission: str = "read") -> dict:
        """★ 由测试框架主动执行共享, 并写入 share_log（构造式真值）。"""
        o = self.request(owner, "POST", f"/doc/{doc_id}/share",
                         {"grantee": grantee, "permission": permission})
        rec = {"doc_id": doc_id, "grantee": grantee, "permission": permission,
               "by": owner, "status": o.status, "resp": o.body}
        self.share_log.append(rec)
        return rec

    # ---- 构造式真值查询 ---------------------------------------------------

    def shares_of(self, doc_id: str) -> list[dict]:
        """E3 探测的数据源 = 我们自己的共享操作记录（非查询应用内部状态）。"""
        return [s for s in self.share_log if s["doc_id"] == doc_id and s["status"] == 200]


# --------------------------------------------------------------------------
# 场景构造
# --------------------------------------------------------------------------

# 场景清单（来自 研究方案_v5.md §2.4 / EXPERIMENT_PLAN.md Block 2）
#
#   场景   设计意图                                     访问者动作真值(在正确应用上)
#   S1     无共享的阴性对照 (基线 FP 应为 0)             应被拒
#   S2     无共享 + 访问者访问他人对象                  应被拒
#   S3     拥有者**显式共享**给访问者, 访问者访问该对象    **应被允许** ← E3 例外
#   S4     存在共享 a1, 但访问者访问**未共享**的 a2       应被拒
#   S5     共享 a1 为**只读**, 访问者对其发起**写**       应被拒 (E3 权限层级不覆盖)
#   ────── 以下为第五轮追问后新增（针对「共享全部由框架自建」这一缺口）──────
#   S6     **预存**共享（带外种入，框架无记录）, 访问者访问该对象  应被允许 ← 同 S3 但授权不可观测
#   S7     **预存**共享（带外种入）, 但访问者访问**未共享**的另一对象 应被拒 ← 同 S4 但授权不可观测
#
# ★ S6/S7 的判别价值: S3/S4 的授权是**测试框架自己创建的**(client.share → 记入 share_log),
#   因此 Boundary-aware 探测天然能看到它。S6/S7 把授权改成**带外种入**(管理员配置/历史委派/第三方共享),
#   框架侧 share_log 为空 → 探测机制在此失效。这一对场景刻画的是**修正机制的有效范围**。
#
# ★ 真值不按场景硬编码, 而由授权模型在动作级计算（见 ground_truth）。
#   理由: 同一个场景对 MR-002 与 MR-004 触发的动作不同(写 vs 读),
#         真值必须跟着**实际动作**走, 否则会把 FN/FP 记反。
SCENARIOS = ("S1", "S2", "S3", "S4", "S5", "S6", "S7")

# 需要应用具备对象级共享能力才有意义（S3–S7）；S1/S2 是无共享对照
E3_SCENARIOS = ("S3", "S4", "S5", "S6", "S7")

SCENARIO_INTENT = {
    "S1": "无共享阴性对照：跨用户访问同一对象，应用应正确拒绝",
    "S2": "无共享 + 访问他人对象 → 越权",
    "S3": "拥有者显式共享给访问者，访问者访问该对象 → 合法（E3 例外，授权由框架创建、可观测）",
    "S4": "存在共享 a1，但访问未共享的 a2 → 越权",
    "S5": "共享为只读，访问者发起写 → 写越权（E3 权限层级不覆盖）",
    "S6": "**预存**共享（带外种入，框架无记录），访问者访问该对象 → 合法，但授权对框架不可观测",
    "S7": "**预存**共享（带外种入），访问者访问未共享的另一对象 → 越权（检验检测力是否受损）",
}

# 哪些 MR 在哪些场景上有意义（S5 是写越权，只有 MR-002 会发出写请求）
SCENARIO_MRS = {
    "S1": ("MR-002", "MR-004"),
    "S2": ("MR-002", "MR-004"),
    "S3": ("MR-002", "MR-004"),
    "S4": ("MR-002", "MR-004"),
    "S5": ("MR-002",),
    "S6": ("MR-002", "MR-004"),
    "S7": ("MR-002", "MR-004"),
}


@dataclass
class ScenarioSetup:
    scenario: str
    intent: str
    owner: str
    actor: str
    target_doc: str          # 被访问的对象
    actor_doc: str           # 访问者自己的对象 (供 MR-004 的 Input(1) 用)
    unshared_doc: str        # 拥有者的另一个对象 (供核查用)
    op: str = "read"         # read | write —— MR-002 发出的操作类型
    shares: list[dict] = field(default_factory=list)
    # 授权来源: none | framework（框架调用共享 API 创建）| out_of_band（带外种入，框架不可观测）
    share_origin: str = "none"

    def as_dict(self):
        return {"scenario": self.scenario, "intent": self.intent, "owner": self.owner,
                "actor": self.actor, "target_doc": self.target_doc,
                "op": self.op, "shares": self.shares,
                "share_origin": self.share_origin}


def setup_scenario(client: TargetClient, cfg, scenario: str, state=None) -> ScenarioSetup:
    """构造场景。所有对象由本函数创建。

    授权来源有两种（这是 S3/S4/S5 与 S6/S7 的唯一区别）：
      * framework   —— 框架调用 POST /doc/{id}/share 创建 → 记入 client.share_log（可观测）
      * out_of_band —— 用 app.seed_share 直接种入服务端授权表 → 框架侧无记录（不可观测）
    """
    if scenario not in SCENARIOS:
        raise ValueError(scenario)

    # --- 基础数据: A 拥有 main/second, B 拥有 main ---
    a_main = client.create_doc("A", "A-main", "content-of-A-main")
    a_second = client.create_doc("A", "A-second", "content-of-A-second")
    b_main = client.create_doc("B", "B-main", "content-of-B-main")

    shares: list[dict] = []
    share_origin = "none"
    op = "read"

    def _framework_share(doc_id: str):
        nonlocal share_origin
        shares.append(client.share("A", doc_id, "B", "read"))
        share_origin = "framework"

    def _out_of_band_share(doc_id: str):
        nonlocal share_origin
        if state is None:
            raise RuntimeError("S6/S7 需要传入 state 以带外种入授权")
        from app import seed_share                       # 延迟导入：mrs 包不硬依赖 target_api
        shares.append(seed_share(state, doc_id, "B", "read"))
        share_origin = "out_of_band"

    if scenario == "S1":
        owner, actor, target, actor_doc, unshared = "B", "A", b_main, a_main, a_second

    elif scenario == "S2":
        owner, actor, target, actor_doc, unshared = "A", "B", a_main, b_main, a_second

    elif scenario == "S3":
        # E3: A 显式共享 a_main 给 B（read）—— 由**框架**创建，可观测
        if cfg.mode == "e3":
            _framework_share(a_main)
        owner, actor, target, actor_doc, unshared = "A", "B", a_main, b_main, a_second

    elif scenario == "S4":
        # a_main 已共享给 B, 但 B 访问的是**未共享**的 a_second
        if cfg.mode == "e3":
            _framework_share(a_main)
        owner, actor, target, actor_doc, unshared = "A", "B", a_second, b_main, a_main

    elif scenario == "S5":
        # 共享为 read-only, B 对 a_main 发起**写**
        if cfg.mode == "e3":
            _framework_share(a_main)
        owner, actor, target, actor_doc, unshared = "A", "B", a_main, b_main, a_second
        op = "write"

    elif scenario == "S6":
        # **预存**共享: 授权带外种入, 框架侧无记录。B 访问该共享对象 → 合法
        if cfg.mode == "e3":
            _out_of_band_share(a_main)
        owner, actor, target, actor_doc, unshared = "A", "B", a_main, b_main, a_second

    else:  # S7
        # **预存**共享 a_main, 但 B 访问**未共享**的 a_second → 越权
        if cfg.mode == "e3":
            _out_of_band_share(a_main)
        owner, actor, target, actor_doc, unshared = "A", "B", a_second, b_main, a_main

    return ScenarioSetup(scenario=scenario, intent=SCENARIO_INTENT[scenario],
                         owner=owner, actor=actor, target_doc=target,
                         actor_doc=actor_doc, unshared_doc=unshared,
                         op=op, shares=shares, share_origin=share_origin)


# --------------------------------------------------------------------------
# 动作级真值
# --------------------------------------------------------------------------

def ground_truth(state, cfg, actor: str, doc_id: str, op: str,
                 observed_status: int) -> dict:
    """动作级构造式真值。

    定义（唯一且先于实验确定）:
        BOLA ⟺ 应用**允许**了一次**不该被允许**的访问

        should_allow = 授权模型判定 (state.can_access —— 与是否注入缺陷无关的正确逻辑)
        app_allowed  = 实测观测 (status == 200)

        should_allow ∧ ¬app_allowed → normal （过度拒绝, 不算 BOLA）
        ¬should_allow ∧ app_allowed → **bola**
        其余                        → normal
    """
    doc = state.docs[doc_id]
    should_allow = state.can_access(actor, doc, op)
    app_allowed = observed_status == 200
    is_bola = (not should_allow) and app_allowed
    return {
        "actor": actor, "doc_id": doc_id, "op": op,
        "doc_owner": doc["owner"],
        "should_allow": should_allow,
        "app_allowed": app_allowed,
        "truth": "bola" if is_bola else "normal",
        "is_own_object": doc["owner"] == actor,
    }


def action_path(setup: ScenarioSetup) -> tuple[str, str]:
    """把场景映射为 MR 的 action (method, path)。"""
    if setup.op == "write":
        return "PUT", f"/doc/{setup.target_doc}"
    return "GET", f"/doc/{setup.target_doc}"

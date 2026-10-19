"""
把「原生 MST-wi 引擎运行」的结果并入论文数字流水线。
====================================================

输入（全部为实测产物，任何数字都不手敲）：
  * experiments/native_engine/results/native_engine.json   —— run_native.py 的产物
  * 上游仓库 `git status --porcelain`                       —— 保真性声明的机械凭据
  * 我方新增源码行数（wcount）                              —— harness 规模

输出：
  * 04_绘图与分析/results/native_engine_numbers.tex  —— 宏定义（\\Nt*）
  * 04_绘图与分析/results/native_engine_table.tex    —— 逐条 MR 结果表
  * stdout: 人读小结

用法:
  python ingest_native_engine.py [native_engine.json]
"""

from __future__ import annotations

import collections
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent                      # 3区论文/
RESULTS = HERE.parent / "results"
MST_SRC = Path(os.environ.get("MST_SRC_PATH", r"C:/Users/Administrator/WorkBuddy/mst_engine/MST"))
HARNESS_SRC = ROOT / "experiments" / "native_engine" / "src"
ENGINE_RESULTS = ROOT / "experiments" / "native_engine" / "results"
LAB_OUT = Path(r"C:/Users/Administrator/WorkBuddy/mst_native_lab/out")
DEFAULT_JSON = ENGINE_RESULTS / "native_engine.json"

PREFIX = "Nt"

# 真值分类必须与真实系统实验**共用同一份定义**（`entitlement.classify`），否则
# 「假证明」在两条路径上会各自漂移——这正是本工作批评过的那类错误。
sys.path.insert(0, str(ROOT / "experiments" / "real_system"))
from entitlement import classify as truth_classify, covers as perm_covers  # noqa: E402


# --------------------------------------------------------------------------
# 保真性凭据：上游仓库的改动面
# ★ R1.14 整改：历史事实只从冻结文件 frozen_source_state.json 读取（由
#   freeze_native_sources.py 一次性固化），实时 git 状态仅作附加诊断比对，
#   绝不进宏。冻结文件缺失时非零退出（fail-closed），不静默降级。
# --------------------------------------------------------------------------
FROZEN_SRC_STATE = ENGINE_RESULTS / "frozen_source_state.json"


def repo_facts() -> dict:
    if not FROZEN_SRC_STATE.exists():
        raise SystemExit(
            "[FATAL] 缺少冻结的上游源码状态: " + str(FROZEN_SRC_STATE) + "\n"
            "         历史事实（上游改动面）必须由 freeze_native_sources.py "
            "冻结后才能复算，\n"
            "         不得退回实时 git 状态（输出须是归档记录的确定函数）。")
    f = json.loads(FROZEN_SRC_STATE.read_text(encoding="utf-8"))
    c = f.get("counts") or {}
    out = {"ok": True,
           "modified_total": c.get("modified_total"),
           "java_modified": c.get("java_modified"),
           "build_modified": c.get("build_modified"),
           "head": (f.get("head") or {}).get("commit"),
           "diff_pom_lines": c.get("diff_lines"),
           "frozen_at": f.get("frozen_at")}
    # 附加诊断：实时状态与冻结状态比对（不一致只告警，不改数字）
    try:
        r = subprocess.run(["git", "-C", str(MST_SRC), "status", "--porcelain"],
                           capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            live = [ln for ln in r.stdout.splitlines() if ln.strip()]
            if len(live) != len(f.get("status_entries") or []):
                print(f"  [diag] 实时上游工作区改动 {len(live)} 条 != 冻结 "
                      f"{len(f.get('status_entries') or [])} 条"
                      "（历史事实仍以冻结文件为准）")
    except Exception:                                          # noqa: BLE001
        print("  [diag] 实时上游状态不可读（仅诊断，历史事实仍以冻结文件为准）")
    return out


def harness_lines() -> int:
    n = 0
    if HARNESS_SRC.exists():
        for f in sorted(HARNESS_SRC.rglob("*.java")):
            n += len(f.read_text(encoding="utf-8", errors="replace").splitlines())
    return n


# --------------------------------------------------------------------------
# 从引擎产物中抽取要点
# --------------------------------------------------------------------------
def extract(d: dict) -> dict:
    eng = d.get("engine") or {}
    mrs = eng.get("mrs") or []
    c = eng.get("counters") or {}
    cells = eng.get("crtg_cells") or {}
    dat = d.get("data") or {}
    key = dat.get("key_cell") or {}

    executed = [m for m in mrs if m.get("status") == "executed"]
    fired = [m for m in executed if (m.get("fired") or 0) > 0]
    alarm_total = sum((m.get("fired") or 0) for m in executed)
    # 中止（引擎自身在上游报错路径上抛异常，未产出判决）。必须在正文里如实报，
    # 否则表格里的 `error` 行会变成没人解释的悬空项。
    errored = [m for m in mrs if m.get("status") == "error"]

    key_repo = key.get("repo")
    key_grantee = key.get("grantee")

    # 关键格：谓词在 (受让者, 含关键仓库的 URL) 上判「不可达」的**调用次数**。
    # ⚠️ 早先版本数的是**去重后的格子个数**，恒为 1，在正文里读作「1 次」不成句。
    # 这里改为累加调用计数，得到可直接入句的频次。
    key_crtg_true = 0
    key_cells = []
    for k, v in cells.items():
        parts = k.split("|", 2)
        if len(parts) != 3:
            continue
        res, who, url = parts
        if key_repo and key_repo in url and who == key_grantee:
            if res == "true":
                key_crtg_true += v
            key_cells.append((url, res, v))

    # 哪些 MR 在关键仓库上告警（从 failure_samples 里检索，不用人工判断）
    key_mrs = []
    if key_repo:
        for m in executed:
            blob = "\n".join(m.get("failure_samples") or [])
            if key_repo in blob:
                key_mrs.append({"mr": m["mr"], "fired": m.get("fired") or 0})

    return {
        "mr_total": len(mrs),
        "mr_executed": len(executed),
        "mr_errored": len(errored),
        "mr_fired": len(fired),
        "alarm_total": alarm_total,
        "input_view": eng.get("input_view_size"),
        "chunk_size": eng.get("chunk_size_floor_div_160"),
        "derived": eng.get("derived_inputs"),
        "derive_failed": eng.get("derive_failed"),
        "base_inputs": eng.get("base_inputs"),
        "http_calls": c.get("http_calls_total"),
        "memo_hits": c.get("http_memo_hits"),
        "crtg_calls": c.get("cannotReachThroughGUI_url_calls"),
        "crtg_true": c.get("cannotReachThroughGUI_url_true"),
        "sup_calls": c.get("isSupervisorOf_calls"),
        "sup_true": c.get("isSupervisorOf_true"),
        "ucrc_calls": c.get("userCanRetrieveContent_calls"),
        "ucrc_true": c.get("userCanRetrieveContent_true"),
        "key_repo": key_repo,
        "key_grantee": key_grantee,
        "key_in_snapshot": key.get("in_snapshot_of_grantee"),
        "key_crtg_true": key_crtg_true,
        "key_cells": sorted(key_cells),
        "key_mrs": key_mrs,
        "user_count": len(eng.get("users") or []),
        "user_names": list(eng.get("users") or []),
        "channel": (d.get("channel") or {}).get("channel"),
        "gitea": (d.get("gitea") or {}).get("version"),
        "elapsed_s": d.get("elapsed_s"),
        "rows": mrs,
        "oob": dat.get("oob_grants") or [],
    }


def side_evidence() -> dict:
    """读可选的两份旁证产物（缺失即返回 None，不报错）。

    - `seedcheck.json`：播种期**机械核验**的访问点数（每个快照对象可读 + 每个带外
      授予生效且在采集期不可见）。正文引用它的数字，必须由产物复算。
    - `channel_bytes.json`：`verify_channel_bytes.py` 产出的摘要级凭据
      （同一 URL 对拥有者/受让者的 sha256 是否相同 + 无权者 404 对照）。
    """
    out = {"seed_points": None, "byte_cells": None}
    sc = ENGINE_RESULTS / "seedcheck.json"
    if sc.exists():
        try:
            d = json.loads(sc.read_text(encoding="utf-8"))
            out["seed_points"] = (d.get("data") or {}).get("seed_verified_points")
        except Exception:                                          # noqa: BLE001
            pass
    cb = ENGINE_RESULTS / "channel_bytes.json"
    if cb.exists():
        try:
            d = json.loads(cb.read_text(encoding="utf-8"))
            if d.get("all_owner_grantee_identical") and d.get("all_outsider_denied"):
                out["byte_cells"] = len(d.get("cells") or [])
        except Exception:                                          # noqa: BLE001
            pass
    return out


def esc(s) -> str:
    return (str(s).replace("\\", r"\textbackslash{}").replace("_", r"\_")
            .replace("&", r"\&").replace("%", r"\%").replace("#", r"\#"))


def parse_one_alarm(block: str, granted: set, mr: str = "?") -> dict | None:
    """从一个告警块里取出 (受试者, 原身份, 仓库) 并按拓扑分类。

    ★ 这是针对 **harness 缺陷** 的哨兵，两条分类路径共用同一逻辑（防止分叉）。

    原文引擎用 WebDriver 回放：身份由**登录动作**确立并延续到后续动作；而
    `WebInputCrawlJax.changeCredential` 只改写**带凭证的那个动作**，后续动作的
    `user` 字段仍是原用户。若观测通道按「每个动作自己的 user」取凭证，凭证替换后的
    输入会以**原身份**重抓 ⇒ 响应逐字相同 ⇒ 在主体**自己的**仓库上也报出告警。

    因此：`subject_own` / `owner_object_not_granted` 上出现告警 = harness 有缺陷，
    必须当作**污染**处理，不得计入假确证。返回 None = 该块无法解析。
    """
    urls = re.findall(r"click on (https?://\S+?)/raw/", block)
    logins = re.findall(r"log in with \((\w+),", block)
    if not urls or len(logins) < 2:
        return None
    # `click on` 的捕获是**完整 URL 前缀**（含 scheme/host），须取末两段才是 owner/name
    parts = urls[0].rstrip("/").split("/")
    if len(parts) < 2:
        return None
    repo, owner = "/".join(parts[-2:]), parts[-2]
    # ⚠️ 消息里 **Input(2) 先打印**，故 logins[0] 是**替换后的身份**（即受试者
    # `User()`），logins[1] 是源输入的原身份。取反会让分类全落到 other。
    subject, origin = logins[0], logins[1]
    if (repo, subject) in granted:
        k = "out_of_band_grant"
    elif repo.endswith("/pub"):
        k = "public"
    elif owner == subject:
        k = "subject_own"
    elif owner == origin:
        k = "owner_object_not_granted"
    else:
        k = "other"
    return {"mr": mr, "repo": repo, "subject": subject, "origin": origin, "class": k}


def classify_alarms(rows: list, oob: list) -> tuple:
    """按产物里**每关系至多 8 条**的 failure_samples 分类（只是下界）。"""
    granted = {(g.get("repo"), g.get("grantee")) for g in (oob or [])}
    cls = collections.Counter()
    detail = []
    for m in rows:
        nm = m.get("mr", "?").split(".")[-1]
        for s in (m.get("failure_samples") or []):
            r = parse_one_alarm(s, granted, nm)
            if r:
                cls[r["class"]] += 1
                detail.append(r)
    return cls, detail


# --------------------------------------------------------------------------
# 完整分类：直接解析引擎 stdout，拿到**全部**唯一告警
# --------------------------------------------------------------------------
# `MR.fail()`（MR.java:909）先打 INFO "FAILURE"，再走去重；只有入库成功才接着打
# `FAILURE: ` + verboseMSG。故 `^FAILURE: ` 的段数 == getFailures().size()。
# 产物里的 failure_samples 每关系只留 8 条（RunAuthzMRs.java:182），撑不起
# 「**全部**告警都落在带外授予上」这一断言 ⇒ 必须回到日志。
# 段界取下一条 java.util.logging 头（以 `smrl.mr.language.MR fail` 结尾，
# 与 locale / 时间格式无关）。
_LOG_SEP = r"\n[^\n]*smrl\.mr\.language\.MR fail\n"
_LOG_BLOCK = re.compile(r"^FAILURE: \n(.*?)(?=" + _LOG_SEP + r"|\Z)", re.S | re.M)


def find_engine_log(mode: str | None) -> Path | None:
    names = ([f"java_{mode}.log"] if mode else []) + ["java_augmented.log", "java_base.log"]
    for n in names:
        for d in (ENGINE_RESULTS, LAB_OUT):
            p = d / n
            if p.exists():
                return p
    return None


def log_iterations(path: Path | None) -> int:
    """叶子求值总数 = 各 split 末尾 `MR tested with N sets of inputs` 之和。

    这不是装饰性统计：该计数**就是上游 `killChromeDriver()` 的调用次数**
    （`MR.java:752`，每个叶子一次），而该函数在 Windows 上会 spawn
    `taskkill /f /im chrome.exe` 与 `taskkill /f /im chromedriver` 各一次并
    `waitFor()`（`MR.java:809-832`）。因此本轮墙钟时间的构成可以不用手工计时
    就从日志机械解释——这正是"库只发布关系、不发布执行环境"的一个具体代价。
    """
    import re
    if path is None or not Path(path).exists():
        return 0
    txt = Path(path).read_text(encoding="utf-8", errors="replace")
    return sum(int(x) for x in re.findall(r"MR tested with (\d+) sets of inputs", txt))


def parse_log_alarms(path: Path, oob: list) -> tuple:
    """返回 (分类计数, 明细, 段数)；段数可与 sum(fired) 交叉校验。

    同时统计 `fail()` 的**调用次数**与库自身丢弃的重复数，使
    「告警数 = 引擎 getFailures() 的返回值」这句话可被独立审计。
    """
    granted = {(g.get("repo"), g.get("grantee")) for g in (oob or [])}
    txt = path.read_text(encoding="utf-8", errors="replace")
    blocks = _LOG_BLOCK.findall(txt)
    cls = collections.Counter()
    detail = []
    for b in blocks:
        r = parse_one_alarm(b, granted, "log")
        if r:
            cls[r["class"]] += 1
            detail.append(r)
    return cls, detail, len(blocks)


def log_fail_calls(path: Path) -> dict:
    """`fail()` 被调用几次、其中几次被库的过滤器当重复丢掉。"""
    txt = path.read_text(encoding="utf-8", errors="replace")
    calls = len(re.findall(r"^\u4fe1\u606f: FAILURE$", txt, re.M))
    dups = len(re.findall(r"^\(DUPLICATED FAILURE, ignoring\)$", txt, re.M))
    return {"fail_calls": calls, "duplicates_filtered": dups,
            "recorded": calls - dups}


# --------------------------------------------------------------------------
# A / H / T 三段分离
# --------------------------------------------------------------------------
def alarm_units(rows: list, oob: list) -> list:
    """(MR, 受试者, 仓库) 明细，取自产物里的 failure_samples。

    日志块本身不含 MR 名（段界是 `smrl.mr.language.MR fail` 这条 logger 记录），
    所以 MR 归属只能来自产物样本；样本每关系至多 8 条，故调用方必须与全量告警数
    交叉校验，不允许拿样本直接当全量。
    """
    granted = {(g.get("repo"), g.get("grantee")) for g in (oob or [])}
    units = []
    for m in rows:
        nm = m.get("mr", "?").split(".")[-1]
        for s in (m.get("failure_samples") or []):
            r = parse_one_alarm(s, granted, nm)
            if r:
                units.append(r)
    return units


def stage_split(detail: list, oob: list, rows: list,
                promotion: bool = True) -> dict:
    """把原生告警拆成三段，**每段各自说明它证明了什么**。

    A（native alarm）：引擎 `getFailures()` 里确实有一条 ⇒ 上游代码层面的断言只有
        "这条变形关系不成立"（`MR.fail()` 只写 `FAILURE` + verboseMSG，不判定安全）。
    H（promotion）：把 A 读成"观察到一次授权违规"。这一步**不是上游代码做的**，是本
        文声明的升格策略 P；不承认 P 的读者只应接受 A。
    T（独立真值）：只用与引擎无关的两样证据——台账授予事件（E）与内容复读（Y，
        `channel_bytes.json` 的 sha256 相同 + 无权者 404）。缺任一即 unobserved，
        绝不按 allow/deny 猜。

    返回逐条记录与计数。T 的判定复用 `entitlement.classify`，与真实系统实验同源。
    """
    grants = {(g.get("repo"), g.get("grantee")): (g.get("perm") or "read")
              for g in (oob or [])}
    cells = {}
    cb = ENGINE_RESULTS / "channel_bytes.json"
    if cb.exists():
        doc = json.loads(cb.read_text(encoding="utf-8"))
        for c in doc.get("cells") or []:
            cells[(c.get("repo"), c.get("grantee"))] = c

    units = alarm_units(rows, oob)
    # MR 归属只有在样本数与全量告警数一致时才可用；否则退化为"未归属"，并如实计数。
    attributed = len(units) == len(detail)
    marks = units if attributed else [dict(r, mr="unattributed") for r in detail]

    out = []
    for r in marks:
        key = (r["repo"], r["subject"])
        perm = grants.get(key)
        if perm is None:
            e_val, e_basis = "unknown", "no grant event in the ledger"
        elif perm_covers(perm, "read"):
            e_val, e_basis = "allow", f"out-of-band {perm} grant made after the crawl"
        else:
            e_val, e_basis = "deny", f"grant {perm} does not cover read"

        c = cells.get(key)
        if c is None:
            y_val = None
        else:
            y_val = bool((c.get("grantee_resp") or {}).get("status") == 200
                         and c.get("owner_grantee_identical_bytes"))

        if y_val is None:
            t = {"category": "unobserved", "true_positive": False, "false_proof": False}
            y_basis = "no independent content re-read for this cell"
        else:
            t = truth_classify(e_val, y_val, alarm=True, promotion=promotion)
            y_basis = ("owner-identical bytes" if c.get("owner_grantee_identical_bytes")
                       else "bytes differ from owner")
        out.append(dict(r, A=True, H=bool(promotion), E=e_val, E_basis=e_basis,
                        Y=y_val, Y_basis=y_basis,
                        byte_identical=None if c is None else bool(c.get("owner_grantee_identical_bytes")),
                        outsider_denied=None if c is None else bool(c.get("outsider_denied")),
                        T=t["category"], true_positive=t["true_positive"],
                        false_proof=t["false_proof"]))

    return {
        "rows": out,
        "attributed": attributed,
        "cells": sorted({(r["repo"], r["subject"]) for r in out}),
        "A": len(out),
        "H": sum(1 for r in out if r["H"]),
        "T_true": sum(1 for r in out if r["true_positive"]),
        "T_false": sum(1 for r in out if r["false_proof"]),
        "T_unobserved": sum(1 for r in out if r["Y"] is None),
        "T_allow": sum(1 for r in out if r["E"] == "allow" and r["Y"] is True),
    }



def main() -> int:
    p = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_JSON
    if not p.exists():
        print(f"!! 找不到 {p}（原生引擎尚未跑完？）")
        return 2
    log_arg = Path(sys.argv[2]) if len(sys.argv) > 2 else None
    d = json.loads(p.read_text(encoding="utf-8"))
    e = extract(d)
    rf = repo_facts()
    hl = harness_lines()
    se = side_evidence()
    al_cls, al_detail = classify_alarms(e["rows"], e["oob"])
    logp = log_arg if log_arg is not None else find_engine_log(d.get("mode"))
    if logp is not None and not logp.exists():
        logp = None
    log_cls: collections.Counter = collections.Counter()
    log_detail: list = []
    log_n = 0
    if logp is not None:
        log_cls, log_detail, log_n = parse_log_alarms(logp, e["oob"])
    iter_n = log_iterations(logp)
    # 优先用日志的**完整**分类；日志缺失才退回样本分类（只是下界）
    use_log = log_n > 0
    cls_eff = log_cls if use_log else al_cls
    det_eff = log_detail if use_log else al_detail
    al_on = cls_eff.get("out_of_band_grant", 0)
    al_off = sum(v for k, v in cls_eff.items()
                 if k in ("subject_own", "owner_object_not_granted", "other"))
    # 告警落在多少个**不同格子**（仓库 × 受试者）上
    alarm_cells = sorted({(r["repo"], r["subject"]) for r in det_eff})
    # A/H/T 三段分离（T 用台账 E + 内容复读 Y，与引擎无关）
    sp = stage_split(det_eff, e["oob"], e["rows"])

    # ---------------- 宏 ----------------
    M = {
        "NtMrTotal": e["mr_total"],
        "NtMrExecuted": e["mr_executed"],
        "NtMrErrored": e["mr_errored"],
        "NtMrFired": e["mr_fired"],
        "NtAlarms": e["alarm_total"],
        "NtInputView": e["input_view"],
        "NtChunkSize": e["chunk_size"],
        "NtUserCount": e["user_count"],
        "NtDerived": e["derived"],
        "NtDeriveFailed": e["derive_failed"],
        "NtBaseInputs": e["base_inputs"],
        "NtHttpCalls": e["http_calls"],
        "NtCrtgCalls": e["crtg_calls"],
        "NtCrtgTrue": e["crtg_true"],
        "NtSupCalls": e["sup_calls"],
        "NtSupTrue": e["sup_true"],
        "NtUcrcCalls": e["ucrc_calls"],
        "NtUcrcTrue": e["ucrc_true"],
        "NtKeyCrtgTrue": e["key_crtg_true"],
        "NtKeyMrFired": len(e["key_mrs"]),
        "NtAlarmsOnGranted": al_on,
        "NtAlarmsOffGrant": al_off,
        "NtAlarmsLogged": log_n,
        "NtAlarmCells": len(alarm_cells),
        "NtIterations": iter_n,
        "NtKeyMrNames": (", ".join(sorted({m["mr"].split(".")[-1] for m in e["key_mrs"]})) or None),
        "NtKeyRepo": (e["key_repo"] or None),
        "NtKeyGrantee": (e["key_grantee"] or None),
        "NtGiteaVersion": (e["gitea"] or None),
        "NtHarnessLines": hl,
        "NtSeedVerified": se["seed_points"],
        "NtByteCells": se["byte_cells"],
        "NtUpstreamModified": rf["modified_total"],
        "NtUpstreamJavaModified": rf["java_modified"],
        "NtUpstreamBuildModified": rf["build_modified"],
        "NtElapsedS": e["elapsed_s"],
        # --- A / H / T 三段（A8 项④） ---
        "NtStageA": sp["A"],
        "NtStageH": sp["H"],
        "NtStageTTrue": sp["T_true"],
        "NtStageTFalse": sp["T_false"],
        "NtStageTUnobserved": sp["T_unobserved"],
        "NtStageTCells": len(sp["cells"]),
    }
    if e["crtg_calls"]:
        M["NtCrtgTruePct"] = f"{100.0 * e['crtg_true'] / e['crtg_calls']:.1f}"
    else:
        M["NtCrtgTruePct"] = None

    lines = ["% 由 analysis/ingest_native_engine.py 自动生成 —— 请勿手改",
             "% 源: experiments/native_engine/results/native_engine.json",
             ""]

    def _val(v):
        """序列化成可安全塞进 \\newcommand 的文本。

        ⚠️ 所有字符串值都必须过 esc()：MR 类名形如 OTG_AUTHZ_002，
        裸下划线会让 LaTeX 报 `Missing $ inserted`（已踩过一次）。
        None 用破折号，且不回灌 esc（否则会转义掉 \\textemdash 本身）。
        """
        if v is None:
            return r"\textemdash{}"
        if isinstance(v, str):
            return esc(v)
        return v

    for k, v in M.items():
        lines.append(f"\\newcommand{{\\{k}}}{{{_val(v)}}}")
    out_tex = RESULTS / "native_engine_numbers.tex"
    out_tex.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ---------------- 表 ----------------
    # ⚠️ 不含墙钟时间列：本配置下的耗时由**上游** `killChromeDriver` 的进程清理
    # 主导（每个叶子 2 次 taskkill / waitFor），既非 SUT 亦非关系本身的属性；
    # 放进表里只会诱导"harness 空转"的误读。该事实改由正文一句说明。
    tl = ["% 由 analysis/ingest_native_engine.py 自动生成 —— 请勿手改",
          "% 逐条 MR 结果：status 为引擎返回的执行结果，告警数由引擎自己 getFailures() 返回，非本工作判读",
          "\\begin{tabular}{llrr}", "\\toprule",
          "MR & status & alarms & requests \\\\", "\\midrule"]
    for m in e["rows"]:
        nm = esc(m.get("mr", "?").split(".")[-1])
        st = m.get("status")
        if st != "executed":
            tl.append(f"{nm} & {esc(st)} & --- & --- \\\\")
        else:
            tl.append(f"{nm} & executed & {m.get('fired', 0)} & {m.get('http_calls', 0)} \\\\")
    tl += ["\\bottomrule", "\\end{tabular}"]
    (RESULTS / "native_engine_table.tex").write_text("\n".join(tl) + "\n", encoding="utf-8")

    # ---------------- A / H / T 表 ----------------
    # 每一行 = 一条原生告警的三个阶段。列 A 恒为 fired（表的存在前提），
    # 故改由 caption 说明，不占列宽。T 列只在 Y 可观测时才给判定。
    st = ["% 由 analysis/ingest_native_engine.py 自动生成 —— 请勿手改",
          "% A=原生报警（引擎 getFailures）；H=本文声明的升格策略；"
          "E=台账真值；Y=内容复读（sha256 与拥有者相同）；T=独立判定",
          "\\begin{tabular}{lllccc}", "\\toprule",
          "MR & subject & object & $E$ & $Y$ & $T$ \\\\", "\\midrule"]
    for r in sorted(sp["rows"], key=lambda x: (x["mr"], x["repo"], x["subject"])):
        if r["Y"] is True:
            ylab = r"allow$^{\dagger}$"
        elif r["Y"] is False:
            ylab = "deny"
        else:
            ylab = "---"
        tlab = {"false_proof": "false proof",
                "true_positive": "violation confirmed",
                "unobserved": "unobserved"}.get(r["T"], r["T"])
        # MR 名去掉公共前缀 OTG_AUTHZ_（caption 里说明），否则单栏放不下
        mr_short = r["mr"].replace("OTG_AUTHZ_", "")
        st.append(f"{esc(mr_short)} & {esc(r['subject'])} & {esc(r['repo'])} & "
                  f"{r['E']} & {ylab} & {tlab} \\\\")
    st += ["\\bottomrule", "\\end{tabular}"]
    (RESULTS / "native_split_table.tex").write_text("\n".join(st) + "\n", encoding="utf-8")

    # 逐条记录留档，供外部按行复核
    (ENGINE_RESULTS / "native_split.json").write_text(
        json.dumps({"attributed_to_mr": sp["attributed"], "counts": {
            k: sp[k] for k in ("A", "H", "T_true", "T_false", "T_unobserved")},
            "rows": sp["rows"]}, ensure_ascii=False, indent=1),
        encoding="utf-8")


    # ---------------- 人读小结 ----------------
    print("=" * 78)
    print("原生 MST-wi 引擎运行 · 结果消化")
    print("=" * 78)
    print(f"被测系统        Gitea {e['gitea']}   观测通道={e['channel']}   耗时 {e['elapsed_s']}s")
    print(f"输入视图        base={e['base_inputs']} 派生={e['derived']} 失败={e['derive_failed']} "
          f"视图={e['input_view']} chunk=floor(LEN/160)={e['chunk_size']}")
    print(f"引擎载入账号    {e['user_count']} 个: {', '.join(e['user_names'])}")
    print(f"MR              共 {e['mr_total']} 条，执行 {e['mr_executed']} 条，"
          f"其中 {e['mr_fired']} 条产生告警，告警总数 {e['alarm_total']}")
    print("\n--- 逐条 MR ---")
    for m in e["rows"]:
        nm = m.get("mr", "?").split(".")[-1]
        st = m.get("status")
        print(f"  {nm:18s} {st:10s} alarms={m.get('fired', 0):<4} http={m.get('http_calls', 0):<6} "
              f"ms={m.get('ms', 0)}")
    print("\n--- 谓词调用（纯委托计数） ---")
    print(f"  cannotReachThroughGUI(url)  calls={e['crtg_calls']}  true={e['crtg_true']}  "
          f"({M['NtCrtgTruePct']}%)")
    print(f"  isSupervisorOf              calls={e['sup_calls']}  true={e['sup_true']}")
    print(f"  userCanRetrieveContent       calls={e['ucrc_calls']}  true={e['ucrc_true']}")
    print(f"  HTTP 实际请求 {e['http_calls']}（memo 命中 {e['memo_hits']}）")
    print("\n--- 关键格 ---")
    print(f"  仓库 {e['key_repo']} → 受让者 {e['key_grantee']}；"
          f"采集快照里可见? {e['key_in_snapshot']}")
    print(f"  (受让者, 关键仓库) 上判「不可达」的调用次数 = {e['key_crtg_true']}")
    for u, r, n in e["key_cells"]:
        print(f"      crtg={r:5s} ×{n:<4d} {u}")
    print(f"  在关键仓库上告警的 MR（{len(e['key_mrs'])} 条）: "
          + ", ".join(f"{m['mr'].split('.')[-1]}({m['fired']})" for m in e["key_mrs"]))

    print("\n--- 告警落点自检（harness 哨兵） ---")
    print(f"  分类来源: {'引擎全量日志 ' + str(logp.name) if use_log else '产物样本（**仅下界**）'}")
    if use_log:
        print(f"  日志中 `FAILURE: ` 段数 = {log_n}；产物 sum(fired) = {e['alarm_total']}"
              + ("  [ok] 交叉校验一致" if log_n == e["alarm_total"] else "  !! 不一致，须查"))
        fc = log_fail_calls(logp)
        print(f"  fail() 被调用 {fc['fail_calls']} 次，其中库自身按重复丢弃 "
              f"{fc['duplicates_filtered']} 次 ⇒ 入库 {fc['recorded']} 条")
        print(f"  样本分类（每关系≤8 条）下界计 = {sum(al_cls.values())} 条")
    for k in ("out_of_band_grant", "public", "subject_own",
              "owner_object_not_granted", "other"):
        if cls_eff.get(k):
            print(f"  {k:28s} {cls_eff[k]}")
    print(f"  告警落在 {len(alarm_cells)} 个不同格子: "
          + ", ".join(f"{r}×{s}" for r, s in alarm_cells))
    if al_off:
        print(f"  !! 有 {al_off} 条告警落在受试者**不应有权限**的对象上 —— 疑似 harness")
        print("     缺陷（会话语义），**不得计入假确证**，须先修 harness 再重跑！")
    else:
        print(f"  [ok] 全部分类到的 {sum(cls_eff.values())} 条告警均落在带外授权对象上"
              " ⇒ 与会话语义修复一致")
    print("\n--- A / H / T 三段分离 ---")
    print(f"  A 原生报警（getFailures）           {sp['A']}")
    print(f"  H 升格为违规主张（本文策略 P）       {sp['H']}")
    print(f"  T 独立真值：确认违规 / 假证明        {sp['T_true']} / {sp['T_false']}"
          f"   （无可观测 Y 的条数 {sp['T_unobserved']}）")
    print(f"  覆盖格子 {len(sp['cells'])} 个；MR 归属"
          + ("可用（样本数与全量一致）" if sp["attributed"]
             else "不可用（样本数与全量不一致，已按未归属计）"))
    print("\n--- 保真性凭据（机械核验） ---")
    print(f"  上游 git status --porcelain 条目数 = {rf['modified_total']}")
    print(f"     其中 src* 下 .java 改动 = {rf['java_modified']}")
    print(f"     其中构建文件改动        = {rf['build_modified']}")
    print(f"  本工作新增 harness 源码行数 = {hl}")
    if se["seed_points"] is not None:
        print(f"  播种期机械核验的访问点数 = {se['seed_points']}"
              "（快照对象可读 + 带外授予生效且采集期不可见）")
    if se["byte_cells"] is not None:
        print(f"  逐字节相同性凭据覆盖的授予格数 = {se['byte_cells']}"
              "（channel_bytes.json：sha256 相同 + 无权者 404）")
    print(f"\n产出  {out_tex}")
    print(f"      {RESULTS / 'native_engine_table.tex'}")
    print(f"      {RESULTS / 'native_split_table.tex'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

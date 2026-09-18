# -*- coding: utf-8 -*-
"""
Undermind MCP 批处理驱动（复用 undermind_mcp.py 的 MCP 客户端）

用法:
  python _um.py launch                  # 建目录 + 发起三路 deep search
  python _um.py status                  # 查看 deep search 状态
  python _um.py results                 # 拉取三路 deep search 的结果论文
  python _um.py call <tool> <jsonfile>  # 任意工具调用，参数从 json 文件读
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from undermind_mcp import MCP  # noqa: E402

WS = "68e924b3-ec86-4d62-bf1c-b997e03767c3"   # JISA 2026 · WebAPI 安全与漏洞挖掘
EMAIL = "ubfbuz3@gmail.com"

FOLDERS = [
    "/01-BOLA-BFLA 检测/",
    "/02-LLM 授权语义推理/",
    "/03-Oracle 与差分测试/",
]

# --------------------------------------------------------------------------
# Deep search goals：self-contained 段落，不给关键词清单
# --------------------------------------------------------------------------
SEARCHES = [
    (
        "BOLA BFLA 自动化检测技术全景",
        "/01-BOLA-BFLA 检测/",
        "We are preparing a journal paper on automatically finding broken authorization in web APIs — "
        "specifically Broken Object Level Authorization (BOLA, also called IDOR) and Broken Function Level "
        "Authorization (BFLA) in REST APIs, which are the top entries of the OWASP API Security Top 10. "
        "We want to understand the full landscape of techniques proposed to detect, test or verify "
        "authorization and access-control flaws in APIs: static analysis and taint tracking over "
        "server-side source code, dynamic black-box and grey-box testing, model-based testing driven by "
        "OpenAPI/Swagger specifications, search-based and coverage-guided fuzzing, and formal or Petri-net "
        "style modelling of API access policies. We especially care about how each work constructs its "
        "detection oracle — how it decides that an observed response really is an authorization violation "
        "rather than a benign denial — and how it handles false positives caused by ambiguous responses "
        "such as 401, 403 and 404. We also want to know which benchmarks, vulnerable-by-design testbeds "
        "and real-world applications are used for evaluation. Work that combines several of these ideas, "
        "or that has been validated on production-scale APIs, is the most central to us.",
    ),
    (
        "LLM 推断授权与访问控制语义",
        "/02-LLM 授权语义推理/",
        "Large language models are increasingly used to reason about security properties of code, but the "
        "reported work concentrates heavily on memory-safety bugs, injection flaws and generic CWE "
        "classification. We want to know what has actually been done on using large language models to "
        "infer or recover authorization and access-control semantics: extracting access-control policies "
        "and permission rules from server-side source code, route definitions, authentication middleware, "
        "ORM models or API specifications; inferring ownership and role relationships between resources "
        "and identities; and recovering business-logic or tenancy constraints that are not written down in "
        "any machine-readable form. We are equally interested in the empirical limits of language models "
        "for this kind of reasoning — hallucination, unsupported claims, output instability — and in how "
        "researchers ground model output in evidence from the codebase, for example by requiring citations "
        "back to specific code locations, or by pairing the model with a deterministic verifier or program "
        "analysis so that the model only generates hypotheses and never makes the final judgement. Also "
        "include work on specification and invariant inference from code when the goal is recovering "
        "latent semantics, even if it is not framed as security research.",
    ),
    (
        "Security Oracle 与差分测试",
        "/03-Oracle 与差分测试/",
        "We are designing a detection method for authorization flaws in web APIs whose central mechanism is "
        "a differential oracle: the same request is issued under several carefully constructed control "
        "conditions and the responses are compared to decide whether an authorization violation has "
        "occurred, with the explicit goal of eliminating false positives caused by ambiguous status codes, "
        "rate limiting, caching or ordinary access denials. We want to learn how similar ideas have been "
        "used in security testing and software engineering: differential testing and differential fuzzing "
        "for security properties, metamorphic testing of access control, the general oracle problem in "
        "software testing, false-positive suppression strategies in vulnerability detection, and automatic "
        "generation of proof-of-concept requests or executable exploits once a violation is suspected. We "
        "are also interested in how ownership and identity ground truth is established in API security "
        "experiments — whether by manual annotation or by construction through legitimate API calls — and "
        "in any published criticism of annotation-based ground truth in vulnerability datasets.",
    ),
]

STATE = os.path.join(HERE, "_um_state.json")


def load_state():
    if os.path.exists(STATE):
        return json.load(open(STATE, encoding="utf-8"))
    return {}


def save_state(st):
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def retry_call(m, name, args, tries=6, wait=25):
    last = None
    for i in range(tries):
        last = m.call(name, args)
        blob = json.dumps(last, ensure_ascii=False).lower()
        if "rate_limited" in blob or "rate limit" in blob:
            print("    [rate limited] 等待 %ss 重试 (%d/%d)" % (wait, i + 1, tries), flush=True)
            time.sleep(wait)
            continue
        return last
    return last


def brief(r):
    """把返回压成一行摘要"""
    if isinstance(r, dict):
        if "content" in r:
            txt = " ".join(c.get("text", "") for c in r["content"] if c.get("type") == "text")
            return txt[:300].replace("\n", " ")
        return json.dumps(r, ensure_ascii=False)[:300]
    return str(r)[:300]


def cmd_launch():
    m = MCP()
    m.initialize()
    st = load_state()

    # 1) 建目录
    for f in FOLDERS:
        r = retry_call(m, "create_folder", {"workspace_id": WS, "path": f})
        print("[folder] %s -> %s" % (f, brief(r)), flush=True)
        time.sleep(2)

    # 2) 发起深挖
    st.setdefault("searches", {})
    for name, folder, goal in SEARCHES:
        r = retry_call(m, "launch_deep_search", {
            "workspace_id": WS, "goal": goal, "name": name, "folder_path": folder,
        })
        print("[launch] %s -> %s" % (name, brief(r)), flush=True)
        st["searches"][name] = {"folder": folder, "launch": brief(r)}
        save_state(st)
        time.sleep(3)

    print("\n完成。workspace: https://app.undermind.ai/projects/%s" % WS)


def cmd_status():
    m = MCP()
    m.initialize()
    r = retry_call(m, "inspect_deep_searches", {
        "workspace_id": WS, "status_only": True,
    })
    print(json.dumps(r, ensure_ascii=False, indent=2))


def cmd_results(out_prefix="_um_ds"):
    m = MCP()
    m.initialize()
    names = [s[0] for s in SEARCHES]
    r = retry_call(m, "inspect_deep_searches", {
        "workspace_id": WS, "names": names, "detail_level": "standard", "limit": 50,
    })
    p = os.path.join(HERE, out_prefix + "_results.json")
    json.dump(r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[ok] ->", p)
    print(json.dumps(r, ensure_ascii=False)[:3000])


def cmd_call():
    tool = sys.argv[2]
    args = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else {}
    args.setdefault("workspace_id", WS)
    m = MCP()
    m.initialize()
    r = retry_call(m, tool, args)
    txt = json.dumps(r, ensure_ascii=False, indent=2)
    out = os.path.join(HERE, "_um_last.json")
    open(out, "w", encoding="utf-8").write(txt)
    print(txt[:8000])
    print("\n[full output -> %s]" % out)


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "status"
    {"launch": cmd_launch, "status": cmd_status, "results": cmd_results, "call": cmd_call}[c]()

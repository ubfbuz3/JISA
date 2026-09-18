"""
生成原生引擎所需的 {config.json, inputs.json, output_store/}
=============================================================
契约见同目录 DATA_CONTRACT.md（每条带 file:line）。

拓扑（与 experiments/real_system 对齐，便于交叉比对）：
  alice 拥有 alice/r1(private) alice/pub1(public)
  acme 组织（拥有者 dave）有 acme/t1(private)
  alice/r1 在**采集期之后**被带外共享给 bob        ← 边界 1 的关键格
  acme/t1 在**采集期之后**被带外共享给 carol

采集期快照（snapshot）= 每个用户在变更前**能通过界面看到**的 URL 集合。
  alice : /alice/r1 /alice/pub1 /acme/t1
  bob   : /bob          （无仓库 ⇒ 看不到 alice/r1）
  carol : /carol        （无仓库 ⇒ 看不到 acme/t1）
  dave  : /dave /acme/t1
⇒ snapshot 读法下 cannotReachThroughGUI(bob, /alice/r1) = 真，但 bob 实际可访问
   ⇒ 该格正是「合法访问被判成 violation」的假确证格。

用法：
  python gen_inputs.py                # 离线：写到 ASCII 工作目录
  python gen_inputs.py --base URL     # 覆盖主机
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 纯 ASCII 工作目录（Java 8 在中文路径下有编码风险，硬约束）
WORK = Path(r"C:\Users\Administrator\WorkBuddy\mst_native_lab")
DATA = WORK / "data"

PASS = "LabPass123!"
HOST_DEFAULT = "http://127.0.0.1:3311"
LOGIN_PATH = "/user/login"

# 用户 → 采集期可见 URL 路径
SNAPSHOT = {
    "alice": ["/alice/r1", "/alice/pub1", "/acme/t1"],
    "bob":   ["/bob"],
    "carol": ["/carol"],
    "dave":  ["/dave", "/acme/t1"],
}

# 采集期**之后**才生效的带外授权（本实验的关键变量）
OOB_LIVE = {
    "bob":   ["/alice/r1"],     # alice 事后把 r1 共享给 bob
    "carol": ["/acme/t1"],      # dave 事后把 acme/t1 共享给 carol
}

# 监督关系（写进 config.supervisedUser）：dave 监督 acme 团队成员
SUPERVISED = {"dave": ["alice", "bob", "carol"]}


def action(url: str, method: str = "get", current: str | None = None,
           cred: tuple[str, str] | None = None, text: str = "") -> dict:
    a: dict = {
        "text": text or url,
        "id": "xpath /HTML[1]/BODY[1]/DIV[1]/A[1]",
        "element": f"Element{{node=[A: null], tag=A, text= {text or url}}}",
        "eventType": "click",
        "currentURL": current or url,
        "elementURL": url,
        "method": method,
    }
    if cred is not None:
        up, pp = cred
        a["formInputs"] = [
            {"identification": {"value": up}, "values": [text or ""]},
            {"identification": {"value": pp}, "values": ["x"]},
        ]
    return a


def build_inputs(base: str) -> dict:
    up, pp = "user_name", "password"
    login_url = base + LOGIN_PATH
    out: dict = {}

    for user, paths in SNAPSHOT.items():
        acts = []
        # 登录动作必须 method=post 且 URL 命中 loginURL，否则 isLogin 为假
        acts.append(action(login_url, method="post", current=base + "/",
                           cred=(up, pp), text=user))
        for p in paths:
            acts.append(action(base + p, current=base + "/"))
        out[f"snapshot|{user}"] = acts

    return out


def build_config(base: str, inputs_file: Path, out_file: Path, store: Path) -> dict:
    return {
        "SUT": "Gitea-1.22.6-Lab",
        "inputFile": str(inputs_file).replace("\\", "/"),
        "outputFile": str(out_file).replace("\\", "/"),
        "outputStore": str(store).replace("\\", "/"),
        "loginParams": [
            {"loginURL": base + LOGIN_PATH,
             "userParameter": "user_name",
             "passwordParameter": "password"},
        ],
        "supervisedUser": SUPERVISED,
        "headless": True,
        "ignoreURLs": [],
        "errorSigns": {
            "title": ["Not Found", "Internal Server Error", "Sign In"],
        },
        "randomFilePathFile": "",
        "randomAdminFilePathFile": "",
    }


def build_output_store(store: Path, base: str) -> int:
    """磁盘输出仓库：<user>/<name>.html。userCanRetrieveContent 读它。"""
    n = 0
    for user, paths in SNAPSHOT.items():
        d = store / user
        d.mkdir(parents=True, exist_ok=True)
        for p in paths:
            name = p.strip("/").replace("/", "_")
            (d / f"{name}.html").write_text(
                f"<html><body><h1>{p}</h1><p>collected by {user}</p></body></html>",
                encoding="utf-8")
            n += 1
    anon = store / "ANONYMOUS"
    anon.mkdir(parents=True, exist_ok=True)
    (anon / "public.html").write_text("<html><body>public</body></html>", encoding="utf-8")
    return n


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=HOST_DEFAULT)
    args = ap.parse_args()
    base = args.base.rstrip("/")

    DATA.mkdir(parents=True, exist_ok=True)
    inputs_file = DATA / "inputs.json"
    out_file = DATA / "engine_out.txt"
    store = DATA / "output_store"

    inputs = build_inputs(base)
    inputs_file.write_text(json.dumps(inputs, ensure_ascii=False, indent=2), encoding="utf-8")

    cfg = build_config(base, inputs_file, out_file, store)
    (DATA / "config.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

    n_files = build_output_store(store, base)

    print(f"[gen] 工作目录      {WORK}")
    print(f"[gen] config        {DATA / 'config.json'}")
    print(f"[gen] inputs        {inputs_file}  ({len(inputs)} 条输入)")
    print(f"[gen] outputStore   {store}  ({n_files} 个 html)")
    print(f"[gen] 用户           {', '.join(SNAPSHOT)}")
    for u, ps in SNAPSHOT.items():
        print(f"[gen]   snapshot[{u}] = {ps}")
    for u, ps in OOB_LIVE.items():
        print(f"[gen]   +oob   [{u}] = {ps}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

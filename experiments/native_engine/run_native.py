"""
原生引擎实验驱动（单命令闭环）
==============================
  python run_native.py [--users N] [--base N] [--mode base|augmented]

流程（必须一条命令走完，因为本机进程树会被回收）：
  1 起 Gitea（独立 ASCII 数据目录）
  2 播种拓扑：N 个用户 / 每人私有仓库 / 每人公开仓库 / 一个组织（拥有者 dave）
  3 **通道自检**：网页仓库页能否用 Basic 认证区分授权？能则用网页 URL，否则退回 API URL
  4 采集期快照 = 变更前各用户在界面上能看到的 URL 集合
  5 带外变更 = 采集**之后**才授予的 repo 级协作（正是边界 1 的关键格）
  6 写 config.json / inputs.json / output_store
  7 跑原生引擎（Java，见 GiteaHttpProvider）
  8 落结果 JSON + 报告

诚实边界：见 DATA_CONTRACT.md §5。通道自检结论会写进结果文件。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
os.environ.setdefault("BOLA_LAB_DIR", r"C:\Users\Administrator\WorkBuddy\gitea_native_lab")
sys.path.insert(0, str(HERE.parent / "real_system"))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import gitea_lab as gl                                                     # noqa: E402
from gitea_lab import Client, Server, ensure_migrated, write_config         # noqa: E402

WORK = Path(r"C:\Users\Administrator\WorkBuddy\mst_native_lab")
DATA = WORK / "data"
OUT = WORK / "out"
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)

PASS = "LabPass123!"
UP, PP = "user_name", "password"
LOGIN_PATH = "/user/login"

ORG = "acme"
ORG_OWNER = "dave"
ORG_MEMBERS = ["alice", "bob", "carol"]
TEAM = "dev"

NAMES = ["alice", "bob", "carol", "dave", "eve", "frank",
         "grace", "hugo", "iris", "jack", "kate", "leo", "mallory"]

# 采集期**之后**才带外授予的共享 —— 边界 1 的关键格
# (仓库 owner/name, 被授予者, 权限)  授予者必须是仓库拥有者或管理员
OOB_GRANTS = [
    ("alice/s1", "bob", "read"),        # bob 在快照里看不到 alice/s1，但事后确实可读
    ("carol/s1", "eve", "read"),
    ("acme/t1", "frank", "read"),       # dave 事后把组织仓库给 frank
]


def win(p) -> str:
    return str(p).replace("\\", "/")


# ==========================================================================
# 1) 拓扑
# ==========================================================================
def topology(users: list[str]) -> dict:
    own = {u: [f"{u}/s{i}" for i in (1, 2, 3)] for u in users}
    pub = [f"{u}/pub" for u in users]
    return {"own": own, "pub": pub, "org_repos": [f"{ORG}/t{i}" for i in (1, 2, 3, 4)]}


def snapshot_urls(u: str, topo: dict, users: list[str]) -> list[str]:
    """采集期该用户**能通过界面看到**的仓库（= GUI 可达性的代理）。"""
    urls = list(topo["own"][u])              # 自己的私有仓库
    urls += list(topo["pub"])                # 所有人的公开仓库
    if u in ORG_MEMBERS or u == ORG_OWNER:
        urls += list(topo["org_repos"])      # 组织成员可见组织仓库
    seen, out = set(), []
    for x in urls:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ==========================================================================
# 2) 播种
# ==========================================================================
def seed(users: list[str], topo: dict, log: list[str]) -> int:
    admin = Client(user=gl.ADMIN_USER, password=gl.ADMIN_PASS, label="root")

    def rec(msg: str) -> None:
        log.append(msg)
        print("   " + msg)

    for u in users:
        st, body = admin.post("/api/v1/admin/users",
                              {"username": u, "email": f"{u}@lab.local",
                               "password": PASS, "must_change_password": False,
                               "must_change_passwd": False})
        rec(f"user {u:8s} -> {st}")

    # ---- 组织：**必须由 ORG_OWNER 创建** ----------------------------------
    # ⚠️ 早先由 admin 建组织 ⇒ owner 是 root ⇒ dave 建组织仓库全部失败，而
    # `snapshot_urls` 仍按拓扑写入 4 个 org 仓库 × 4 名成员 = **16 条指向不存在
    # 对象的 phantom 记录**（输入视图的 10%），第三个带外授予也随之为空。
    # 组织级授权的**授权单位是团队**：成员经团队获得组织仓库读权限。
    dave = Client(user=ORG_OWNER, password=PASS, label=ORG_OWNER)
    st, _ = dave.post("/api/v1/orgs",
                      {"username": ORG, "visibility": "private", "full_name": "Acme"})
    rec(f"org {ORG:10s} (owner={ORG_OWNER}) -> {st}")

    st, tb = dave.post(f"/api/v1/orgs/{ORG}/teams",
                       {"name": TEAM, "permission": "read", "units": ["repo.code"],
                        "includes_all_repositories": False})
    team_id = tb.get("id") if isinstance(tb, dict) else None
    rec(f"team {TEAM:9s} -> {st} (id={team_id})")

    for full in topo["org_repos"]:
        name = full.split("/")[1]
        st, _ = dave.post(f"/api/v1/orgs/{ORG}/repos",
                          {"name": name, "private": True, "auto_init": True})
        rec(f"org repo {full:14s} -> {st}")

    for u in ORG_MEMBERS:                      # 基线：采集**之前**就是团队成员
        st, _ = dave.put(f"/api/v1/teams/{team_id}/members/{u}")
        rec(f"team member {u:8s} -> {st}")
    for full in topo["org_repos"]:             # 基线：组织仓库挂到团队
        st, _ = dave.put(f"/api/v1/teams/{team_id}/repos/{full}")
        rec(f"team repo {full:15s} -> {st}")

    # ---- 用户仓库 ----
    for u in users:
        c = Client(user=u, password=PASS, label=u)
        for full in topo["own"][u] + [f"{u}/pub"]:
            name = full.split("/")[1]
            private = name != "pub"
            st, _ = c.post("/api/v1/user/repos",
                           {"name": name, "private": private, "auto_init": True})
            rec(f"repo {full:14s} -> {st}")

    # ---- 采集期快照就此定格；以下为「带外变更」 ----
    rec("--- 采集期结束，开始带外授权变更 ---")
    for full, grantee, perm in OOB_GRANTS:
        owner = full.split("/")[0]
        c = dave if owner == ORG else Client(user=owner, password=PASS, label=owner)
        st, _ = c.put(f"/api/v1/repos/{full}/collaborators/{grantee}",
                      {"permission": perm})
        rec(f"OOB grant {full:12s} -> {grantee:8s} ({perm}) -> {st}")

    return verify_seed(users, topo)


def verify_seed(users: list[str], topo: dict) -> int:
    """机械核验播种结果：**每个快照对象真的可读、每个带外授予真的生效**。

    ★ 必须做。phantom 记录问题（组织仓库全部建失败而快照照写）正是因为
    全程没有一步校验、所有失败只体现为日志里的一个状态码，才静默通过。
    这里一旦有对象不可读就抛异常，把缺陷变成**硬失败**。

    返回核验的**访问点数**（须落盘：正文引用的数字必须能由产物复算）。
    """
    bad: list[str] = []
    n = 0
    for u in users:
        c = Client(user=u, password=PASS, label=u)
        for full in snapshot_urls(u, topo, users):
            st, _ = c.get(f"/api/v1/repos/{full}/raw/README.md")
            n += 1
            if st != 200:
                bad.append(f"快照对象不可读: {u} -> {full} (HTTP {st})")
    for full, grantee, _perm in OOB_GRANTS:
        c = Client(user=grantee, password=PASS, label=grantee)
        st, _ = c.get(f"/api/v1/repos/{full}/raw/README.md")
        n += 1
        if st != 200:
            bad.append(f"带外授予未生效: {grantee} -> {full} (HTTP {st})")
        if full in snapshot_urls(grantee, topo, users):
            bad.append(f"带外授予在采集期已可见（不是带外）: {grantee} -> {full}")
    print(f"   [verify] 核验 {n} 个访问点")
    if bad:
        for b in bad:
            print("   !! " + b)
        raise RuntimeError(f"播种核验失败 {len(bad)} 项 —— 见上")
    print("   [verify] 全部通过：快照对象可读、带外授予生效且采集期不可见")
    return n


# ==========================================================================
# 3) 通道自检
# ==========================================================================
def probe_channel(users: list[str], topo: dict, log: list[str]) -> dict:
    """返回 {'channel': 'html'|'api', 'evidence': [...]}"""
    ev = []
    owner = "alice"
    target = topo["own"]["alice"][0]                 # alice/s1
    other = "eve"                                     # 未被授权者
    grantee = "bob"                                   # 事后被授权者（OOB_GRANTS 第一条）
    co = Client(user=owner, password=PASS, label=owner)
    cx = Client(user=other, password=PASS, label=other)
    cg = Client(user=grantee, password=PASS, label=grantee)
    ca = Client(label="anon")

    def kind(body, st):
        if st != 200:
            return f"HTTP{st}"
        s = body if isinstance(body, str) else json.dumps(body)
        if s.lstrip().startswith("<!DOCTYPE html>") or "<html" in s[:200].lower():
            return "html-page"
        return "json/other"

    html_ok = True
    for label, c in ((owner, co), (other, cx), (grantee, cg), ("anon", ca)):
        st, body = c.get(f"/{target}")
        k = kind(body, st)
        ev.append({"channel": "html", "url": f"/{target}", "as": label, "status": st, "kind": k})
        print(f"   html /{target} as {label:9s} -> {st} {k}")
    # html 可用判据：拥有者拿到 html-page，且未被授权者与之不同
    st_o, b_o = co.get(f"/{target}")
    st_x, b_x = cx.get(f"/{target}")
    if not (st_o == 200 and "DOCTYPE" in str(b_o)[:200]):
        html_ok = False
    if html_ok and st_x == 200 and str(b_x)[:400] == str(b_o)[:400]:
        html_ok = False   # 拿到同一页 ⇒ 无法区分

    for label, c in ((owner, co), (other, cx), (grantee, cg), ("anon", ca)):
        for suffix in ("", "/raw/README.md"):
            u = f"/api/v1/repos/{target}{suffix}"
            st, body = c.get(u)
            s = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
            ev.append({"channel": "api", "url": u, "as": label,
                       "status": st, "len": len(s)})
            print(f"   api  {u:52s} as {label:9s} -> {st} len={len(s)}")

    channel = "html" if html_ok else "api"
    log.append(f"通道自检结论: {channel}")
    print(f"   => 采用通道: {channel}")
    return {"channel": channel, "evidence": ev}


# ==========================================================================
# 4) 生成引擎数据
# ==========================================================================
def url_of(channel: str, repo: str) -> str:
    """观测目标 URL。

    ⚠️ 申报要点（必须写进正文）：观测到的是**对象内容端点**，即
        `.../raw/README.md` —— 持有读权限的任意用户拿到的**字节完全相同**。
    为什么不用仓库对象端点 `.../repos/{owner}/{repo}`：
        它的 JSON 里带 `permissions` 等**按视点变化**的字段，会让「合法共享」
        与「越权」在比较上无法区分；而 MST-wi 自己的被测目标（Jenkins/Joomla
        的 HTML 页面）比较的是**收到内容**，`userCanRetrieveContent` 的原文定义
        也是 "the output data ... received"。用内容端点才是对原文语义的忠实实例化。
    副产物：小体量响应让引擎自带的 Levenshtein 比较器（阈值 html 0.95 / text 0.7）
        从 O(4KB×4KB) 降到 O(0.2KB×0.2KB)，否则单次比较就要百万级字符运算。
    """
    if channel == "html":
        return f"{gl.BASE}/{repo}"
    return f"{gl.BASE}/api/v1/repos/{repo}/raw/README.md"


def login_action(user: str) -> dict:
    return {
        "text": "Sign In",
        "id": "xpath /HTML[1]/BODY[1]/DIV[1]/FORM[1]/INPUT[1]",
        "element": "Element{node=[INPUT: null], tag=INPUT, text= Sign In}",
        "eventType": "click",
        "currentURL": f"{gl.BASE}/user/login",
        "elementURL": f"{gl.BASE}{LOGIN_PATH}",
        "method": "post",
        "formInputs": [
            {"identification": {"value": UP}, "values": [user]},
            {"identification": {"value": PP}, "values": [PASS]},
        ],
    }


def visit_action(channel: str, repo: str) -> dict:
    u = url_of(channel, repo)
    return {
        "text": repo,
        "id": f"xpath /HTML[1]/BODY[1]/DIV[2]/DIV[1]/A[1]",
        "element": f"Element{{node=[A: null], tag=A, text= {repo}, attributes={{href=/{repo}}}}}",
        "eventType": "click",
        "currentURL": f"{gl.BASE}/",
        "elementURL": u,
        "method": "get",
    }


def build_inputs(users: list[str], topo: dict, channel: str,
                 base_target: int) -> tuple[dict, dict]:
    """返回 ({dbid: [actions...]}, {dbid: partner}).

    partner 决定该基输入要派生出「换成谁的凭证」的那条输入。
    规则：若该 (用户, 仓库) 命中带外授予表，则 partner = 受让者；
          否则 partner = 用户列表里的下一个（确定性轮转）。
    """
    pool: list[tuple[str, str]] = []
    for u in users:
        for repo in snapshot_urls(u, topo, users):
            pool.append((u, repo))

    # 强制包含关键格：alice 的记录里必须有 alice/s1（事后带外共享给 bob）
    forced = [(OOB_GRANTS[0][0].split("/")[0], OOB_GRANTS[0][0])]
    rest = [p for p in pool if p not in forced]
    rest.sort()
    need = max(0, base_target - len(forced))
    chosen = forced + rest[:need]

    grant_map = {(r, g): g for r, g, _ in OOB_GRANTS}
    out: dict = {}
    pairing: dict = {}
    for idx, (u, repo) in enumerate(chosen):
        dbid = f"snapshot|{u}|{repo}"
        out[dbid] = [login_action(u), visit_action(channel, repo)]
        partner = None
        for (r, g) in grant_map:
            if r == repo and g != u:
                partner = g
                break
        if partner is None:
            i = users.index(u)
            partner = users[(i + 1) % len(users)]
            if partner == u and len(users) > 1:
                partner = users[(i + 2) % len(users)]
        pairing[dbid] = partner
    return out, pairing


def build_config(inputs_file: Path, out_file: Path, store: Path) -> dict:
    return {
        "SUT": "Gitea-1.22.6-Lab",
        "inputFile": win(inputs_file),
        "outputFile": win(out_file),
        "outputStore": win(store),
        "loginParams": [{"loginURL": f"{gl.BASE}{LOGIN_PATH}",
                         "userParameter": UP, "passwordParameter": PP}],
        "supervisedUser": {ORG_OWNER: ORG_MEMBERS},
        "headless": True,
        "ignoreURLs": [],
        "errorSigns": {"title": ["Not Found", "Internal Server Error", "Sign In"]},
        "randomFilePathFile": "",
        "randomAdminFilePathFile": "",
    }


def build_output_store(store: Path, users: list[str], topo: dict) -> int:
    """写采集期输出记录。

    ⚠️ 必须**成对**写 `<name>.html` 与 `<name>.txt`：上游 loader
    （WebOperationsProvider.java:177-179）用
        textFileName = <html 文件名去掉 4 个字符> + "txt"
    去读同名文本文件。若缺 .txt，outCleaned.text 为 null，谓词比较
    （WebOutputCleaned._compare）在 null 侧会抛异常/退化，构成一处
    不必要的偏离。返回 html 文件数（与旧口径可比）。
    """
    n = 0
    for u in users:
        d = store / u
        d.mkdir(parents=True, exist_ok=True)
        for repo in snapshot_urls(u, topo, users):
            base = repo.replace("/", "_")
            (d / (base + ".html")).write_text(
                f"<html><body><h1>{repo}</h1><p>collected by {u}</p></body></html>",
                encoding="utf-8")
            (d / (base + ".txt")).write_text(
                f"{repo} collected by {u}", encoding="utf-8")
            n += 1
    anon = store / "ANONYMOUS"
    anon.mkdir(parents=True, exist_ok=True)
    (anon / "root.html").write_text(
        "<html><body>anonymous</body></html>", encoding="utf-8")
    (anon / "root.txt").write_text("anonymous", encoding="utf-8")
    return n


# ==========================================================================
# 5) 跑 Java
# ==========================================================================
def run_engine(mode: str, log: list[str]) -> dict:
    """跑 Java。⚠️  stdout 必须落盘而不是 capture —— 引擎输出可达数十万行，
    capture 会把它全塞进内存，而且出问题时看不到进度。"""
    build = HERE / "build_run.sh"
    OUT.mkdir(parents=True, exist_ok=True)
    jlog = OUT / f"java_{mode}.log"
    res = OUT / f"result_{mode}.json"
    # ⚠️ 必须先删掉旧结果。否则一旦引擎崩溃 / 被杀，下面 `if not res.exists()`
    # 会看到**上一次**留下的文件而静默把它当成本次产物返回。
    # 2026-09-18 真实踩到：被杀的那一轮让 native_engine.json 里装的是 40 分钟前
    # 另一次（且是被淘汰的）运行的结果，而流程一路绿灯。
    if res.exists():
        res.unlink()
    t_start = time.time()
    with open(jlog, "w", encoding="utf-8", errors="replace") as f:
        subprocess.run(["bash", str(build), mode], stdout=f,
                       stderr=subprocess.STDOUT, cwd=str(HERE),
                       env=dict(os.environ))
    lines = jlog.read_text(encoding="utf-8", errors="replace").splitlines()
    n_exc = sum(1 for x in lines if "Exception" in x or "\tat " in x)
    log.append(f"java_stdout_lines={len(lines)} exception_lines={n_exc}")
    # 全量日志留档：告警的**完整分类**必须读它。
    # 理由：产物里的 failure_samples 每关系只留 8 条（RunAuthzMRs 的截断），
    # 而引擎每次 fail() 的 verbose 文本在 stdout 里是全的 ⇒ 日志才是完整来源。
    shutil.copyfile(jlog, RESULTS / jlog.name)
    for line in lines[-20:]:
        print("   " + line)
    log.extend(lines[-20:])
    if not res.exists():
        raise RuntimeError(f"引擎未产出 {res}（日志 {jlog}，{len(lines)} 行）")
    if res.stat().st_mtime < t_start - 1:
        raise RuntimeError(
            f"{res} 的修改时间早于本次启动（{res.stat().st_mtime:.0f} < {t_start:.0f}）"
            f" —— 产物不可信，拒绝返回")
    return json.loads(res.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=13)
    ap.add_argument("--base", type=int, default=160)
    ap.add_argument("--mode", default="augmented")
    ap.add_argument("--seed-only", action="store_true",
                    help="只播种+核验+生成引擎数据，不跑引擎（冒烟用，约 60s）")
    args = ap.parse_args()

    users = NAMES[:max(3, min(args.users, len(NAMES)))]
    topo = topology(users)
    log: list[str] = []
    t0 = time.time()

    cfg = write_config()
    ensure_migrated(cfg)
    report: dict = {"users": users, "base_target": args.base, "mode": args.mode}

    with Server(cfg) as srv:
        report["gitea"] = {"base": gl.BASE, "ready_ms": srv.ready_ms,
                           "version": gl.version()}
        print("[1] 播种")
        n_seed_verified = seed(users, topo, log)
        print("[2] 通道自检")
        report["channel"] = probe_channel(users, topo, log)

        print("[3] 生成引擎数据")
        channel = report["channel"]["channel"]
        DATA.mkdir(parents=True, exist_ok=True)
        OUT.mkdir(parents=True, exist_ok=True)
        store = DATA / "output_store"
        inputs, pairing = build_inputs(users, topo, channel, args.base)
        inputs_file = DATA / "inputs.json"
        inputs_file.write_text(json.dumps(inputs, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        pairing_file = DATA / "pairing.json"
        pairing_file.write_text(json.dumps(pairing, ensure_ascii=False, indent=2),
                                encoding="utf-8")
        cfg_json = build_config(inputs_file, DATA / "engine_out.txt", store)
        (DATA / "config.json").write_text(json.dumps(cfg_json, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
        n_store = build_output_store(store, users, topo)
        report["data"] = {
            "base_inputs": len(inputs), "store_files": n_store,
            "pairing_entries": len(pairing),
            "pairing_sample": dict(list(pairing.items())[:5]),
            "snapshot_size": {u: len(snapshot_urls(u, topo, users)) for u in users},
            "oob_grants": [{"repo": r, "grantee": g, "perm": p} for r, g, p in OOB_GRANTS],
            "key_cell": {"repo": OOB_GRANTS[0][0], "grantee": OOB_GRANTS[0][1],
                         "in_snapshot_of_grantee":
                             OOB_GRANTS[0][0] in snapshot_urls(OOB_GRANTS[0][1], topo, users)},
            # 播种期机械核验通过的**访问点数**（每个快照对象可读 + 每个带外授予生效
            # 且在采集期不可见）。正文引用该数字时由此复算，不手敲。
            "seed_verified_points": n_seed_verified,
        }
        print(f"   base_inputs={len(inputs)} store={n_store}")
        if args.seed_only:
            print("[seed-only] 到此为止（不跑引擎）")
        else:
            print("[4] 运行原生引擎")
            report["engine"] = run_engine(args.mode, log)

    report["elapsed_s"] = round(time.time() - t0, 1)
    report["log_tail"] = log if args.seed_only else log[-40:]
    out_json = RESULTS / ("seedcheck.json" if args.seed_only else "native_engine.json")
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[ok] {out_json}  ({report['elapsed_s']}s)")
    print(json.dumps(report.get("engine", {}).get("counters", {}), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

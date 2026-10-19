"""核对回复信里的承重数字是否与生成器当前输出一致。

每条检查 = (编号, 说明, 信中正则, 宏名元组)。设计要点：

* 正则里**每个捕获组**对应宏名元组里的一个宏，脚本把捕获到的字面值与宏的
  **当前值**做数值比较。宏变了而信没跟上，这里就报错；信写了而宏不存在，
  val() 直接 FATAL。
* 若正则里直接写了宏命令（如 \\BlSharedProbes{}），该处数字由 LaTeX 渲染保证，
  不再做值比较，只要求正则可命中（防止宏被删/改名）。
* 没有宏的条目只要求正则可命中（结构件：页数、表数、恒等式等）。

用法：python check_letter_numbers.py
退出码 0 = 全部一致；1 = 有不一致（逐条打印）。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LETTER = os.path.join(HERE, "response_to_reviewers.tex")
RESULTS = os.path.normpath(os.path.join(HERE, "..", "..", "04_绘图与分析", "results"))

# 信里偶发把数字写成英文单词，比较时先归一
WORDNUM = {"fifteen": "15", "eight": "8", "twelve": "12", "twenty": "20"}


def load_macros():
    """宏名 -> (值, 来源文件)"""
    out = {}
    for name in sorted(os.listdir(RESULTS)):
        if not name.endswith(".tex"):
            continue
        txt = open(os.path.join(RESULTS, name), encoding="utf-8").read()
        for m in re.finditer(r"\\newcommand\{\\([A-Za-z]+)\}\{([^}]*)\}", txt):
            out[m.group(1)] = (m.group(2), name)
    return out


MACROS = load_macros()


def val(macro):
    if macro not in MACROS:
        raise SystemExit(f"[FATAL] 宏 {macro} 不在任何生成文件里")
    return MACROS[macro][0]


def as_float(text):
    s = text.strip()
    if s in WORDNUM:
        s = WORDNUM[s]
    return float(s)


# (编号, 说明, 信中正则, 宏名元组；None = 只要求命中)
CHECKS = [
    # ---- R1.7 竞争基线 ----
    ("B-cells", "42 个受控格", r"same (\d+) controlled cells", ("BlCells",)),
    ("B-extra", "27 个报警格多一次自省读取", r"on the (\d+) cells where a relation alarms", ("BlOursExtraCells",)),
    ("B-extra-avg", "均值 0.64 次/格", r"\((\d\.\d+) per cell on average", ("BlOursExtraAvg",)),
    ("B-shared", "共享探测 84 次", r"\\BlSharedProbes\{\} shared probes in all", ("BlSharedProbes",)),
    ("B-extra-total", "额外读取合计 27 次", r"\\BlOursExtraTotal\{\} reads in total", ("BlOursExtraTotal",)),
    ("B-total-req", "ours 总请求 111 次", r"ours issues \\BlOursRequestsTotal\{\} requests", ("BlOursRequestsTotal",)),
    ("B-b1-claims", "B1/B2 各宣称 27", r"B1 and B2 claim on all\s+(\d+) allowed cells", ("BlBOneClaims",)),
    ("B-b1-fp", "B1/B2 各 12 个假确证", r"allowed cells with (\d+) false proofs each", ("BlBOneFP",)),
    ("B-b1-prec", "B1/B2 精度 55.56%", r"\(precision (\d+\.\d+)\\%\)", ("BlBTwoPrecision",)),
    ("B-b3", "B3 宣称 21 / 6 个假证明", r"B3 claims (\d+) with\s+(\d+) false proofs", ("BlBThreeClaims", "BlBThreeFP")),
    ("B-b3-prec", "B3 精度 71.43%", r"false proofs \((\d+\.\d+)\\%\)", ("BlBThreePrecision",)),
    ("B-ours-claims", "ours 宣称 10", r"and ours claims (\d+) with\s+no false proof", ("BlOursClaims",)),
    ("B-ours-abstain", "ours 17 弃权", r"but (\d+) abstentions \(coverage", ("BlOursAbstain",)),
    ("B-ours-cov", "ours 覆盖 59.52%", r"abstentions \(coverage (\d+\.\d+)\\%\)", ("BlOursCoverage",)),
    ("B-recall-dec", "条件召回 100%", r"on the cells ours rules on, recall is (\d+)\\%", ("BlOursRecallDecided",)),
    ("B-viol-cells", "15 个真违规格", r"over all (\d+) violation\s+cells", ("BlBolaCells",)),
    ("B-abst-viol", "其中弃权 5 个", r"including the (\d+) it abstains on", ("BlOursAbstainViol",)),
    ("B-recall-all", "总召回 66.67%", r"total recall is (\d+\.\d+)\\%", ("BlOursRecallAll",)),
    ("B-rs-b2", "Gitea 快照 25 个合法格", r"fires on all (\d+) legitimately allowed cells", ("BlRsBTwoClaims",)),
    ("B-rs-b3", "in-band 日志后剩 24", r"still leaves (\d+),", ("BlRsBThreeClaims",)),
    ("B-rs-rate", "0.96 不可观测", r"does not observe (\d\.\d+) of the effective", ("ResRsChannelNotObservableRate",)),
    ("B-seconds", "整轮 22.5 s", r"ran in \\BlRunSeconds\{\}~s of wall-clock", ("BlRunSeconds",)),
    # ---- 时序 ----
    ("T-cells", "712 个跨凭证格", r"the (\d+) temporal cells", ("TmpBothCells",)),
    ("T-gitea", "Gitea 280 格 / 13 个陈旧假确证", r"Gitea (\d+)\s+cells with (\d+) stale false proofs", ("TmpCells", "TmpStaleFP")),
    ("T-fixed-g", "Gitea 修好 13", r"all (\d+) repaired by a recrawl", ("TmpFixed",)),
    ("T-gitlab", "GitLab 432 格 / 16 个陈旧假确证", r"GitLab CE (\d+) cells with (\d+)\s+stale false proofs", ("TmpGCells", "TmpGStaleFP")),
    ("T-fixed-l", "GitLab 修好 16", r"all (\d+) repaired and 0 under live reading", ("TmpGFixed",)),
    ("T-both", "合计修好 29/29", r"repairs (\d+) of (\d+)", ("TmpBothFixed", "TmpBothStaleFP")),
    ("T-loop-g", "Gitea 环 21.2 s", r"Gitea (\d+\.\d+)~s", ("CvgLoopGiteaTotal",)),
    ("T-loop-l", "GitLab 环 7.3 s", r"GitLab (\d+\.\d+)~s", ("CvgLoopGitlabTotal",)),
    ("T-probe", "探针 20.7 / 6.0 s", r"probes are (\d+\.\d+)~s and (\d+\.\d+)~s", ("CvgLoopGiteaProbe", "CvgLoopGitlabProbe")),
    # ---- 真值表 / 命题 ----
    ("P-records", "576 条构造记录", r"against (\d+) constructed records", ("DsgRecords",)),
    ("P-cells", "712 个时序格", r"and (\d+) temporal cells with zero", ("TvtCells",)),
    ("P-agree", "584 个可读格中 530 一致", r"coincide in (\d+) of the (\d+)\s+readable cells", ("TvtAgree", "TvtReadable")),
    ("P-row6", "行 6 为 40 格", r"(\d+) cells\s+where the model is right and the oracle wrong", ("TvtOracleWrong",)),
    ("P-row7", "行 7 为 14 格", r"and (\d+) where the model is stale", ("TvtModelWrong",)),
    # ---- 576 枚举对账 ----
    ("D-grid", "S3--S7 原始 54 条", r"original grid of (\d+) records", ("DsgGridN",)),
    ("D-v2fp", "其中 8 条 v2 假证明", r"which contains (\d+) v2 false proofs", ("DsgGridVtwoFP",)),
    ("D-union", "并集恰为 576", r"union is exactly\s+(\d+)", ("DsgRecords",)),
    ("D-split", "312 可读 / 264 不可读", r"split (\d+) readable / (\d+) unreadable", ("DsgFullOn", "DsgFullOff")),
    ("D-identity", "加法恒等式 44·2·3·2+8·3·2=576", r"\$44\\cdot2\\cdot3\\cdot2\+8\\cdot3\\cdot2=576\$", None),
    # ---- 覆盖率 / 弃权 ----
    ("C-req-total", "4833 次枚举请求", r"(\d+) enumeration requests", ("CvgReqTotal",)),
    ("C-req-med", "中位 8 次", r"median (\d+),", ("CvgReqMedian",)),
    ("C-req-range", "范围 7--10", r"range (\d+)--(\d+)", ("CvgReqMin", "CvgReqMax")),
    ("C-probe", "104 次探针 GET", r"and (\d+) probe \\texttt\{GET\}s", ("CvgProbeGets",)),
    ("C-direct-cov", "direct 覆盖 54.17%", r"contract \(coverage (\d+\.\d+)\\%", ("CvgObsCoveragePct",)),
    ("C-forced-miss", "forced-negative 漏 108", r"coverage 100\\%, (\d+) misses", ("CvgForcedObsFN",)),
    ("C-forced-risk", "forced-negative 风险 18.75%", r"risk (\d+\.\d+)\\%---", ("CvgForcedObsRiskPct",)),
    # ---- native 三段 ----
    ("N-A", "A = 6 原生报警", r"getFailures\(\)\} alarms, (\d+);", ("NtAlarms",)),
    ("N-H", "H = 6 升格后仍为 6", r"\$H\$, our promotion policy applied to them, (\d+);", ("NtStageH",)),
    ("N-T", "T 确认 0 / 假证明 6", r"\$T\$, confirmed, (\d+)---with (\d+) false proofs", ("NtStageTTrue", "NtStageTFalse")),
    ("N-mr-total", "11 条目录关系", r"Of the \\NtMrTotal\{\} catalog authorization relations", ("NtMrTotal",)),
    ("N-mr-exec", "10 条执行", r"\\NtMrExecuted\{\} ran", ("NtMrExecuted",)),
    ("N-mr-err", "1 条中止", r"and \\NtMrErrored\{\} aborted", ("NtMrErrored",)),
    ("N-mr-fired", "2 条报警", r"\(\\NtMrFired\{\} relations", ("NtMrFired",)),
    ("N-alarms-all", "共 6 条报警", r"\\NtAlarms\{\} alarms in all", ("NtAlarms",)),
    # ---- 制品 ----
    ("A-pages", "正文 27 页", r"revised manuscript \((\d+) pages", None),
    ("A-tables", "23 张表", r"(\d+) tables\)", None),
    ("A-zip", "源码包 90 文件", r"(\d+)-file submission package", None),
    ("A-artefacts", "31 个逐位复现输出", r"all (\d+) byte-reproducible\s+outputs", None),
    # ---- Gogs 渠道矩阵（R1.8）----
    ("G-ch-cells", "Gogs 渠道矩阵 48 格", r"the same \\GgChCells\{\} snapshot cells", ("GgChCells",)),
    ("G-ch-collab", "直接协作者 4 格全对", r"all \\GgChCollaboratorAgree\{\}\s+direct-collaborator cells", ("GgChCollaboratorAgree",)),
    ("G-ch-none", "无授予 27 格全对", r"and all \\GgChNone\{\} cells with no\s+recorded grant", ("GgChNone",)),
    ("G-ch-fd", "17 个假拒绝", r"on all \\GgChFalseDeny\{\} cells whose", ("GgChFalseDeny",)),
    ("G-ch-fd-team", "团队渠道 4 个假拒绝", r"team membership \(\\GgChTeamFalseDeny\{\}\)", ("GgChTeamFalseDeny",)),
    ("G-ch-fd-public", "公开渠道 5 个假拒绝", r"public visibility\s+\(\\GgChPublicFalseDeny\{\}\)", ("GgChPublicFalseDeny",)),
    ("G-ch-fd-admin", "管理员渠道 8 个假拒绝", r"site administration\s+\(\\GgChSiteAdminFalseDeny\{\}\)", ("GgChSiteAdminFalseDeny",)),
    ("G-ch-fa", "0 个假允许", r"no false \\emph\{allow\}\s+anywhere \(\\GgChFalseAllow\{\}\)", ("GgChFalseAllow",)),
    ("G-ch-multi", "1 个多渠道重叠格", r"\\GgChMultiBasis\{\} cell carries two", ("GgChMultiBasis",)),
    ("G-ch-probe-perm", "permission 后缀 404", r"permission suffix returns \\GgChProbePermSuffix\{\}", ("GgChProbePermSuffix",)),
    ("G-ch-probe-team", "逐对象团队路由 404", r"per-object team route\s+\\GgChProbeTeamMember\{\}", ("GgChProbeTeamMember",)),
    ("G-ch-probe-collab", "协作路由 204", r"collaboration route the oracle consults\s+\\GgChProbeCollabGet\{\}", ("GgChProbeCollabGet",)),
    ("G-ch-probe-orgteams", "组织团队列表 200", r"organisation team listing is reachable\s+\(\\GgChProbeOrgTeams\{\}\)", ("GgChProbeOrgTeams",)),
    ("G-ch-live", "live 读法 31 一致 / 17 假拒绝", r"\(\\GgChLiveAgree\{\} agreements and \\GgChLiveFalseDeny\{\} false denials", ("GgChLiveAgree", "GgChLiveFalseDeny")),
    ("G-ch-src", "来源轴小样本 4/5/8", r"\(\\GgChSrcTeam\{\},\s+\\GgChSrcPublic\{\} and \\GgChSrcSiteAdmin\{\} cells\)", ("GgChSrcTeam", "GgChSrcPublic", "GgChSrcSiteAdmin")),
]


def main() -> int:
    letter = open(LETTER, encoding="utf-8").read()
    flat = re.sub(r"\s+", " ", letter)

    bad = []
    for cid, desc, pattern, macros in CHECKS:
        m = re.search(pattern, flat)
        if m is None:
            bad.append((cid, desc, f"正则未命中: {pattern}"))
            continue
        if not macros:
            continue
        # 模式里直接写了宏命令 => 该数字由 LaTeX 渲染保证，只需捕获组对齐剩余宏。
        # 模式是正则源码，宏命令可能以 \BlX{} 或转义形式 \\BlX\{\} 出现，两种都认。
        def is_ref(mac):
            return ("\\" + mac + "{}") in pattern or ("\\\\" + mac + "\\{\\}") in pattern

        referenced = [mac for mac in macros if is_ref(mac)]
        pending = [mac for mac in macros if not is_ref(mac)]
        if referenced and pending:
            bad.append((cid, desc, "模式同时混用宏引用与字面值，无法对齐，请拆成两条"))
            continue
        groups = [g for g in m.groups() if g is not None]
        if len(groups) < len(pending):
            bad.append((cid, desc, f"捕获组 {len(groups)} 个 < 待比宏 {len(pending)} 个"))
            continue
        for g, macro in zip(groups, pending):
            want = val(macro)
            try:
                got = as_float(g)
                exp = as_float(want)
            except ValueError:
                bad.append((cid, desc, f"信中写 {g!r}，宏 {macro}={want}（非数值）"))
                continue
            if abs(got - exp) > 1e-9:
                bad.append((cid, desc, f"信中写 {g}，宏 {macro}={want}"))
    if bad:
        print(f"[FAIL] {len(bad)} 处不一致：")
        for cid, desc, why in bad:
            print(f"  {cid:14s} {desc:28s} {why}")
        return 1
    print(f"[ok] {len(CHECKS)} 项承重数字与生成器当前输出一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())

from pathlib import Path

rev = Path("06_论文追踪/2026-10-18_IEEEAccess重投诊断/本轮决定信与审稿意见_原文.txt").read_text(encoding="utf-8")
rev = rev[rev.index("Reviewers' Comments to Author:"):]

main = Path("03_论文撰写/paper/main.tex").read_text(encoding="utf-8")
abstract = main[main.index(r"\begin{abstract}") + len(r"\begin{abstract}"):main.index(r"\end{abstract}")]

prop_src = Path("03_论文撰写/paper/sections/06_boundaries.tex").read_text(encoding="utf-8")
prop = prop_src[prop_src.index(r"\begin{proposition}"):prop_src.index("The proposition concerns")]
concl = Path("03_论文撰写/paper/sections/09_conclusion.tex").read_text(encoding="utf-8")
concl_body = concl[:concl.index(r"\paragraph{What we do not claim")]

head = """你是 IEEE Access 的资深副编辑，同时扮演这次拒稿的两位审稿人（R1 给了 15 条，R2 给了 6 条）。下面是完整材料，请全部读完再回答。

【任务】
A. 逐条裁决：21 条每条给 closed / partially / open，并写明"还缺的那一个具体证据或那一句表述"。复述已完成工作不算裁决。
B. 哪 5 条在重投时最可能再次导致 reject？按"审稿人会在哪里抓住它"写。
C. 文本级处方（只给要点与可用句式）：命题 2 的同义反复风险；specificity 分母；旧的 blind/aware 错配与"不能裁决真正违规"一类旧句；标题/摘要/结论如何按现有证据收窄。
D. 两天计划：必须做 / 应当做 / 可以放弃，并指出哪些工作即使做完也不会改变裁决（不要做）。

【约束】不要建议需要新数据集或新产品的实验；不要建议撤销已有实验；现有证据边界如实承认。中文，1800 字以内，用 A/B/C/D 标题分段。

==================== 审稿意见原文 ====================
"""

state = """

==================== 已完成的工作与现有证据（作者自述，数字均可在产物中核对） ====================

A 包（真值与裁决分离）
- E（期望授权）只由台账推导：setup 事务 + 带外变更事务 + 六类继承规则（owner/org owner/site admin/public/collaborator/team），禁用任何探针响应、oracle 答案或观测效果。
- Y（观测效果）改为内容级：读用 sha256 与拥有者复读一致；写用"主体建唯一文件 → 拥有者逐字节复读 → 拥有者删除并复读 404"。三系统（Gitea 1.22.6 / Gogs 0.14.3 / GitLab 17.11.7）共 120 个换凭证写格，E==Y 120/120，越权写 0，状态码与内容不一致 0。两条限制如实入文：Gogs contents API 无 DELETE（restore 不支持）；site_admin 在 Gogs/GitLab 实际不可写（那 24 行剔除为 control）。
- 裁决器阶梯重排为 raw（触发即 violation-proven，无例外谓词）< v1（存在性过滤）< v2（存在性+操作覆盖）< v3 < degrade_all，另有 direct_only/direct_observe。576 条全矩阵重跑后 v1/v2/v3/degrade_all 计数与旧结果逐项相同；raw 比 v1 多 75 个告警（333 vs 258）。旧结果已归档作为同源证明。
- v3 的 228 次弃权拆为 156 次 oracle 不可读 + 72 次合法覆盖共享。
- native 三段分离：源码核实 MR.fail() 只写 FAILURE 日志、不做任何授权判定；拆成 A=6 原生报警 / H=6（本文升格策略，按构造）/ T=确认违规 0、假证明 6（覆盖 3 格）。

E 包（真实 vulnerable/fixed 配对）
- Gitea 1.20.5（脆弱）→ 1.20.6（修复），修复条目 "Fix comment permissions"（#28213/#28216），同缺陷在 Forgejo 侧为 CVE-2023-49946；两版二进制 sha256 与官方 .sha256 逐字节核对。
- 缺陷是评论 edit/delete 缺"对象归属"校验：bob 借自己公开仓库的路径、传 alice 私有仓库的评论 id，1.20.5 返回 200 且拥有者复读到被改内容；1.20.6 返回 404 且内容不变。
- 结果：TP 1 / 假证明 0 / 修复版告警 0；每版 5 条对照（共 10 条）全部符合预期；恢复 2/2。正文明确：这证明 E/Y 闸门在真缺陷上会正确主张、修复后停止主张，不证明"我们能发现这类缺陷"，不是有效性估计。

B 包（真时序，双产品）
- 预注册协议 c_protocol.json（sha256 d09d9047…），先冻结再开跑；hv 明确为 harness 逻辑版本，不是服务器原子快照。
- Gitea 1.22.6：8 个转移、7 对象、5 用户+匿名 = 280 换凭证格。E==Y 280/280，0 弃权，8/8 事务提交、8/8 M0 摘要未变、8/8 版本一致。陈旧假确证 13（直授 1、团队继承 1、private→public 5、site-admin 6），同权限 recrawl 修好 13/13，仍漏 0，live 假确证 0，真实违规 0。撤销侧陈旧高估 7，全部被 enforcement 拒绝。oracle：owner 视点 224/280，自视点仅 7/280（全在 admin 授予后）。
- GitLab CE 17.11.7：同协议、独立容器全新卷，8 转移、9 对象、6 用户+匿名 = 432 格。E==Y 432/432，0 弃权，8/8 事务、8/8 摘要、8/8 版本一致。陈旧假确证 16，修好 16/16，仍漏 0，live 假确证 0，真实违规 0。撤销侧陈旧高估 10。
- 两份修正案在观察任何 GitLab 响应之前写下：A1 校准门槛改为主视点 4/4（副视点本就未被协议承认为 oracle，只作诊断列）；A2 多通道测试的替代通道从组内直授移到组外个人项目——首轮试跑发现 GitLab 在移除组成员时会连带删除该组项目的项目级成员记录（直接成员列表从 1 条变 0 条），不把这条未文档化的产品规则编码进台账。
- oracle 保真度：GitLab 的 members/all 对任何项目成员可读，自视点可答 360/432；但它回答的是"是不是成员"，对公开仓库非成员、对站点管理员都返回 404，与台账分歧 53 格，全部落在 public（44）与 site_admin（9）通道。Gitea 端点则与台账 0 分歧。结论：可读 ≠ 可靠，admissibility 不能只靠可读性。

尚未完成的已知缺口
- 没有多种独立故障模式的阳性对照（现有 3 个 seeded 实例是同一故障模式，加上 1 个真实配对）。
- 没有竞争性多账户差分基线（匹配预算、逐方法成本）。
- R1.8 要求的分渠道混淆矩阵只做了部分（时序实验给出 public 44 / admin 9 两个通道的分歧计数）。
- 命题 2 仍可能被读成同义反复。
- specificity 分母仍是输入级。
- 正文仍有少量旧表述与新证据不一致。

==================== 当前正文（节选） ====================

【摘要】
"""

tail = """

【命题 2 现状】
"""

tail2 = """

【结论里的旧句】
"Across the statuses the oracle can take, the outcomes the evaluated relations can yield are thus a false proof, a result no better than the plain request (and, where the oracle is readable, worse), or an abstention; adjudication of a genuinely illegal access is not among them for these relations."

【结论正文】
"""

full = head + rev + state + abstract + tail + prop + tail2 + concl_body
Path(".review_full_prompt.txt").write_text(full, encoding="utf-8")
print("chars", len(full))

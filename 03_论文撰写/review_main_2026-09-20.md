# 审稿报告：Limits of Metamorphic Testing for Object-Level Authorization

**期刊**：Journal of Information Security and Applications（JISA）
**稿件**：main.pdf（13 页，双栏，cas-dc 模板）
**审稿日期**：2026-09-20
**总体建议**：**Major Revision**（大修后再审）

---

## 1. 论文概述

本文对 MST-wi（Chaleshtari et al., TSE 2023）这一基于蜕变测试的 Web 安全测试方法在对象级授权（BOLA）场景下的适用性边界做了方法学刻画，提出三个发现：

- **F1（时间边界）**：谓词把裁决委托给爬取时刻冻结的可达性快照，带外（out-of-band）授权变更后被判定为"已证明的违规"——确定性假证明（false proof）。
- **F2（oracle 边界）**：当存在可读、可靠的授权 oracle 时，蜕变步骤相对"直接观察"（同一 oracle + 请求结果）没有可观察的增量裁决收益（Lemma 1 给出必要条件）。
- **F3（度量边界）**：文献报告的输入级特异度（specificity）对场景级一致性失效可被任意稀释（Proposition 1 及推论）。

证据链：576 条记录的构造系统场景/配置研究 + Gitea 1.22.6 真实系统研究（含内源性对照）+ Gogs 0.14.3 / GitLab 17.11.7 跨厂商复制 + 原生引擎（源码零修改）执行 + 播种漏洞阳性对照。作者明确声明：不提出新机制、不报告 MST-wi 的灵敏度/特异度、结论限于两条 MR、一个门控家族。

## 2. 优点（审稿人认可的部分）

1. **方法学诚实度罕见地高。** 每个发现都附了证伪条件（§6.4）；统计上把记录明确定性为"固定枚举而非样本"，拒绝挂推断区间；RQ2 比较报告不一致对数而非显著性检验；§7 "Our own earlier claims" 公开记录了自己早期不成立的主张并给出任何类似主张必须满足的条件。这是本稿最突出的品质。

2. **原生引擎执行是最强证据。** 上游 Java 源码零修改（仅 1 行 pom.xml + 612 行外部 harness），直接在 Gitea 上复现了假证明（6 个告警全部落在 3 个带外授权 cell 上），排除了"复现实现的偏差"这一最常见的反驳。带内/带外、快照/实况的两把"故意开关"设计干净。

3. **内源性对照设计漂亮。** 两个最终同样公开、但公开时刻不同的对象，把"可见性"与"读取时刻"解耦（Table 5：after-crawl 5/6 触发 vs from-start 0/6），这是全文最有说服力的单项实验。

4. **可复现性工程化程度高。** 全部数字由管线从原始记录重算（正文零手敲数字）、GitHub artifact + Zenodo DOI、SHA-256 完整性校验。我抽查了关键数字的内部一致性：消融表各方法 TP+FN=216、FP+TN=360；recall 差 0.0139 = 3/216 与不一致对数吻合；Corollary 1 的阈值 m > (fa/s)·t/(1−t) 代数推导正确。

5. **跨厂商复制发现了真实现象**：Gogs 上 oracle 可读但不可靠（31/48 一致），可读的盲区被转译成 8 个假证明——"readability does not imply soundness" 这一观察对后续工作有实际价值。

## 3. 主要问题（Major Concerns）

### M1. F2 与 F3 的形式化内核是平凡的，贡献的实际含量必须更明确地论证

Lemma 1 陈述的是"V = f(O,R) 与 D := f(O,R) 逐点相等"——这是 f=f 的同义反复，其证明自认"同一个函数作用于同一对参数"。Proposition 1 是初等比例稀释算术。作者对此是坦白的（"a necessary condition, not an empirical surprise"），但一篇期刊论文的贡献不能只靠"我们严谨地陈述了一个平凡事实"。真正有经验含量的命题其实是：**"被评估的 MR 族在 oracle 完备时的裁决是 (O,R) 的函数"**——这是源码检查 + 实验才确立的经验前提，而 Lemma 把它藏在了形式化外衣里。建议把 Lemma 1 重写为以该经验前提为主体的命题，并删减与推论重复的表述。

同理，F3 的实践价值不在 Proposition（任何人都能看出分母稀释），而在于"99.81% 这个已发表数字没有以模型=授权态为条件"这一针对具体文献的测量批评。建议把表述重心从"我们证明了一个稀释性质"移到"我们指出了一个已发表度量的具体失效模式"。

### M2. 【最重要】Table 1 中 v1/v2 的 recall（0.92/0.99）与 direct_observe 的 0.50 形成刺眼的不对称，论文没有正面处理

这是我认为必须解决的核心问题。消融表（Table 1）显示：

| 方法 | recall | FP |
|---|---|---|
| v1 (raw) | 0.92 | 60 |
| v2 (exception-aware) | **0.99** | 60 |
| v3 (oracle-gated) | 0.49 | 0 |
| direct_observe | 0.50 | 0 |

"无增量收益"的结论只在 **v3 vs direct_observe** 之间成立（0 FP 平局、3 条不一致记录）。但 v2 作为最接近"已发表技术实际行为"的裁决器，recall 是 direct_observe 的两倍。论文的逻辑是：direct_observe 在 oracle 缺失层必须弃权，所以 recall 只有 0.50，而 v2 在该层照常告警。**但这恰恰意味着：MR 步骤的全部增量价值都在"无 oracle"的层——也就是蜕变测试存在的理由所在的那一层——而论文对这一层只做了裁决（adjudication）分析，没做检测（detection）分析。**

后果有二：

1. **F2 的实际含义被读弱了。** 仔细限定后 F2 说的是"当你已经拥有可读、可靠、完备的 oracle 时，不需要 MT"。而作者自己的 Table 3 显示：黑盒主体视角下该 oracle **从不**可读（0/40）。也就是说 F2 的前提条件在 MST-wi 针对的黑盒场景中从不成立。一个诚实的表述是：**F1+F2 联合起来蕴含——在黑盒场景中，该技术要么产生假证明、要么必须弃权，即它根本无法裁决。** 这比两个发现各自都更强、也更有攻击性的结论，论文在 §6.4 末尾擦边而过（"where it does not, the honest method abstains"）但没有点破。建议明确写出。

2. **缺失的补充分析：oracle 缺失层的检测价值。** 在该层，v2 告警覆盖了绝大多数真违规（v2 全表 FN=3），代价是 60 个 FP/假证明。对人工分析者而言告警的价值不为零。一篇"刻画"论文应完成刻画：请报告 oracle 缺失层内 v1/v2 相对某个无 oracle 基线（如朴素差分探测）的 precision/recall，明确 MT 在其设计场景中到底带来多少检测信号、付出多少假证明代价。缺了这块，F2 会被审稿人和读者质疑为"打了稻草人之后的胜利"。

### M3. 泛化天花板与实际显著性的落差需要更诚实的定价

作者自己承认（§7 "two MRs, one family" 是 single most important limitation），但以下几点叠加后，实际结论比标题暗示的窄得多：

- 只实例化了 2 条 MR（76 条目录中的 2 条），且同属"证据缺失门控"一族；原生引擎执行中 11 条授权关系只有 2 条触发（OTG_AUTHZ_002/002c），内容谓词 `userCanRetrieveContent` 从未被调用（0 次调用）——即"执行已发表关系"的证据只覆盖可达性门控子集。
- 真实系统侧只测了假证明面（三个系统在受测端点上都不存在漏洞）；检测面只有自建 Gitea 仿真靶机上的**单一故障模式**（同一路由上的 N 个实例，作者正确地指出这不是 N 个独立缺陷）。
- 40% 的 Gitea 假证明率是在 96% 授权通道不可观测的**自设拓扑**下产生的——作者声明"channel proportions are topology design parameters, not field prevalence"，很诚实，但这样一来，论文能主张的就只是"该失效模式存在且确定性发生"，而无法对部署环境中的发生率说任何话。建议在 Conclusion 中把"what a practitioner should do differently after reading this paper"写实一段。

### M4. 全文零图，摘要可读性差，行文密度已损害信息传递

- **13 页实证论文没有任何一张图。** 三阶段协议的时间线、快照/实况两个读取时刻的机制示意、三系统 mismatch 对照、消融结果——都适合可视化。源码注释声称"全部图为矢量、由 matplotlib 确定性生成"，但正文没有一张 includegraphics。对审稿人而言这是明显的呈现缺陷。
- **摘要不可卒读。** 第一句到第三句之间没有给不熟悉 MST-wi 的读者任何立足点；"deterministically, in one direction" 这类压缩表述在摘要里是反效果。建议按"背景—做法—三个发现各一句—含义"重写，每个发现一句话、一个数字。
- 行文的自我限定密度过高（几乎每个论断带三层 hedging），同样的 scope 声明在摘要、引言、§3、§5、§6、§7、结论中重复出现 5+ 次。诚实是优点，但重复不是。建议：scope 声明集中到一处（§3 或 §7），其余处以交叉引用代替。

### M5. 相关工作覆盖有缺口（部分文献已在你自己的 refs.bib 里但未引用）

Related Work 对黑盒/白盒两条线的梳理是合格的，但以下与 BOLA 直接相关的工作未在正文出现（我注意到它们存在于你的文献库中，说明曾被视为相关）：

- Wu et al., *Rethinking Broken Object Level Authorization Attacks Under Zero Trust Principle*（TOSEM 2026）——零信任视角下的 BOLA 分析，与本文的授权态判定问题直接相关；
- Filho et al., *Automated BOLA detection ... via OpenAPI to colored Petri nets*（IJIS 2025）——黑盒 BOLA 检测的另一条 oracle 路线；
- Schlaubitz et al., *A2CT*（2025）——函数级+对象级访问控制自动化检测；
- 另有两篇 JISA 论文（Defendroid 2024、Liu et al. 2024）在库中未引用——投 JISA 时引用目标期刊的邻近工作既是礼貌也是策略。

尤其 Wu 2026 与 Filho 2025 属于"检测 BOLA 的 oracle 从哪来"这一本文核心问题的直接对话对象，不讨论会被下一个审稿人抓住。

## 4. 次要问题（Minor Issues）

1. **参考文献字段不一致**：`Sahin2026Enhancing` 年份 2027 但 DOI 是 `jss.2026.113060`；`Chaleshtari2022Metamorphic` key 为 2022、年份 2023；`Seran2025Handling` key 2025、年份 2026。key 不影响编译，但 Sahin 的年份/DOI 冲突需核实。
2. §6.2 两处使用 `\S\ref{...}` 而全文其余用 `Section~\ref{...}`，风格不一致。
3. 锚定配置的假证明率 2/2 = 100%（\ResFpEthreePct）——作者已声明分母过小，既然如此建议直接删掉百分比、只报计数，避免"100%"在引用中被剥离语境传播。
4. F3 的 84.62% 建立在"每 case 两个 follow-up 输入"的自设近似上；结论不依赖具体值，但建议在正文首次出现处（而非仅 Threats）就用脚注标记该值为示意性近似。
5. "Table 1 closes this line of work" 的措辞自封了讨论，改为 "concludes the ablation" 更妥。
6. 摘要称 "a Gitea study replicated on Gogs and GitLab"，但 §5.2 明确指出 Gogs/GitLab 上 oracle 不可靠导致 v3 产生新假证明——这不是严格意义的 replication 而是带方法学变异的扩展，摘要措辞建议更准确。
7. Zenodo DOI 与 GitHub repo 建议在录用前由编辑/审稿人实际点开验证（本审稿未验证链接可达性）。
8. cas-dc 模板下 `\shortauthors` 为 "Q. Lin and N. Chen"，请确认与期刊作者署名规范一致（通讯作者标注清晰）。

## 5. 给作者的问题（请在回复信中逐条回答）

1. 在 oracle 缺失层内，v1/v2 的告警相对任何无 oracle 基线的检测增益是多少？（M2 的核心）
2. F1+F2 的联合推论——黑盒场景下该技术"要么假证明、要么弃权、无法裁决"——你们是否接受？若接受，为何不在文中明说？若不接受，反驳路径是什么？
3. Lemma 1 若按 M1 建议重写为经验前提为主体的命题，作者是否有异议？
4. 原生引擎运行中 `userCanRetrieveContent` 零调用、仅 2/11 关系触发——你们认为这本身是否构成对 MST-wi 工程可用性的另一个（未主张的）发现？
5. 三个真实系统上未发现真实漏洞，是否尝试过注入配置类授权缺陷（而非仅自建靶机）来在真实系统上闭合检测面？

## 6. 总体评价

这是一篇**方法学罕见地严谨、但贡献定位需要重新校准**的稿件。它的证据工程（零修改原生执行、内源性对照、全管线重算）达到了软件工程顶会的 artifact 标准；它的诚实（证伪条件、自我纠错记录）超过绝大多数已发表论文。但它目前有三个结构性弱点：(a) F2/F3 的形式化内核平凡，实际贡献需重新表述；(b) 消融表里 v2 recall 0.99 vs direct 0.50 的不对称未被处理，oracle 缺失层（MT 的本命场景）的检测分析缺失，使 F2 有"打稻草人"之嫌；(c) 全文无图、摘要难读、hedging 重复，严重削弱了传播力。

三个主要问题都是可修的，且修完之后论文会更强。**建议：Major Revision。** 若作者完成 M2 的补充分析并接受 M1 的重写，我对修改稿的预期评价会显著上升。

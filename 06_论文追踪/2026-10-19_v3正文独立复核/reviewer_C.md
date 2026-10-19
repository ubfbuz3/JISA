# Reviewer C 独立冻结报告

审阅对象为 `8e2c706d3c843d517747fa94fa47eb80b5b59a46`。本报告使用 nature-reviewer 的证据定位、严重程度和可检验解决条件，按 IEEE Access 及用户要求评估，不采用 Nature 的选择性标准。预先指定的侧重为叙述、新颖性、初稿到当前稿的变化、回复覆盖与范围。未阅读既往审计、其他审稿人报告或会话记录，未改动正文、数据或 Git。

完整相对路径以 `C:/Users/Administrator/WorkBuddy/3区论文/` 为根。为方便阅读，`paper/` 简写 `03_论文撰写/paper/`，`sections/` 简写其 `sections/` 子目录，`baseline/` 简写 `03_论文撰写/response_to_reviewers/baseline/`；回复信均为 `03_论文撰写/response_to_reviewers/response_to_reviewers.tex`。行号来自本次读取的当前源码。已核对 HEAD 正是目标提交，正文及回复相对该提交无差异。读了当前完整正文源码、主要生成表、初稿 PDF 及相关源码对照、原决定信和当前回复，并抽查与争议直接相关的代码和原始记录。本次没有重跑整套实验或重新编译，不能将作者声称的全包字节复现作为本审稿人独立验证的结论。

## 总体判断

这篇稿件作为两条 reachability-gated 关系的安全测试方法学个案，已有可以成立的有限科学内容。真正有用的是区分时序陈旧、渠道不可见、可读但不保真的权限表面，以及报警与独立确证；新增加的时序循环和公开缺陷修复配对使这些区分更可审查。它不是一个已经验证检测效能的新工具，也不足以评价 MST-wi 整个关系目录，但当前标题和大部分正文已经承认这一点。受众是 Web/API 授权测试工具开发者、测试结果复核者及安全实证研究者。

我建议先完成有实质内容的修订再提交。以下三项 Major 均为 Blocking No。它们影响贡献定位、关键机制的统一叙述或重投回复的可信度，但我未在本审阅侧重内发现必须增加一个多缺陷检测基准，才能建立当前有限中心论点的理由。未把原审稿人的每一项扩展建议自动视为科学阻断条件，也不预测编辑结论。

## 确实成立的优点

- 标题、PDF metadata 和摘要已明确限制为 MST-wi 的两条关系。`paper/main.tex` 59、152、168–174 行与 `sections/07_threats.tex` 28–33 行一致地保留目录外推的边界。
- `sections/06b_support.tex` 124–142 行将原生引擎的 A、作者增加的 promotion policy P 所得 H、独立真值 T 分开。尤其明确 H 的数量是构造结果，不是引擎本身声称了安全证明。这比初稿把原生失败直接叫 false proof 更严谨。
- `sections/05_realsystem.tex` 181–326 行报告有事件顺序、模型摘要、相同凭据 recrawl 和并发边界的时序实验，并承认逻辑版本不是服务端原子快照。`04_绘图与分析/results/temporal_table.tex` 13–22 行给出 Gitea 13/13、GitLab 16/16 的修复，不能再把渠道不可见与普通陈旧混为一种不可修复问题。
- `sections/05_realsystem.tex` 488–534 行明确公开缺陷配对没有执行关系本身，支持的是 E/Y gate 的正确性，而不是关系的真实缺陷召回率。这样的克制应保留。
- 原稿关于 99.81% 等于与自身 crawler 一致的归因已撤回。当前 `sections/04_synthetic.tex` 236–256 行承认人工验证标签，并限制为分母和覆盖范围问题；84.62% 的具体示例已从正文删除。
- 补充 coverage、弃权及成本，使 perfect precision 不再孤立呈现。`sections/04_synthetic.tex` 150–229 行还区分可读表面显示覆盖授权时的非决策和不可读引起的非决策，不把安全弃权算成成功检测。

## 初稿到当前稿的实质变化

已独立核对 `baseline/submitted_main.pdf` 的 SHA-256 为 `d641e6dad6899658385f5eb8aac008069ee5ac83ef4233d29a554d780c3d440c`，与 `git show 157edec:03_论文撰写/paper/main.pdf` 字节相同。源码 ZIP 同样与该提交字节相同，SHA-256 为 `98c765fc471687a7116562f30fe30bfde7fc001bbfa4c337200d482ec2066323`。这证明当前选用的历史基线有仓库依据，不证明它就是门户实际收到的最终文件；未访问 Author Portal，后者仍不可独立确认。

初稿为 16 页，当前为 28 页。初稿已经有 576 条构造记录、Gitea/Gogs/GitLab 的快照研究、seeded control、原生关系执行及 oracle 可读性分层。它们不应被整体叙述成此次新增。当前真正新增或实质改写的内容主要包括两产品逐事件时序循环、Gitea 1.20.5/1.20.6 的公开缺陷 gate 配对、竞争差分规则的独立受控实验、完整设计与 record-key 对账、显式谓词/真值表、决策覆盖与弃权成本、Gogs 逐渠道表，以及回顾性 oracle independence admission rule。

初稿 PDF 第 2 页称更多 crawling 不能修复；第 3 页还把构造研究的 blind/aware 称作 frozen/live。当前分别在 `03_protocol.tex` 155–158、188–189 行及 `05_realsystem.tex` 184–211 行纠正，形成有意义的证据类型分离。初稿第 10–11 页的等价性与“真正非法访问的裁决不在可能结果中”的表述，也分别改为明确的 H⇒D 子集结论和 E/Y gate 的确证条件。这是科学解释上的修订，不只是文字润色。不过背景段仍残留与这些修订冲突的关键句，见 C-M3。

## Major Concerns

### C-M1 新颖性响应仍主要是自述贡献，缺少针对既有方法学认识的可追溯对照

- **Severity** Major
- **Blocking** No
- **Axis** novelty-significance
- **Claim pointer** `03_论文撰写/paper/sections/08_related.tex` 45–76 行将三个增量称为本文新增，46–47 行又因不比较 detection rate 而排除这些文献作为 comparison class；回复信 79–103 行称已响应原 R1.1 的 structured comparison。
- **Evidence pointer** 同一 related-work 节 4–15、17–44、49–54、99–109 行。原生证明升级的实际边界由 `sections/06b_support.tex` 126–142 行限定，P 是本文增加且 H 数量无经验内容。`sections/06_boundaries.tex` 63–120 行则明确吸收引理是代数，实际非增益结论是限定规则下的 subset，而非一般信息等价。
- **Concern** 当前承认“快照会陈旧”和“oracle 会不健全”已知，也列出了三个具体结果，确比初稿更清楚。但文献比较仍主要按检测方式罗列，随后以不研究检测率为由整体退出比较，尚未逐项回答原 R1.1 所问的已知问题、新示范及超出应用到 MST-wi 的方法学增量。尤其把外加 P 下的 false proof、条件化 H⇒D、通用 pooled-denominator 算术统称三个增量时，需要把新发现、已知原则在此 artifact 上的验证、研究建议分开。当前材料足以主张可复核的个案刻画，尚不足以从引用清单本身确认更广的方法学新颖性。
- **Why it matters** 对没有新检测器的论文，可核实的新知识本身就是原创性主轴。没有这层定位，读者仍容易把贡献读成给已有 stale-state/partial-oracle 认识换名字。本意见不声称某篇未提供的论文已经证明同一结论，也不要求制造新算法。
- **Resolution test** 给出简短而有引文依据的逐项对照，可用表也可用清楚分段。每项说明既有认识、本文确切新增的 artifact 级证据或可迁移规则、P 和固定输入域等必要前提及不新之处。将“新证明”与“首次在本 artifact 上量化/执行验证”区分开。相应修正回复信 R1.1 的完成口径。

### C-M2 R1.7 的同总预算要求没有做到，回复总述却仍称 matched request budget

- **Severity** Major
- **Blocking** No
- **Axis** claim-moderation
- **Claim pointer** 回复信 `03_论文撰写/response_to_reviewers/response_to_reviewers.tex` 58–62 行称竞争基线是在 matched request budget 上完成的，64–67、714–742 行仅列五项部分完成，未列 R1.7。
- **Evidence pointer** 正文 `sections/06_boundaries.tex` 365–380 行、回复信 287–300、327–337 行明确只有 probe pair 匹配，总请求、可见信息和权限不同。原始 `experiments/results/baseline_compare.json` 的 `summary._budget` 为 shared_probe_requests=84、ours_extra_requests_total=27、ours_total_requests=111。`experiments/run_baseline.py` 81–111、192–202 行直接显示共同两请求后仅 ours 额外读 oracle。
- **Concern** 新实验是实在的，不应因未运行某个完整竞品就否认它的价值，正文也已诚实地把它叫不同信息成本下的裁决权衡。但是它没有满足原 R1.7 明文要求的 matched query budgets。开头未限定的“matched request budget”以及“仅五项未完全完成”的总表，与细节自认不一致。无 per-method wall-clock 在共享观测的重放评分中有合理说明，不能由此自动要求伪造一个 timing；真正未闭合的是预算/信息成本不等的请求及其范围回应。
- **Why it matters** 仅有一次重投机会时，完成状态的准确性直接影响回复可信度。当前结果不是同预算检测优越性证据，但也没有必要为当前有限论点强行增加这种主张。
- **Resolution test** 最小可行修订是把总述明确改为“matched probe pair, unequal total budget”，在部分完成/范围异议清单增加 R1.7，说明为何其不支撑检测 superiority、为何有限裁决问题采用该替代设计。不必为满足列表而强制新增实验。若作者坚持标作完全满足同预算比较，才需要实际等总预算、等可见信息的设计和结果。

### C-M3 RQ1 的前置解释仍把“同凭据刷新可修复”说成需要 privileged recrawl

- **Severity** Major
- **Blocking** No
- **Axis** writing-clarity
- **Claim pointer** `03_论文撰写/paper/sections/02_background.tex` 26–30 行称重爬同一界面不能消除 false proof，只有能看见 granting channel 的 recrawl 才能消除，并把修复 29 个 stale cells 的时序实验称为 privileged recrawl。
- **Evidence pointer** `sections/05_realsystem.tex` 195–211 行和 `04_绘图与分析/results/temporal_table.tex` 4、13–22 行明确相同凭据 recrawl 修复全部 29 个。`experiments/real_system/run_temporal.py` 344–360 行对 M0/M1 均调用同一个 `crawl(self.cl[s])`；205–230 行列出的 sources 是 user_repos、org_repos、search。GitLab 的 `run_temporal_gitlab.py` 236–260 行也使用每个主体的项目/组项目/可见项目表面。回复信 599–605、437–449 行采用的是同凭据修复这一解释。
- **Concern** 两种不同边界在稿件其他位置已经正确区分。授权在 crawl 后改变但后来能列出，是普通陈旧，刷新即可修复；渠道始终不被所选表面列出，才是同表面反复刷新也无效。当前背景把二者混写，还把使用相同凭据的新实验误说成增加权限。这是进入论文时读者第一次看到的中心机制解释，会改变对 RQ1 新意和内部控制的理解，也使回复 R1.10/R2.1 显得前后不一。
- **Why it matters** 这不是一般措辞偏好。能否通过同凭据更新修复，决定中心反例是在说明过期快照，还是不可见授权渠道；它同时关系到实验是否偷加了信息。
- **Resolution test** 用两个明确分开的条件句说明修复边界，删去对该时序实验不实的 privileged 定性。说明 recrawl 只需重新列出授权后可见的对象，不必能读取“发生授权的管理事件”本身。逐处核对背景、RQ1、related work、conclusion 与回复信，令“不可刷新修复”仅指实测的渠道不可见场景。无需重跑已展示的 29 个修复。

## Minor Comments

### C-m1 时序路径并非所有 observation 都是 GET

- **Severity** Minor
- **Blocking** No
- **Axis** reproducibility
- **Claim pointer** `sections/05_realsystem.tex` 303–306 行和回复信 437–440 行声称所有 observation 都是 GET，只有 transitions 会变更状态。
- **Evidence pointer** 同一正文 239–242 行已经报告角色提升后的写入和清理。`experiments/real_system/run_temporal.py` 275–305 行实际以 POST 写探针文件并 DELETE 清理；GitLab runner 315–340 行以 POST 建文件/分支并 DELETE 分支。
- **Issue** 核心可达性枚举和 oracle 读取可以是 GET，但针对写能力的补充 effect probe 显然有写和清理。现有代码及正文有恢复说明，未因此发现授权状态被改动的证据，故为局部报告错误而非新实验要求。
- **Required correction** 将 GET-only 限定到模型枚举、oracle 和读探针，显式列出补充写探针及恢复步骤，并说明其不改授权配置。

### C-m2 表 17 的说明定义了 H，但表内没有 H 列

- **Severity** Minor
- **Blocking** No
- **Axis** figures-and-tables
- **Claim pointer** `sections/06_boundaries.tex` 91–100、150–169 行及回复信 113–121 行把真值表作为完整裁决映射。
- **Evidence pointer** `04_绘图与分析/results/truth_table.tex` caption 定义 H=A∧¬o，但列头仅列 Y、M、O、A、D、verdict、E 两种计数；表中 row 7 的“true positive / false proof”是 A 的读法，H 在 O=allow 时实际上为 0。
- **Issue** 公式本身足以推导 H，故不把这当成原 R1.2 全面未响应。但 caption、正文反复说“两种 verdict”时，读者容易把 A 的 false proof 误归给 state-calibrated H。
- **Required correction** 增加 H 列，或明确 verdict 列究竟评价 A 还是 D，并另注 H 的对应结果及 O 不可用时的弃权。不要只在 caption 定义一个未在表内显示的裁决变量。

### C-m3 一致性与 soundness 的必要条件被写得过强

- **Severity** Minor
- **Blocking** No
- **Axis** claim-moderation
- **Claim pointer** `sections/08_related.tex` 13–15 行称 relation 只有在 model 等于 authorization state 时才 sound。
- **Evidence pointer** `sections/06_boundaries.tex` 91–100 行给出 A=y∧¬m；`sections/05_realsystem.tex` 218–222 行及 `04_绘图与分析/results/truth_table.tex` 的 Y=deny、M=reach 行说明 model 与 entitlement 不同可以只导致静默，未必导致错误确证。
- **Issue** 完整相等是充分的强条件，不是有限域内“没有 false proofs”的必要条件。过时的正向 reachability 可能造成漏报风险，但请求被拒绝时不会发出该错误确证。
- **Required correction** 把 soundness 指标说清，改为所需方向的保真条件，或仅称模型一致性是一个足够条件。不要以必须全相等的句子覆盖已经细分好的方向性结果。

## 原审稿意见覆盖审计

下表的“已响应”指当前文本和可见材料给出针对性的处理，不等于所有数值和整套复现都由本审稿人重验。

| 原意见 | 本次判断及边界 |
|---|---|
| R1.1 | 部分响应。承认已知 ingredients 并列增量，但缺少可追溯方法学逐项比较，见 C-M1。 |
| R1.2 | 实质响应。E、Y、O、A、D、H、P、unknown/failure 已出现。表中 H 的展示仍应改进，见 C-m2。 |
| R1.3 | 有边界地响应。列出实际事件及未测事件，承认并发写者及 request/adjudication 内交错不在实验内。不要求无限扩展状态机。 |
| R1.4 | 仅部分满足“结果前判定”的原请求。回顾性规则和 shared/reject 状态透明，不可把它说成预注册过。当前有限 post-hoc gate 正确性个案不因此失效。 |
| R1.5 | 实质响应。代数 lemma、实际谓词和 subset 分开，未再简单推称全域等价。 |
| R1.6 | 实质响应。因子、nested/untested 角落、配对归因及 36/18 到 312/264 的对账明确。不应仍把它叫没有缺角的 complete factorial。 |
| R1.7 | 部分满足。同探针对已实现，同总预算没有实现，见 C-M2。缺失 per-method timing 已有合理说明。 |
| R1.8 | 实质响应。Gogs 也有 ledger 渠道矩阵，staleness 与 oracle omission 分开。小拓扑不能估计渠道发生率。 |
| R1.9 | 多独立缺陷和逐缺陷效能明确未做。公开缺陷 gate 配对加范围收缩是可辩护替代，但不能写成完成了多缺陷请求。作者目前承认这一点。 |
| R1.10 | 核心控制和时序材料已给出。背景的 privileged recrawl 及 GET-only 与实现冲突，见 C-M3、C-m1。 |
| R1.11 | 已响应。未找回原始每案例分母，改用参数化论证；不再把 84.62% 当量化支持，不再暗示替代指标修复 oracle。 |
| R1.12 | 核心异质权重/内生计数问题已有条件化算式和两种增长例子。不把没有 generative model 自动视为必须再做实验，原请求的数学泛化与新实验是两件事。 |
| R1.13 | 实质响应。coverage、弃权和风险均有，重放方法不报告虚构的独立 wall-clock 合理。 |
| R1.14 | 当前正文给出 engine alarm/error 区分及 missing/failure 规则，包内有代码/原始记录入口。整套 28 产物字节复现和空目录编译，本报告未独立执行，不宣告已验证。 |
| R1.15 | 实质响应。证据到主张表和 gate 非 detection 的边界已在。仍应修复 C-M3 以免摘要之外的早期机制叙述残留旧说法。 |
| R2.1 | 相关新实验已运行且解释大体响应；背景残留冲突，见 C-M3。 |
| R2.2 | 已响应。标题/摘要明确两关系，未要求为了改标题额外扩整个目录。 |
| R2.3 | 已响应，见 R1.5。 |
| R2.4 | 以“移除广泛 detection 非增益主张”的分支已基本响应。公开缺陷仅测 gate 这一点足够坦诚；不能把它当成 relation 在真实漏洞上的验证。它与 R1.9 的多缺陷扩展不是同一完成标准。 |
| R2.5 | 已响应。84.62% 不在摘要及正文。 |
| R2.6 | 关于构造率如何依赖设计的讨论和计数已响应。原意见没有明确要求 equal-per-cell-weight 重算，不应把回复信自行新增的这一缺项升级为审稿硬要求。若采用此分析，可作为补充而非科学阻断。 |

## 支持范围、不可评估项和建议姿态

原创性可以定位为“有限关系族的可复核机制个案与评价警示”，不宜包装为新的 oracle 问题理论或竞争检测器。对安全测试受众具有实际价值，但无部署发生率、跨领域普遍性、真实漏洞召回率或整体 MST-wi 准确率的证据。跨产品效果是受控拓扑内的现象，不是三份独立的漏洞发现。

当前 admission rule 在实验后提出且全产品保守 reject，故支持诊断与独立 ledger 复核的边界，不支持已取得 independence-certified 黑盒未知漏洞证明。初稿基线的仓库同一性已核实，门户来源、在线 artifact tag/DOI 的实际可用性、全量引用真实性与全包复现不在本报告已独立确认的结果内，不能因未确认就推定为伪造或缺失。

本报告侧重下没有 Blocking Yes。优先解决 C-M2 的完成口径和 C-M3 的机制冲突，再补强 C-M1 的可审查贡献定位，同时完成三项局部修正。R1.9 仍是明确未执行的扩展请求，应保留作者的范围异议交由编辑判断；不应用它否定已经被范围收缩后的所有中心发现。

报告至此冻结。仅允许纠正客观转录错误，不根据其他审稿意见修改观点或严重程度。

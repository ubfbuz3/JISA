# Reviewer A 独立复核报告

审阅对象为提交 `8e2c706d3c843d517747fa94fa47eb80b5b59a46`。本报告使用 nature-reviewer 的证据锚定和严重度规则，按 IEEE Access 与本轮决定信的要求判断，不采用 Nature 的选题门槛。本报告在独立上下文中完成，未读取其他审阅报告、既往审计结论或综合意见，冻结后不因其他审阅者的判断而改写。

本文所有相对路径均以 `C:/Users/Administrator/WorkBuddy/3区论文/` 为根。行号均为本次实际读取的源码行号。

## 总体判断

修订后的窄结论总体成立。构造实验和真实时序实验支持如下命题。过期的可达模型可能对合法访问报警；在作者明确添加的推广政策 P 下，这些报警成为错误的违规声明。健全且完整解决目标授权问题的 oracle，与实际访问效果结合，已经足以完成该问题的裁决。池化 specificity 也不能单独保证每个场景类别都被覆盖或具有足够权重。

我没有发现推翻这三项窄结论的数学反例，也没有发现目前必须补做多类漏洞实验才能使这些窄结论成立的理由。现有研究不支持代表性 BOLA 检测有效性，而作者已将真实漏洞配对限定为 E/Y gate 的阳性对照。

但当前版本仍有一项需要实质修正的问题。协议中 unknown 与实现中 default deny 的差异，虽然不改变已观察到的 29 个错误声明，却会改变哪些格子拥有可评分的 E，不能一并声称对所有报告分母和 712/712 的 E/Y 一致性没有影响。另有若干局部定义、证据措辞与重爬描述需要统一。

本报告的 Major Concern 为 1 项，Blocking No。没有确认的 Blocking Yes 问题。这不等于建议将当前文本原样提交。

## 审阅范围与核验边界

已阅读当前正文所有科学论证章节、原决定信、当前回复信涉及理论与真值定义的部分，以及原稿与修订稿 PDF 的首页和元数据。原稿 PDF 为 16 页，修订稿为 28 页，标题变化与决定信相容。这个核验只能证明所给本地文件的内容与元数据相容，不能独立证明其即为投稿系统接收的原件。

重点逐行核验 `entitlement.py`、两套 temporal runner、`ingest_truth.py`、MR 移植谓词、时序原始 JSON 和生成的 truth table。另以只读脚本重新统计记录并穷举布尔代数。复核脚本和结果保存在本报告同目录的 `reviewer_A_work/verify_a.py` 与 `reviewer_A_work/checks.json`。未启动真实服务、未重跑原生浏览器引擎，未改变正文、原始数据、生成结果或 Git 状态。没有把回复信当作独立实验证据。

## 实际优势

1. 原生报警 A、作者推广政策 P 产生的 H，以及独立真值 T 已在 `03_论文撰写/paper/sections/06b_support.tex` 第 124 至 142 行分开。尤其承认原生引擎本身不输出授权定罪，这比把 MR failure 直接归因于工具的违规证明更准确。
2. E 的构造已从 Y 中分离。`experiments/real_system/entitlement.py` 第 158 至 207 行仅从台账推理，temporal runner 分别在第 385 至 394 行与第 419 至 428 行记录内容效果、计算 E 和分类。这个结构支持反循环标注；E 与 Y 恰好一致也没有被用作其逻辑定义。
3. 新的命题明确给出 `A=D iff y=0 or m=o` 与 `H_v3 => D`。我对 8 个 definite-oracle 布尔组合独立穷举，两式均成立。正文也承认模型陈旧时 lemma 的第二前提可能失败，见 `06_boundaries.tex` 第 104 至 120 行。
4. 时序实验同时提供原模型、重爬模型、独立 entitlement 和内容效果。我重新统计得到 Gitea 280 格、13 个 stale false proofs，GitLab 432 格、16 个，live false proofs 均为 0。576 条构造记录的现有谓词复核也无不一致。这里的 712 格和 576 条均为固定设计的枚举，不是独立随机样本，作者目前对此处理合理。
5. measurement 论证的限度比原稿清楚。`04_synthetic.tex` 第 258 至 289 行给出固定权重命题与推论，`06_boundaries.tex` 第 292 至 317 行再处理异质且可随方法变化的计数。固定 FP 与同比例增长的 FP 被分别讨论，未错误声称任意输入增长必然使 specificity 趋近 1。

## Major Concerns

### RA-M1

**Severity** Major

**Blocking** No

**Axis** technical soundness / evidence-to-claim fit

**Claim pointer** `03_论文撰写/paper/sections/03_protocol.tex` 第 84 至 97 行称，协议将无授予渠道的已建模对象规定为 unknown，而实现规定为 deny，但两种解释在报告运行中效果相同，没有格子的裁决依赖该选择。同节第 81 至 83 行又规定 E-undefined 不在 truth table 中，应排除并报告。摘要 `main.tex` 第 186 至 191 行和真实系统正文 `05_realsystem.tex` 第 201 至 206 行强调 712/712 的 entitlement-effect 一致性。回复信第 137 至 143 行再次称两种解释在所有报告格上相同。

**Evidence pointer** `experiments/real_system/c_protocol.json` 第 19 行明确将“ledger models no channel”规定为 unknown，且禁止将 unknown 映射为 deny。`experiments/real_system/entitlement.py` 第 199 至 202 行则将无 grant 的已建模对象判为 deny。Gitea 原记录 `experiments/real_system/results/temporal/temporal_gitea.json` 第 303 至 306 行已有这种格子的实例，总计见第 14998 至 15004 行。GitLab 总计见 `temporal_gitlab.json` 第 23592 至 23598 行。本次逐格复算得到 Gitea 的 203 个 deny 格和 GitLab 的 338 个 deny 格全部属于没有 granting channel 的情形。

**Concern** 这里必须区分“当前报警/错误声明计数不变”与“评分集合和真值状态不变”。两产品共 541 格若按冻结协议字面执行，应为 E-unknown。按正文自己对 E-unknown 的排除约定，可评分集合将从 712 变为 171，分别为 77 与 94。当前 29 个 false proofs 都落在 E-allow 格，因而确实可以保留；但 712/712 的 E/Y 一致性以及以 E-deny 为负例的表格，依赖后来实际采用的闭世界 default-deny 语义。完整的封闭实验拓扑可以为这种语义提供合理性，却不能使 unknown 与 deny 成为同一个状态，也不能使协议字面规定没有改变。

**Why it matters** 本次修订的核心改进之一是独立 truth 与缺失值处理。若在这里把裁决计数不变推广为整个证据分母不变，读者无法判断“全部格子都被验证”究竟针对冻结协议还是实现后的定义。这是评分契约和预先规则的实质差异，不是单纯措辞问题。但已确认的合法 stale access 不依赖这些 deny 格，因此我不把它定为阻断三项窄结论的问题。

**Resolution test** 保留原协议和原数据。把闭世界 no-grant-implies-deny 明确登记为实现采用且与协议字面不同的分析规则，并指出它需要完整渠道拓扑这个前提。提供最小敏感性对账，分别列出 literal-protocol 与 implemented-policy 的 scored、unknown、E/Y 可比格数以及 stale/live false proofs。对账应呈现 712 与 171 的评分集合差异，同时保留 29 与 0 的 false-proof 计数。摘要、truth table 说明和回复信中，不再以“没有效果差异”掩盖评分集合差异。无需为此修改原记录或强制重跑服务。

## Minor Comments

### RA-m1

**Severity** Minor

**Axis** writing clarity / formal definitions

**Affected element** truth table 中 raw alarm 与 state-calibrated verdict 的语义。

**Evidence pointer** `04_绘图与分析/results/truth_table.tex` 第 4 行定义 H 为 `A and not o`，第 10 行表头却没有 H 列。第 18 行 `Y=allow, M=blocked, O=allow` 标为 `true positive / false proof`。`06_boundaries.tex` 第 91 至 100 行使用 H_v3，而 temporal runner 的 `run_temporal.py` 第 419 至 422 行及 `run_temporal_gitlab.py` 第 456 至 459 行使用 `H=A`。

**Issue** 上述行若指 raw A 加推广政策 P，其标签可以成立；若指同一 caption 定义的 state-calibrated H，则 H=0，E-deny 时是 miss，E-allow 时没有 false proof。现在公式是对的，但一列名为 verdict 的文字混用了 A、D、H 的读法。尤其 54 格的 A/D 不一致不能被读成 v3/D 的 54 格不一致。

**Required correction** 显式使用 `H_P` 与 `H_v3` 两个符号，并在表中补 H_v3 列，或将现有 verdict 列明确命名为“raw A under P”，分别说明 D。复核上述 row 7 必须有 `A=1, D=0, H_v3=0`。不需新增实验。

### RA-m2

**Severity** Minor

**Axis** mechanism evidence / internal consistency

**Affected element** 同凭证重爬与 privileged recrawl 的表述。

**Evidence pointer** `03_论文撰写/paper/sections/02_background.tex` 第 18 至 30 行称同一界面重爬不会消除 false proof，并称 temporal 实验使用 privileged recrawl。`05_realsystem.tex` 第 195 至 210 行及摘要则明确称 same credentials。代码 `experiments/real_system/run_temporal.py` 第 345 行与第 359 行对 M0、M1 使用同一组 `self.cl[s]`，GitLab 第 380 与第 394 行同样如此。

**Issue** 给 grant 的管理渠道不在 subject 的爬取界面里，并不推出 grant 生效后对象不会进入 subject 可列举的集合。当前 temporal 数据正好展示同凭证、同来源的第二次列举修复全部 29 格。因此这里同时混淆授予渠道与列举可见性，并误称重爬凭证。

**Required correction** 把永久 channel blindness 明确限定为“授予后对象仍不出现在该 crawl source 的列举中”。说明 temporal 实验测量的 stale cases 被 same-credential recrawl 修复；删除把该实验称作 privileged recrawl 的句子。永久不可列举的例子可由已有 Gogs 残留提供，不应由这 29 格承担。

### RA-m3

**Severity** Minor

**Axis** claim moderation / source-to-formula fit

**Affected element** 命题中 by source inspection 的证据层级。

**Evidence pointer** `03_论文撰写/paper/sections/06_boundaries.tex` 第 87 至 90 行称两关系仅读取 crawl-time model 与 response，nothing else。同节第 124 至 131 行实际上列出 supervisor guard 及两个响应的相等性，并用本实验域内常量和 `q=y` 才完成化简。`experiments/mrs/mstwi_mrs.py` 第 239 至 263 行可以直接看到这些输入。temporal runner 第 389 至 394 行直接由 M 与 Y 定义 A；`04_绘图与分析/analysis/ingest_truth.py` 第 126 至 131 行只是重新检查同一个式子。

**Issue** 当前数据域内化简有证据，不能把它写成一般 source dependence 仅有一个请求 bit 的事实。temporal 部分的零 disagreement 证明记录自洽，并非再次独立验证完整 MR-002 的 supervisor 与双响应语义。正文已经给出完整公式，因此这是局部证据措辞问题，不是对化简结果的否定。

**Required correction** 将 source-level 完整输入与 domain-specific reduction 分开叙述。完整关系读静态 supervisor、模型和响应对；在指定域中这些条件退化后，才有 `A=y and not m`。把 712 格验证称作实例化公式的逐格一致性检查，保留 576 条实际谓词记录与 native run 各自不同的验证范围。

### RA-m4

**Severity** Minor

**Axis** writing clarity / truth provenance

**Affected element** ground truth 的总述。

**Evidence pointer** `03_论文撰写/paper/sections/03_protocol.tex` 第 51 至 57 行仍将 Gitea、Gogs、GitLab 的 ground truth 描述为 effective authorization 的 live re-probes。相对地，`05_realsystem.tex` 第 255 至 259 行明确不让 oracle 决定 E，`entitlement.py` 第 21 至 29 行和第 158 至 207 行使用独立台账，而 re-probe 只观察 Y。

**Issue** 修订后最重要的反循环改进已经实现，但总述保留了容易被理解为 `E=Y` 的旧说法，尤其会让首次阅读者误解“没有漏洞时观察与授权相同”就是 truth 的来源。

**Required correction** 把总述改为分别命名 E 的台账来源、Y 的内容读取来源以及 O 的诊断来源，并说明 E/Y agreement 是验证结果而非定义。不需要额外实验。

## 五个评估轴

| 轴 | 独立判断 |
|---|---|
| 相对于声明范围的原创性 | modest but concrete。模型陈旧、oracle 问题和池化度量都已知；当前可核验的增量是两条特定关系的谓词化分析、政策依赖的错误声明链、渠道分解和同凭证重爬控制。不能把一般函数代入恒等式作为新定理的主要价值。 |
| 对目标读者的重要性 | 对维护 Web/API 授权测试工具、复用 MST-wi 和解释黑盒报警的读者有用，尤其能避免把 relation failure 自动写成 confirmed vulnerability。无需主张跨学科广泛重要性。 |
| 技术可靠性 | 布尔恒等式、subset 结论和 specificity 计数论证在明确域内正确；E/Y 分离的实现可靠性比原稿清楚。RA-M1 需要纠正评分契约解释。 |
| 证据与结论匹配 | 支持固定实验设计内的错误声明机制、条件裁决比较和 metric 分辨率限制。不能估计 field prevalence、真实漏洞总体 recall、独立性认证通过率或完整目录效果。现稿多数地方已主动限制。 |
| 可读性 | 标题、摘要和 evidence-to-claim 表已有明显收窄；但正文关于 E、Y、A、H 的切换仍要求读者自行消歧，RA-m1 至 RA-m4 是具体可修的障碍。 |

## 未解决或不可评估的项目

- oracle admission rule 在 `06_boundaries.tex` 第 410 至 443 行被明确承认为事后提出，三个产品均 conservative reject。这个处理避免把同源 API 当作独立证明，但没有完成原 R1.4 所要求的“观察结果前验证的、能够接受某个真实 oracle 的 procedure”。这是回复中已承认的部分满足。对于当前不主张独立性认证效果的论文，我不据此追加一个阻断问题。
- 多类独立 BOLA 缺陷及真实缺陷上的 MR recall 仍未验证，现有 real vulnerable/fixed pair 未运行关系本身，见 `05_realsystem.tex` 第 521 至 534 行。原 R1.9 的范围异议仍需编辑判断，不能写成实验已满足；也不能据这项缺失否定当前仅针对 adjudication gate 的正对照结论。
- SHA 摘要证明内容绑定，不独立证明外部注册时间。本次未取得第三方注册时间戳或投稿平台认证材料，故不认证这些来源的外部时间真实性，也不从缺失该材料推断造假。当前 A2 时间异常已在正文第 290 至 300 行披露。
- 本复核未对引用的每篇原始文献做外部查新或逐条引文审计，不认证“无其他工作先做过”这样的广义原创性。

## 有界建议

这是一篇可成立的、范围较窄的方法学案例研究，现有结果不需要被包装成新检测算法或真实漏洞总体基准。我建议先完成 RA-M1 的双规则分母对账，以及四项局部修正，再将回复中的“已完成”“部分完成”“范围不同意”保持为可检查的三种状态。当前未发现需要推翻或重做三项窄结论的 Blocking Yes 事项；最终是否允许以窄范围回应原 R1.9，属于编辑的范围判断，本报告不代作决定。

本报告至此冻结。

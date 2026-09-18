# Baseline 矩阵与可得性裁决

> 生成：2026-09-18 · 依据：`01_文献调研/工具与数据可得性核查.md`（实测）+ `refine-logs/EXPERIMENT_RESULTS.md`（Block 0–10）
> 原则：**每个进入矩阵的条目都必须能指回一次实测或一句原文**；未实测的一律标 `待核实`，不得写入正文的比较性陈述。

---

## 0. 结论速览

| 类别 | 条目 | 是否**运行** | 作用 |
|---|---|---|---|
| **定位基线**（related work） | MST-wi、MST/Mai19、EvoMaster（fault 306/304/307/308/310）、BACFuzz、BACScan、MOCGuard、BolaRay、ACBreaker、NeO、A2CT、PCFinder、JAuthGuard、SeeAuthz、AUTHSCOPE | ❌ 不运行 | 界定本文结论的**适用范围**与差异 |
| **内部对照**（同一实验台） | `v1`、`v2`、`v3`、`v3_self`、`degrade_all`、`direct_only`、`direct_observe` | ✅ 已运行 | 支撑三条边界结论的**全部数字** |
| **真实系统仪器** | Gitea 1.22.6（正确系统） | ✅ 已运行 | 假确证侧 + 机制空间普查（实例无关） |
| **不可得** | BACFuzz、BolaRay（运行成本）、MOCGuard、BolaZ | ❌ | 只进 related work；**禁止**任何数值比较 |

**一句话**：本文体裁是「刻画 + 度量口径注记 + 一条阴性结论」，**不是"新检测器"**。
因此 baseline 的作用从"证明我更好"降为"界定我在哪些条件下不适用"，
**真正承担证据的是内部对照**，而它们全部在同一实验台、同一真值口径下可复现。

---

## 1. 为什么 baseline 结构由体裁决定（这一节必须写进论文，否则会被误判为"没跟 SOTA 比"）

| | 检测器论文 | **本文（刻画型）** |
|---|---|---|
| 核心问句 | 我的方法比 SOTA 好吗？ | SOTA 的度量**在什么条件下失去意义**？ |
| 需要的对照 | 竞品**运行结果** | 竞品**定义与谓词词汇表** + 我方**内部消融** |
| 最大的拒稿风险 | 基线不可比 / 未调参 | **"你凭什么替 MST-wi 判定"** |
| 本文的应对 | — | ① 全部论断**按 MST-wi 原文定义**实例化（§4）；② 只称"该 MR 家族的结构在此系统上的实例化"，**不称"MST-wi 实测表现"**；③ 未跑原生引擎，故**删除一切运行级断言** |

> ⚠️ 硬约束：本机 **Maven 未安装**、JDK 仅 1.8（最新 EvoMaster 需 17+）。
> ⇒ **在补齐之前，本文没有任何 MST-wi 的运行级数字**。这条必须在 Limitations 首段明写。

---

## 2. 定位基线（不运行，只定位）

| # | 制品 | 在本文里的角色 | 可得性（实测） | 依此可写 / 不可写 |
|---|---|---|---|---|
| B1 | **MST-wi**（Bayati Chaleshtari et al., TSE 2023） | **主定位对象**：76 MR / 55 DSL 函数 / 灵敏度 85% / **特异性 99.81%** | ✅ 制品已下载解析（`01_文献调研/mstwi_artifact/`，含 `catalog_text.txt`） | 可写：谓词词汇表普查、特异性口径、原文对 `cannotReachThroughGUI` / `userCanRetrieveContent` 的**定义**。<br>不可写：任何"其实测表现优于/劣于" |
| B2 | **MST / Mai19**（22 MR，specificity 99.50%，32/6401 FP） | 同族先例，说明口径问题**先于** MST-wi 存在 | ✅ 全文（`文献调研报告_v2.md` [24]） | 可写：该报告的 FP 归因是"爬虫无法到达复杂状态/异步"，**与授权状态无关** |
| B3 | **EvoMaster** fault 306 / 304 / 307 / 308 / 310 | **SOTA 开源 fuzzer 的自陈**：`"Without a formal specification … it is hard to say automatically if we are in the case of a BOLA/BFLA vulnerability"` | ✅ 仓库可达；`docs/faults.md` 37 fault code | 可写：**引用原文**；该 oracle 名为 "Likely Should Had Been Protected"，命名本身承认是**猜测非判定**。<br>`待核实`：是否支持外部传入策略规格 → 未核实前**只能引原文** |
| B4 | **BACFuzz**（Dha25） | 最接近的工程竞品 | ❌ 论文原文 *"artifacts **will be** publicly released"*（将来时） | 只进 related work，**零数值比较** |
| B5 | **MOCGuard**（S&P'25；161 0-day / 73 CVE） | 静态归属推断线的顶点 | ❌ 未检索到公开仓 | 只进 related work；用于说明"**推断归属**这条线已被 CCS'24 + S&P'25 双点占住" |
| B6 | **BolaRay**（CCS'24；FPR 21.86%） | 静态线（PHP）；需人工 DAL 规格；**不支持 SELECT** | ⚠️ 代码可达，运行链路重（Py2 + Neo4j 2.1.8） | 可写其**两处硬约束**（需人工规格、忽略 SELECT）；`不承诺数值比较` |
| B7 | **BACScan / ACBreaker / NeO / A2CT / PCFinder / JAuthGuard / SeeAuthz / AUTHSCOPE** | 覆盖矩阵的其余格子 | ❌ / 摘要级 | 只进 related work，逐条标证据等级（全文 / 摘要） |
| B8 | **WFD（原 EMB）** + **VAmPI** + **crAPI** | 曾计划作为语料与靶场 | ✅ 可达 | ⚠️ **本文不使用**：VAmPI/crAPI **无对象级共享模型**（本文的必要条件）；WFD **无 BOLA 真值标注** |

---

## 3. 内部对照：真正承担全部数字的七个方法

定义域：`experiments/results/raw_matrix.jsonl`（576 条，0 错误）+ `real_system/results/real_system.json`

| 方法 | 访问证据来源 | 例外判定来源 | 无 oracle 时的行为 | 定位 |
|---|---|---|---|---|
| `v1` | MR 触发 | 测试框架自己的动作账本 | 仍出告警 | Block 3 基线层级 ℒ₁ |
| `v2` | MR 触发 | 账本 + 权限层级匹配 | 仍出告警 | **MST-wi 位置的上界代理**（例外谓词能力上限 ℒ₂） |
| **`v3`** | MR 触发 | **被测系统自报的授权面** | **强制弃权** | 本文修正的**最强形态**（已被第七轮部分证伪，见 Block 9） |
| `v3_self` | MR 触发 | 同 `v3`，但以**被测主体自身凭证**读取 | 强制弃权 | 检验"可容许条件能否由黑箱视点满足" |
| `degrade_all` | 无 | 一律降级 | 全部弃权 | **诚实弃权地板** |
| `direct_only` | **无**（只看 oracle） | 授权面 | 弃权 | 第七轮被判定为**稻草人**，保留以自证错误 |
| `direct_observe` | **普通请求 HTTP 200** | 授权面 | 弃权 | **决定性对照**（第七轮） |

> 「访问证据」是本文理论上的关键变量：`v*` 家族用**变形关系被违反**作证据，`direct_*` 家族用**一次普通请求的状态码**。
> 三者的差别**只在这一点**（见 `experiments/ablate_direct_observe.py` 的语义表）。

**必须与数字并列报出的两条**（禁止只报对己方有利的一支）：

| 必须报 | 数字 |
|---|---|
| `v3` 的召回 | **R = 0.4861**（不是只看 P = 1.0000）；F1 ≈ 0.654 |
| `direct_observe` 支配性的**构造性来源** | 其两输入与真值定义同源（`bola ⟺ ¬should_allow ∧ app_allowed`）⇒ 该对照与真值**部分同构**，支配性是构造性的 |
| `direct_observe` 与 `v3` 召回差异的**显著性** | ΔR = 0.0139，95% CI **[−0.0797, +0.1072] 含 0 ⇒ 不显著**。只能称"点估计不劣于"，**不得称"严格支配"** |

---

## 4. 忠实性依据：每条谓词按谁的定义实现

这是本文最容易被攻击处，必须逐条给出处：

| 谓词 | 实现依据（原文） | 出处 |
|---|---|---|
| `cannotReachThroughGUI(u, URL)` | "Returns true if a URL **cannot be reached by the given user by exploring the user interface** (e.g., by traversing anchors)." | `mstwi_artifact/mstwi_paper_text.txt` |
| `userCanRetrieveContent(u, out)` | "Returns true if the output data **has ever been received** … **during data collection**." | 同上 |
| `isSupervisorOf(a, b)` | 论文 DSL 表定义为 "can **access the URLs** of b" ⇒ **同为 GUI 可达性派生**，不是独立的一类 | 同上 |
| 例外处理 | 原文设计意图：*"if the system does not provide a URL to a user through its GUI, then she should not access the URL"* | 同上 |

⇒ 因这两条谓词**都相对"采集期爬取记录"定义**，忠实的实例化必须是**三阶段**：采集（快照）→ 授权变更（带外）→ 执行 MR。
**实时且完备的枚举是过度强化的实例化，会人为抹掉失效**（本文初版正是如此，已推翻，见 `EXPERIMENT_RESULTS.md` Block 10 §10.1）。

---

## 5. 真实系统仪器（Gitea 1.22.6）

| 项 | 值 | 性质 |
|---|---|---|
| 版本 / 形态 | Gitea 1.22.6 官方单文件绿色二进制（自带 sqlite） | 可复现，无需 Docker |
| 授权授予端点 | 253 条 API 路径中 **15** 条授予端点（另 2 条仅撤销），其中 **8** 条**不需站点管理员** | **实例无关**的结构事实 |
| 框架账本覆盖上界 | 上述 15 条中，测试框架自建共享动作最多覆盖 **1** 条 | 实例无关 |
| 待测单元格 | **96**（96 = 8 主体 × 12 对象×读法） | 构造 |
| oracle 视点可读性 | 拥有者/管理员 **56/56**；黑箱主体自身 **0/40** | 构造实例上的实测 |
| oracle 保真度 | **48/48** 一致（8 格为不适用，见口径说明） | 实测 |
| 通道分解 | 25 个有效访问中，**1** 条框架内共享、**24** 条非框架可观测（11 显式带外 + 8 站点管理员 + 5 公开仓库） | **构造拓扑的设计参数，不是野外发生率** |

> ⚠️ Gitea 是**正确系统**（无真 BOLA）⇒ 真 violation 恒为 0 ⇒ **本仪器只测假确证侧，无任何检出率数字**。

---

## 6. 每个 claim 需要哪个 baseline（claim → 对照 的绑定表）

| Claim | 需要 | 由谁提供 | 现状 |
|---|---|---|---|
| C1 门控谓词同族、DSL 无授权态谓词 | MST-wi 制品目录 | B1（已下载） | ✅ 普查可复算（`refine-logs/catalog_census.csv`） |
| C2 带外授权 ⇒ 假确证 | `v1`/`v2` vs `degrade_all` | 内部对照（已运行） | ✅ Block 6/7 |
| C3 修正的可容许条件可测 | `v3` vs `v2`，按 oracle on/off 分层 | 内部对照（已运行） | ✅ Block 8 |
| C4 有 oracle 时 MR 可省 | `direct_observe` vs `v3` | 内部对照（已运行） | ⚠️ **点估计成立、统计不显著**（见 §3 末表） |
| C5 真实系统上同一失效存在 | Gitea 仪器 | B（已运行） | ✅ Block 10 |
| C6 可容许条件只能由特权视点满足 | Gitea 仪器 | B（已运行） | ✅ M2（黑箱自身 0/40） |

---

## 7. 禁止事项（写进投稿检查清单）

1. ❌ 任何"MST-wi 实测表现"的措辞（未跑原生引擎）。
2. ❌ 与 BACFuzz / MOCGuard / BolaZ 的任何数值比较（不可得）。
3. ❌ 只报 `v3` 的 precision 而不报 recall / F1。
4. ❌ 把"点估计不劣于"写成"严格支配"。
5. ❌ 把 Gitea 的 96% / 24-of-25 通道占比写成"野外发生率"。
6. ❌ 把 `isSupervisorOf` 当作"与 GUI 可达性不同的一类"谓词（论文 DSL 表定义为 "can access the URLs of b"）。
7. ❌ 声称"已证明 MST-wi 失效"——只能说"该 MR 家族的结构在此系统上的这种实例化会产生确定性方向的假确证"。

# 统计报告审查 · 以 Nature Portfolio 统计规范为准

> 审查对象：`04_绘图与分析/results/metrics.json`（由 `analysis/compute_all.py` 从原始记录重算）
> 审查方法：`nature-statistics` skill 的 audit 流程（设计抽取 → n 与重复定义 → 声称—分析映射 → 常见失效模式 → 报告完整性 → 图统计对齐）
> 结论摘要：**1 条 P0（分析单元非独立 → 区间系统性偏窄）**、**1 条 P0（未校正的多重比较）**、**3 条 P1**、**3 条 P2**。
> 全部修法已回写 `EVALUATION_METRICS.md` 与 `compute_all.py`（设计结构块）。

---

## 1. 设计抽取（design readout）

| 项 | 事实 | 来源 |
|---|---|---|
| 响应变量 | 逐记录的混淆类别（TP/FP/FN/TN）、告警、假确证、弃权 | `raw_matrix.jsonl` |
| 实验条件 | 情景 S1–S7 × 配置标签（mode/vulnerable/share_visibility/introspection） × MR × `precond_variant` × `gui_mode` | 同上 |
| **独立实验单元** | **设计格 = (情景, 配置) = 52 个** | `design_structure.design_cells` |
| 技术/参数重复 | `precond_variant`（3，例外阶梯）与 `gui_mode`（2，GUI 模型读法） | `design_structure.cell_expansion = 6` |
| 情景数 | 7 | `design_structure.n_scenarios` |
| **MR 条数** | **2**（MR-002、MR-004） | `design_structure.n_mrs` |
| 真实系统 | Gitea 1.22.6，构造拓扑，每读法 48 格 | `real_system` |
| 随机化 / 盲法 | 不适用（构造式设计，非抽样研究） | — |
| 排除规则 | 无排除；错误记录 0 条（`meta.synthetic_errors = 0`） | `meta` |
| 缺失数据 | 无 | — |

**关键事实**：`576 条记录 = 52 设计格 × (3 precond_variant × 2 gui_mode) 的确定性展开`（MR-004 只覆盖 44 格，故 52×6 + 44×6 = 576）。`precond_variant` 与 `gui_mode` 是**被刻意拨动的开关**，不是重复实验。

---

## 2. 主要统计问题

### [P0] 分析单元非独立 —— 记录级区间系统性偏窄

- **证据**：`design_structure.independence_verdict`；`records_per_cell ∈ {6, 12}`；同一格内记录共享对象图、`setup` 与真值。
- **为何重要**：所有 Wilson / Newcombe 区间（Block 0 的 n=9、Block 6 的 n=12、Block 8 的 n=18/36、Block 9 的 n=576）都把确定性展开当成独立伯努利抽样。**未校正的依赖结构只会让区间变窄**（伪重复，pseudoreplication，见 common-failure-modes P0）。
- **修法（已落实）**：
  1. 正文**每条计数同时给出设计格数与记录数**；
  2. 区间一律标注为"**约定性**"（convention），仅用于说明量级与不确定方向；
  3. **禁止**用记录级区间做跨方法显著性主张；
  4. 显式给出**有效重复层级**：设计格 52 / MR 2 / 情景 7 / 真实系统 1 —— 对"MST-wi 的 MR 总体"的外推上界即 **MR 条数 = 2**。

### [P0] 未校正的多重比较

- **证据**：Block 9 比较 6 个方法 × 2 个指标；Block 8 比较 2 层 × 6 变体；Block 6 比较 3 情景 × 3 裁决器。
- **为何重要**:比较族未定义、未校正，读者无法判断假阳性膨胀。
- **修法（已落实）**：在方法节声明——本工作**只报点估计与未校正区间，属描述性枚举**；**唯一的推断性检验**是 Block 9 的单一预设对照（`direct_observe − v3` 的召回差值，Newcombe 混合得分法），它是一个**预设的主对照**，不构成多重比较族。

### [P1] 小样本上界不足 —— 以 2 例报"1.00"

- **证据**：`block2.FP_E3 = 2/2 = 1.00`，Wilson 95% CI **[0.3424, 1.0]**。
- **风险**：以 n=2 头版"假确证率 1.00"是典型小样本过度声称。
- **修法（已落实）**：① `FP_E3` **必须**始终带区间出现；② 正文**改用大分母口径领衔**——Block 0 的每格 9 例（4/9 = 44%，CI [0.189, 0.733]）与 Block 9 的 FP = 0/360；③ 措辞降为"在已枚举的设计内"。

### [P1] 第二实现一致性 54/54 未报区间

- **证据**：`m5_second_implementation = 54/54 = 1.00`。
- **修法（已落实）**：报 Wilson 95% CI **[0.934, 1.0]**；并保留既有 caveat——同一模型编写，只排除实现偶然性，**不排除共同盲点**。

### [P1] "差异不显著"须防误读为"无差异"

- **证据**：Block 9 `direct_observe − v3` 召回差 **0.0139**，Newcombe 95% CI **[−0.0797, 0.1072]**，`significant_at_95 = false`。
- **为何重要**：不能写成"两者等价"；且此区间同样偏窄 ⇒ **偏窄只会更容易判显著，故"不显著"这一结论是稳健的**（对结论方向有利）。
- **修法（已落实）**：正文固定用语 = "**点估计非劣**（point-estimate non-inferiority）"，并显式写出"差异在 95% 水平不可与零区分"。**禁止**出现 "strictly dominates / 严格支配"。

### [P2] 误差线未定义

- **修法（已落实）**：全部图注声明"误差线 = Wilson 95% 得分区间；见 `EVALUATION_METRICS.md`"；图中凡出现区间处均按同一口径。

### [P2] 面板 `n` 未逐面板给出

- **修法（已落实）**：`fig2`–`fig6` 的 `xticklabels` 内已内嵌各类别 `n`；图注再逐面板复述。

### [P2] 软件/版本未声明

- **修法（已落实）**：方法节声明 Python 3.13.12；**区间由脚本手写实现**（Wilson 得分区间、Newcombe 混合得分差值区间），**未使用 scipy**（本机不可得），公式在 `compute_all.py` 中可核。

---

## 3. 可粘贴的方法节文字（英文，已按上述修法写定）

见 `03_论文撰写/paper/sections/03_protocol.tex` 的 *Statistical treatment* 小节。要点：

- `n` 定义：**设计格**为独立单元；`precond_variant`/`gui_mode` 为确定性开关，非重复。
- 未校正、描述性；唯一预设推断对照为 Block 9 的召回差值。
- 区间口径与实现（手写 Wilson / Newcombe，Python 3.13.12）。
- 有效重复上界：2 条 MR、1 个生成器、1 个真实系统。

---

## 4. AUTHOR_INPUT_NEEDED

- `AUTHOR_INPUT_NEEDED`：是否要再补一条**不同机制**的 MR（当前 2 条，MR-002/MR-004 同属"授权面缺失"族），以抬高 MR 层外推上界？（这是唯一能把 N 从 2 抬起来的动作，见 `EXPERIMENT_DESIGN.md`）
- `AUTHOR_INPUT_NEEDED`：Gitea 之外是否再上第二个真实系统（Nextcloud / Joomla）？当前真实系统外推上界为 1。

---

## 5. 审稿人仍可能挑战的点（reviewer-risk note）

1. **2 条 MR 不足以称"MST-wi 的 MR"** —— 这是最硬的一条，已在正文承认并作为外推上界写明。
2. **设计格内的语义等价性** —— 审稿人可能质疑 `precond_variant` 三档是否真的语义不同；`EXPERIMENT_DESIGN.md` 已逐档给出定义，但最好补一份语义对照表。
3. **区间偏窄的方向** —— 已论证对"不显著"结论稳健；但若审稿人要求把区间做在格层（n=52 或更小），需准备一个格层重算版本（可作为补充材料）。

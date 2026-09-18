# Research Contract（研究契约 · claims 与证据的绑定）

**生成日期**：2026-09-17
**来源**：`refine-logs/EXPERIMENT_PLAN.md` 的 Claim Map
**下游消费者**：`result-to-claim`（判断结果支持哪些 claim）、`ablation-planner`、`auto-review-loop`

> 本契约的作用：把"论文要主张什么"与"哪个证据文件能支撑它"**在跑实验之前**绑定。
> 任何 claim 若无对应证据文件 → 不得进入论文。任何结果若不在契约内 → 记录为探索性发现，
> 不得反向补进 claim。

---

## Claims 与证据绑定

| # | Claim | 证据来源（文件级） | 当前状态 | 允许的主张强度 |
|---|---|---|---|---|
| **C1** | 合法例外分 E1/E2/E3 三层；MST-wi 76 条 MR 的谓词全集只覆盖 E1/E2 | `01_文献调研/mstwi_artifact/catalog_text.txt`（穷举脚本 + 命中表）<br>`01_文献调研/MST-wi先例核查与机制重定位.md` | **已有证据**（谓词穷举完成） | 可作事实陈述，附可复核的检索命令 |
| **C2** | E3 在 MR 范式内原理上不可表达（否则退化为重言式） | `refine-logs/FINAL_PROPOSAL.md` § 不可表达性命题<br>`02_Idea与架构/研究方案_v5.md` §2.2 | **纯逻辑，不需实验** | 作命题陈述，必须写出可证伪条件 |
| **C3** ★ | 存在 E3 例外时，授权类 MR 的假阳率上升，且 FP 与 TP 观测不可区分；Boundary-aware 能恢复可判定性 | `experiments/results/raw_matrix.jsonl`<br>`experiments/results/summary.json`<br>`experiments/results/SUMMARY.md` | **本次实验产出** | 受控系统上的量化结论；**不得外推为真实世界覆盖率** |
| **C4** | 可复现的分层评测协议 | `experiments/` 全目录 + `run_meta.json`（version pin 记录） | **本次产出** | 说明第三方可重跑；若引擎非原生须显式声明 |

## 已知限制（必须随 claim 一起报告）

| 限制 | 影响的 claim | 处理方式 |
|---|---|---|
| MR 为**语义移植**，非 MST-wi 原生引擎（本机无 Maven） | C3, C4 | 在 Limitations 明示；提供 catalog 行号供逐行比对；提供原生构建步骤作为可选路径 |
| 被测系统为**自建受控系统**，非真实开源应用 | C3 | 明确定位"受控实验以测可控性"；说明 crAPI 无对象级共享、VAmPI 无共享语义 |
| GUI 可达性谓词使用**代理语义**（列举端点） | C3 | 双向报告 `gui_blind` 与 `gui_aware` 两个变体；结论方向不一致时如实报告 |
| 特异性口径复现为**近似**（分母非原引擎输入计数） | M4（探索性） | 标注为近似，仅用于说明该口径的掩盖效应 |
| **缺少异厂商模型独立复核**（Codex 额度限制） | 全部 | 必须显式标注；`experiment-integrity.md` 要求"写实验代码的模型不得自判实验完整性" |

## 禁止的主张（anti-claims，写论文时逐条自查）

1. ❌ 不得声称本方法"发现了更多漏洞"或与 MST-wi 做数值优越性比较
   —— 输出语义不同（它报 binary，我们报三级裁决），不可比。
2. ❌ 不得声称 MST-wi 的实现有 bug
   —— 其 specificity 在其语料上成立；我们指出的是**语言表达力的边界**。
3. ❌ 不得声称 E3 限制会导致真实世界大规模漏报/误报
   —— 只能说"在受控系统上该失效模式可复现且可量化"。
4. ❌ 不得把 `indeterminate` 包装成"确证正常"
   —— 它是**诚实弃权**，必须与 `pass` 区分。
5. ❌ 不得声称本工作"解决了 oracle problem"
   —— 只声称"刻画了其中一层边界并给出局部修正"。

## 结果判定规则（预注册）

| Claim | 支持（claim_supported） | 部分支持 | 被证伪 |
|---|---|---|---|
| C3（前半：FP 上升） | `FP_E3` > `基线 FP` 且 `基线 FP` = 0 | `FP_E3` > 0 但基线 FP 也 > 0（归因不纯） | `FP_E3` = 0 |
| C3（后半：可恢复） | 恢复率 > 0 且 `Degrade-all` 的检测力保持率 = 0（说明不是靠弃权） | 恢复率 > 0 但代价 > 0 且 v2 无法消除 | 恢复率 = 0 |
| C1（实证侧） | `FP_E3(E1E2) ≈ FP_E3(raw)` | 有差异但方向一致 | E1/E2 过滤显著降低 FP |

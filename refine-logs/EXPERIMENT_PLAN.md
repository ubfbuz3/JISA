# Experiment Plan

**Problem**: 变形测试（MT）的授权类 MR 在什么条件下会丧失对 BOLA 的判定能力？边界在哪里？能否量化、能否修正？
**Method Thesis**: BOLA 的合法例外分三层（E1 主体属性 / E2 主体间关系 / **E3 主体×对象显式授权**）；现有 MR 目录（MST-wi 76 条）只能表达 E1/E2，E3 在 MR 范式内原理上不可表达；因此当被测应用存在 E3 例外时，授权类 MR 的假阳率上升且 FP 与 TP 观测不可区分；给 MR 触发加一个**对象级 E3 探测**可恢复可判定性。
**Date**: 2026-09-17
**目标期刊**: JISA（中科院三区）
**Plan 生成流程**: ARIS W1 `experiment-plan` → 本文件 → ARIS W1.5 `experiment-bridge` 实现执行

---

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|-------|-----------------|-----------------------------|---------------|
| **C1** 表达力层级：合法例外分 E1/E2/E3 三层；MST-wi 76 条 MR 只覆盖 E1/E2 | 若无此层级，"边界"无处安放；这是全部立论的地基 | 谓词全集穷举（`isAdmin`/`isSupervisorOf` 命中，`ACL`/`owns`/`canAccess`/`shared` 零命中）+ 76 条 MR 条件逐条核对 | B1 |
| **C2** 不可表达性：E3 在 MR 范式内原理上不可表达（否则退化为重言式） | 把"经验观察"上升为"原理边界"，否则审稿人会说"只是没写而已" | 形式化命题 + 可证伪条件（若能给出目录中任一可表达 E3 的谓词即被推翻）。**纯逻辑，不需实验** | B1 |
| **C3** ★ 辨识力丧失可量化：存在 E3 例外时授权类 MR 的假阳率显著上升，且 FP 与 TP 观测不可区分；Boundary-aware 执行能恢复可判定性 | 这是全文唯一的**实证**贡献，也是 JISA 接受的关键 | `FP_E3` 显著高于基线 FP（方向性即可，不预设阈值）+ S3/S4 存在响应等价实例 + 恢复率与代价同时报告 | B2, B3, B4, B5 |
| **C4** 可复现的分层评测协议 | 三区期刊对 artifact 的要求；也是"新方法"形态的载体 | 第三方按 version pin 可重跑出同表 | B2 全流程 |

> **Anti-claim to rule out**（必须主动排除的反主张）：
> - ❌ "FP 升高只是因为 MR 太宽松，跟 E3 无关" → 由 **B3** 排除（V-noE3 上同一批 MR 的基线 FP 必须为 0）
> - ❌ "加个 E1/E2 过滤就解决了，不需要 E3" → 由 **B3** 排除（复现 MST-wi 的 `!isSupervisorOf` 做法，FP_E3 不降）
> - ❌ "Boundary-aware 只是'一律弃权'，等于放弃检测" → 由 **B4** 排除（一律降级会把 S2/S4 的真 BOLA 也降级，检测力归零；对象级探测则保留）
> - ❌ "结论依赖你自己的 MR 实现" → 由 **B5** 排除（双实现：忠实移植 MST-wi 语义版 + 独立最小版）

---

## Paper Storyline

- **Main paper must prove**：C3（`FP_E3`、辨析力丧失率、恢复率与代价）+ C1 的谓词穷举表 + C2 的命题
- **Appendix can support**：specificity 口径复现（分母=follow-up 输入数为何掩盖该失效）、GUI 可达性模型的敏感性分析
- **Experiments intentionally cut**：
  - 与 EvoMaster fault 306 的数值优越性比较（**不做**：输出语义不同——它报"疑似"、我们报三级裁决，不可比，只引原文做层级定位）
  - 真实开源应用上的大规模扫描（**不做**：crAPI 无对象级共享、VAmPI 无共享语义，且真实应用无法获得"构造式真值"这一 E3 探测前提）
  - 新增 MR 目录（**不做**：本工作不是"再提一套 MR"）

---

## Experiment Blocks

### Block 1: 表达力层级证据（C1 + C2）

- **Claim tested**: C1, C2
- **Why this block exists**: 没有这张表，整篇论文就是"我猜 MR 处理不了共享"
- **Dataset / task**: MST-wi 复现包中的 `Catalog_of_MRs.pdf`（129 页 MR 源码）+ `PatternsOfMRs.xlsx` + 论文正文（43 页）
- **Compared systems**: 不适用（文档分析）
- **Metrics**:
  - 谓词全集（按元数分类：1 元主体属性 / 2 元主体-主体 / 2 元主体-对象）
  - 对象级谓词命中数（目标：**0**）
  - `owner`/`ownership`/`delegat`/`ACL`/`shared` 在正文中的命中数
- **Setup details**: 已在 `01_文献调研/mstwi_artifact/catalog_text.txt`（22.7 万字符）与 `mstwi_paper_text.txt`（23.3 万字符）上可复跑；脚本需落盘以保证可复核
- **Success criterion**: 对象级谓词命中 0 且能被独立复核；E3 不可表达性命题的可证伪条件被明确写出
- **Failure interpretation**: 若发现任一对象级谓词 → C1 成立性受损、C2 被推翻，方案回到"需要新的边界刻画"（应立刻改投他处）
- **Table / figure target**: Table 1（谓词层级表）、Table 2（与 MST-wi 对照表）、§3 命题
- **Priority**: **MUST-RUN**

### Block 2: 主锚点 —— E3 场景下的假阳率矩阵（C3）

- **Claim tested**: C3（前半：FP 上升）
- **Why this block exists**: 这是论文的**第一个硬数字**
- **Dataset / split / task**: 受控最小 API 的两个变体，端点与 OpenAPI **完全一致**，仅差共享端点

  | 变体 | 端点 | 说明 |
  |---|---|---|
  | **V-noE3** | `POST /auth/login`、`GET /doc`（列举）、`GET /doc/{id}`、`PUT /doc/{id}`、`POST /doc` | 仅归属判定 |
  | **V-E3** | 上述全部 **+** `POST /doc/{id}/share`、`GET /doc/{id}/shares` | 增加对象级显式授权 |

- **Compared systems**: 不适用（同一批 MR 在两个变体上跑）
- **四场景真值表**（构造式真值，非推断）：

  | 场景 | 设置 | 真值 | 期望 MR 行为 |
  |---|---|---|---|
  | S1 | 无共享，B 访问自己的 doc | 正常 | 不触发 |
  | **S2** | 无共享，B 访问 A 的 doc | **BOLA** | 触发（TP） |
  | **S3** | A **显式共享** doc 给 B，B 访问 | 正常 | **不应触发** |
  | **S4** | A 共享 doc1 给 B，B 访问**未共享**的 doc2 | **BOLA** | 触发（TP） |
  | **S5** | A 共享 doc1 给 B（**只读**），B 对 doc1 发起 **PUT** | **BOLA（写越权）** | 触发（TP） |

- **Metrics**: `FP_E3` = S3 触发率；`基线 FP` = V-noE3 上 S1 触发率；S2/S4/S5 触发率（召回侧）
- **Setup details**: 每条 MR 在每个场景上跑 N=30 次重复（同 seed 控制对象 ID 分配）；请求与响应全文落盘
- **Success criterion**: `FP_E3` > `基线 FP`（方向性），且 `基线 FP` = 0（保证差异可归因于 E3 而非 MR 宽松）
- **Failure interpretation**: 若 `FP_E3` = 0 → C3 被证伪，如实报告；此时论文退化为纯理论 + 文档分析（需重新评估三区可投性）
- **Table / figure target**: Table 3（触发矩阵，论文主表）
- **Priority**: **MUST-RUN**

### Block 3: 新颖性隔离 —— E1/E2 过滤能救回多少？（C1 的实证支撑）

- **Claim tested**: C3（"现有例外处理不足以覆盖 E3"）
- **Why this block exists**: 直接回答"你说 E3 不可表达，但 MST-wi 已经有 `isAdmin`/`isSupervisorOf`，加上不就完了？"
- **Dataset / task**: 同 Block 2，但 MR precondition 加上 MST-wi 的例外谓词
- **Compared systems**（3 个变体，严格对应 MST-wi 的 DSL 能力）:
  1. `MR-raw`：无例外谓词（≈ EvoMaster fault 306 的层级 ℒ₁）
  2. `MR-E1`：+ `!isAdmin(B)`
  3. `MR-E1E2`：+ `!isAdmin(B)` + `!isSupervisorOf(B, A)`（**= MST-wi 的实际能力上限 ℒ₂**）
- **Metrics**: 三个变体各自的 `FP_E3`
- **Setup details**: 关键设计——把 B 设为 A 的**非**下级、**非**管理员、但**被共享**了对象。此时 E1/E2 谓词全部为真（不构成例外），MR 照常触发
- **Success criterion**: `FP_E3(MR-E1E2) ≈ FP_E3(MR-raw)`（E1/E2 过滤对 E3 无效）
- **Failure interpretation**: 若 E1/E2 过滤显著降低 FP → C1 的层级划分在实证上不成立（则 MST-wi 的能力被低估，需重新定位）
- **Table / figure target**: Table 4（消融 3）／图：FP_E3 vs 例外谓词层级
- **Priority**: **MUST-RUN**

### Block 4: 简洁性检查 —— 对象级探测 vs 一律降级

- **Claim tested**: C3（后半：Boundary-aware 的收益**不是**靠弃权换来的）
- **Why this block exists**: 排除"你只是把所有触发都降级，检测力归零，当然 FP 变 0"这一致命质疑
- **Dataset / task**: 同 Block 2
- **Compared systems**:
  1. `Baseline-raw`：原始 MR（触发即报缺陷）
  2. `Degrade-all`：凡触发即降级 `indeterminate`（**退化方案**）
  3. **`Boundary-aware(v1)`**：触发后探测该对象是否存在 E3 记录，有则降级、无则 `violation-proven`
  4. **`Boundary-aware(v2)`**：v1 + **权限层级匹配**（共享记录带 `read`/`write`，触发动作的操作类型必须被共享权限覆盖才降级）
- **Metrics**: 恢复率（S3→indeterminate）、检测力保持率（S2/S4/S5→violation-proven）、代价（真 BOLA 被误降为 indeterminate 的比例，主要在 S5）
- **Setup details**: `Degrade-all` 的检测力保持率**必然为 0**（构造性事实），用以证明对象级探测的必要性
- **Success criterion**: `Boundary-aware(v2)` 在 S3 上恢复率 100% 且 S5 代价 0；`Degrade-all` 检测力保持率 0
- **Failure interpretation**: 若 v2 无法消除 S5 代价 → 如实报告代价，并说明"对象级探测的粒度上限"
- **Table / figure target**: Table 5（消融 1/2 + 增益-代价表）
- **Priority**: **MUST-RUN**

### Block 5: 失败分析 —— 辨析力丧失与不可区分性

- **Claim tested**: C3（"FP 与 TP 观测不可区分"这一关键论断）
- **Why this block exists**: 这是"必须弃权"而非"应当报缺陷"的**唯一理由**。若能区分，就不需要 indeterminate
- **Metrics**:
  - `辨析力丧失率` = S3 与 S4 产生**响应等价**（状态码+body+headers 规范化后相同）的比例
  - 反例检查：若不区分率 < 100%，报告哪些字段能区分（说明边界比预想窄）
- **Setup details**: 响应规范化规则须预注册（去时间戳/去随机 ID/排序 JSON key）；原始响应全文落盘可复核
- **Success criterion**: 存在 S3/S4 响应等价的实例（不需 100%，存在即成立）
- **Failure interpretation**: 若 S3/S4 全部可区分 → 可判定性并未丧失，`indeterminate` 的必要性被削弱；此时应退守为"仅 S5 类写越权需探测"
- **Table / figure target**: Table 6 + 一个响应 diff 的定性示例
- **Priority**: **MUST-RUN**

---

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|-----------|------|------|---------------|------|------|
| **M0** Sanity | 单条 MR 在 V-noE3 上跑通 S1/S2，验证认证/归属/判定三条链路正确 | 2 场景 × 2 MR = 4 | S1 不触发 **且** S2 必须触发。任一不满足 → 修实现，不得进入 M1 | ~1 min, 数十请求 | 归属判定写错导致 S2 不触发（最常见） |
| **M1** Baseline | 两个系统变体 × 四/五场景 × MR-raw | 2 × 5 × 2 = 20 | `基线 FP`(V-noE3@S1) 必须为 0 | ~5 min, 数百请求 | V-E3 的端点若与 V-noE3 不一致 → 变体对照失效（**须自动校验 OpenAPI 一致**） |
| **M2** Main | Boundary-aware(v1) 与 (v2) 在 M1 的触发集上裁决 | 复用 M1 观测，纯离线裁决 | 恢复率与代价同时可得 | ~0（离线） | 共享记录若无法在触发时点回溯 → 构造式真值不成立 |
| **M3** Ablation | Block 3（E1/E2 过滤）+ Block 4（Degrade-all）+ Block 5（不可区分性） | 3 组 | `FP_E3(E1E2) ≈ FP_E3(raw)` 且 `Degrade-all` 检测力 = 0 | ~5 min | E2 谓词在 V-E3 上无天然对手（需显式构造"非下级"保证谓词为真） |
| **M4** Polish | specificity 口径复现（分母=follow-up 输入数） | 1 | 两变体分别报告 | ~2 min | 分母口径若理解错 → 数字不可比（须以原文定义为准并标注） |
| **M5** Robustness | 换引擎实现（独立最小版 MR 执行器）重跑 M1 | 20 | 主结论方向不变 | ~5 min | 第二实现若与第一实现语义漂移 → 须报告差异而非掩盖 |

**First three runs to launch**:
1. `M0-R001`：MR-002（换凭证等价性语义）在 V-noE3 上跑 S1
2. `M0-R002`：MR-002 在 V-noE3 上跑 S2
3. `M1-R003`：MR-002 在 V-E3 上跑 S3（**第一个预期会出现 FP 的点**）

---

## Compute and Data Budget

- **Total estimated container-minutes**: ~30 分钟（本机进程内起服务，无需容器；容器版本作为复现载体提供但非必需）
- **Total HTTP requests**: ~2,000（远低于任何 rate limit）
- **No GPU required**（本工作非 ML 训练类；ARIS 的 GPU 相关常量在此不适用，已置空）
- **Data preparation needs**:
  - 受控 API：本次自建（需 `POST /doc` 造数据、`POST /doc/{id}/share` 造 E3 真值）
  - MST-wi MR 目录：**已在本地**（`01_文献调研/mstwi_artifact/`），无需重新下载
- **Human evaluation needs**: 无
- **Biggest bottleneck**: **GUI 可达性谓词（`userCanRetrieveContent` / `cannotReachThroughGUI`）在 MST-wi 中依赖爬取 GUI 才能求值**。受控系统没有 GUI，故须显式定义其代理语义并做敏感性分析（见 Risks）

## Environment Constraints（实测，2026-09-17）

| 项 | 状态 | 对实验的影响 |
|---|---|---|
| Docker 守护进程 | ❌ 未运行 | 容器版 compose 作为复现载体产出，但**不在本机作为执行路径**；执行路径改用纯 Python stdlib 进程内服务（零第三方依赖，更可复现） |
| Maven | ❌ 未安装 | **MST-wi 原生引擎无法在本机构建** → 直接走 v5 §7 的退路：**忠实移植其 MR 语义的最小执行器**（源码已逐行提取，可溯源）。论文中须明示此限制 |
| Java 1.8.0_291 | ✅ | 保留可能性：若后续装 Maven 可尝试原生构建 |
| Python 3.13 | ✅ | 主实现语言 |
| MVP 依赖策略 | 零第三方 | 服务端 `http.server`、客户端 `urllib.request`；matplotlib 仅用于出图（缺失不阻塞） |

## Risks and Mitigations

- **[可行性] MST-wi 原生引擎本机不可构建（Maven 缺失 + 需 chromedriver/VM）**
  - **Mitigation**：以逐行提取的 MR 源码为规范，实现忠实的最小执行器；**每条 MR 标注其在 catalog 中的行号**，使第三方可逐行比对。论文中把"未使用原引擎"写入 Limitations，并给出装好 Maven 后的构建步骤作为可选路径。
- **[效度] `userCanRetrieveContent` / `cannotReachThroughGUI` 依赖 GUI 爬取，受控系统无 GUI**
  - **Mitigation**：定义两个代理语义并**双向报告**：`GUI-blind`（保守：该谓词恒 false，等价于"仅凭 API 观测"）与 `GUI-aware`（用用户的列举端点 `GET /doc` 建模可达性）。若两条路径结论方向一致 → 结论稳健；若不一致 → 这本身就是"判定依赖 GUI 模型完整性"的证据，是**发现而非缺陷**，如实报告。
- **[效度] 受控系统非真实应用**
  - **Mitigation**：明确定位为"受控实验以测可控性"，不声称真实世界覆盖率；在 Limitations 说明 crAPI 无对象级共享、VAmPI 无共享语义，故 E3 场景必须自建（且**必须自建**才能获得构造式真值）。
- **[审稿] "E3 显然不可表达，太 trivial"**
  - **Mitigation**：Block 2/3/4/5 四个实证块证明该限制在实践中确有影响（FP 上升、E1/E2 过滤无效、检测力与可判定性的权衡）。
- **[审稿] "你自己实现的 MR 可能不是 MST-wi 的原意"**
  - **Mitigation**：双实现（M5）+ 逐行溯源标注 + 公开 MR 源码片段对照表。
- **[诚信] 跨模型审查缺失**
  - Codex 账号额度此前耗尽（至 2026-10-08）。若 W1.5 的 Phase 2.5 跨模型代码审查不可用，**必须在结果文件中显式标注"本批实验缺少异厂商模型独立复核"**，不得静默跳过（`shared-references/experiment-integrity.md` 要求：写实验代码的模型不得自判实验完整性）。

## Final Checklist

- [ ] Main paper tables are covered（Table 3 触发矩阵 + Table 4/5/6 消融/代价）
- [ ] Novelty is isolated（Block 3 证明 E1/E2 过滤无效）
- [ ] Simplicity is defended（Block 4 证明不是"一律弃权"）
- [ ] Frontier contribution is justified or explicitly not claimed（**本工作非 frontier-model 依赖**：显式不声称 LLM 环节；无 LLM 参与判定）
- [ ] Nice-to-have runs are separated from must-run runs（Must-run: B1–B5；Nice: M4 specificity 复现、M5 第二实现）
- [ ] Every claimed number traces to an output file in `experiments/results/`
- [ ] 每个判定附证据：MR 触发记录 + 共享操作记录 + 对照响应（v5 §4.4 第 5 条）

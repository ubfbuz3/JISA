# 实验结果汇总（自动生成，勿手改）

- 记录总数：576，成功 576，错误 0
- 代表切片：precond=raw，gui_mode=aware（n=96）

## Block 0 · 2×2 网格（通道可见性 × 应用授权正确性）

- 口径：仅含存在对象级共享的场景 S3–S7；代表切片 raw+GUI-aware
| config | 通道可见性 | 应用授权 | case 数 | FP | FN | TP | TN |
|---|---|---|---|---|---|---|---|
| V-E3-vuln0-unlisted | unlisted | correct | 9 | 4 | 0 | 0 | 5 |
| V-E3-vuln0-listed | listed | correct | 9 | 0 | 0 | 0 | 9 |
| V-E3-vuln1-unlisted | unlisted | violating | 9 | 4 | 0 | 5 | 0 |
| V-E3-vuln1-listed | listed | violating | 9 | 0 | 1 | 4 | 4 |

> 每个格子都可能同时出现 FP 与 FN —— 这正是「谓词在误报与漏报之间二选一」的可视化证据，也说明误报并非「关掉谓词」造出来的。

## Block 2 · 主触发矩阵（T=触发，·=未触发）

| config | S1 | S2 | S3 | S4 | S5 | S6 | S7 |
|---|---|---|---|---|---|---|---|
| V-E3-vuln0-listed | ·· (0/2) | ·· (0/2) | ·· (0/2) | ·· (0/2) | · (0/1) | ·· (0/2) | ·· (0/2) |
| V-E3-vuln0-unlisted | ·· (0/2) | ·· (0/2) | TT (2/2) | ·· (0/2) | · (0/1) | TT (2/2) | ·· (0/2) |
| V-E3-vuln0-unlisted-nointro | ·· (0/2) | ·· (0/2) | TT (2/2) | ·· (0/2) | · (0/1) | TT (2/2) | ·· (0/2) |
| V-E3-vuln1-listed | TT (2/2) | TT (2/2) | ·· (0/2) | TT (2/2) | · (0/1) | ·· (0/2) | TT (2/2) |
| V-E3-vuln1-unlisted | TT (2/2) | TT (2/2) | TT (2/2) | TT (2/2) | T (1/1) | TT (2/2) | TT (2/2) |
| V-E3-vuln1-unlisted-nointro | TT (2/2) | TT (2/2) | TT (2/2) | TT (2/2) | T (1/1) | TT (2/2) | TT (2/2) |
| V-noE3-vuln0 | ·· (0/2) | ·· (0/2) | ·· (0/2) | ·· (0/2) | · (0/1) | — | — |
| V-noE3-vuln1 | TT (2/2) | TT (2/2) | TT (2/2) | TT (2/2) | T (1/1) | — | — |

**`FP_E3`**（V-E3-vuln0-unlisted @ S3，即存在 E3 例外且应用授权正确） = **2/2 = 1.0**

**基线 FP**（V-noE3-vuln0 @ S1，无共享阴性对照） = **0/2 = 0.0**

**对照 FP**（V-E3-vuln0-listed @ S3，共享对 GUI 可见） = 0/2 = 0.0


召回侧（vuln=1）：

| scenario | 触发 | 比例 |
|---|---|---|
| S2 | 2/2 | 1.0 |
| S4 | 2/2 | 1.0 |
| S5 | 1/1 | 1.0 |

## Block 3 · 例外谓词层级消融（V-E3-vuln0-unlisted @ S3）

| 例外谓词配置 | FP_E3 触发 | 比例 | 含义 |
|---|---|---|---|
| MR-raw | 2/2 | 1.0 | 无例外谓词（≈ EvoMaster fault 306 层级 ℒ₁） |
| MR-E1 | 2/2 | 1.0 | + !isAdmin |
| MR-E1E2 | 2/2 | 1.0 | + !isSupervisorOf（= MST-wi 能力上限 ℒ₂） |

## Block 4 · 裁决质量：收益与代价（全部应用配置）

| 裁决器 | 原始误报 | 恢复(→indeterminate) | 恢复率 | 检测力保持 | 代价(真BOLA被降级) | 代价率 | 漏报(BOLA未触发) |
|---|---|---|---|---|---|---|---|
| v1 | 16 | 8 | 0.5 | 33 | 2 | 0.0571 | 1 |
| v2 | 16 | 8 | 0.5 | 35 | 0 | 0.0 | 1 |
| v3 | 16 | 16 | 1.0 | 17 | 18 | 0.5143 | 1 |
| degrade_all | 16 | 16 | 1.0 | 0 | 35 | 1.0 | 1 |

> 仅看 FP 发生的那一个配置（V-E3-vuln0-unlisted）：v1 恢复率 0.5，v2 恢复率 0.5。
> `degrade_all`（凡触发即降级）的检测力保持率为 **0.0**、代价率 1.0 —— 这正是它只能靠放弃全部检测来换取零误报的证据，从而说明对象级探测相对「一律弃权」的必要性。
> `v2`（+权限层级匹配）把 v1 的代价率 0.0571 降到 **0.0**，同时检测力保持率由 0.9429 升到 **1.0**。

## Block 5 · 辨析力丧失（不可区分性）

- 比较域：仅 vuln=1 的应用（此时 S4/S5 亦为 BOLA，才构成『合法 vs 越权』的不可区分对）
- 比较对数：12
- **判定等价率** = 0.8333
- **结构等价率** = 1.0

> 判定等价 = MR 对「合法共享访问」与「越权访问」给出相同触发结论; 结构等价 = 两次观测在 status+schema 形状上不可区分（具体取值不同）

| config | MR | gui | 对比对 | truth(S3) | truth(对照) | 触发(S3) | 触发(对照) | 判定等价 | 结构等价 |
|---|---|---|---|---|---|---|---|---|---|
| V-E3-vuln1-unlisted | MR-002 | aware | S3 vs S4（访问未共享对象） | normal | bola | True | True | True | True |
| V-E3-vuln1-unlisted | MR-002 | blind | S3 vs S4（访问未共享对象） | normal | bola | True | True | True | True |
| V-E3-vuln1-unlisted | MR-004 | aware | S3 vs S4（访问未共享对象） | normal | bola | True | True | True | True |
| V-E3-vuln1-unlisted | MR-004 | blind | S3 vs S4（访问未共享对象） | normal | bola | True | True | True | True |
| V-E3-vuln1-unlisted | MR-002 | aware | S3 vs S5（写越权） | normal | bola | True | True | True | True |
| V-E3-vuln1-unlisted | MR-002 | blind | S3 vs S5（写越权） | normal | bola | True | True | True | True |
| V-E3-vuln1-listed | MR-002 | aware | S3 vs S4（访问未共享对象） | normal | bola | False | True | False | True |
| V-E3-vuln1-listed | MR-002 | blind | S3 vs S4（访问未共享对象） | normal | bola | True | True | True | True |
| V-E3-vuln1-listed | MR-004 | aware | S3 vs S4（访问未共享对象） | normal | bola | False | True | False | True |
| V-E3-vuln1-listed | MR-004 | blind | S3 vs S4（访问未共享对象） | normal | bola | True | True | True | True |
| V-E3-vuln1-listed | MR-002 | aware | S3 vs S5（写越权） | normal | bola | False | False | True | True |
| V-E3-vuln1-listed | MR-002 | blind | S3 vs S5（写越权） | normal | bola | True | True | True | True |

## Block 7 · S3 与 S5 能否同时判对（判定能力二选一）

| config | S3 不触发(正确) | S5 触发(正确) | 两者同时正确 |
|---|---|---|---|
| V-E3-vuln1-unlisted | False (0/2) | True (1/1) | False |
| V-E3-vuln1-listed | True (2/2) | False (0/1) | False |

- **存在同时判对的配置** = False
- 在 vuln=1（S3 与 S5 仅能靠授权区分）上，不存在使 S3 与 S5 同时判对的配置 ⇒ MR 判定被迫在「误报」与「漏报」之间二选一。

## Block 6 · 修正机制的可观测性边界（框架创建 vs 带外预存共享）

| 场景 | 授权来源 | 框架侧授权记录 | 原始误报 | v1/v2 恢复 | v1/v2 恢复率 | v1/v2 假确证 | v1/v2 假确证率 | **v3 恢复** | **v3 恢复率** | **v3 假确证** | **v3 假确证率** | **v3 真越权确证** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S3 框架创建（可观测） | framework | 12 | 8 | 8 | 1.0 | 0 | 0.0 | 8 | 1.0 | 0 | 0.0 | 0 |
| S6 带外预存（不可观测） | out_of_band | 0 | 8 | 0 | 0.0 | 8 | 1.0 | 8 | 1.0 | 0 | 0.0 | 0 |
| S7 带外预存 + 真越权 | out_of_band | 0 | 0 | 0 |  | 0 |  | 0 |  | 0 |  | 4 |

> **主张**：修正机制的有效范围 = 共享操作对测试框架可观测；不可观测时失效方向为**假确证**
> 
> S3 与 S6 的**唯一差异**是授权来源：S3 由框架调用共享 API 创建（`share_log` 记 1 条），S6 由带外种入（`share_log` 记 0 条）。应用侧授权判定完全相同（都正确允许）。
> 结果是恢复率从 **1.00 崩到 0.00**，且失效方向不是「恢复不了」而是**把正确应用升级为 `violation-proven`（假确证）**——比原始误报更危险，因为它带「已确证」标签。
> S7 说明该边界是**单侧的**：带外授权不会损害真越权的检测力（仍为确证）。

## Block 8 · v3 的可容许性边界（授权自省面 on / off）

| 配置 | case 数 | 原始误报 | 真越权触发 | v3 恢复率 | v3 假确证率 | v3 检测力保持率 | v3 因自省面缺失弃权 |
|---|---|---|---|---|---|---|---|
| 自省面 **on** | 36 | 8 | 9 | 1.0 | 0.0 | 1.0 | 0 |
| 自省面 **off** | 18 | 8 | 5 | 1.0 | 0.0 | 0.0 | 13 |

- **主张**：v3 的可容许性条件 = 应用暴露测试者可读的授权自省面；面可读 ⇒ 既消除假确证又保住检测力；面缺失 ⇒ 退化为诚实弃权（检测力归零）。
> 
> v3 与 v1/v2 的**唯一差异**是探测数据的来源：v1/v2 读**测试框架自己的账本**（`share_log`），v3 读**被测系统自报的授权面**（`GET /doc/{id}/shares`，以拥有者身份）。
> 对照 v2（同为'权限层级匹配'语义，仅数据源不同）的最强配置：自省面 on 时 v3 假确证 0 次 vs v2 4 次；真越权确证 v3 9 次 vs v2 9 次。
> 自省面 off 时 v3 **全部因无法排除不透明授权而弃权**（13 次），检测力保持率降为 **0.0** —— 这是诚实的代价，而非缺陷。

## 附 · 漏报分析（FN：真 BOLA 但 MR 未触发）

共 1 条。逐条列出来源，避免只报喜不报忧：

| config | scenario | MR | gui | 真值 | 前置条件成立 | 输入1 | 输入2 | 原因 |
|---|---|---|---|---|---|---|---|---|
| V-E3-vuln1-listed | S5 | MR-002 | aware | bola | False | 200 | 200 | 前置条件被 GUI 可达性判定挡住 → MR 不适用 |

> 这说明：依赖 GUI 可达性的前置条件在**共享对 GUI 可见**时会把 MR 变成「不适用」，从而对真正的越权访问**漏报**。它与假阳是同一枚硬币的两面——都是判定能力外包给 GUI 模型的后果。

## M4 · specificity 口径复现（近似）

| config | cases | false alarms | follow-up 输入(≈) | specificity |
|---|---|---|---|---|
| V-noE3-vuln0 | 9 | 0 | 18 | 1.0 |
| V-E3-vuln0-unlisted | 13 | 4 | 26 | 0.846154 |
| V-E3-vuln0-listed | 13 | 0 | 26 | 1.0 |

> 分母口径按 MST-wi 定义为 follow-up 输入数；本表以每 case 2 条 follow-up 输入近似，**不是原引擎的精确输入计数**，仅供说明「该口径为何掩盖失效模式」。

## M5 · 第二实现一致性（排除实现偶然性）

- 可比对数：54，一致 54，不一致 0，**一致率 1.0**
- 映射规则：第二实现的 MR-002 无 GUI 前置条件 → 与主实现 gui_blind 切片对比；第二实现的 MR-004 用列举建模可见性 → 与主实现 gui_aware 切片对比。映射错位会产生假分歧，故显式记录。
- 注意：同一模型编写的独立实现，只排除实现偶然性，不排除共同盲点。

> 无不一致项。

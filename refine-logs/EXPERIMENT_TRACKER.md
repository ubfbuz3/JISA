# Experiment Tracker

> 状态值：TODO / RUNNING / DONE / FAILED / BLOCKED
> 每个 DONE 都指向 `experiments/results/` 下的真实文件（`experiment-integrity.md` 禁止 phantom results）
> 更新时间：2026-09-17 20:05

## M0 · Sanity（阻断门：链路正确）— ✅ 通过

| Run ID | Milestone | Purpose | System / Variant | Scenario | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R001 | M0 | sanity | V-noE3-vuln0 | S1 | triggered | MUST | **DONE** | False（200 vs 403）✅ |
| R002 | M0 | sanity | V-noE3-vuln1 | S2 | triggered | MUST | **DONE** | True（200 vs 200）✅ |

→ 归档：`results/sanity_matrix.jsonl`（144 条，0 错误）

## M1 · Baseline — ✅ 通过（基线 FP = 0）

| Run ID | Milestone | Purpose | System / Variant | Scenario | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R003 | M1 | baseline | V-noE3-vuln0 × MR-raw | S1,S2 | FP, recall | MUST | **DONE** | 基线 FP = **0.00**（0/2）✅ 归因纯净 |
| R004 | M1 | **main anchor** | V-E3-vuln0-unlisted × MR-raw | S1–S5 | **FP_E3** | MUST | **DONE** | **`FP_E3` = 1.00（2/2）** ✅ |
| R005 | M1 | variant-parity | V-noE3 vs V-E3 | — | 端点/OpenAPI 一致性 | MUST | **DONE** | 由 `GET /openapi.json` 校验：仅差共享端点 |

→ 归档：`results/raw_matrix.jsonl`

## M2 · Main Method — ✅ 完成

| Run ID | Milestone | Purpose | System / Variant | Scenario | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R006 | M2 | main | Boundary-aware(v1) | S1–S5 | 恢复/保持/代价 | MUST | **DONE** | 恢复 1.00 / 保持 0.9545 / 代价 0.0455 |
| R007 | M2 | main | Boundary-aware(v2) | S1–S5 | 同上 | MUST | **DONE** | 恢复 1.00 / **保持 1.00 / 代价 0.00** ✅ |
| R014 | M2 | failure-analysis | V-E3-vuln1 | S3 vs S4/S5 | 辨析力丧失率 | MUST | **DONE** | 结构等价 1.00；判定等价 0.8333（unlisted 1.00 / listed 0.50） |

## M3 · Ablation — ✅ 完成

| Run ID | Milestone | Purpose | System / Variant | Scenario | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R008 | M3 | ablation-3 | MR-E1 | S3 | FP_E3 | MUST | **DONE** | 1.00（**无改善**） |
| R009 | M3 | ablation-3 | MR-E1E2 | S3 | FP_E3 | MUST | **DONE** | 1.00（**= MST-wi 能力上限，仍无改善**）✅ 构造性结论 |
| R010 | M3 | ablation-1 | 去 E3 探测（= R004） | S3 | FP_E3 | MUST | **DONE** | 1.00 |
| R011 | M3 | ablation-2 | Degrade-all | S2,S4,S5 | 检测力保持率 | MUST | **DONE** | **保持 0.00 / 代价 1.00** ✅ 反证成立 |
| R012 | M3 | ablation-4 | 第二实现重跑 | 同 R004 | FP_E3 | NICE | **DONE** | **54/54 一致（1.00）** ✅ |

## M4 · Specificity 口径复现 — ✅ 完成（近似）

| Run ID | Milestone | Purpose | System / Variant | Scenario | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| R013 | M4 | polish | V-noE3 / V-E3 | 全部 | specificity | NICE | **DONE** | 1.000 → **0.889**（unlisted）／1.000（listed）；分母为近似 |

## 待补（未完成项，如实记录）

| 项 | 阻塞原因 | 计划 |
|---|---|---|
| MST-wi 原生引擎复核 | 本机 Maven 缺失 | 装 Maven 后 `mvn clean compile package assembly:single`；用原生结果复核语义移植结论 |
| 跨模型独立复核（ARIS W1.5 Phase 2.5） | Codex 额度耗尽（提示 2026-10-08 恢复）；无其他厂商 API 通道 | 额度恢复后补做；在此之前 **不得启动 `/auto-review-loop`** |
| 76 条 MR 条件逐条核对（C1 完整性） | 需人工/脚本逐条比对 | 可作为论文 Camera-ready 前的补强 |
| `docker compose up` 验证 | Docker 守护进程未运行 | 具备 Docker 的环境上验证（同一份 app.py，参数一致） |

## 环境与限制记录

| 项 | 值 | 影响 |
|---|---|---|
| 执行环境 | Windows，Python 3.13（纯 stdlib 实现） | 无 GPU 需求 |
| MST-wi 原生引擎 | ❌ 未使用（Maven 缺失） | 语义移植 + catalog 行号溯源；须在 Limitations 明示 |
| Docker | ❌ 守护进程未运行 | compose 作为复现载体产出，非执行路径 |
| 跨模型审查 | ❌ 不可用 | **缺失已显式标注**（见 EXPERIMENT_RESULTS.md「必须报告的限制」第 5 条） |

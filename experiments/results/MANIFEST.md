# MANIFEST · 实验产物清单

**生成**：2026-09-17
**协议**：ARIS `shared-references/output-manifest.md`
**原则**：每个被引用的数字都必须能回溯到本清单中的文件

## 计划与契约（refine-logs/）

| 文件 | 作用 | 生成方式 |
|---|---|---|
| `EXPERIMENT_PLAN.md` | claim → evidence → run order 路线图 | ARIS W1 `experiment-plan` |
| `EXPERIMENT_TRACKER.md` | run 级执行与状态表 | 手写 + 实测回填 |
| `FINAL_PROPOSAL.md` | 方法规格（实现一致性依据） | 从 v5 提炼 |
| `RESEARCH_CONTRACT.md` | claims 与证据绑定 + 预注册判定规则 | 本流程新建 |
| `EXPERIMENT_RESULTS.md` | **结果报告（主要交付）** | ARIS W1.5 Phase 5 |

## 代码（experiments/）

| 文件 | 作用 |
|---|---|
| `target_api/app.py` | 受控目标系统（三开关：mode / vulnerable / share-visibility） |
| `target_api/Dockerfile` | 容器复现载体（**本机未验证**） |
| `mrs/mstwi_mrs.py` | **MST-wi 授权类 MR 语义移植**（catalog line 154 / 579 溯源） |
| `mrs/engine.py` | HTTP 客户端、场景构造、动作级构造式真值 |
| `mrs/alt_engine.py` | 第二实现（独立代码路径） |
| `boundary_aware.py` | E3 探测与三级裁决（v1 / v2 / degrade-all） |
| `run_matrix.py` | 主矩阵 runner |
| `compute_metrics.py` | 指标计算与出图 |
| `docker-compose.yml` | 六变体编排 |
| `README.md` | 复现说明与限制 |

## 原始数据与结果（experiments/results/）

| 文件 | 内容 | 大小 |
|---|---|---|
| `sanity_matrix.jsonl` | M0 门禁记录 | 144 条 |
| `raw_matrix.jsonl` | **主矩阵原始观测**（含两次观测全文、前置条件明细、真值、裁决、评级） | 324 条 |
| `alt_matrix.jsonl` | 第二实现记录 | 30 条 |
| `run_meta.json` | 运行元数据（配置、MR 溯源、环境限制、version pin） | — |
| `run_meta_sanity.json` | sanity 元数据 | — |
| `summary.json` | 机读汇总（Block 2–5 + M4 + M5） | — |
| `SUMMARY.md` | 人读汇总表 | — |
| `figures/fig1_trigger_matrix.png` | 触发率矩阵图 | — |
| `figures/fig2_verdict_benefit_cost.png` | 裁决收益-代价图 | — |

## 论文表格映射

| 论文位置 | 数据源 | 关键值 |
|---|---|---|
| Table 3（主触发矩阵） | `SUMMARY.md` Block 2 | `FP_E3` = 1.00；基线 FP = 0.00 |
| Table 4（例外谓词消融） | `SUMMARY.md` Block 3 | 1.00 → 1.00 → 1.00（无效） |
| Table 5（收益-代价） | `SUMMARY.md` Block 4 | v2：恢复 1.00 / 代价 0.00 |
| Table 6（辨析力） | `SUMMARY.md` Block 5 | 结构等价 1.00；判定等价 0.8333 |
| 附表（口径复现） | `SUMMARY.md` M4 | 1.000 → 0.889 |
| 附录（实现独立性） | `SUMMARY.md` M5 | 54/54 = 1.00 |
| §7 Discussion（两面性） | `SUMMARY.md` 漏报附表 + Block 5 | listed → FN；unlisted → FP |

## 未产出 / 已知缺口

- MST-wi 原生引擎运行日志（Maven 缺失）
- 跨模型独立复核报告（Codex 额度耗尽）
- 76 条 MR 条件的逐条核对表（未完成）
- 容器运行验证日志（Docker 守护进程未运行）

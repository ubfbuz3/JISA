# 实验代码与复现说明

**对应方案**：`02_Idea与架构/研究方案_v5.md`（例外表达力边界与 BOLA 判定的可判定性）
**实验计划**：`refine-logs/EXPERIMENT_PLAN.md`
**研究契约**：`refine-logs/RESEARCH_CONTRACT.md`
**结果**：`experiments/results/SUMMARY.md`、`results/summary.json`、`results/raw_matrix.jsonl`

---

## 1. 目录结构

```
experiments/
├── target_api/
│   ├── app.py                    # 受控目标系统（零第三方依赖）
│   └── Dockerfile                # 容器复现载体（主矩阵实测走进程内实例，未逐一验证镜像）
├── mrs/
│   ├── mstwi_mrs.py              # ★ MST-wi 授权类 MR 的忠实语义移植（含 catalog 行号溯源）
│   ├── engine.py                 # HTTP 客户端 / 场景构造 / 动作级构造式真值
│   └── alt_engine.py             # 第二实现（独立代码路径，排除实现偶然性）
├── boundary_aware.py             # E3 探测与三级裁决（v1 / v2 / degrade-all）
├── run_matrix.py                 # 主矩阵 runner
├── compute_metrics.py            # 指标计算与出图
├── docker-compose.yml            # 六变体编排（复现载体）
└── results/                      # 全部观测与汇总（每个数字可回溯到 JSONL 记录）
```

## 2. 一键复现

```bash
# 零第三方依赖；仅需 Python >= 3.10
python run_matrix.py            # 全矩阵（约 3 分钟，324 条记录）
python mrs/alt_engine.py        # 第二实现（约 30 秒）
python compute_metrics.py       # 汇总 + 出图
```

输出：
- `results/raw_matrix.jsonl` —— 每条记录含**两次观测全文 + 前后置条件明细 + 真值 + 三项裁决 + 四项评级**
- `results/summary.json` —— 机读汇总
- `results/SUMMARY.md` —— 人读汇总表
- `results/figures/` —— 图 1（触发矩阵）、图 2（收益-代价）

## 3. 被测系统设计（三个正交开关）

| 开关 | 取值 | 含义 |
|---|---|---|
| `--mode` | `noe3` / `e3` | 是否存在对象级共享能力（V-noE3 / V-E3） |
| `--vulnerable` | `0` / `1` | 是否注入 BOLA 缺陷（对象级端点只查登录、不查归属） |
| `--share-visibility` | `listed` / `unlisted` | 共享是否对列举端点（GUI 可达性代理）可见 |

两个系统变体的**端点与 OpenAPI 完全一致**，唯一差异是 V-E3 多出
`POST /doc/{id}/share` 与 `GET /doc/{id}/shares`。这一致性由
`GET /openapi.json` 可直接校验。

## 4. 关键设计说明

### 4.1 为什么必须自建系统
- crAPI 无对象级共享功能（官方 challenges 仅"访问他人车辆/报告"）
- VAmPI 无共享语义
- 且 E3 探测的**构造式真值**要求"我们主动创建共享" → 必须自建

### 4.2 为什么 E3 探测不循环
E3 探测读取的是 `TargetClient.share_log` —— **测试框架自己调用共享 API 时写下的记录**，
不是从实现制品推断的政策。这是构造式真值（constructive ground truth）。

### 4.3 真值定义（先于实验确定）
```
should_allow = 授权模型判定（与是否注入缺陷无关的正确逻辑）
app_allowed  = 实测观测（status == 200）
BOLA ⟺ (¬should_allow) ∧ app_allowed        # 应用允许了本不该允许的访问
```

### 4.4 `unlisted` 为什么是 E3 盲点的落点
当共享**只对对象级端点生效**而**不出现在列举/GUI** 时：
- 用户**合法**有权访问该对象
- 但 MR 的 `cannotReachThroughGUI` / `userCanRetrieveContent` 判定为"不可达"
- → MR 触发并报告缺陷 → **假阳**

现实中对应：分享链接、API scope 授权、委派访问、团队空间权限等
**UI 不展示的对象级授权**。

## 5. 限制（必须随结果一起报告）

1. **MR 为语义移植，非 MST-wi 原生引擎**。原生引擎需 Maven + chromedriver + Selenium +
   被测系统 OVA 虚拟机，本机 Maven 缺失。移植依据是 catalog 行号与逐行源码片段，
   第三方可逐行比对（见 `mrs/mstwi_mrs.py` 表头）。
2. **被测系统为自建受控系统**，非真实开源应用。定位是"受控实验以测可控性"。
3. **GUI 可达性谓词使用代理语义**（列举端点），因受控系统无 GUI。
   已双向报告 `gui_blind` / `gui_aware` 两个变体。
4. **M4 的 specificity 为口径近似复现**，分母非原引擎的精确输入计数。
5. **缺少异厂商模型的独立复核**（Codex 账号额度耗尽至 2026-10-08）。
   `alt_engine.py` 提供的是**同源独立实现**，只能排除实现偶然性，不能排除共同盲点。

## 6. R1.7 竞争基线（`run_baseline.py`，2026-10-19 新增）

审稿人要求"按候选和预算匹配的公平基线"。本实验实现三种**常规差分**规则，与本文方法
（MR-002 + v3 裁决）在**同一批 SUT 实例、同一对探测请求**上对比：

| 标签 | 判定规则 | 授权知识 |
|---|---|---|
| B1 `status_only` | 低权账户请求返回非错误状态即告警 | 无 |
| B2 `diff_equal` | 拥有者成功且低权账户拿到逐字节相同响应才告警 | 无 |
| B3 `diff_inband` | B2 + 用框架自己的 share_log 压制（= 已知测试期全部自建授权的理想差分） | 仅框架可见的授权 |
| ours `mr_v3` | MR-002 触发后查询 SUT 授权自省面；不可读则弃权 | 特权自省面 |

公平性要点：
- **预算匹配**：四方法共用同一对请求（owner 一次、actor 一次）；ours 额外发 1 次自省查询，
  成本在 `baseline_compare.json` 的 `budget` 字段单列。
- **B3 是上界式对照**：真实工具连框架账本都没有，B3 比它们更强，不是稻草人。
- **真值同源**：仍用 `engine.ground_truth` 的动作级构造式真值；真阳性 = E=deny ∧ Y=allow，
  假确证 = E=allow ∧ 仍宣称 `violation-proven`。
- **域**：只取具备对象级共享能力的 6 个配置 × S1–S7 = 42 格（无共享配置上 S3–S7 构造不成立）。

结果（42 格：15 真违规 / 12 合法授权访问 / 15 拒绝）：

| 方法 | 宣称 | 真阳性 | 假确证 | 弃权 | 覆盖率 |
|---|---|---|---|---|---|
| B1 | 27 | 15 | 12 | 0 | 100.00% |
| B2 | 27 | 15 | 12 | 0 | 100.00% |
| B3 | 21 | 15 | 6 | 0 | 100.00% |
| ours | 10 | 10 | 0 | 17 | 59.52% |

B3 压掉 6 个 in-band 假确证后剩下的 6 个全在 S6（带外种入授权）。
ours 的 17 个弃权 = 12 个合法授权 + 两个 no-introspection 配置上的 5 个真违规。
**这不是检测增益**：基线检出全部 15 个，ours 只在自省面可读时确证 10 个。

复现：
```bash
cd experiments
python run_baseline.py        # 约 25 秒，42 格，需 Python >= 3.10
python ../04_绘图与分析/analysis/ingest_baseline.py   # 出 baseline_numbers/table.tex
```
Docker 守护进程当前可用（29.6.2），但本实验走的是进程内 `make_server`，
与主矩阵同一条执行路径，不依赖容器。

## 7. 未在本机执行的部分

| 项 | 原因 | 补偿 |
|---|---|---|
| `docker compose up` | 主矩阵改走进程内实例（与容器同一条执行路径），未逐一验证容器镜像 | 使用同一份 `app.py` 的进程内实例执行；两者参数完全一致 |
| MST-wi 原生引擎构建 | Maven 未安装 | 语义移植 + 逐行溯源；保留原生构建步骤作为可选路径 |
| 跨模型代码审查（ARIS W1.5 Phase 2.5） | Codex 额度耗尽 | 显式标注；用第二实现部分补偿 |

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
│   └── Dockerfile                # 容器复现载体（本机未验证，Docker 守护进程未运行）
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

## 6. 未在本机执行的部分

| 项 | 原因 | 补偿 |
|---|---|---|
| `docker compose up` | Docker 守护进程未运行 | 使用同一份 `app.py` 的进程内实例执行；两者参数完全一致 |
| MST-wi 原生引擎构建 | Maven 未安装 | 语义移植 + 逐行溯源；保留原生构建步骤作为可选路径 |
| 跨模型代码审查（ARIS W1.5 Phase 2.5） | Codex 额度耗尽 | 显式标注；用第二实现部分补偿 |

# A 包 · 真值链改造（E/Y 分离）

日期 2026-10-18。对应审稿意见：R1.2（假证明定义）、R1.5/R2.3（命题 2 前提）、R1.8（跨渠道真值）、R2.6（构造真值/率）。

## 1. 改的是什么

原实现把**观测效果**直接当成**应有授权**：

```python
granted       = (http_status == 200)
truth_map[k]  = granted
authorized    = granted
false_proof   = alarm and authorized
```

`status == 200` 是 Y（实际访问观测），不是 E（应有授权）。对真实 BOLA 缺陷，
E=deny 而 Y=200 恰好就是漏洞本身；用 Y 填 E 会把这个真阳性判成"已授权"，
再加一层 `alarm` 就翻成"假证明"。在 Gitea/Gogs/GitLab 三个**正确系统**上
E 与 Y 恰好重合，所以缺陷一直没暴露。

## 2. 新口径

| 符号 | 含义 | 来源 |
|---|---|---|
| **E** | 预期有效授权 `allow/deny/unknown` | 授权台账（phaseA 建局事务 + phaseC 带外变更）+ 继承规则；**绝不读被测请求的返回值** |
| **Y** | 实际观测效果 | 被测请求的状态码 / 响应体 / 写操作后的实际状态变化 |
| **O** | oracle 回答 | 自省面读取，另记视点与独立性 |
| **A** | 原始报警 | MR 是否触发 |
| **H** | 升级为 violation-proven | 本文裁决器的 promotion，**H ⇒ A** 强制断言 |

判定：

- **假证明** = H 且 **E=allow**
- **真阳性** = H 且 **E=deny 且 Y=allow**（越权访问真的发生了）
- H 且 E=deny 且 Y=deny → **`alarm_on_denied_not_exploitable`**：只是"策略查询命中"，
  不是漏洞证据。这一类必须单列，否则纯观测型对照（如 `direct_only`）的"检出"会虚高。

## 3. 实现

新增 `experiments/real_system/entitlement.py`：

- `PolicyModel`：只建模实验室实际用到的机制（owner / org owner / site admin /
  public / collaborator / org-team 继承），未知对象返回 `unknown` 而不是猜 deny；
- 每次授权事务都进 `ledger`，`Decision.basis` 保留推导链，可回溯；
- `Decision.alternatives` 给出全部生效渠道，支撑 R1.8 要求的多来源标注；
- `classify(E, Y, A, H)` 实现上表，并对 `H ⇒ A` 做断言。

新增 `experiments/real_system/manifests.py`：三个系统的台账构造器
（`gitea_model` / `gogs_model` / `gitlab_model`），从各自 phaseA/phaseC 记录重建。

三个 runner 已改为同时落盘
`expected_entitlement / expected_channel / expected_basis / observed_effect /
observed_status / verdicts / true_positives`；`authorized` 仅作 Y 的兼容别名保留。

## 4. 离线验证（未开 Docker）

`validate_entitlement.py` 用历史结果回放：

| 系统 | 格数 | E == Y |
|---|---:|---:|
| Gitea 1.22.6 | 48 组 × 2 读法 | **48/48** |
| Gogs 0.14.3 | 48 × 2 | **48/48** |
| GitLab | 48 × 2 | **48/48** |

三个都是正确系统，E 与 Y 本就应当重合，48/48 说明台账推导能复现系统行为。
**新旧假证明计数完全一致**（Gitea `mr_bookkeeping` 10、Gogs 11、GitLab 10 等），
即：这次改造**没有改变任何已报数字**，改变的是判定链在**漏洞系统**上的有效性。

同时暴露一处此前的隐性虚高：`direct_only` 在三个系统分别有
**23 / 27 / 22** 次属于"策略说不允许、但访问也确实被拒绝"，按新口径不计真阳性。
正文若曾把它与检测能力并列，必须改。

## 4b. 真实系统实跑（2026-10-18，Docker 已启动）

容器/二进制与旧运行完全相同（Gitea 1.22.6 单文件、Gogs 0.14.3 单文件、
GitLab 17.11.7-ce.0 容器），但**一律用全新实例目录/卷**，旧库与旧原始结果不动：

| 系统 | 实例 | 拓扑/变更 | 耗时 | E == Y（配对） | 假证明（mr_bookkeeping） |
|---|---|---|---:|---:|---:|
| Gitea | `gitea_lab_r2`（端口 3411） | 20 步 / 6 变更（1 个 405，与旧运行同） | 35.2 s | **48/48** | **10**（旧 10） |
| Gogs | `gogs_lab/inst_r2`（端口 3412） | 20 步 / 5 变更，0 失败 | 17.8 s | **48/48** | **11**（旧 11） |
| GitLab | 新建 `gitlab_lab_vol`（端口 3320） | 11 步 / 5 变更，0 失败 | 210.1 s（另启动 116 s） | **48/48** | **10**（旧 10） |

逐方法假证明计数与旧运行**逐项相同**（Gitea 仅 `mr_bookkeeping`=10；Gogs
`direct_only`=34、`direct_observe`=34、`direct_observe_self`=16、`mr_bookkeeping`=16、
`v3`=13；GitLab `direct_only`=36、`direct_observe`=36、`direct_observe_self`=36、
`mr_bookkeeping`=10、`v3`=5、`v3_self`=5）。`analyze_real.py` 重算的
`real_system_summary.json` 与旧汇总**零差异**。

同时修复：`run_gitlab.py:559` 的重命名漏改（裸 `granted` → `observed_allow`），
该 bug 在旧代码里被 `granted` 的全局残留掩盖，只有实跑才暴露。

旧原始结果已归档在 `experiments/real_system/results/archive_2026-09-18/`。

## 5. 这条验证证明不了什么

E 模型是**我们对规则的建模**。如果模型与系统共享同一个错误假设，二者会"一致地错"。
所以：

- 对三个正确系统，48/48 只证明**台账 ↔ 行为**自洽，不证明外部语义正确；
- 对**漏洞系统**（后续 vulnerable/fixed 配对），E 必须来自**意图策略**
  （fixed 版本的实测行为 + 规格/补丁说明），**不能**由 buggy 版本的响应反推，
  也不能只由本模型的规则推导。

## 6. 尚未完成

1. **写路径**：现有三系统只测读。E(Y) 对写操作要求记录**实际状态变化**
   （owner 复核内容），不能只看状态码 —— 这是 vulnerable/fixed 配对的必要条件。
2. **v1 标注**：`boundary_aware.py` 的 v1 实为"存在任意共享即降级"的存在性过滤器，
   不是 raw。需保留真正 raw 行，并给存在性/权限两个过滤器准确命名，重生相关表。
3. ~~**弃权拆分**~~ **已核算**：v3 共 **228** 次 indeterminate =
   **156** 次 oracle 不可读（`e3` 102 + `noe3` 54）+ **72** 次合法覆盖共享（全在 `e3`）。
   逐记录 ID 见 `v3_abstention_breakdown.json`。**正文尚未改写**——须在重写阶段
   把"只计不可读导致的弃权"改为全量 228 并给出两因分解。
4. **native 分离**：`getFailures()` 证明的是原生报警，不等于工具宣称
   `violation-proven`；需拆成 native alarm / promotion policy / 独立真值确认三段。
5. ~~**实跑**~~ **已完成**，见 §4b。


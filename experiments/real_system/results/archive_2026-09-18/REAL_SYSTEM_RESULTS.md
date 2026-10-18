# 实验 B · 真实系统对照结果（Gitea 1.22.6）

> 诚实边界：Gitea 是正确系统，不含对象级授权漏洞 ⇒ 只测假确证侧与发生率，不测检出率；不声称实验证明 MST-wi 失效（未跑其原生引擎）；GUI 模型的 snapshot / live 两种读法都报，失效只在前者出现。

阶段：A 基线拓扑 → B 采集爬取 → C 带外授权变更 → D 变更后爬取 → E MR 执行与四方法裁决 → F M1/M2/M3 → G M6
实验台：`C:\Users\Administrator\WorkBuddy\gitea_lab\inst5`；耗时 31.1s。
拓扑步骤 20，失败 0。
带外授权变更 6 项，失败 1。
- **失败** `admin_add_org_member:acme<-frank` status=405 

## M1 · 授权授予机制空间普查（实例无关）

判据：端点计入当且仅当：在不修改被测系统代码的前提下，能使某 (主体, 对象) 的访问权限从否变为是；方向由该端点实际可用的 HTTP 方法推出（仅 DELETE ⇒ 撤销，不算授予）。

Gitea swagger 路径总数 **253**；其中可作为「授权授予机制」的端点 **15** 个（另有 2 个仅能撤销、不算授予），其中**不需站点管理员即可执行**的 **8** 个。

| 端点 | 方法 | 方向 | 需要站点管理员 | 类别 |
|---|---|---|---|---|
| `/repos/{owner}/{repo}/collaborators/{collaborator}` | DELETE,PUT | 授予 | 否 | 仓库级：协作者（PUT 授予 / DELETE 撤销） |
| `/teams/{id}/repos/{org}/{repo}` | DELETE,PUT | 授予 | 否 | 组织级：仓库挂到团队 |
| `/teams/{id}/members/{username}` | DELETE,PUT | 授予 | 否 | 组织级：用户加入团队 |
| `/orgs/{org}/members/{username}` | DELETE | 撤销 | 否 | 组织级：用户移出组织（**仅 DELETE**） |
| `/orgs/{org}/teams` | POST | 授予 | 否 | 组织级：新建团队（授权单位） |
| `/orgs` | POST | 授予 | 否 | 组织级：新建组织 |
| `/repos/{owner}/{repo}/transfer` | POST | 授予 | 否 | 仓库级：转移所有权 |
| `/repos/{owner}/{repo}` | DELETE,PATCH | 授予 | 否 | 仓库级：切换可见性（私有→公开即向所有人授予） |
| `/repos/{owner}/{repo}/keys` | POST | 授予 | 否 | 部署密钥：授予仓库读写 |
| `/admin/users` | POST | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}` | DELETE,PATCH | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}/badges` | DELETE,POST | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}/keys` | POST | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}/keys/{id}` | DELETE | 撤销 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}/orgs` | POST | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}/rename` | POST | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |
| `/admin/users/{username}/repos` | POST | 授予 | 是 | 站点级：建/改用户（含受限标志、加入组织） |

按层面（仅授予）：站点级 7；组织级 4；仓库级 3；部署密钥 1

## M2 · 自省面视点可读性矩阵

对象 `alice/r1`，被查询主体 `bob`：

| 视点 | 读取对象 | 列举协作者 | 查询权限 |
|---|---|---|---|
| anonymous | `404` | `404` | `404` |
| root | `200` | `200` | `200` → `read` |
| alice | `200` | `200` | `200` → `read` |
| bob | `200` | `200` | `403` |
| carol | `404` | `404` | `404` |
| dave | `404` | `404` | `404` |
| eve | `404` | `404` | `404` |
| frank | `404` | `404` | `404` |

对象 `acme/t1`，被查询主体 `bob`：

| 视点 | 读取对象 | 列举协作者 | 查询权限 |
|---|---|---|---|
| anonymous | `404` | `404` | `404` |
| root | `200` | `200` | `200` → `read` |
| alice | `404` | `404` | `404` |
| bob | `200` | `200` | `403` |
| carol | `404` | `404` | `404` |
| dave | `200` | `200` | `200` → `read` |
| eve | `404` | `404` | `404` |
| frank | `200` | `200` | `403` |


## M3 · 自省面保真度（以拥有者凭证读到的所报权限 vs 有效访问）

| 单元格 | 主体 | 有效访问 | 自省面状态 | 所报权限 | 一致 |
|---|---|---|---|---|---|
| alice/r1 | bob | 是 | `200` | read | ✓ |
| alice/r1 | carol | 否 | `200` | none | ✓ |
| alice/r1 | dave | 否 | `200` | none | ✓ |
| alice/r1 | eve | 否 | `200` | none | ✓ |
| alice/r1 | frank | 否 | `200` | none | ✓ |
| alice/r1 | root | 是 | `200` | owner | ✓ |
| alice/r2 | bob | 否 | `200` | none | ✓ |
| alice/r2 | carol | 是 | `200` | read | ✓ |
| alice/r2 | dave | 否 | `200` | none | ✓ |
| alice/r2 | eve | 否 | `200` | none | ✓ |
| alice/r2 | frank | 否 | `200` | none | ✓ |
| alice/r2 | root | 是 | `200` | owner | ✓ |
| alice/r3 | bob | 否 | `200` | none | ✓ |
| alice/r3 | carol | 否 | `200` | none | ✓ |
| alice/r3 | dave | 否 | `200` | none | ✓ |
| alice/r3 | eve | 是 | `200` | read | ✓ |
| alice/r3 | frank | 否 | `200` | none | ✓ |
| alice/r3 | root | 是 | `200` | owner | ✓ |
| alice/r4 | bob | 是 | `200` | read | ✓ |
| alice/r4 | carol | 是 | `200` | read | ✓ |
| alice/r4 | dave | 是 | `200` | read | ✓ |
| alice/r4 | eve | 是 | `200` | read | ✓ |
| alice/r4 | frank | 是 | `200` | read | ✓ |
| alice/r4 | root | 是 | `200` | owner | ✓ |
| alice/pub1 | bob | 是 | `200` | read | ✓ |
| alice/pub1 | carol | 是 | `200` | read | ✓ |
| alice/pub1 | dave | 是 | `200` | read | ✓ |
| alice/pub1 | eve | 是 | `200` | read | ✓ |
| alice/pub1 | frank | 是 | `200` | read | ✓ |
| alice/pub1 | root | 是 | `200` | owner | ✓ |
| acme/t1 | alice | 否 | `200` | none | ✓ |
| acme/t1 | bob | 是 | `200` | read | ✓ |
| acme/t1 | carol | 否 | `200` | none | ✓ |
| acme/t1 | eve | 否 | `200` | none | ✓ |
| acme/t1 | frank | 是 | `200` | read | ✓ |
| acme/t1 | root | 是 | `200` | owner | ✓ |
| acme/t2 | alice | 否 | `200` | none | ✓ |
| acme/t2 | bob | 是 | `200` | read | ✓ |
| acme/t2 | carol | 否 | `200` | none | ✓ |
| acme/t2 | eve | 否 | `200` | none | ✓ |
| acme/t2 | frank | 是 | `200` | read | ✓ |
| acme/t2 | root | 是 | `200` | owner | ✓ |
| dave/r5 | alice | 否 | `200` | none | ✓ |
| dave/r5 | bob | 否 | `200` | none | ✓ |
| dave/r5 | carol | 否 | `200` | none | ✓ |
| dave/r5 | eve | 否 | `200` | none | ✓ |
| dave/r5 | frank | 否 | `200` | none | ✓ |
| dave/r5 | root | 是 | `200` | owner | ✓ |

（已排除「执行者自身」单元格：它们不是换凭证测试的对象，不参与一致性判定。）

→ 不一致 **0 / 48**（自省面在该拓扑上保真）

其中「自省面状态」的分布：`200` × 48

## M3b · 自省面的两种视点：拥有者/管理员 vs 被测主体自身

| 视点 | 可读单元格数 | 读不到的单元格数 | 读不到时的状态码分布 |
|---|---|---|---|
| 拥有者/管理员（v3 的规定视点） | 48 / 48 | 0 | — |
| 被测主体自身（黑箱测试者的自然视点） | 8 / 48 | 40 | `404` × 23；`403` × 17 |

→ **自省面在「被测主体自身」视点下**：部分可读，需逐单元格讨论。

按主体拆开看（关键：那 8 个「可读」的单元格是谁的）：

| 主体 | 单元格数 | 自身视点可读 | 不可读时的状态码 |
|---|---|---|---|
| root | 8 | 8 | — |
| bob | 8 | 0 | `403` × 5；`404` × 3 |
| carol | 8 | 0 | `404` × 5；`403` × 3 |
| dave | 5 | 0 | `404` × 3；`403` × 2 |
| eve | 8 | 0 | `404` × 5；`403` × 3 |
| frank | 8 | 0 | `404` × 4；`403` × 4 |
| alice | 3 | 0 | `404` × 3 |

⇒ 除**站点管理员**外，任何主体在自己的视点下都读不到授权自省面。

## M4 · 采集期爬取记录 vs 变更后有效访问

**snapshot 读法**：`cannotReachThroughGUI` 为真**但主体确实可访问**的单元格 **10** 个

| 主体 | 对象 |
|---|---|
| bob | acme/t2 |
| bob | alice/r4 |
| carol | alice/r2 |
| carol | alice/r4 |
| dave | alice/r4 |
| eve | alice/r3 |
| eve | alice/r4 |
| frank | acme/t1 |
| frank | acme/t2 |
| frank | alice/r4 |

**live 读法**：`cannotReachThroughGUI` 为真**但主体确实可访问**的单元格 **0** 个


## M5 · 方法对照（Gitea 正确 ⇒ 真 violation 恒为 0，任何告警都是误报）

| 方法 | 说明 |
|---|---|
| `mr_bookkeeping` | MR 触发 ∧ 框架自己的共享日志无记录（≈MST-wi 的位置：谓词相对采集记录） |
| `v3` | MR 触发 ∧ **以拥有者/管理员凭证**读自省面 ∧ 自省面明确报告 none |
| `v3_self` | MR 触发 ∧ **以被测主体自己凭证**读自省面 ∧ 报告 none（黑箱测试者的自然视点） |
| `direct_only` | 只看自省面（不消费访问结果） |
| `direct_observe` | 普通请求可访问 ∧ **拥有者视点**自省面报告 none |
| `direct_observe_self` | 普通请求可访问 ∧ **主体自身视点**自省面报告 none |

### snapshot 读法（单元格 48，其中主体真实被授权 25）

| 方法 | 告警总数 | **假确证**（落在被授权单元格） | 落在被拒绝单元格 | 假确证残差 |
|---|---|---|---|---|
| `mr_bookkeeping` | 10 | **10** | 0 | 0.4000 |
| `v3` | 0 | **0** | 0 | 0.0000 |
| `v3_self` | 0 | **0** | 0 | 0.0000 |
| `direct_only` | 23 | **0** | 23 | 0.0000 |
| `direct_observe` | 0 | **0** | 0 | 0.0000 |
| `direct_observe_self` | 0 | **0** | 0 | 0.0000 |

MR 触发（家族签名成立：测试者 GUI 到不了 ∧ 非管理员 ∧ 输出与执行者相同）**10 / 48**：

| 对象 | 主体 | 触发但真实被授权 | 框架日志有无记录 | 自省面所报 |
|---|---|---|---|---|
| acme/t1 | frank | 是 | **无** | read |
| acme/t2 | bob | 是 | **无** | read |
| acme/t2 | frank | 是 | **无** | read |
| alice/r2 | carol | 是 | **无** | read |
| alice/r3 | eve | 是 | **无** | read |
| alice/r4 | bob | 是 | **无** | read |
| alice/r4 | carol | 是 | **无** | read |
| alice/r4 | dave | 是 | **无** | read |
| alice/r4 | eve | 是 | **无** | read |
| alice/r4 | frank | 是 | **无** | read |

### live 读法（单元格 48，其中主体真实被授权 25）

| 方法 | 告警总数 | **假确证**（落在被授权单元格） | 落在被拒绝单元格 | 假确证残差 |
|---|---|---|---|---|
| `mr_bookkeeping` | 0 | **0** | 0 | 0.0000 |
| `v3` | 0 | **0** | 0 | 0.0000 |
| `v3_self` | 0 | **0** | 0 | 0.0000 |
| `direct_only` | 23 | **0** | 23 | 0.0000 |
| `direct_observe` | 0 | **0** | 0 | 0.0000 |
| `direct_observe_self` | 0 | **0** | 0 | 0.0000 |

MR 触发（家族签名成立：测试者 GUI 到不了 ∧ 非管理员 ∧ 输出与执行者相同）**0 / 48**：


## M6 · 授权通道定性与带外占比

有效访问单元格 **25**。按通道：

| 通道 | 数量 | 被「框架自己的动作日志」记录 |
|---|---|---|
| out_of_band | 11 | ❌ |
| implicit_site_admin | 8 | ❌ |
| implicit_public | 5 | ❌ |
| in_band_share | 1 | ✅ |

→ **带外（不被框架动作日志记录）= 24 / 25 = 96.0%**

⚠️ 该比例依赖本实验构造的拓扑（是设计参数，不是野外发生率估计）；实例无关的部分是 M1 的机制空间普查。

---

## ★ 结论（按读法分层，不得只报其一）

- **snapshot 读法**：MR 家族在采集**之后**新增的授权上签名成立，`mr_bookkeeping` 产生 **10** 个假确证（占 25 个被授权单元格的 40.0%）。
- **live 读法**：同一批单元格上 `mr_bookkeeping` 假确证 **0** ⇒ 失效**仅**在 GUI 模型取快照时出现（这是必须与结论一起声明的条件）。
- `v3`（拥有者/管理员视点读面）两种读法下假确证均 **0**，但它需要**特权凭证**才能读面。
- `v3_self`（被测主体自身视点读面）假确证 **0**，且因自省面在该视点下不可读而**全部弃权** ⇒ 检出力 0。
- `direct_only` 的 **23** 个告警全部落在**被正确拒绝**的单元格上，即「忽略访问结果」的产物，与第七轮审判方的定性一致。

⇒ **真实系统上的完整图景**：不存在一个视点同时满足（a）能读到授权自省面 与（b）是合法的黑箱测试者——能读面的只有已经知道答案的拥有者/管理员；而真正处于黑箱位置的被测主体读不到面，只能弃权。

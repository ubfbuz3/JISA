# MST-wi 先例核查与机制重定位

> 核查日期：2026-09-17
> 核查动因：v4 方案把「跨通道一致性」当作核心新机制。苏格拉底式追问已判定 Novel=2（最低项），本次核查用可溯源证据确认**低到什么程度**，并据此重定位。
> 核查方式：① 先例检索（WebSearch + Undermind deep search）② 实测制品可得性 ③ 下载并解析其 MR 目录原文
> 结论：**v4 的三条判据中，判据 B 已被现有工作覆盖；但核查同时发现了一个更窄、可证明、可实证的真实缺口。**

---

## 1. 核查发现：一个此前被完全遗漏的强竞品

**MST-wi**（Metamorphic Security Testing for Web-interactions）
- 作者：Nazanin Bayati Chaleshtari, Fabrizio Pastore, Arda Goknil, Lionel C. Briand
- 出处：**IEEE TSE, Vol.49 No.6, pp.3430–3471, 2023**（DOI `10.1109/TSE.2023.3256322`）
- 前身：ICST'20 会议论文 + ICSE'20 工具演示
- **本篇论文的前序工作里已有 SST / SMRL 一系；本文扩展到 76 条 MR 目录**

### 1.1 它的成绩（原文）

| 项 | 数值 |
|---|---|
| MR 目录规模 | **76 条**系统无关（system-agnostic）MR |
| OWASP 覆盖 | 自动化了**未被现有方法覆盖的 41 项中的 16 项（39%）** |
| CWE 覆盖 | 可测 **101–102 种 CWE 漏洞类型（占安全设计原则类漏洞的 45%）** |
| 实验对象 | Jenkins v2.121、Joomla v3.8.7（真实系统） |
| 敏感度 | **85%**（crawler 单独可达 >60%） |
| 特异性 | **99.81%**（false alarm ≤ **0.19%**） |
| 新发现 | Jenkins 一个新漏洞（**CVE-2018-17857**） |

### 1.2 制品完全公开可得（已实测）

| 制品 | 位置 | 实测 |
|---|---|---|
| 工具源码 | `github.com/MetamorphicSecurityTesting/MST` | ✅ `git ls-remote` OK，master 最新 commit 2025-10-31 |
| 构建 | Maven（`pom.xml`）→ `MST-1.0.0-jar-with-dependencies.jar` | ✅ |
| 复现包 | Zenodo DOI `10.5281/zenodo.7702754` | ✅ API 可达，12 个文件 |
| └ `MST-wi.zip` | Eclipse 工程 + MR 目录 + 生成的 Java 类 | 70.9 MB |
| └ `Catalog of MRs.pdf` | **129 页完整 MR 目录源码** | 0.9 MB（已下载解析） |
| └ `PatternsOfMRs.xlsx` | MR 模式统计表 | 16 KB（已下载解析） |
| └ Jenkins / Joomla VM | `latestJenkins2_121_2.ova` / `joomla.ova` | 5.5 GB / 4.6 GB |

> **已经下载到** `01_文献调研/mstwi_artifact/`：`Catalog_of_MRs.pdf`、`PatternsOfMRs.xlsx`、`catalog_text.txt`（提取文本，227,664 字符）

---

## 2. 逐条核对：v4 的三条判据有几条是新的

### 2.1 判据 B（跨通道一致性）→ **已被覆盖** ❌

v4 判据 B 的设计：若 `i` 能直接访问 `o_A`，但 `o_A` 不在 `i` 的列表枚举结果中 → 矛盾 → 缺陷。

MST-wi 的 **`MR CWE_266_267_268_269_285_522_529_862_863_OTG_AUTHZ_002`** 原文：

```
for ( Action action : Input(1).actions() ) {
  IMPLIES(
    !isSupervisorOf(User(), action.user) &&
    cannotReachThroughGUI( User(), action.url ) &&
    CREATE( Input(2), changeCredentials(Input(1), User()) )
    ,
    OR(
      isError(Output(Input(1),action.position)),
      NOT( Output(Input(1),action.position).equals(Output(Input(2),action.position)) )
    ));
}
```

`cannotReachThroughGUI(u, url)` 就是「`u` 在 GUI 中不可达该 URL」——**与 v4 判据 B 的「`o_A` 不在 `i` 的枚举结果中」是同一件事**。
其论文对该 MR 的自然语言描述更直白：

> "A URL that cannot be reached by a user while navigating the user interface should not be available to that same user even when she directly requests the URL to the server."

**判定：判据 B 与 MST-wi 的授权类 MR 同构，不构成新机制。**

### 2.2 §5.1「合法跨账户负例」（管理员/上级）→ **已被覆盖** ❌

v4 §5.1 设计了"表面行为完全匹配的合法/非法配对端点"，用以检验方法能否区分合法共享。

MST-wi 处理方式：**在 MR 的 precondition 里排除合法例外**。
- `PatternsOfMRs.xlsx` 统计原文：**"33 out of 76 MRs hold a precondition on the user e.g. isAdmin()"**
- 目录中实际出现的例外谓词：`!isAdmin(action.user)`、`!isSupervisorOf(User(), action.user)`
- 论文原文（OTG_AUTHZ_002 该 MR 注释）："Checks whether the user in User() is not a supervisor of the user performing the current [action]"

**判定：管理员 / 上级（supervisor）这类**主体属性**与**主体间关系**例外，MST-wi 已系统化处理。**

### 2.3 判据 A（配对不变性）、判据 C（状态转移不可逆）→ **部分重叠，但已无独立新意**

- **判据 A**：其"同一输入序列换凭证执行"（`changeCredentials(Input(1), User())` + `CREATE(Input(2), Input(1))`）就是配对对照的做法。MST-wi 的对照是**用户级**而非**端点级同构对**，严格说不完全相同，但**"用对照执行差异推断缺陷"这个机制已被占据**，差异只是构造方式，不足以支撑一个 claim。
- **判据 C**：`parameterValuesUsedByOtherUsers` + `userCanRetrieveContent` 已覆盖"跨账户取到内容"的判定；写路径的副作用检查在变形测试框架中属于同类。

**综合判定：v4 §2 的三条判据，没有一条能作为独立的新机制主张。** 追问给出的 **Novel=2 是准确的**，本次核查提供了它的具体证据。

---

## 3. 核查同时发现的**真实缺口**（重定位的依据）

逐词核查 MST-wi 的 DSL 内置谓词全集（从 129 页目录中提取的全部函数调用）：

| 类别 | MST-wi 已有谓词 |
|---|---|
| 主体属性 | `isAdmin(user)`、`isLogin(action)`、`afterLogin(action)`、`notAvailableWithoutLoggingIn`、`isSignup` |
| **主体间关系** | `isSupervisorOf(user1, user2)` |
| 可达性 | `cannotReachThroughGUI(user, url)`、`notTried(user, url)` |
| 输出 | `isError`、`different`、`equal`、`userCanRetrieveContent(user, output)`、`contains` |

**关键搜索（全部零命中）**：`ACL` ／ `acl` ／ `shared`（唯一命中是"shared computer"的无关用法）／ `Owner` ／ `belongsTo` ／ `canAccess` ／ `hasAccess` ／ `granted` ／ `permission`（命中均为 CWE 描述文本）。

### 3.1 缺口的精确表述

BOLA 的合法例外有三类：

| 例外类型 | 形式 | MST-wi 能否表达 | 证据 |
|---|---|---|---|
| **主体属性例外** | `isAdmin(i)` | ✅ 能 | `!isAdmin(action.user)` 出现在 MR 条件中 |
| **主体间关系例外** | `isSupervisorOf(i, owner)` | ✅ 能 | `!isSupervisorOf(User(), action.user)` |
| **（主体 × 对象）显式授权例外** | `canAccess(i, o)`（对象级 ACL／共享／委派） | ❌ **不能** | DSL 谓词全集零命中对象级谓词 |

**这不是实现的疏漏，而是语言表达力的边界**：`canAccess(i, o)` 一旦加入，就等于把政策真值喂给 oracle——**MR 就不需要了（循环）**。所以这个例外在 MR 范式内**原理上不可表达**。

### 3.2 后果：辨识力丧失（这就是"可判定边界"的机制性刻画）

以 **`MR CWE_15_639_OTG_AUTHZ_004`**（CWE-639 = "Authorization Bypass Through User-Controlled Key"，即 BOLA 的标准 CWE 定义）为例，其完整条件为：

```
for ( usedValue : parameterValuesUsedByOtherUsers(action, par) ) {
  IMPLIES(
    CREATE ( Input(2), Input(1) ) &&
    Input(2).actions().get(pos).setParameterValue(par, usedValue)
    ,
    OR( Output(Input(2),pos).isError(),
        userCanRetrieveContent( action.user, Output(Input(2),pos) ) )
  );
}
```

**注意：这条 MR 连 `!isSupervisorOf` 这类主体间关系例外都没有排除**（对比 OTG_AUTHZ_002 有）。

于是在存在对象级显式共享的应用上：

| 场景 | MR 触发 | 真实情况 | 该 MR 能否判定 |
|---|---|---|---|
| 无共享 + 漏检 | 触发 | BOLA | ✅ 可判定（TP） |
| 无共享 + 正常 | 不触发 | 正常 | ✅ 可判定（TN） |
| **有共享 + 正常** | **触发** | **合法** | ❌ **误报，且原理上无法避免** |
| **有共享 + 越权** | 触发 | BOLA | ❌ **与上一行观测完全相同 → 不可判定** |

**第 3、4 行的观测完全一致。** 该 MR 逻辑上无法区分"合法共享"与"越权访问"——**辨识力丧失**。

> **这就是 v4 想立但没有立住的"可判定边界"，现在它有了精确、可证明、可实证的形式：**
> **一个 MR 的辨识力，取决于其例外条件能否在该 MR 的形式语言内被表达。**
> - 例外可表达（主体属性、主体间关系）→ **可判定**
> - 例外不可表达（`主体 × 对象` 显式授权）→ **原理上不可判定，必须弃权**

### 3.3 为什么这是可发表的缺口

1. **MST-wi 的 99.81% 特异性是在 Jenkins / Joomla 上测得的**——这两个系统的授权模型是"角色 + 权限"，**没有对象级共享语义**。所以这个失效模式**在其原始实验中不可能暴露**，也没被讨论。
2. 而现代 API（文档协作、工单分配、团队资源、车辆共享）**对象级共享普遍存在**，且 BOLA 是 **OWASP API Security Top 10 第一位**。
3. **可证伪**：只要在共享场景下实测该 MR，结论立现。
4. **成本极低**：MST-wi 代码公开可跑，共享场景可自建。

---

## 4. 与 v4 原定位的对比

| | v4 原定位 | **v5 新定位** |
|---|---|---|
| 我们提出什么 | 三条辨识性判据（判据 A/B/C） | **对 MR 范式的例外表达力分析**（不提出新 MR） |
| 与 MST-wi 的关系 | 竞争（"更好的 oracle"） | **元分析 + 边界刻画**（用它的目录做实验对象） |
| 新机制 | 判据 B | **辨识力判据：例外可表达性 → 可判定性** |
| 实证对象 | 自建 oracle vs EvoMaster | **MST-wi 的授权 MR（可复现）** + 共享场景 |
| 新颖性风险 | **高**（核证后确认已被覆盖） | 中（缺口窄但可证明，且无人讨论过） |
| 实验成本 | 高（自建 oracle + 多层基准） | **低**（跑现成工具 + 构造共享场景） |

**这次核查净效果**：v4 的核心机制被证伪，但方案**没有被推翻**——它被**重新锚定到一个更窄、更可证明、更容易做的缺口上**。

---

## 5. 关键核实：MST-wi 是否自己讨论过这个缺口

**已核实（2026-09-17）**。下载 arXiv 全文（`2208.09505`，43 页，233,434 字符）并逐词检索：

### 5.1 Section 11 (Threats to Validity) 实际内容

| 子节 | 讨论内容 |
|---|---|
| Internal validity | 两名作者交叉核验 + **Cohen's Kappa = 0.707**（95% CI 0.611–0.804）；补充在 DVWA 上验证 MR 能发现注入类漏洞 |
| Conclusion validity | 报告比例而非做统计检验的理由；Spearman 相关性 |
| Construct validity | sensitivity / specificity / execution time 作为"有效性/效率"的指标构念 |

**结论：Section 11 完全没有讨论对象级授权例外、共享、委派或归属概念。**

### 5.2 全文关键词计数（决定性证据）

| 关键词 | 命中数 | 说明 |
|---|---|---|
| `ownership` | **0** | 完全没有归属概念 |
| `owner` | **0** | 同上 |
| `delegat` | **0** | 完全没有委派概念 |
| `access control list` | **0** | — |
| `shar` | 4 | 经查全部为 "shared computer" 等无关用法 |
| `policy` | 5 | — |
| `supervisor` | 9 | 全部为 `isSupervisorOf` 相关 |
| `false positive` / `false alarm` | 12 / 11 | 均作为**设计目标**出现，非局限讨论 |

### 5.3 作者对误报的应对方式（关键原文）

论文 Section IV-A 图 2 注解：

> "Also, **to avoid false alarms**, the user who cannot access the URL from the GUI (indicated as User(2) in Fig. 2) **should not be a supervisor** with access to all the resources of the other user (User(1))."

Section VIII-A1：

> "Action preconditions avoid redundant follow-up inputs and false positives. For example, the function `notTried(actionURL)` is used not to test the same URL twice... To reduce false positives, we may avoid actions whose output leads to error or alert messages."

**这两句证实了本核查的核心论断**：作者处理"合法跨账户访问"的手段，**就是用 precondition 把已知的合法角色（supervisor）过滤掉**——即**只能处理可用主体关系谓词表达的例外**。

### 5.4 specificity 的分母口径（影响可比性）

论文原文：

> "Specificity captures the proportion of **follow-up inputs** not leading to failures (i.e., a large majority for **stable systems like Jenkins and Joomla**)..."

**99.81% 的分母是"follow-up 输入数"，且在 Jenkins / Joomla 上测得**——这两个系统的授权模型是"角色+权限"，**没有对象级共享语义**。因此该数值**不可迁移**到有共享语义的 API。

### 5.5 核实结论

> **缺口成立，且未被工作自身披露。** 可以在论文中声称"该失效模式尚未被讨论"，但仍须在 Related Work 中正面比较——MST-wi 是最强的相关工作，不是可忽略的背景。

---

## 6. 仍待核实项（不得假设）

| # | 事项 | 影响 |
|---|---|---|
| 1 | MST-wi 工具能否在本机跑通（Maven 构建 + chromedriver + 目标系统） | 决定"用它做实验对象"是否可行 |
| 2 | **crAPI 是否有对象级共享功能** → **已核实：没有**（官方 challenges 只有"访问他人车辆/报告"，无共享语义；此前记忆中的"crAPI 车辆共享"是错的） | 对象级共享场景**需自建** |
| 3 | VAmPI 是否有对象级共享（其模型较简单，可能没有） | 同上 |
| 4 | 是否存在其他变形测试 / 差分测试工作已处理对象级例外 | 若存在，缺口收窄 |
| 5 | MST-wi 的 Related Work 是否提到对象级政策真值问题 | 影响相关工作写法 |

---

## 6. 证据索引

| 证据 | 位置 |
|---|---|
| MR 目录全文（129 页） | `mstwi_artifact/Catalog_of_MRs.pdf` |
| MR 目录提取文本 | `mstwi_artifact/catalog_text.txt` |
| MR 模式统计（含"33/76 hold precondition"） | `mstwi_artifact/PatternsOfMRs.xlsx` |
| 工具仓库 | `github.com/MetamorphicSecurityTesting/MST`（实测可达） |
| 复现包 | Zenodo `10.5281/zenodo.7702754`（实测可达，12 文件） |
| 论文 | IEEE TSE 2023, DOI `10.1109/TSE.2023.3256322`；arXiv `2208.09505` |

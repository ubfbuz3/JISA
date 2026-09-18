# 投稿目标评估：Cybersecurity vs JISA

**日期**：2026-09-17
**评估对象**：v5 方案（例外表达力边界 + Boundary-aware 修正）与其 2026-09-17 首批实验结果
**结论一句话**：**两刊都可投，Cybersecurity 的层级与周期都优于 JISA；但真正的瓶颈不是选刊，是实验体量——按现状投任何一本都会被同一个理由拒。**

---

## 1. 两刊事实对照（均已核实来源）

| 维度 | **Cybersecurity** | **JISA** |
|---|---|---|
| 全称 | Cybersecurity（网络空间安全科学与技术） | Journal of Information Security and Applications |
| 出版方 | SpringerOpen（Springer Nature） | Elsevier |
| 主办 | 中国科学院主管；**中国科学院信息工程研究所 + 中国科技出版传媒股份有限公司** | Elsevier |
| ISSN | 2096-4862 / E-ISSN 2523-3246 | 2214-2126 |
| **CCF 类** | **B 类**（2026 年 3 月第七版目录由 C 升 B） | **C 类** |
| 中科院分区 | 计算机科学 **3 区**（2025 升级版；小类：信息系统 3 / 软件工程 3 / 跨学科应用 4） | 计算机科学 **3 区** |
| JCR | Q2 | Q2 |
| 影响因子 | **4.1（2025）** / 3.7（2024）；5 年 IF 5.3 | 3.7 |
| WoS 收录 | **ESCI**（Springer 官方期刊页列 Emerging Sources Citation Index） | **SCIE** |
| 其他收录 | EI Compendex、Scopus、DBLP、INSPEC、CSCD 核心、中国科技核心、DOAJ | SCIE、EI、Scopus |
| 国内评价 | CCF 计算领域高质量期刊 **T1 类**；中国科技期刊卓越行动计划二期入选 | — |
| 初审时效 | **中位 14–15 天**（官网） | — |
| 全流程 | 官网 9 周；网友经验全程约 3 个月 | 常见 3–6 个月 |
| 年发文量 | 79–121 篇 | 数百篇 |
| 出版模式 | 全 OA | 订阅制（可选 OA） |
| 费用 | 有 APC；**IIE CAS 提供部分赞助**，多来源标注 €1190/$1485 或 0，**需向编辑部确认** | 订阅制投稿免费 |
| 预警 | 否 | 否 |
| 范围匹配 | ✅ 明确含 **"数据及其应用安全"、"软件和系统安全"** | ✅ 明确含 **"Authentication and access control"** |

### 两个需要用户自己拍板的差异

1. **ESCI vs SCIE**：Cybersecurity 目前为 ESCI 收录，**尚未进入 SCIE**（Springer 官方索引列表可查）。若所在单位/考核口径要求"SCI（SCIE）收录"，这一点风险高于分区与 CCF 等级带来的收益。**建议投稿前先向编辑部或查 WoS Master Journal List 核实当前状态**——本评估未能 100% 确认。
2. **APC**：全 OA 期刊通常有文章处理费。Cybersecurity 有 IIE CAS 部分赞助，但减免额度不明。JISA 订阅制投稿本身不收费。

---

## 2. 范围匹配度

Cybersecurity 官网 scope 原文枚举：网络与关键基础设施安全、系统安全、网络安全数据分析与 AI、**数据及其应用安全（data and application security）**、对抗推理、恶意软件分析、隐私。

v5 的工作（Web/API 对象级授权缺陷的变形测试判定边界）直接落在 **data and application security** 与 **systems security** 两格内。该刊亦刊载访问控制漏洞检测类工作，方向无排斥。

JISA 的 scope 明确列出 **Authentication and access control**，同样对口。

**两刊在范围上都不构成障碍。**

---

## 3. 真正的瓶颈：实验体量（投哪本都要先补）

按现状（2026-09-17 首批结果）投稿，无论 JISA 还是 Cybersecurity，审稿人都最可能用同一句话拒：

> "你在一个自建的玩具系统上跑了 2 条 MR，就声称推翻了 MST-wi 的能力边界。"

### 必补三项（按必要性排序）

| # | 缺口 | 现状 | 补法 |
|---|---|---|---|
| 1 | **MR 为语义移植，非 MST-wi 原生引擎** | 本机缺 Maven，用手写执行器复现 catalog 语义 | 装 Maven 跑通 `mvn clean compile package assembly:single`，用**原生引擎**复核结论；或至少用它跑一遍对照 |
| 2 | **被测系统是自建受控系统** | 1 个自建 Flask 应用 | 扩到真实系统：MST-wi 复现包内含 Jenkins & Joomla 的 OVA；另可加 crAPI / VAmPI / OWASP Juice Shop（共享功能需自行注入） |
| 3 | **缺异厂商模型独立复核** | Codex 额度锁定至 2026-10-08；环境无其他厂商 API | 额度恢复后跑 `/auto-review-loop` 或 `experiment-integrity` 独立审计 |

### 建议同步补强

- **MR 族扩到全部 4 条授权类 MR**（catalog 中 `CWE_15_639_OTG_AUTHZ_00x` 系列），当前只覆盖 2 条
- **把 `listed/unlisted` 两面性写成核心贡献**——这是本次实验超出预注册预期的发现，也是最能体现"边界刻画"而非"批评"的部分
- **Boundary-aware 修正要写成有分量的算法**（含复杂度与代价分析），否则容易被判"批评多于建设"

---

## 4. 建议路径

**首选：双轨，先把实验补到体量，再决定投哪本。**

| 情形 | 建议 |
|---|---|
| 时间宽松、追求期刊层级 | 投 **Cybersecurity**（CCF-B > JISA CCF-C，周期更快，范围对口） |
| 单位硬性要求 SCIE 收录 | 投 **JISA**（SCIE 确定；Cybersecurity 为 ESCI，需先核实） |
| 单位硬性要求"3 区 + 快周期" | 投 **Cybersecurity**（初审 15 天，全程约 3 个月） |
| 经费敏感、不愿付 APC | 投 **JISA**（订阅制投稿免费） |

**优先顺序**：补实验（1→2→3）→ 按上表定刊 → 投稿。

> 换刊不会改变审稿人对实验体量的判断。**换刊不是解药，补实验才是。**

---

## 5. 来源

- Springer 期刊主页：`https://www.springer.com/journal/42400/about`（IF 4.1/2025、初审 15 天、scope、IIE CAS 赞助）
- Cybersecurity 官网：`https://cybersecurity.springeropen.com/`（indexing 列表、recent articles）
- CCF 2026 第七版目录（Cybersecurity 升 B 类）：中科院信工所编辑部公告 + 多份整理版；CCF 官网 NIS 页面仍为第六版（2022），未同步
- LetPub / 学术之家 / 多份中文期刊资料：中科院 3 区、JCR Q2、年发文量、审稿周期
- JISA scope：`ftp.neuhaus.cn/journal/393`（引 JISA 官方 scope）

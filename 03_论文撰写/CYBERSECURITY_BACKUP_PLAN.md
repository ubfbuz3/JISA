# Cybersecurity（Springer）备份投稿方案

> 用户 2026-09-18 决策：**主投 JISA（SCIE）**，同时**备好 Cybersecurity 备份稿**。
> 本文件只写"换刊要改什么"，不改动现有 JISA 主稿。

## 1. 为什么留这个备份

| 维度 | JISA | Cybersecurity |
|---|---|---|
| 收录 | **SCIE** | **ESCI**（Scopus / DOAJ / PMC，**非 SCIE**） |
| 分区 | 中科院 3 区（CCF C） | 中科院 2 区/3 区变动中；Scopus Q1 |
| 影响因子 | 3.7–3.8 | 4.1 |
| 费用 | 订阅制 **¥0**；Gold OA 约 US$2,400–3,130 | 全 OA：**£1,060 / US$1,485 / €1,190**（+VAT） |
| 评审 | 单盲为主 | **双盲**，约 9 周 |
| 主办 | Elsevier | 中科院信工所（SKLOIS）× Springer × 科学出版社 |

⇒ 备份的真实用途只有一个：**若 JISA 出现拒稿/超长滞留**，可低成本改投。
⇒ ⚠️ 用户单位硬性要求 **SCI 收录**，ESCI 不计入 ⇒ **备份不等于等价选项**，投前必须再核 WoS MJL。

## 2. 就绪度检查（可复跑，非人工判断）

```bash
cd 03_论文撰写/paper
python check_springer_readiness.py
```

当前结果 **PASS 6 / 9**：

| 状态 | 检查项 | 现状 |
|---|---|---|
| PASS | 数字不使用逗号千分位 | 未发现（Cybersecurity 明令禁止） |
| PASS | 表格无颜色/底纹 | 未使用 `colortbl` / `rowcolor` |
| PASS | 网页链接已进参考文献 | 正文 0 处裸 URL |
| PASS | 关键词 4–6 个 | 6 个 |
| PASS | 正文引用的图均为矢量且存在 | 7 张，全 PDF，无缺失 |
| PASS | 身份信息可剥离（双盲） | 仅 `main.tex` 的占位符，需替换后另出匿名版 |
| **TODO** | 文档类切到 Springer 模板 | 当前 `elsarticle` → 目标 `sn-jnl.cls` |
| **TODO** | 必需声明章节 | 缺 **5 个**：Data availability / Competing interests / Funding / Authors' contributions / Ethics approval |
| **TODO** | 摘要 ≤250 词 | 当前约 **380 词**，需压缩 ~35% |

## 3. 三项必改（按工作量排序）

### 3.1 补 5 个声明章节（约 20 分钟）
Springer 要求它们排在 References 之前，作为独立小节。本项目可写的内容：

- **Data availability** —— 合成矩阵 `experiments/raw_matrix.jsonl`（576 条）、
  Gitea 实验台脚本 `experiments/real_system/`、原生引擎桥接 `experiments/native_engine/`、
  以及 `04_绘图与分析/analysis/compute_all.py`（全部数字的唯一来源）。需声明是否公开、公开在哪。
- **Competing interests** —— 无。
- **Funding** —— 待用户补（如无可写 none）。
- **Authors' contributions** —— 待用户补（本项目目前只有一位作者）。
- **Ethics approval** —— 不涉及人类/动物受试；被测系统为自建实验台上的开源软件，无第三方系统未授权测试。
  **这一条对本工作尤其重要**，因为稿件涉及攻击性测试方法，必须显式写明实验只在本机自建实例上进行。

### 3.2 文档类切换（约 1–2 小时，纯机械）
- 目标 `sn-jnl.cls`（Springer Nature LaTeX 模板）。
- 机械改动面：`\documentclass`、`\begin{frontmatter}`→`\title/\author/\affil`、
  `\begin{abstract}` 位置、`\sep` → 逗号分词、`\bibliographystyle{spbasic}`。
- ⚠️ **bib 切换**：Cybersecurity 的具体参考文献风格需在投稿页确认（Springer Basic 为
  作者–年制；部分 SpringerOpen 刊用数字制）。`normalize_bib.py` 已从 DOI 机械生成 `refs.bib`，
  切风格只需换 `\bibliographystyle`，**不需要改条目**。
- ⚠️ **不允许手敲数字**这条纪律在换刊后同样适用：所有 `\Res*` 宏原样搬过去即可。

### 3.3 摘要压缩到 ≤250 词（约 40 分钟）
现 380 词。压缩原则（**不得损失任何限定语**）：
- 三条边界各留一句话，但**"point-estimate non-inferiority"**、**"tie at 0 非优势"**、
  **"specificity 分母是 the generated inputs"** 三个限定语必须保留；
- 删除方法细节枚举（读者去正文看）；
- 删除"本文组织如下"一类结构句。

## 4. 双盲评审的额外要求（容易被忽略）

Cybersecurity 是**双盲**，需要单独一份匿名稿：
1. 作者名/单位/邮箱置空 —— 现 `main.tex` 是占位符，替换正式信息后要**另存匿名版**。
2. 检查自我引用措辞：不得出现 "our previous work" 一类可识别表述。
3. **致谢与基金删掉或改为匿名**。
4. 仓库链接：`github.com/MetamorphicSecurityTesting/MST` 是**第三方**作品，不是自引，可保留；
   但自建的实验材料（`experiments/`）如果公开，需用匿名仓库或写"available upon request"。
5. 稿件里描述"我们跑通了他们的引擎" —— 这是对第三方制品的复现，不构成身份泄露。

## 5. 封面信 6 项（Cybersecurity 明文要求）

1. 为什么这篇该发在 Cybersecurity
2. 与期刊政策相关的任何问题说明
3. 潜在利益冲突声明
4. 全体作者已批准投稿的确认
5. 未一稿多投的确认
6. 若投专刊，写明专刊名

## 6. 时程与费用

- 评审平均 **9 周**（比 JISA 的 7 个月快得多）—— 这是备份的**主要优势**。
- APC **US$1,485 / £1,060 / €1,190**（+VAT）。国内作者**可申请减免**，
  但 Springer 明确要求**在投稿时**提出，评审中或录用后不再受理。
- 若单位能报销，这笔钱换到的是一篇全 OA、可立即公开的文章。

## 7. 结论：备份的成本

| 动作 | 成本 |
|---|---|
| 就绪度检查 | ¥0（已建脚本，可复跑） |
| 补声明章节 | 20 分钟（Data availability / Ethics 需用户确认口径） |
| 文档类切换 | 1–2 小时 |
| 摘要压缩 | 40 分钟 |
| APC | **US$1,485**（若走这条路；订阅制不存在这个选项） |

⇒ **除 APC 外，备份稿的边际成本约半天工作量。** 建议在 JISA 投稿后、等审的窗口期再做，
不必现在动手 —— 因为如果 JISA 顺利，这份工作就白做了。

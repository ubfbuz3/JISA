# Access-2026-49387 重投提交包（v12）

冻结版本：tag `access-resubmission-v12`（解引用 SHA：`d9f08778aa68eeeb0b0b9a61f9e9b7c089f8c66e`）。2026-10-20 构建；
本目录四个文件是该提交的产物，**未改动一个字节**。上一版 `07_投稿_v11_superseded/` 仅作快照，
**不要上传**。

## 一、文件与门户槽位

| 序号 | 文件 | 门户槽位 | 页数/内容 | 字节 | SHA-256 |
|---|---|---|---|---|---|
| 1 | `response_to_reviewers.pdf` | Author's Response Files | 12 页，21 Concern / 21 Response / 21 Action | 179 015 | `87ae135162049692…`（完整值见 `SHA256SUMS.txt`） |
| 2 | `main_highlighted.pdf` | Highlighted PDF（changes marked） | 32 页，2262 行标注 | 2 146 410 | `a59b3b6e6f2d5345…` |
| 3 | `main.pdf` | Main Manuscript — PDF | 32 页 / 26 表 | 716 399 | `a158486a3e8e3104…` |
| 4 | `latex_source_files_submission.zip` | Main Manuscript — LaTeX source | 97 个文件；空目录编译 32 页 / 716 399 B / 0 error | 1 187 987 | `bea12e9aa0bc0c9f…` |
| 5 | `Request_for_Byline_Change_Access-2026-49387.docx` | **Request for byline change form**（编辑原信指定的专用类型，不要只当 Author's Response 附件） | 原名单 2 人 → 新名单 3 人，含理由；原题目已改回编辑决定信记载的原投稿标题 | 11 629 | `8ca9c569c4cec76e…` |

`SHA256SUMS.txt` 覆盖前四个（第五个是 Office 文档，重新保存会改变字节，不入校验；其哈希单独记在本表）。

### 作者变更表的两个字段（2026-10-20 最终审核后已核对）

| 字段 | 值 |
|---|---|
| Original Manuscript ID | `Access-2026-49387` |
| Original Article Title | Limits of Metamorphic Testing for Object-Level Authorization: Temporal Reachability, Oracle Admissibility, and Measurement Resolution（**原投稿题目**，取自编辑决定信；不是修订后的 "Two Reachability-Gated Relations in MST-wi…"） |
| Original Author List | Qiulong Lin; Nanlei Chen (corresponding author) |
| Updated Author List | Qiulong Lin; Xiaoyu Ke; Nanlei Chen (corresponding author) |

## 二、v12 相对 v11 改了什么

只改作者名单相关，**科学内容、数字、表格、结论一字未动**：

| 位置 | v11 | v12 |
|---|---|---|
| 标题块 | LIN, CHEN | LIN, KE, CHEN（Ke 第二作者，Chen 仍是通信作者、第三位） |
| 单位 1 | 只列 ubfbzu3@163.com | 加 5197211@qq.com（Ke 的邮箱） |
| 页眉（markboth） | Lin and Chen | Lin, Ke, and Chen |
| 作者简介 | 2 段 | 3 段（Ke：Yango University, Fuzhou，仅此一句，未编造学位/职称/研究方向） |
| Authors' contributions | Lin、Chen 共同完成 | 加一句：Xiaoyu Ke guided the experimental work and reviewed the experiments and their analysis |
| PDF 元数据 pdfauthor | Lin and Chen | Lin, Ke, and Chen（正文与回复信两处） |
| 回复信首页署名 | Lin and Chen，19 October 2026 | Lin, Ke, and Chen，20 October 2026 |
| Data availability | 指向 v11 | 指向 v12，并说明 v11 与 v12 只差作者块/简介/贡献声明 |

页数不变（32 页 / 26 表），因此回信里 41 处表号页码引用与 75 项承重数字**全部照旧通过**。

## 三、门户里要填的信息

| 项 | 值 |
|---|---|
| Manuscript ID | `Access-2026-49387` |
| Title（修订后） | Two Reachability-Gated Relations in MST-wi: Temporal Mismatch, Oracle Admissibility, and Measurement Limits |
| Authors（顺序） | Qiulong Lin; Xiaoyu Ke; Nanlei Chen |
| Corresponding author | Nanlei Chen（ubfbzu3@163.com） |
| Article type | Research Article（Original Research） |

**门户里的作者列表必须与 `main.pdf` 第 1 页一致**（三作者、顺序如上）；若门户仍显示两作者，
在 Author List 步骤增补 Ke 并调整顺序，再按下面第四节的专用槽位上传
`Request_for_Byline_Change_Access-2026-49387.docx`，并在回复信正文说明。

## 四、上传顺序

1. Author Portal → 该稿件 **Start Resubmission**。
2. **Author's Response Files**：`response_to_reviewers.pdf`。
3. **Highlighted PDF**：`main_highlighted.pdf`。
4. **Main Manuscript**：PDF 槽位 `main.pdf`；LaTeX 槽位 `latex_source_files_submission.zip`（整包，不要解压）。
5. **Request for byline change form**：`Request_for_Byline_Change_Access-2026-49387.docx`。
   编辑原信明确要求以该**专用文件类型**上传（"uploading it as *Request for byline change form*"），
   并在门户填写变更理由；不要只在 Author's Response 里附一份。
6. Preview 后核对下面五处，再 Submit。

## 五、上传后预览要看的地方

| 位置 | 应看到 |
|---|---|
| `main.pdf` p.1 | 标题；**QIULONG LIN, XIAOYU KE, NANLEI CHEN** 三人；单位 1 含两个邮箱；Corresponding author: Nanlei Chen |
| `main.pdf` p.18 | Table 17 表注：oracle 在记录上答对 ≠ 独立性；末尾 69/64/42 成本句 |
| `main.pdf` 末页 | 三段作者简介，Ke 的一段在 Lin 与 Chen 之间 |
| `main_highlighted.pdf` | 32 页，与净稿文本逐字相同，仅多标注层 |
| `response_to_reviewers.pdf` p.1 / p.4 / p.12 | 三作者署名与 20 October 2026；p.4 长路径断行；p.12 结尾完整 |
| byline 表 | Original Manuscript ID = `Access-2026-49387`；**Original Article Title = 原投稿题目（Limits of Metamorphic Testing…Measurement Resolution）**；Original 2 人 / Updated 3 人顺序正确 |

## 六、校验记录（本轮实测）

- 净稿与高亮稿逐页提取文本一致：182 170 字符，sha256 前缀 `088a702a0c87477d`。
- 源码 zip：97 文件、CRC 通过，空目录 `pdflatex → bibtex → pdflatex ×2` 得 32 页 / 716 399 B / 0 error / 0 undefined。
- 回信：12 页；75 项承重数字、41 项表号页码引用全部通过；overfull 与 v11 相同（仅类文件 `\Output` 项）。
- 正文页内 overfull：65 × 505.12 pt（`ieeeaccess.cls` 页输出例程，全篇每页一条，历史一致）+ 2 × 9.27 pt（`\maketitle`），无新增真实越界。
- 作者变更表（2026-10-20）：`Original Article Title` 由修订后题目改为编辑决定信记载的**原投稿题目**，
  改后逐字回读确认旧题目 "MST-wi" 字样已不存在、字段内引号成对；其余字段（稿号、旧名单、新名单、理由）未动。
  该表是 Office 文档，**不属于** `access-resubmission-v12` 冻结产物，改它不改变上面四个文件的任何字节。

## 七、边界

- 未登录 Author Portal、未代按 Submit：需作者本人 IEEE 账号与 ORCID，且提交是署名行为。
- 作者名单变更需**全体作者同意**；表单里已写"agreed by all authors"，上传前请与 Nanlei Chen 确认这一句属实。
- Ke 的简介只写单位一句。若需要补学位/职称/研究方向，请提供事实，我再补并重编（会改变 PDF 字节，需重新生成包）。

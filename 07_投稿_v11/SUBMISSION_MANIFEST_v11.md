# Access-2026-49387 重投提交包（v11）

冻结版本：`4d1036ce26abab79a49078ca9241da6d7fb7a860`（tag `access-resubmission-v11`，tag 对象
`97fc6d405dd156aa72d84cad386767003ad10970`）。2026-10-20 用 `ls-remote` 核对：远端 `main`、
tag 解引用、本地 HEAD 三者同一提交。本目录四个文件是该提交的构建产物，**未重新编译、未改动一个字节**。

## 一、四个文件与门户槽位

| 序号 | 文件 | 门户槽位 | 页数/内容 | 字节 | SHA-256 |
|---|---|---|---|---|---|
| 1 | `response_to_reviewers.pdf` | Author's Response Files | 12 页，21 Concern / 21 Response / 21 Action | 178 755 | `33a2c6827aa3220f39aa094fdd5058e40860f4f7f0abf209217dba75b4ff6bdb` |
| 2 | `main_highlighted.pdf` | Highlighted PDF（Revision with changes marked） | 32 页，2216 处修改（删除项见回复信差分说明） | 2 115 736 | `74b45965e99272751c772fd5d4a5e68a8061a183bdd5ab5111c4500b16b2fc70` |
| 3 | `main.pdf` | Main Manuscript — PDF | 32 页 / 26 表 | 714 929 | `a64634a1595a0600a6189919b33e322be9f250269f33223744d3e289015f5550` |
| 4 | `latex_source_files_submission.zip` | Main Manuscript — LaTeX source | 97 个文件；空目录编译 32 页 / 714 929 B / 0 error | 1 187 746 | `0aca4ef9b58292101319a50a6fb9c17f4e92d6ab0a3e555438d8a89fb795ea86` |

`SHA256SUMS.txt` 为上述四行的标准格式；在本目录执行 `sha256sum -c SHA256SUMS.txt` 应为四项 OK。

净稿与高亮稿的**逐页提取文本完全一致**（181 645 字符），差别只在标注层，这一点已作为上传前的自检项。

## 二、门户里要填的信息

| 项 | 值 |
|---|---|
| Manuscript ID | `Access-2026-49387` |
| Title（修订后） | Two Reachability-Gated Relations in MST-wi: Temporal Mismatch, Oracle Admissibility, and Measurement Limits |
| Authors | Qiulong Lin; Nanlei Chen |
| Corresponding author | Nanlei Chen（ubfbzu3@163.com） |
| Article type | Research Article（Original Research） |

标题、作者、通信作者与 `main.pdf` 第 1 页、回复信首页、README 与 zip 内 `main.tex` 一致；作者块
两处 ORCID：Lin `0009-0000-5392-4475`。

## 三、上传顺序（Start Resubmission）

1. 进入 Author Portal → 该稿件的 **Start Resubmission**。
2. **Author's Response Files**：上传 `response_to_reviewers.pdf`（若门户允许多文件，只传这一个，
   它是完整的 21 条逐条回复 + 缺口表）。
3. **Highlighted PDF / Revision with changes marked**：上传 `main_highlighted.pdf`。
4. **Main Manuscript**：PDF 槽位传 `main.pdf`；LaTeX/editable source 槽位传
   `latex_source_files_submission.zip`（不要解开单独上传，也不要换成别的 zip）。
5. 保存后进入 **Preview / Build PDF**：确认门户自己编译出的 PDF 是 32 页、第 1 页标题为上面那一行、
   参考文献无 “??”；若门户编译失败，先看是否漏传 zip 里的 `tables/`、`figures/` 子目录。

## 四、上传后预览要看的四处

| 位置 | 应看到 |
|---|---|
| `main.pdf` p.1 | 标题为修订后标题；作者 Qiulong Lin、Nanlei Chen；两处单位与 ORCID 图标 |
| `main.pdf` p.18 | Table 17 表注：oracle 在记录上答对 = soundness，不等于独立性，无 admit 行；末尾有 69/64/42 的成本句 |
| `main_highlighted.pdf` p.1 起 | 修改段有底色标注；页数与净稿同为 32 |
| `response_to_reviewers.pdf` p.4 | 冻结协议路径在斜杠处断行，无越界；p.12 为末页，无半截段落 |

## 五、本次实际做了什么、没做什么

- **做了**：核对四个文件与冻结提交逐字节一致（哈希见上）、页数、zip CRC 与成员数、净稿/高亮稿文本一致、
  远端 SHA；把文件整理成独立目录并附校验清单；把 `SUBMISSION_CHECKLIST.md` 的页数/文件数/产物数/
  标签口径校准到 v11；修正 `cover_letter_ieee_access.md` 里遗留的旧标题与“首次投稿”措辞。
- **没做**：**没有登录 IEEE Author Portal，也没有代按提交**。门户登录需要作者本人的 IEEE 账号与
  ORCID 授权，且提交是作者署名行为，只能由作者完成。上面的步骤到“Preview 确认”为止都可照做，
  最后一步 **Submit** 请本人点击。
- **没做（也不需要做）**：没有重跑任何实验、没有重新编译任何 PDF、没有改动 `main.tex`/章节/表格/宏。
  因此本包与验收结论（`06_论文追踪/2026-10-20_v11定点验收/验收结论.md`）指向同一份物理文件。

## 六、备选件

若门户另设 **Cover Letter** 必填项：`03_论文撰写/cover_letter_ieee_access.md` 已按修订后标题与
“resubmit (Access-2026-49387)” 更新，需要时可以一分钟转成 PDF 再传；不要求时不必上传，
回复信本身已含给编辑的说明。

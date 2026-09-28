# IEEE Access 投稿操作清单（照着点）

> 状态：稿件已按 IEEEtran 模板就绪（15 页 / 双栏 / 含两位作者简介 / 含 Lin 的 ORCID 脚注）。
> 本清单对应 IEEE Access **官方投稿系统**：Atypon ReX。
> 投稿入口：**https://ieee.atyponrex.com/journal/ieee-access**
> （旧 ScholarOne 链接 `mc.manuscriptcentral.com/ieee-access` 已废弃，以 Atypon ReX 为准。）

---

## 0. 投稿前必做的两件事（硬门槛）

1. **ORCID 绑定**（系统侧，不是只在 PDF 里挂）
   - IEEE Access 要求**投稿人账号**必须关联一个**公开可见且资料填全**的 ORCID iD。
   - 你（Qiulong Lin）的 ORCID = **0009-0000-5392-4475**，已在 PDF 作者块脚注里挂了；
     现在还要在 IEEE 投稿账号里把它**绑上并设为公开**。
   - 建议 Chen（Nanlei）也注册并绑定 ORCID（IEEE 要求所有作者都有，至少投稿人必须有）。
   - 注册免费：https://orcid.org

2. **语法自查**（否则可能被"立即拒稿"）
   - IEEE Access 明确规定：*语法差的稿件会立即 reject*。
   - 投前务必通读一遍英文；可用 IEEE 的 Paperpal Preflight 预检（非强制，但推荐）。

---

## 1. 登录 / 建账号
- 打开 https://ieee.atyponrex.com/journal/ieee-access
- 用 **IEEE 账号**登录（没有就注册一个；注册时填 ORCID 并设为公开）。
- 进入后点 **"Submit Manuscript" / "Begin Submission"**。

---

## 2. 选稿件类型（Manuscript Type）
- 选 **"Research Article"**（不确定时的标准选项）。
- 不要选 Review / Survey / Comment 等。

---

## 3. 上传文件（File Upload）
系统要求 **同时提交源文件 + PDF，且两者内容完全一致**（文件 ≤ 40 MB）。我们已备好：

| 上传项 | 选哪个文件 | 备注 |
|---|---|---|
| **Manuscript (PDF)** | `03_论文撰写/paper/main.pdf` | 15 页，已含作者简介与 ORCID 脚注 |
| **Source file (LaTeX)** | `03_论文撰写/paper/latex_source_files_submission.zip` | 26 文件；PDF 由它编译而来，**内容一致** |
| **Cover letter** | `03_论文撰写/cover_letter_ieee_access.md`（转 PDF 或直接粘贴） | 说明研究契合 IEEE Access  multidisciplinary 范围 |
| **Graphical Abstract（可选但推荐）** | `04_绘图与分析/figures/fig1_protocol.pdf` | 三阶段协议图，可直接当作 GA 上传 |
| **Author biography** | 已内嵌在 PDF/源文件里（参考文献后），**无需单独上传** | IEEE Access 要求 bios 直接放进正文，我们已做 |

> 注意：投稿系统会从你上传的文件里**自动抽取作者列表**。提交后务必在下一步
> 核对抽出来的作者是 **Qiulong Lin + Nanlei Chen**、单位与邮箱无误。

---

## 4. 填元数据（Metadata）
- **Title**：直接复制论文标题（已存于 `main.tex`，逐字粘贴，勿加换行）。
- **Abstract**：粘贴 `main.tex` 里的摘要正文（231 词，已 ≤250）。
- **Keywords（系统字段，3–10 个）**：这是**投稿系统单独的必填项**，不是正文里的
  Index Terms。建议用：`metamorphic testing; object-level authorization; BOLA/BFLA;
  oracle problem; API security; false proof`（选 4–6 个最贴切的）。
- **Author list**：核对系统自动抽取结果——
  - Qiulong Lin — Yango University, Fuzhou, China / Sogang University, Seoul, Republic of Korea
  - Nanlei Chen（**Corresponding Author**）— ubfbzu3@163.com
  - 顺序提交后**不能改**（除非全体同意 + 编辑批准），提交前确认无误。
- **Corresponding author**：设为 **Chen Nanlei**（ubfbzu3@163.com），他是录用后校样联系人。

---

## 5. 推荐/回避审稿人（可选）
- **Suggested reviewers**：可填 1–3 位（姓名+单位+邮箱），加速送审。
- **Opposed reviewers**：如有利益冲突的审稿人可列（无则跳过）。

---

## 6. 确认并提交
- 复查所有步骤 → 点 **"Submit"**。
- 提交后会收到**确认邮件**（含稿件编号 MS 号，形如 `ACCESS-XXXX-XXXX`）。
- 状态流转：`Submitted` → `With Editor` / `Under Review` → `Required Reviews Completed` →
  编辑决定（`Accept` / `Reject` / `Reject with resubmit`）。
- IEEE Access 是**二元决定**（接收或拒稿，附建设性意见），平均审稿约 4 周，但也可能更快/更慢。

---

## 7. 录用后的事（先心里有数）
- **APC = US$2,075**（2025 官方价，另加当地税；**投稿免费，录用后缴纳**；
  IEEE 会员可享 5–20% 折扣，低收入国家可申请减免）。
- 需缴 APC 才正式发表，发表于 IEEE Xplore，SCIE 收录。

---

## 8. 两个合规提醒（别踩雷）
1. **AI 生成内容披露**：IEEE Access 规定，若文中使用了 AI 生成文本，须在**致谢**
   部分披露并引用所用 AI 系统。请确认稿件是否有需要披露之处，按需补一句致谢。
   （我们的实验数据/数字均来自你真实跑的分析，仅写作/排版有工具辅助——是否构成
   "AI-generated text" 由你判断；稳妥起见可加一句 disclosure。）
2. **缩写首次定义**：BOLA/BFLA、MT、API 等缩写**首次出现处（含摘要）必须给出全称**，
   投稿前通读确认一遍（我们的正文一般已定义，重点查摘要与引言开头）。

---

## 9. 当前交付物清单（都在仓库里，已提交 `930bf76`）
- `03_论文撰写/paper/main.pdf` — 手稿（PDF）
- `03_论文撰写/paper/latex_source_files_submission.zip` — LaTeX 源
- `03_论文撰写/cover_letter_ieee_access.md` — 投稿信
- `04_绘图与分析/figures/fig1_protocol.pdf` — 可作 Graphical Abstract
- `SUBMISSION_CHECKLIST.md` — 投前总清单
- 本文件 — 投稿操作步骤

> 投稿是网页端操作，需你自己的 IEEE 账号登录，我无法代为登录提交。
> 按上面 0→6 步点完即可。提交后把 **MS 稿件号**发我，我帮你记到日志里。

# IEEE Access 投稿前 Checklist

> **投稿目标：IEEE Access**（Elsevier→JISA 已 desk reject「范围不符」；已切换到 IEEE Access **官方 `ieeeaccess.cls`** 模板）。
> 逐项核对；每项标 ☑（已满足）/ ☐（待办）。配套脚本：`reproduce.sh`、`verify_artifact.sh`、
> `04_绘图与分析/analysis/make_manifests.py`。Zenodo 步骤见 `ZENODO_GUIDE.md`。
>
> **2026-10-20 校准到 v12 冻结稿（`d9f0877` / `access-resubmission-v12`）**：下方页数、文件数、
> 产物数、Zenodo 标签口径均为 v11 实测值；重投上传见 `07_投稿_v11/`。

---

## A. Zenodo DOI（永久可引用归档）——已完成
- ☑ `.zenodo.json` 已提交，Zenodo 已按 `artifact-v1`（= 提交 `a86cd4c`）归档。
- ☑ **DOI 已派发：`10.5281/zenodo.22859942`**，已回填 `sections/10_declarations.tex` §Data availability。
- ☑ GitHub 远端 `main` = **`d9f0877`**（= tag `access-resubmission-v12` 解引用，2026-10-20 用 `ls-remote` 核对；工作树干净）。
  `artifact-v1` 冻结于 `a86cd4c`，**勿重锚**（重锚会使 tag 与 Zenodo 快照不一致）。

---

## B. Cover letter 要点（`cover_letter_ieee_access.md` 已起草）
按"实证方法学刻画"而非"新工具/新防御"定位，避免被当成 tool paper 误判。

1. **稿件类型**：Research Article（Original Research）。
2. **核心贡献定位**：对"对象级授权（BOLA/BFLA）oracle 问题"中变形测试的**边界**做
   **实证方法学刻画**——不是提出新工具或新防御。三点发现：
   - F1 时序可达性（带外授权被误报为 proven violation / false proof）；
   - F2 oracle 可容许性（修好 oracle 后 MR 步骤不再提供额外裁决信息，Proposition 1）；
   - F3 度量分辨率（reported specificity 未以可达≡授权为条件，分母输入级、可被稀释）。
3. **诚实的范围声明**（务必写清，防 reviewer 误解）：
   - 结论只覆盖 **reachability-gated authorization relations examined here**，不泛化到变形测试整体；
   - 实例化的是 **2 条 MR × 跨 3 厂商**（Gitea 1.22.6 / Gogs 0.14.3 / GitLab 17.11.7）；
   - 阳性对照是**受控研究靶机**（controlled research artefact），**不是**生产 Gitea，不声称发现 Gitea 真实 CVE。
4. **统计措辞**：文中只给**描述性点估计**，无 non-inferiority / domination 声明，也不以 sensitivity/specificity 的推断统计含义使用这些词。
5. **可复现性卖点**：公开 artifact（GitHub tag `artifact-v1` + Zenodo DOI）；正文无任何手敲数字，全部由 `compute_all.py` 重算；PDF 字节可复现；`verify_artifact.sh` 校验每个原始记录与字节可复现产物的 SHA-256。
6. **期刊契合**：点明落在 *IEEE Access* 的两大方向交集——**网络与 Web/API 系统的安全与隐私**（认证/授权）与**软件工程/软件测试**，且为应用导向的实证研究。
7. **AI 使用声明**：论文 §Declarations 已声明（生成式 AI 仅用于文献核对、分析脚本开发、语言润色，所有计算由作者独立复核）——IEEE Access 要求 AI 生成内容在致谢/声明中披露。
8. **利益与资助**：无竞争利益、无基金资助（论文 §Declarations 已声明）。

---

## C. Data availability（已精确化并回填真实 DOI）
`10_declarations.tex` 的 Data availability 段现已给出真实 DOI：`10.5281/zenodo.22859942`，并指向
**`access-resubmission-v12`**（含两个新实验的逐格记录；v9 只含初版运行，v10/v11 为中间冻结），
并点名列明四类原始记录（场景/配置研究、真实系统 cell 研究、原生引擎执行、seeded 阳性对照）、
分析管线与自检脚本。无需再改（如后续重锚 tag 须同步更新措辞）。

---

## D. `reproduce.sh` 干净环境一命令自检（已实现）
`verify_artifact.sh` 由 `reproduce.sh` 委托。三种模式：

| 命令 | 作用 |
|---|---|
| `bash verify_artifact.sh` 或 `bash reproduce.sh check` | **默认/干净环境自检**：① 工具链就绪；② **25** 个原始记录 SHA-256 与 `provenance/RAW_RECORDS_SHA256.json` 一致；③ **35** 个字节可复现产物与 `provenance/OUTPUTS_SHA256.json` 一致；④ 报告 git 工作树是否干净。 |
| `bash verify_artifact.sh repro` | **强证明**：`git archive HEAD` 抽出已提交树到临时副本，重跑整套分析管线，比对重生成产物是否**逐字节一致**；用完即删，不污染工作树。 |
| `bash verify_artifact.sh gen-manifest` | 在**合法**更新原始记录或生成脚本后，重算两个 SHA-256 清单并提交。 |

- ☑ 投稿前已在 v11 提交上跑 `bash verify_artifact.sh repro`：**PASS 35/35**（删除全部输出后重生成，逐字节一致）。

---

## E. 通用投稿前核对（排版/合规）
- ☑ **模板**：已切换为 **IEEE Access 官方 `ieeeaccess.cls`**（`\documentclass{ieeeaccess}`）；作者块（大写姓名+上标单位号）、编号单位、`Corresponding author`、ORCID iD 图标、INDEX TERMS、文末作者简介均按官方版式。单盲（作者信息在手稿中）。
- ☑ **页数**：当前 **32 页 / 26 表**（ieeeaccess.cls 双栏；IEEE Access 不设硬性页数上限，但超出 20 页需付 overlength 费）。
- ☑ **摘要词数** ≤ 250（当前 **244**；统计须先展开 `\Res*` 宏再计，脚本在 `AppData/Local/Temp/count_abstract*.py`）。
- ☑ 0 undefined references / citations / control sequences（`build.sh` 第 4 步校验）。
- ☑ **投稿包自足可编译**（2026-10-19 修正）：`make_submission_zip.py` 的宏文件清单改为从正文
  `\input{}` 自动推导——旧的硬编码清单漏了 `temporal_*`、`cve_pair_*`、`native_split_table`
  共 6 个生成表，ReX 端会直接编译失败。现为 **97 个文件**（含 R1.7/R1.9 的两个新生成表与宏文件）；
  已验证：解压到空目录编译直接出 **32 页 / 716399 B** PDF，0 error、0 个未定义引用（与交付 PDF 同页数、同字节数，文本一致）。
- ☑ **表格宽度实测**（2026-10-19）：把 12 张表的 tabular 取出单独装箱测 `\wd`，全部 ≤ `\textwidth`
  (505.1 pt)；正文段落只剩类文件 `\maketitle` 自带的 9.3 pt 一条 overfull。
- ☑ 参考文献真实可溯源、无手敲（`refs.bib` 由 `normalize_bib.py` 规范化，字段值无 CJK）；bibliographystyle 已换 `IEEEtran`。
- ☑ 图表全部矢量、无 AI 生成像素；矢量图字节可复现。
- ☑ 标题/摘要主张只覆盖 reachability-gated relations，不泛化（红线 ⑦）。
- ☑ 撤回清单红线全部遵守（无 sensitivity/specificity 声明、无"机制非冗余"、无 "strictly dominates"、"自省面可读"带特权视点、无 "crawl-time aware" / "responsible variable" 措辞）。
- ☑ **作者简介**：三位作者（Lin / Ke / Chen）的简介已内嵌正文（参考文献后，`IEEEbiographynophoto`，`main.tex`），无需单独上传。
- ☐ **Graphical Abstract**（IEEE Access 终稿阶段通常要求）：可复用现有矢量图 `04_绘图与分析/figures/fig1_protocol.pdf` 单独上传。

---

## F. 待用户决策 / 后续（IEEE Access 提交）
- ☐ **ORCID（硬门槛）**：IEEE Access 要求投稿账号绑定**公开可见的 ORCID iD**（若作者尚无 ORCID 需先免费注册 `orcid.org`）。
- ☐ **APC**：**US$2,075**（2025 官方价，另加当地税；接受后缴纳，投稿免费；IEEE 会员 5–20% 折扣，低收入国家可申请减免，询问 `apcinquiries@ieee.org`）。
- ☐ **投稿系统**：**IEEE Author Portal（Atypon ReX）**（非 Elsevier EM；需先建 IEEE 账号）。
- ☑ **上传件（重投，v12）**：见 `07_投稿_v12/`，四个文件与槽位对应关系见该目录 `SUBMISSION_MANIFEST_v12.md`；
  另加 IEEE 作者名单变更申请 `Request_for_Byline_Change_Access-2026-49387.docx`：
  `response_to_reviewers.pdf` → Author's Response；`main_highlighted.pdf` → Highlighted PDF；
  `main.pdf` + `latex_source_files_submission.zip` → Main Manuscript（PDF / LaTeX）。
- ☑ **GitHub 同步**：v11 已提交并推送（`4d1036c`，tag `access-resubmission-v11`，远端已核）。`artifact-v1` 勿重锚。
- ☐ **单位口径确认**：IEEE Access 为 **SCIE 收录**，但**最新中科院分区为 4 区**（2025 版；2024 版曾 3 区）、非 CCF 推荐期刊 ⇒ 若单位硬卡"中科院 3 区/CCF B"，请先与单位确认是否认可。

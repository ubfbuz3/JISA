# JISA 投稿前 Checklist

逐项核对；每项标 ☑（已满足）/ ☐（待办）。配套脚本：`reproduce.sh`、`verify_artifact.sh`、
`04_绘图与分析/analysis/make_manifests.py`。Zenodo 步骤见 `ZENODO_GUIDE.md`。

---

## A. Zenodo DOI（永久可引用归档）
- ☐ 提交 `.zenodo.json` 到仓库（**已完成**，位于仓库根目录）。
- ☐ 按 `ZENODO_GUIDE.md` 第 2–5 步：Zenodo 关联 GitHub → 将 `artifact-v1` 重锚到含
  `.zenodo.json` 的提交 → 在 GitHub 打 Release → Zenodo 自动派发 DOI
  `10.5281/zenodo.XXXXXXX`。
- ☐ 拿到真实 DOI 后，填入 §10 Data availability 的标记 `TODO` 行（**不要**先写占位 DOI）。
- ☐ 确认 LICENSE 与 `.zenodo.json` 中 `"license"` 一致（当前 `cc-by-4.0`，可在发布前改）。

---

## B. Cover letter 要点（投稿信，写给 JISA 编辑）
按"实证方法学刻画"而非"新工具/新防御"来定位，避免被当成 tool paper 误判。

1. **稿件类型**：Full research paper。
2. **核心贡献定位**：对"对象级授权（BOLA/BFLA）oracle 问题"中变形测试的**边界**做
   **实证方法学刻画**——不是提出新工具或新防御。三点发现：
   - F1 时序可达性（带外授权被误报为 proven violation / false proof）；
   - F2 oracle 可容许性（修好 oracle 后 MR 步骤不再提供额外裁决信息，Lemma 1）；
   - F3 度量分辨率（reported specificity 未以可达≡授权为条件，分母输入级、可被稀释）。
3. **诚实的范围声明**（务必写清，防 reviewer 误解）：
   - 结论只覆盖**reachability-gated authorization relations examined here**，不泛化到
     变形测试整体；
   - 实例化的是 **2 条 MR × 跨 3 厂商**（Gitea 1.22.6 / Gogs 0.14.3 / GitLab 17.11.7）；
   - 阳性对照是**受控研究靶机**（controlled research artefact），**不是**生产 Gitea，
     不声称发现 Gitea 真实 CVE。
4. **统计措辞**：文中只给**描述性点估计**，没有做 non-inferiority / domination 声明，
   也没有以 sensitivity/specificity 的推断统计含义使用这些词——投稿信可点明这一点，
   提前消解误解。
5. **可复现性卖点**：公开 artifact（GitHub tag `artifact-v1` + Zenodo DOI），**正文无任何
   手敲数字**，全部由 `compute_all.py` 重算；PDF 字节可复现；一键自检脚本
   `verify_artifact.sh` 校验每个原始记录与字节可复现产物的 SHA-256。
6. **期刊契合**：点明贴合 *Journal of Information Security and Applications* 的范围
   （信息安全的应用、Web 安全 oracle 问题、实证安全方法学）。
7. **政策声明**：生成式 AI 使用声明已写入论文 §10（Claude 仅用于文献核对、分析脚本开发、
   语言润色，所有计算由作者独立复核）——如期刊有 cover-letter AI 声明栏一并勾选。
8. **利益与资助**：无竞争利益、无基金资助（论文 §10 已声明）。

---

## C. Data Availability 精确化（直接替换 §10 对应段落）
当前措辞已合格；下方为**更精确**版本，按数据集点名列明，并预留 Zenodo DOI 行。
将 `10_declarations.tex` 的 Data availability 段替换为：

```latex
\subsection*{Data availability}

The raw records of the studies reported here are publicly available under the
version-pinned snapshot \texttt{artifact-v1} of the companion repository
\url{https://github.com/ubfbuz3/JISA} (re-anchored to the submission commit;
a byte-for-byte identical copy is archived at Zenodo,
DOI:~\texttt{10.5281/zenodo.XXXXXXX})%  TODO: replace with the real DOI after minting
:
(i)~the scenario/configuration study
(\texttt{experiments/results/raw\_matrix.jsonl},
\texttt{ablation\_direct*.json}, \texttt{alt\_matrix.jsonl});
(ii)~the real-system cell study across Gitea~1.22.6, Gogs~0.14.3 and
GitLab~17.11.7 (\texttt{experiments/real\_system/results/*.json});
(iii)~the execution of the published relations on the native engine
(\texttt{experiments/native\_engine/results/*.json});
(iv)~the seeded positive control (\texttt{seeded.json}).
The analysis pipeline \texttt{04\_绘图与分析/analysis/*.py} recomputes every number,
table and figure in this paper from those records; running \texttt{bash reproduce.sh}
regenerates all outputs and the PDF, and \texttt{bash verify\_artifact.sh} asserts the
SHA-256 integrity of every raw record and byte-reproducible output. The manuscript
\LaTeX{} source ships in the same repository.
```

> 拿到 DOI 前，保留上面注释掉的 `TODO` 行；派发后把 `10.5281/zenodo.XXXXXXX` 换成真值并删注释。

---

## D. `reproduce.sh` 干净环境一命令自检（已实现）
新增 `verify_artifact.sh`，由 `reproduce.sh` 委托。三种模式：

| 命令 | 作用 |
|---|---|
| `bash verify_artifact.sh` 或 `bash reproduce.sh check` | **默认/干净环境自检**：① 工具链就绪（Python + svglib/reportlab/matplotlib/pandas、pdflatex、bibtex；Docker 非必需会注明）；② 12 个原始记录 SHA-256 与 `provenance/RAW_RECORDS_SHA256.json` 一致；③ 10 个字节可复现产物（全部数字 `.tex`、`metrics.json`、两张矢量图）与 `provenance/OUTPUTS_SHA256.json` 一致；④ 报告 git 工作树是否干净。 |
| `bash verify_artifact.sh repro` | **强证明**：用 `git archive HEAD` 抽出已提交树到临时副本，重跑整套分析管线，比对重生成产物与清单是否**逐字节一致**；临时副本用完即删，**不污染工作树**。 |
| `bash verify_artifact.sh gen-manifest` | 在**合法**更新原始记录或生成脚本后，重算两个 SHA-256 清单并提交（勿在无关改动时随意重跑）。 |

- ☐ 投稿前在干净环境跑一次 `bash verify_artifact.sh`，确认输出 `RESULT: PASS`。
- ☐ 如 `repro` 报 drift：先用 `gen-manifest` 仅在"有意且原始记录已同步更新"时刷新清单；
  否则说明有非确定性 bug，需先修 `compute_all.py`。
- ☐ 两个清单文件（`provenance/RAW_RECORDS_SHA256.json`、`OUTPUTS_SHA256.json`）与
  `make_manifests.py`、`verify_artifact.sh` 一并提交，使 `repro` 在任意克隆上可复现。

---

## E. 通用投稿前核对（排版/合规）
- ☐ 页数：目标 11–15 页；当前 `cas-dc` 双栏约 13 页（`build.sh` 末行报告页数）。
- ☐ 摘要词数 ≤ 250（当前 250；统计须先展开 `\Res*` 宏再计，脚本在 `AppData/Local/Temp/count_abstract.py`）。
- ☐ 0 undefined references / citations / control sequences（`build.sh` 第 4 步校验）。
- ☐ 浮动体未放置、参考文献未解析告警为 0。
- ☐ overfull hbox：仅 1 处 `\maketitle` 123pt（良性，可接受）。
- ☐ 参考文献真实可溯源、无手敲（`refs.bib` 由 `normalize_bib.py` 规范化，字段值无 CJK）。
- ☐ 图表全部矢量、无 AI 生成像素；两张矢量图字节可复现（已验证）。
- ☐ 标题/摘要主张只覆盖 reachability-gated relations，不泛化（红线 ⑦）。
- ☐ 撤回清单红线全部遵守（无 sensitivity/specificity 声明、无"机制非冗余"、无
  "strictly dominates"、"自省面可读"带特权视点、无 "crawl-time aware" / "responsible variable" 措辞）。
- ☐ 单位硬要求 SCI：主投 JISA（Elsevier，SCIE，免 APC）；备选 Cybersecurity 备份稿待 JISA 后切换。

---

## F. 待用户决策 / 后续
- ☐ **GitHub 同步时机**：本次新增文件先本地提交；推送需在用户发话后执行，推送后**重锚 `artifact-v1`**（见 A 步）。
- ☐ Zenodo DOI 派发（A 步）与 Data availability 回填（C 步）。
- ☐ Cybersecurity 备份稿模板切换（投 JISA 后）。

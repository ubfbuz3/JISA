# BibTeX 规范化审计

- 输入：`01_文献调研\for_codex\references.bib`（39 条，来源 OpenAlex / Undermind，带 DOI）
- 输出：`03_论文撰写\paper\refs.bib`
- 修正类型：pages/volume 字段搬家、`and and` 去重、期刊条目类型纠正、年份以 DOI 为准、venue 名内嵌年份覆盖
- **未做**：补全缺失卷期、猜测页码、改写标题或作者
- **移出**：原 `note` 字段中的溯源标签（source / cited-by / tag / citekey）以及修正说明，**不写进 refs.bib**——它们不是书目信息，且含中文字符
  （BibTeX 会原样写进 .bbl，pdflatex 遇 CJK 直接 Fatal error）。
  溯源内容保留在本文件末尾，修正说明保留在本表中。

| citekey | 修正 |
|---|---|
| `Dharmaadi2025BACFuzz` | fix(type): @inproceedings→@article（venue 为期刊）；skip(year): arXiv DOI（10.48550/arxiv.2507.15984）中的 2507 是编号非年份，保留原 year=2025 |
| `Liu2025BACScan` | fix(author): 去除重复 and |
| `Liu2025MOCGuard` | fix(pages): 从 booktitle 拆出 pages=903-919 |
| `Shi2025Facilitating` | fix(author): 去除重复 and；fix(pages): 从 journal 拆出 pages=10683-10698 |
| `Feng2025JAuthGuard` | fix(pages): 从 booktitle 拆出 pages=3102-3107 |
| `Schlaubitz2025A` | fix(pages): 从 booktitle 拆出 pages=425-436 |
| `Chaleshtari2022Metamorphic` | fix(pages): 从 journal 拆出 pages=3430-3471；fix(year): 2022→2023（以 DOI 为准；原记录年份 2022） |
| `Mai2019Metamorphic` | fix(pages): 从 booktitle 拆出 pages=186-197；fix(year): 2019→2020（venue 名内嵌年份；原记录年份 2019） |
| `Atlidakis2019RESTler` | fix(pages): 从 booktitle 拆出 pages=748-758 |
| `Sun2025LLM` | fix(pages): 从 booktitle 拆出 pages=2078-2086 |
| `Wang2024A` | fix(type): @inproceedings→@article（venue 为期刊）；skip(year): arXiv DOI（10.48550/arxiv.2403.15723）中的 2403 是编号非年份，保留原 year=2024 |
| `Wen2024Enchanting` | fix(author): 去除重复 and；fix(pages): 从 booktitle 拆出 pages=302-328；skip(year): arXiv DOI（10.48550/arxiv.2404.00762）中的 2404 是编号非年份，保留原 year=2024 |
| `Uddin2026Automated` | fix(author): 去除重复 and；fix(pages): 从 booktitle 拆出 pages=41-50 |
| `Wang2025Large` | fix(author): 去除重复 and；fix(type): @inproceedings→@article（venue 为期刊） |
| `Wang2026Measuring` | fix(pages): 从 booktitle 拆出 pages=3146-3157 |
| `LeCong2025Can` | fix(pages): 从 booktitle 拆出 pages=21991-22014；skip(year): arXiv DOI（10.48550/arxiv.2503.04779）中的 2503 是编号非年份，保留原 year=2025 |
| `Croft2023Data` | fix(pages): 从 booktitle 拆出 pages=121-133 |
| `Berger2020Static` | fix(pages): 从 booktitle 拆出 pages=187-197 |
| `Zhang2024Extracting` | fix(type): @inproceedings→@article（venue 为期刊）；skip(year): arXiv DOI（10.48550/arxiv.2411.11380）中的 2411 是编号非年份，保留原 year=2024 |
| `Li2026Detecting` | fix(pages): 从 booktitle 拆出 pages=1747-1765 |
| `Chehade2025Forbidden` | fix(pages): 从 booktitle 拆出 pages=3218-3235 |

## 移出的溯源标签（原 note 字段）

| citekey | 原 note |
|---|---|
| `Wu2026Rethinking` | source: OpenAlex; cited-by: 0; tag: API-越权; citekey: - |
| `Filho2025Automated` | source: OpenAlex; cited-by: 6; tag: API-越权; citekey: - |
| `Sahin2026Enhancing` | source: OpenAlex; cited-by: 0; tag: API-模糊测试; citekey: - |
| `Arcuri2024Advanced` | source: OpenAlex; cited-by: 17; tag: API-模糊测试; citekey: - |
| `Seran2025Handling` | source: OpenAlex; cited-by: 2; tag: API-模糊测试; citekey: - |
| `Lu2024GRACE` | source: OpenAlex; cited-by: 171; tag: LLM-检测; citekey: - |
| `Yang2024DLAP` | source: OpenAlex; cited-by: 38; tag: LLM-检测; citekey: - |
| `Mechri2024SecureQwen` | source: OpenAlex; cited-by: 27; tag: LLM-检测; citekey: - |
| `Mao2025Towards` | source: OpenAlex; cited-by: 17; tag: LLM-检测; citekey: - |
| `Yin2024Multitask` | source: OpenAlex; cited-by: 68; tag: LLM-评测; citekey: - |
| `Senanayake2024Defendroid` | source: OpenAlex; cited-by: 22; tag: JISA-本体; citekey: - |
| `Liu2024Enhancing` | source: OpenAlex; cited-by: 10; tag: JISA-本体; citekey: - |
| `Guo2022HyVulDect` | source: OpenAlex; cited-by: 40; tag: 经典-GNN; citekey: - |
| `Ehrenberg2024Python` | source: OpenAlex; cited-by: 15; tag: 经典-NER; citekey: - |
| `Fu2023AIBugHunter` | source: OpenAlex; cited-by: 66; tag: 经典-工具; citekey: - |
| `Huang2024Detecting` | source: Undermind; cited-by: 15; tag: API-越权; citekey: Hua24 |
| `Dharmaadi2025BACFuzz` | source: Undermind; cited-by: 3; tag: API-越权; citekey: Dha25 |
| `Liu2025BACScan` | source: Undermind; cited-by: 5; tag: API-越权; citekey: Liu25b |
| `Liu2025MOCGuard` | source: Undermind; cited-by: 10; tag: API-越权; citekey: Liu25e |
| `Shi2025Facilitating` | source: Undermind; cited-by: 1; tag: API-越权; citekey: Shi25 |
| `Feng2025JAuthGuard` | source: Undermind; cited-by: 1; tag: API-越权; citekey: Fen25 |
| `Schlaubitz2025A` | source: Undermind; cited-by: 2; tag: API-越权; citekey: Sch25 |
| `Chaleshtari2022Metamorphic` | source: Undermind; cited-by: 37; tag: Oracle-理论; citekey: Cha22 |
| `Mai2019Metamorphic` | source: Undermind; cited-by: 29; tag: Oracle-理论; citekey: Mai19 |
| `Atlidakis2019RESTler` | source: Undermind; cited-by: 322; tag: API-模糊测试; citekey: Atl19 |
| `Sun2025LLM` | source: Undermind; cited-by: 0; tag: LLM-越权; citekey: Sun25b |
| `Wang2024A` | source: Undermind; cited-by: 4; tag: LLM-越权; citekey: Wan24b |
| `Wen2024Enchanting` | source: Undermind; cited-by: 131; tag: LLM-规格; citekey: Wen24 |
| `Uddin2026Automated` | source: Undermind; cited-by: 0; tag: LLM-越权; citekey: Udd26 |
| `Wang2025Large` | source: Undermind; cited-by: 4; tag: LLM-越权; citekey: Wan25d |
| `Wang2026Measuring` | source: Undermind; cited-by: 0; tag: LLM-评测; citekey: Wan26 |
| `LeCong2025Can` | source: Undermind; cited-by: 35; tag: LLM-评测; citekey: Lec25 |
| `Croft2023Data` | source: Undermind; cited-by: 209; tag: 数据集-质量; citekey: Cro23 |
| `Le2021Automated` | source: Undermind; cited-by: 11; tag: 策略推断; citekey: Le21 |
| `Berger2020Static` | source: Undermind; cited-by: 3; tag: 策略推断; citekey: Ber20 |
| `Zhang2024Extracting` | source: Undermind; cited-by: 1; tag: 策略推断; citekey: Zha24b |
| `Li2026Detecting` | source: Undermind; cited-by: 2; tag: Agentic分析; citekey: Li26g |
| `Chehade2025Forbidden` | source: Undermind; cited-by: 6; tag: API-越权; citekey: Che25c |
| `Zuo2017AUTHSCOPE` | source: Undermind; cited-by: 63; tag: 经典-越权; citekey: Zuo17 |

## 手工补充条目（非 DOI 来源，已逐条标注 URL 与核验日期）

以下条目不来自 `references.bib`，是**标准/网页资源**，无法用 DOI 标识；按 Elsevier 惯例以 `@misc` + `url` + `note` 形式引用。除此之外**没有**任何手工添加的学术文献——学术文献一律来自 DOI 记录。

- `OWASP2023API1`

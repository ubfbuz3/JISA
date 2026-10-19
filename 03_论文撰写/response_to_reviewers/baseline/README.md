# 高亮差分基线：Access-2026-49387 初投稿版

这两个文件是 IEEE Access 稿件 **Access-2026-49387** 的实际初投稿版本，用作
`highlight_diff.py` 生成高亮稿的**唯一基线**。

## 来源与鉴定

编辑部决定信日期为 **2026-10-18**。Git 历史里，该日期之前的最后一个提交是：

```
157edec  2026-09-28 19:30  Guide: explain the "select main file" step ...
```

其父提交 `bc3752e`（2026-09-28 19:22）中的 `main.pdf` 与 `157edec` 中的
**逐字节相同**（sha256 均为 `d641e6da…`），说明 09-28 当天论文内容已稳定，
二者任选其一都是同一版本。

| 文件 | 来源 | SHA-256 | 大小 |
|---|---|---|---|
| `submitted_main.pdf` | `git show 157edec:03_论文撰写/paper/main.pdf` | `d641e6dad6899658385f5eb8aac008069ee5ac83ef4233d29a554d780c3d440c` | 499,902 B |
| `submitted_latex_source_files.zip` | `git show 157edec:03_论文撰写/paper/latex_source_files_submission.zip` | `98c765fc471687a7116562f30fe30bfde7fc001bbfa4c337200d482ec2066323` | 1,135,398 B（73 成员，完整性 OK） |

**16 页**，旧标题 *Limits of Metamorphic Testing for Object-Level Authorization:
Temporal Reachability, Oracle Admissibility, and Measurement Limits*。

## 为什么不是 89f3f96

早前的高亮稿误用 `89f3f96` 作基线。该提交是 **2026-10-19 02:29** 的
"Temporal experiment, second product: GitLab CE 17.11.7"，即**拒稿后的返修提交**，
已包含本轮新增实验。逐词比对证实它含有初投稿版没有的内容：
`GitLab CE 17.11.7`、`Gitea 1.20.5`、`1.20.6`、`recrawl`、`M0`、8 个转移事件等。
用它做差分会**漏标这些新增工作本身**。

## 尚未独立确认的部分

- 未能从 Author Portal 直接下载已提交文件核对 SHA-256（无访问凭据）。
  本基线的鉴定依据是「决定信日期 + 投稿前最后提交 + 16 页 + 旧标题」四项一致，
  以及两个相邻提交 PDF 逐字节相同。
- 若 Portal 上的版本与此不同（例如上传后又微调），应以 Portal 版本为准重新生成高亮。

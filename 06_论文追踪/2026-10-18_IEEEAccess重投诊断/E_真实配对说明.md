# E 包：真实 vulnerable / fixed 配对

> 目标：补上"当真存在授权缺陷时，同一套 E/Y 真值能不能给出**真阳性**"这一侧。
> 产物：`experiments/real_system/run_cve_pair.py`、`results/cve_pair.json`；
> 数字：`04_绘图与分析/results/cve_pair_numbers.tex`、`cve_pair_table.tex`；
> 正文：§V-D "A publicly fixed defect"（Table `tab:cvepair`）。

## 1. 选定对象与出处

| 项 | 值 |
|---|---|
| 易受影响版本 | Gitea **1.20.5** |
| 修复版本 | Gitea **1.20.6**（2023-11-27 发布） |
| 修复条目 | `SECURITY: Fix comment permissions`（#28213，回移 #28216） |
| 同缺陷的 CVE | **CVE-2023-49946**（Forgejo < 1.20.5-1；NVD: CWE-732） |
| 缺陷形态 | 只校验**路径**上的仓库权限，未校验**对象**（comment id）属于该仓库 |

出处（均已实际抓取核对，非记忆）：

- Gitea 1.21.1/1.20.6 发布说明：`SECURITY Fix comment permissions (#28213) (#28216)`；
  博客原文："it must also be checked that the ID of the given comment belongs to the
  given repo as you can otherwise retrieve content you are not supposed to see."
- 补丁 <https://github.com/go-gitea/gitea/pull/28213.diff>：`GetIssueComment` 早就有
  `comment.Issue.RepoID != ctx.Repo.Repository.ID`；**真正缺检查的是
  `editIssueComment` / `deleteIssueComment`**（1.20.5 只有
  `ctx.Doer.ID != comment.PosterID && !ctx.Repo.IsAdmin()`），以及
  `GetIssueCommentReactions` 等读接口。
- 二进制：<https://dl.gitea.com/gitea/1.20.5/>、`.../1.20.6/`；
  sha256 与官方 `.sha256` **逐字节核对通过**
  （1.20.5 `40fb4f7a8f13…`，1.20.6 `dc0f97256de3…`）。

## 2. 一次失败的假设（留痕）

最初按 CVE 描述猜"读评论"越权：`GET /repos/bob/pub/issues/comments/{alice 的 id}`。
**1.20.5 实测返回 404**——查源码才确认该读接口的 `RepoID` 检查早已存在。
⇒ 改为**写**路径（编辑评论），一次成功。这条留痕是为了防止后续把"读接口 404"
误当成修复证据。

## 3. 实验与结果

每个版本一个**全新实例**（migrate + 三个用户 + 建库全程自动化），拓扑：
alice 私有仓库 `alice/secret`（含一条 issue 评论）；bob 公开仓库 `bob/pub`。

| 探针 | 1.20.5 | 1.20.6 |
|---|---|---|
| bob PATCH **自己的**评论（有权对照） | 200 | 200 |
| bob PATCH `/repos/alice/secret/...`（正确路径） | 404 | 404 |
| **bob PATCH `/repos/bob/pub/.../{alice 的 id}`（主探针）** | **200，正文被改** | **404，正文不变** |
| carol 借 bob 的路径改 alice 的评论 | 403 | 404 |
| 匿名 | 401 | 401 |
| 不存在的 id | 404 | 404 |
| alice 复读（状态真值） | `TAMPERED-BY-BOB` | 原文 |
| alice 恢复原文 | 成功 | 成功 |

- **Y 不看状态码**：由 alice 复读正文是否变成 bob 的标记决定——与 `write_path.py` 同口径。
- **E 来自台账**：`PolicyModel` 中 bob 对 `alice/secret` 的 `write` 无任何授予通道 ⇒ deny。
- 判定：1.20.5 = `true_positive`；1.20.6 = `no_alarm`。
  合计 **TP 1 / 假证明 0 / 修复版告警 0**；每版 5 条对照（共 10 条）全部符合预期；恢复 2/2。

## 4. 这条证据能主张什么、不能主张什么

**能**：E/Y 闸门在真缺陷上会给出正确主张，并在厂商修复后停止主张——它不是只会
压假警报的装置。这是对"闸门"的阳性对照。

**不能**：
- 不能主张"我们能发现这类缺陷"：id 是给定的，缺陷是公开且已修复的，这不是发现；
- 不能主张总体有效性：1 个缺陷、1 种形态（对象 vs 路径归属）、1 条产品线；
- 不能替代主实验的样本量论证（那部分仍靠 576 条矩阵 + 三系统）。

## 5. 复现

```bash
cd experiments/real_system
python run_cve_pair.py                 # 两个版本都跑；--version 1.20.5 单跑
python ../../04_绘图与分析/analysis/ingest_cve_pair.py
```
`ingest_cve_pair.py` 内置**对照闸门**：任一对照探针偏离预期即非零退出、拒绝生成数字
（宁可构建失败，也不把偏离当结果发出去）。

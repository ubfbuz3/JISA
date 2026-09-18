# 真实系统对照实验台（Gitea）

> 对应第七轮追问判决后的**选项 B**：在真实第三方系统上做 `MR` vs `直接请求` 对照。
> 上游背景见 `../../02_Idea与架构/Idea苏格拉底追问与判断.md` 与
> `../../refine-logs/EXPERIMENT_RESULTS.md` §Block 9。

## 为什么是 Gitea

本机 Docker 守护进程未运行（`docker version` 报 `dockerDesktopLinuxEngine` 管道不存在），
且 Docker Desktop 会拉起常驻进程树，与本项目「进程树会被回收」的约束冲突；
PHP 也未安装（Nextcloud / Joomla 出局）；Maven 未安装（EvoMaster / MST-wi 原生引擎暂不可跑）。
**Gitea 官方提供单文件绿色二进制（含 sqlite 绑定），`gitea web` 即起服务**，
是这台机器上唯一可靠的「真实第三方系统」路径。

## 忠实性依据：谓词按 MST-wi 原文定义实例化

MST-wi 论文（§4.4 与 TABLE 2）对关键谓词的定义是：

| 谓词 | 原文定义 |
|---|---|
| `cannotReachThroughGUI(u, URL)` | "Returns true if a URL cannot be reached by the given user by **exploring the user interface** of the system (e.g., by traversing anchors)." |
| `userCanRetrieveContent(u, out)` | "Returns true if the output data has **ever been received** in response to any of the input sequences executed by the given user **during data collection**." |

原文并给出了这两条谓词的设计意图：

> "if the system does not provide a URL to a user through its GUI, then she should not access the URL.
> Also, **to avoid false alarms**, the user who cannot access the URL from the GUI … should not be a
> supervisor with access to all the resources of the other user."

⇒ 两个谓词都是相对**采集期爬取记录**定义的，**不是**相对系统的授权状态。
⇒ 因此忠实实例化必须是**三阶段**：采集 → 授权变更 → 执行 MR。
（本实验的第一版把「API 完整枚举」当作 GUI 模型，那是**实时且完备**的读法，
对 MST-wi 不公平，已重写。这一自纠记录在 `../../.workbuddy/memory/` 的日志里。）

## 三阶段流程

```
A 基线拓扑      用户/组织/团队/仓库 + 一条 in-band 共享（框架自己的凭证所建）
B 采集爬取      GUI 等价爬取（自己仓库列表 / 组织仓库列表 / 搜索页），逐页跟随分页
C 授权变更      6 项**带外**变更，全部由**非框架**凭证执行（管理员 root / 组织拥有者 dave）
D 变更后爬取    再爬一次（供 GUI 模型的 live 读法）
E MR 执行       实例化 changeCredentials 家族；对 4+2 种判定器统计告警与假确证
F M1/M2/M3      端点普查 / 视点可读性 / 自省面保真度
G 授权通道定性  有效访问矩阵逐格定性，算带外占比
```

## 两种 GUI 模型读法（结论必须带这个条件）

| 读法 | 含义 | 来源 |
|---|---|---|
| **snapshot** | GUI 模型取自**采集期**爬取记录 | 原文 `userCanRetrieveContent` 的 "during data collection" 措辞支持 |
| **live** | 执行 MR 时**重新爬取** | 保守读法 |

**失效只在 snapshot 读法下出现**，这一点必须与结论一起声明。

## 复现

```bash
cd experiments/real_system
PY=<python-with-openpyxl-venv>/python.exe
BOLA_LAB_DIR="C:/Users/Administrator/WorkBuddy/gitea_lab/inst_demo" \
  PYTHONIOENCODING=utf-8 "$PY" run_real.py     # 约 30 秒，内含「起服务→等就绪→采集→关服务」闭环
PYTHONIOENCODING=utf-8 "$PY" analyze_real.py   # 生成 results/REAL_SYSTEM_RESULTS.md
```

- `BOLA_LAB_DIR` 指向一个**全新目录**即可得到干净实例；**不删除任何旧数据**。
- 拓扑构造是**幂等的**（已存在则跳过），同一实例上重复运行安全。
- 无需 Docker；Gitea 版本钉死在 `gitea_lab.py:GITEA_VERSION = 1.22.6`。

## 文件

| 文件 | 作用 |
|---|---|
| `gitea_lab.py` | 实验台生命周期（配置、迁移、起停服务）与 HTTP 客户端 |
| `run_real.py` | 三阶段主实验，产出 `results/real_system.json` |
| `analyze_real.py` | 折表，产出 `results/REAL_SYSTEM_RESULTS.md` |
| `bin/gitea.exe` | Gitea 1.22.6（Windows amd64，约 199 MB） |

## ⚠️ 诚实边界（写死在脚本 `meta.honesty_boundary` 里）

1. Gitea 是**正确**系统，不含对象级授权漏洞 ⇒ 本实验**只测假确证侧与发生率，不测检出率**。
   检出侧仍以合成 SUT（576 条记录）为准。
2. **不**声称「实验证明 MST-wi 失效」——未跑其原生引擎，只声称该 MR 家族的**结构**在真实系统上实例化后的行为。
3. 带外占比（96%）**依赖本实验构造的拓扑**，是设计参数，**不是野外发生率估计**；
   实例无关的部分只有 M1 的机制空间普查（读 Gitea 自带的 `swagger.v1.json`）。
4. 跨实现/跨厂商复核（如 Gogs / GitLab）**尚未做**。

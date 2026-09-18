# 源码级证据核查（MST-wi 实现）· 2026-09-18

> 目的：把稿件中关于"门控谓词锚在采集期快照"的论证，从**论文文字定义**升级为**实现源码**。
> 方法：实取公开仓库源码，`grep`/`read` 逐处定位，不依赖论文叙述。
> 原则：只写**能指回 file:line** 的结论；推测一律标 `（推测）`。

---

## 0. 重大更正：源码**是**公开的（我此前判断错了）

我此前记录"MST-wi 制品只有 PDF/XLSX，无源码"，据此把正文限制为纯结构断言。**这判断错误。**

| 仓库 | URL | 可达性 | 克隆点 |
|---|---|---|---|
| **MST 库** | `github.com/MetamorphicSecurityTesting/MST` | ✅ `git ls-remote` OK | `efa9915b65954640cd256e865e46b1ff4b1aad9b`（2025-10-31） |
| SMRL 站 | `github.com/SNTSVV/SMRL` | ✅ 可达，但**已是文档站**（只剩 `index.md`） | `dc31c47cdcd69feec08bafb1d508ecc25328dc07`（2023-04-04） |
| CWE 仓 | `github.com/MetamorphicSecurityTesting/CWE` | ✅ 可达 | `035b3fee8277a0af64bd7706a0f5404c401162e7` |

来源：论文 ref [45]（MST library）、ref [46]（SMRL editor）。本地克隆在 `C:\Users\Administrator\WorkBuddy\mst_engine\`。

**命名澄清**（两个名字都对，指不同东西）：
- **MST-wi** = 论文提出的**技法**名，"Metamorphic Security Testing for Web-interactions"（原文出现 188 次）
- **MST / SMRL** = 实现该技法的**库**名（仓库名）；SMRL = 其领域语言

## 1. 可运行的 MR 清单

`src-mrs-icst2020/smrl/mr/owasp/` 下 24 个类声明 `extends MR`，其中 `CheckTags` 是辅助类
⇒ **23 条可运行 MR**：

| 族 | 条数 | 标识 |
|---|---|---|
| **OTG_AUTHZ** | **11** | 001, 001b, 001b2, 002, 002a, 002b, 002c, 002d, 002e, 003, 004 |
| OTG_AUTHN | 3 | 001, 004, 010 |
| OTG_SESS | 4 | 003, 006, 007, 008 |
| OTG_INPVAL | 2 | 003, 004 |
| OTG_BUSLOGIC / CONFIG / CRYPST | 3 | 005 / 007 / 004 |

⚠️ **这 23 条 ≠ 论文说的 76 条**。76 条是**跨案例目录册**的全集；本库只含 **ICST 2020 的 MR 集**。
⚠️ **目录册与代码有版本漂移**：目录册（`catalog_text.txt`）含 22 个 `OTG_*` 标识、其中 **10 条 AUTHZ**；
但目录册的 `OTG_AUTHZ_001a` 在代码中不存在，代码的 `OTG_AUTHZ_001` / `001b2` 又不在目录册里。

★ **对硬条件 ⑦ 的意义**：**"≥4 条授权 MR"在"可得性"这一半上已满足**（11 条可运行）。
它仍未满足的是**"逐个实例化"**那一半（见 §4）。

## 2. 三条门控谓词：实现级定位

### 2.1 `cannotReachThroughGUI` —— 爬取期 URL 集合的成员测试

```
Operations.java:766/779            → MR.CURRENT.provider.cannotReachThroughGUI(...)
WebOperationsProvider.java:352     → impl.guiNotContain((Account) user, URL)      ← 唯一实现路径
WebProcessor.java:448              guiNotContain(Account user, String url)
WebProcessor.java:332              guiNotContain(Account user, WebInputCrawlJax input)
WebProcessor.java:414              retrieveURLsAcessedByUser(Account user)
```

`retrieveURLsAcessedByUser`（`:414-446`）的做法是：
遍历 `this.inputList`（**爬取期记录的输入**）→ 取 `i.containAccount(user)` 的那些 → 收集 `acc.getUrl()` 成 `HashSet<String>`。
`guiNotContain` 则判断**待测 URL 是否不在该集合中**。

⇒ **该谓词的全部语义 = "这个 URL 有没有出现在采集期记录的、属于该用户的 URL 集合里"**。
它**不发起任何请求**，不查询系统授权状态。**源码级确认**了稿件 boundary 2 的核心断言。

### 2.2 `userCanRetrieveContent` —— 磁盘上"输出仓库"的比对

```
Operations.java:463                 → MR.CURRENT.provider.userCanRetrieveContent(...)
WebOperationsProvider.java:467      userCanRetrieveContent(Object user, Object output)
WebOperationsProvider.java:126      loadOutputStore()
WebOperationsProvider.java:582      userCanRetrieve(String username, ArrayList<Object> outSequence)
```

- `:468` 先 `if(loadOutputStore()==false || output==null) return false;`
- `:133` `String outputStoreFolder = WebProcessor.getSysConfig().getOutputStore();` ⇒ 读**文件系统目录**
- `:582-601` 在 `this.outputStore.get(username)` 里逐条 `storedOutput.compare(newOutput)`

⇒ **比对对象是采集期落盘的输出**，不是活资源。

### 2.3 `isSupervisorOf` —— 静态配置里的角色关系

```
WebProcessor.java:3359              → sysConfig.isSupervisorOf(username1, username2)
SystemConfig.java:889               isSupervisorOf(String, String)
SystemConfig.java:398-424           supervisedUser ← JSON 配置文件
SystemConfig.java:112-119           SystemConfig(String configFile) 读 JSON
```

⇒ **静态主体属性谓词**，来自配置文件而非系统状态。

### 2.4 `changeCredential` —— 爬取输入的纯句法克隆

```
WebProcessor.java:488-507           _input.clone() + 替换 username/password 参数
```

⇒ 002 家族的构造步骤**不查活系统**。

## 3. ★ 源码级**新增**事实（现有稿件里没有，且比现有论证更硬）

### F1 冻结是**硬编码**的，不是偶发的
`WebProcessor.java:136` 声明 `HashMap<String,HashSet<String>> urlsAccessedByUsers`。
全仓仅 3 处引用：`:136` 声明、`:415` 读、`:443` 写。**没有 `.clear()`、没有失效、没有过期**。
`loadOutputStore()` 同样在 `:127-128` 提前返回 `//already loaded`。

⇒ 「GUI 可达性模型是采集期快照」不是采集时序的副作用，而是**实现里显式缓存、从不刷新**。
⇒ 稿件 boundary 2 的"时序失效"因此**更强**：即使在同一进程内后续发生了授权变更，缓存也不会更新。

### F2 缺数据时**默认判"不可达"** ⇒ 失败方向被写死为告警
`WebProcessor.java:448-455`：
```java
if (user==null || url == null) return true;      // → "cannot reach"
if ( inputList.isEmpty() )    return true;      // → "cannot reach"
```

⇒ **爬取数据缺失 ⇒ 谓词报"主体不可达" ⇒ MR 前置条件成立 ⇒ 发告警。**
这是一条**默认触发**（fail-open to alarm）的路径，**不是随机噪声**。
⇒ 它给稿件"失效方向是确定性的"这一主张提供了**代码级机理**——此前该主张只由合成实验支撑。

### F3 `isSupervisorOf` 在两账号相同时恒真 ⇒ 卫式语义须知
`SystemConfig.java:894-896`：`if(username1.trim().equals(username2.trim())) return true;`

⇒ 002 家族的卫式 `NOT isSupervisorOf(User(), action.getUser())` 在 **MR 用户 == 动作用户**时为假，
MR **不触发**（落到 `else` 直接 `expressionPass()`）。这条是**实现细节**，稿件若详述 002 家族必须写对。

## 4. 能否**真正运行**：现状与缺口

### 已具备（本轮建成）
| 项 | 位置 |
|---|---|
| JDK 8（pom 要求 `source/target 1.8`） | `mst_engine/tools/jdk8u504-b01`（Temurin 8u504） |
| Maven 3.9.9 | `mst_engine/tools/apache-maven-3.9.9` |
| 源码 | `mst_engine/MST` |
| 构建脚本 | `mst_engine/build_mst.sh`（**不经 shell 包装脚本**，直调 classworlds 启动类） |
| **构建结果** | ✅ **BUILD SUCCESS**（18 min 11 s，首次含依赖下载）⇒ `MST/target/MST-1.0.0-jar-with-dependencies.jar`（18 MB） |

### ★ F6 上游 pom **不把 MR 目录配为源码根** ⇒ 默认 jar 里没有 MR 类
`pom.xml` 只设 `<sourceDirectory>src</sourceDirectory>`，`build-helper` 仅追加 `src-ros`。
`src-mrs-icst2020`（**23 条 MR 所在目录**）**未被编译**。

实测：默认构建的 `MST-1.0.0-jar-with-dependencies.jar` 内含 `smrl/**` 共 **93 个类**，
**`OTG_AUTHZ_*` 命中 0**。⇒ 拿上游 jar 直接跑 MR 是跑不了的，必须先补齐源码根。

本地修正（**非上游内容**，已在 `pom.xml` 内注释标明）：在 `build-helper` 的 `<sources>` 里
追加 `<source>src-mrs-icst2020</source>`，重建后才得到含 23 条 MR 类的 jar：
```xml
<sources>
    <source>src-ros</source>
    <!-- 本地构建补充：ICST 2020 的 OWASP MR 集（含 11 条 OTG_AUTHZ） -->
    <source>src-mrs-icst2020</source>
</sources>
```
这条本身就是对"公开制品是否可直接复用"的一个实测答案：**不能**，需要一次构建层面的修补。

### 构建与加载实测（可复核）

| 项 | 上游默认 | 补齐源码根后 |
|---|---|---|
| 构建 | ✅ BUILD SUCCESS（18 min 11 s，含依赖下载） | ✅ BUILD SUCCESS（**1 min 46 s**，依赖已缓存） |
| jar 大小 | 17 993 082 B | 18 021 424 B |
| `smrl/**` 类数 | **93** | **117** |
| `OTG_AUTHZ_*` 类 | **0** | **11** |

加载验证（JDK 8 反射，`-cp` 必须是 **Windows 风格路径**，否则 Windows JVM 报 `ClassNotFoundException`）：
```
OK  smrl.mr.owasp.OTG_AUTHZ_001   super=MR
OK  smrl.mr.owasp.OTG_AUTHZ_002   super=MR
OK  smrl.mr.owasp.OTG_AUTHZ_002e  super=MR
OK  smrl.mr.owasp.OTG_AUTHZ_004   super=MR
OK  smrl.mr.crawljax.WebOperationsProvider  super=Object
OK  smrl.mr.language.MR                     super=Object
```
⇒ 引擎本体 + 11 条授权 MR **可构建、可加载**。这是 **class-loading 级**验证，仍**不是** MR 执行。

> 构建注意：本机 `cmd.exe` 被安全策略拦截，故不能用 `mvn.cmd`；Git Bash 下 Apache 的 POSIX `mvn`
> 脚本会把 POSIX 路径传给 Windows 版 JVM 而报 `找不到主类 Launcher`。
> **正解**：`java -classpath <maven>/boot/plexus-classworlds-2.8.0.jar -Dclassworlds.conf=<maven>/bin/m2.conf
> -Dmaven.home=<maven> -Dmaven.multiModuleProjectDirectory=<proj> org.codehaus.plexus.classworlds.launcher.Launcher ...`
> 且路径必须是 **Windows 风格**（`C:/...`）。

### 缺口（要真跑还缺这些）
1. **`./testData/` 不在仓库里**。样例 `ICSE2020DemoTest.java:65` 指向 `./testData/Jenkins/jenkinsSysConfigDEMO.json` —— 该目录未随仓库发布。
2. **需要被测系统**。样例用 **Jenkins**（`ICSE2020DemoTest`，注释：应检出 CVE-2018-1999004）与 **Joomla**（`JoomlaTest.java`）。
3. **需要浏览器 + Selenium**（`WebProcessor` 基于 Crawljax 3.6 + Selenium 3.141.59；配置含 `headless` 开关）。
4. **需要一次爬取**，以产出 `inputList` 与输出仓库目录 —— 这两个正是 §2 里谓词所读的产物。

⇒ 结论：**"跑引擎"是可行的，但需要一个自建 SUT + 自写 SysConfig + 一次爬取**。
这不是"下载即跑"，而是"按库的协议装配一套可运行环境"。

## 5. 对稿件的影响（诚实分级）

| 主张 | 升级前 | 升级后 | 等级 |
|---|---|---|---|
| 门控谓词锚在采集期记录 | 论文文字定义 | **实现源码 file:line** | **L2 源码级**（此前 L1 文献级） |
| 失效是时序的（快照 vs 可变授权） | 合成 + Gitea 实验 | **＋ 缓存从不失效（F1）** | L2 |
| 失效方向是确定性的 | 合成实验 | **＋ 缺数据默认判不可达（F2）** | L2 |
| 引擎在本系统上的运行时行为 | —（无） | —（**仍无**） | **L3 仍缺** |

⚠️ **必须守住的边界**：源码级证据**不等于运行级证据**。
第 7 节关于"未跑原生引擎"的限制**不能删**，只能改写为：
> "我们核查了实现源码；我们**未**在原生引擎上执行 MR。"

★ 若要把 L3 补上，最小可行路径：自建一个含 ≥3 账号、有对象级共享面的 Web 应用 →
写 `SysConfig` JSON → 跑一次 Crawljax 爬取 → 用 `ICSE2020DemoTest` 的 `MRBaseTest.test(provider, X.class)`
协议跑 §1 里的 11 条 `OTG_AUTHZ`。

## 6. 可复现命令

```bash
# 取源码（纯 ASCII 目录）
mkdir -p /c/Users/Administrator/WorkBuddy/mst_engine && cd $_
git clone --depth 1 https://github.com/MetamorphicSecurityTesting/MST MST
git clone --depth 1 https://github.com/SNTSVV/SMRL SMRL

# 工具链（便携版，不写注册表）
#   JDK 8:  https://api.adoptium.net/v3/binary/latest/8/ga/windows/x64/jdk/hotspot/normal/eclipse
#   Maven:  https://archive.apache.org/dist/maven/maven-3/3.9.9/binaries/apache-maven-3.9.9-bin.zip

# 构建（见 build_mst.sh）
bash /c/Users/Administrator/WorkBuddy/mst_engine/build_mst.sh
# 产物: MST/target/MST-1.0.0-jar-with-dependencies.jar

# 谓词定位
grep -rn "cannotReachThroughGUI" MST/src/
grep -rn "guiNotContain"          MST/src/
grep -rn "userCanRetrieveContent" MST/src/
```

# 原生引擎数据契约（逆向所得 · 每条带 file:line）

> 目的：在**不启动浏览器、不跑 Crawljax** 的前提下，让 MST-wi 的**原生引擎**执行 `OTG_AUTHZ_*`。
> 全部结论来自 `mst_engine/MST` @ `efa9915b` 的源码阅读（`src/` + `src-mrs-icst2020/`）。

## 0. 一句话结论

`WebOperationsProvider` **有三个构造器**，其中一个直接吃磁盘文件：

```java
public WebOperationsProvider(String inputFile, String outFile, String configFile)   // :91
```

⇒ **爬取记录可以从 JSON 加载**，不需要 Crawljax 现场爬。
唯一真正依赖 Selenium 的是 `Output(...)`（动作回放）。

## 1. 配置 `config.json` → `SystemConfig`

`SystemConfig` 用 Gson 逐键读取（`SystemConfig.java:125-440`），只认**存在的键**，缺省留空。

| 键 | 类型 | 作用 | 消费点 |
|---|---|---|---|
| `SUT` | string | 被测系统标识 | `getSUT()` :506 |
| `inputFile` | string | 爬取记录 JSON 路径 | `getInputFile()` :514 |
| `outputFile` | string | 输出文件路径 | `getOutputFile()` :522 |
| `outputStore` | string | **磁盘输出仓库目录** | `getOutputStore()` :530 |
| `loginParams` | array | 登录参数三元组，见下 | :209-235 |
| `supervisedUser` | object | `{监督者: [被监督者…]}` | :400-425 |
| `headless` | bool | 无头浏览器开关 | :427 |
| `errorSigns` | object | 错误页特征（class/script/attribute/id/title/content） | `WebOutputSequence.isError` :179 |

`loginParams` 元素（注意键名是 `loginURL`/`userParameter`/`passwordParameter`，**不是** `userParam`）：

```json
{ "loginURL": "http://127.0.0.1:3311/user/login",
  "userParameter": "user_name", "passwordParameter": "password" }
```

⇒ 三者**任一为空则整个 LoginParam 被丢弃**（`:229-233`）。

## 2. 爬取记录 `inputs.json` → `WebProcessor.loadInput`（`:584`）

顶层是**对象**：key = 该条输入的 DB id，value = **动作数组**。

```json
{
  "alice|acme/t1": [
    { "text":"Sign In", "id":"xpath ...", "element":"Element{...}",
      "eventType":"click", "currentURL":"http://host/",
      "elementURL":"http://host/user/login", "method":"post",
      "formInputs":[
        {"identification":{"value":"user_name"},"values":["alice"]},
        {"identification":{"value":"password"},"values":["LabPass123!"]}
      ] },
    { "eventType":"click", "currentURL":"http://host/",
      "elementURL":"http://host/acme/t1", "method":"get" }
  ]
}
```

要点（均有源码依据）：

1. `loadInput` 遍历顶层 key，每条 `>0` 长度才被收进 `inputList`（`:601-611`）。
2. `eventType` ∈ {`click`,`hover`} → `StandardAction`；其他值被 `Action.newAction` 丢弃（`Action.java:118`）。
3. `method` 只认枚举内值，否则回落 `"get"`（`StandardAction` JSON 构造器 :145-155）。
4. **`formInputs` 的结构是 `{"identification":{"value":<参数名>},"values":[<实际值>]}`**
   —— `containCredential` 比对 `identification.value`（:493-518），
   `getCredential` 从 `values[0]` 取实际账号密码（:579-605）。
   ⚠️ 只写 `value` 不写 `values` 会**认得出参数、取不到值**。
5. **登录动作必须 `method="post"` 且 `elementURL` 等于某个 `loginURL`**，
   否则 `WebProcessor.isLogin` 返回 false（`:2965-1989`），账号识别与 `changeCredential` 全部落空。
6. 首动作带凭证后，`identifyUsers` 会把**后续无凭证动作**继承为该用户（`WebInputCrawlJax:479-497`）。

## 3. 谓词实现（本工作要复核的对象）

| 谓词 | 实现链 |
|---|---|
| `cannotReachThroughGUI(u,url)` | `WebOperationsProvider:352` → `WebProcessor.guiNotContain(Account,String)`:448 |
| `cannotReachThroughGUI(u,input)` | `WebOperationsProvider:347` → `WebProcessor.guiNotContain(Account,input)`:331 |
| `userCanRetrieveContent(u,out)` | `WebOperationsProvider:467` → `loadOutputStore()`:130 + `userCanRetrieve` |
| `isSupervisorOf(u1,u2)` | `WebOperationsProvider:921` → `SystemConfig.isSupervisorOf`:889 |
| `changeCredentials` | `WebOperationsProvider:337` → `WebProcessor.changeCredential` → `WebInputCrawlJax.changeCredential`:283 |

**★ 核心事实**：`retrieveURLsAcessedByUser(user)`（`WebProcessor:414`）遍历的是
**`this.inputList`**（即**加载进来的爬取记录**），**不发起任何请求**。
⇒ 谓词语义 = "该 URL 是否出现在该用户在采集期记录里的 URL 集合中"。
⇒ 喂进合法格式的记录即可驱动真谓词，**这不是本实验的构造伪象，而是它本来的定义**。

两条已知实现事实（本项目其余部分引用）：
- **F1 缓存无失效**：`urlsAccessedByUsers`（`:136` 声明 / `:415` 读 / `:443` 写），无 `clear`。
- **F2 缺数据默认"不可达"**：`guiNotContain(Account,String)` 在 `inputList.isEmpty()` 时 `return true`（`:448-455`）。

## 4. 唯一必须替代的点：`Output(...)`

`WebOperationsProvider.Output(Input)`（`:699`）→ `outputCache` 未命中 → `impl.output(input)`
→ `WebProcessor.output`（`:612`）→ `loadDefaultDriver(input)` → **Selenium/Chrome**。

⇒ **本实验把 Selenium 换成直接 HTTP 请求（Basic Auth）**，其余一律原样。
- 这是**必须申报的替代**：观测通道变了，语义没变（同一用户、同一 URL、记录响应体）。
- 与 Block 10 的 `live` 读法用的是同一条观测通道（HTTP），因此与既有结果可比。
- `Output(Input,int)` 同样是父类实现，会回落 `Output(input)` ⇒ 一并覆盖。

## 5. 本实验**没有**做的事（诚实边界）

1. **没有跑 Crawljax**：输入记录由 Gitea 的真实可达性采集**按上述格式生成**，不是爬虫现场产出。
2. **没有跑浏览器**：观测通道是 HTTP（见 §4）。
3. **没有覆盖全部 11 条**：`OTG_AUTHZ_002` 家族需要 `changeCredentials`；其余家族按依赖分别记录"可执行/不可执行"，不可执行的**不伪报**。
4. **统计意义**：一次运行只说明**引擎能执行且裁决按上述机理产生**，不构成检出率/假确证率估计。

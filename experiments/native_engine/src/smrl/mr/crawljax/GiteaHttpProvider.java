package smrl.mr.crawljax;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;

import smrl.mr.language.Action;
import smrl.mr.language.Input;
import smrl.mr.language.Output;
import smrl.mr.language.SystemConfig;

/**
 * GiteaHttpProvider —— 让 MST-wi 原生引擎在**无浏览器**条件下执行。
 *
 * 设计原则（写死在代码里，避免日后被悄悄放宽）：
 *   1. 本类**只覆盖** Output(Input) 与 Output(Input,int) 两个方法。
 *      其余全部继承 WebOperationsProvider 的原样实现：
 *      loadInput / loadUsers / cannotReachThroughGUI / userCanRetrieveContent /
 *      isSupervisorOf / changeCredentials —— 即本工作要复核的那些谓词。
 *   2. 被替换的只有**观测通道**：Selenium 动作回放 → 直接 HTTP GET（Basic Auth）。
 *      语义不变：同一用户、同一 URL、记录响应体。
 *   3. 登录动作（method=post 且 URL 命中 loginURL）**不发请求**，
 *      统一记一个定值体，使其在跨用户比较中恒等、不参与判别。
 *
 * 放在 smrl.mr.crawljax 包内是**刻意的**：WebOperationsProvider 的
 * outputCache / impl 字段与 WebOutputCleaned 的字段都是包级可见。
 */
public class GiteaHttpProvider extends WebOperationsProvider {

    public static boolean TRACE = false;

    private static int httpCalls = 0;
    private static final int TIMEOUT_MS = 20000;
    private static final String LOGIN_PLACEHOLDER = "LOGIN_ACTION_PLACEHOLDER";

    public GiteaHttpProvider(String inputFile, String outFile, String configFile) {
        super(inputFile, outFile, configFile);
    }

    /**
     * 推荐入口：只吃 config.json，inputFile/outputFile 由 SystemConfig 提供。
     * 父类单参构造器会依次 loadInput / setOutputFile / loadUsers，
     * ⇒ 采集记录直接从磁盘加载，**不启动 Crawljax**。
     */
    public GiteaHttpProvider(String configFile) {
        super(configFile);
    }

    public static int httpCallCount() {
        return httpCalls;
    }

    public static void resetHttpCallCount() {
        httpCalls = 0;
    }

    // ------------------------------------------------------------------
    // 注入扩充后的输入列表（基输入 + 由引擎自身 changeCredential 派生出的输入）
    // ------------------------------------------------------------------
    private List<Input> augmentedInputs = null;

    public void setAugmentedInputs(List<Input> inputs) {
        this.augmentedInputs = inputs;
    }

    @SuppressWarnings("rawtypes")
    @Override
    public List load(String dataName) {
        if ("Input".equals(dataName) && augmentedInputs != null) {
            return augmentedInputs;
        }
        return super.load(dataName);
    }

    // ------------------------------------------------------------------
    // HTTP 观测
    // ------------------------------------------------------------------
    public static class HttpResult {
        public int status;
        public String body;
        public String finalUrl;
    }

    public static HttpResult httpGet(String url, Account user) {
        // 记忆缓存：键 = "username|url"。
        // 理由：父类按**输入对象同一性**缓存（outputCache），而 `changeCredentials`
        // 每次都在卫式里新建对象 ⇒ 同一 (用户,URL) 被反复抓取。
        // 在一次运行内被测系统不发生授权变更，故 (用户,URL) → 响应是函数关系。
        // ⚠️ 这是**观测通道内部**的优化，不改变任何谓词判定；须在正文申报。
        String uname = (user == null) ? "-" : String.valueOf(user.getUsername());
        String key = uname + "|" + url;
        HttpResult hit = MEMO.get(key);
        if (hit != null) {
            memoHits++;
            return hit;
        }
        HttpResult r = httpGetUncached(url, user);
        if (r.status != 0) {
            MEMO.put(key, r);
        }
        return r;
    }

    private static final java.util.HashMap<String, HttpResult> MEMO =
            new java.util.HashMap<String, HttpResult>();
    private static int memoHits = 0;

    public static int memoHitCount() {
        return memoHits;
    }

    private static HttpResult httpGetUncached(String url, Account user) {
        HttpResult r = new HttpResult();
        r.finalUrl = url;
        r.status = 0;
        r.body = "";
        if (url == null || url.trim().isEmpty()) {
            return r;
        }
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
            c.setInstanceFollowRedirects(false);
            c.setConnectTimeout(TIMEOUT_MS);
            c.setReadTimeout(TIMEOUT_MS);
            c.setRequestMethod("GET");
            c.setRequestProperty("Accept", "text/html,application/json,*/*");
            if (user != null
                    && user.getUsername() != null && !user.getUsername().isEmpty()) {
                String cred = user.getUsername() + ":"
                        + (user.getPassword() == null ? "" : user.getPassword());
                c.setRequestProperty("Authorization", "Basic "
                        + Base64.getEncoder().encodeToString(
                                cred.getBytes(StandardCharsets.UTF_8)));
            }
            r.status = c.getResponseCode();
            InputStream is = (r.status >= 400) ? c.getErrorStream() : c.getInputStream();
            r.body = readAll(is);
            String loc = c.getHeaderField("Location");
            if (loc != null && !loc.isEmpty()) {
                r.finalUrl = loc;
            }
            c.disconnect();
        } catch (Exception e) {
            r.status = 0;
            r.body = "HTTP_ERROR: " + e.getClass().getSimpleName() + ": " + e.getMessage();
        }
        httpCalls++;
        if (TRACE) {
            System.out.println("[http] " + r.status + " "
                    + (user == null ? "-" : user.getUsername()) + " " + url);
        }
        return r;
    }

    private static String readAll(InputStream is) {
        if (is == null) {
            return "";
        }
        try {
            ByteArrayOutputStream bos = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = is.read(buf)) > 0) {
                bos.write(buf, 0, n);
            }
            is.close();
            return new String(bos.toByteArray(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            return "";
        }
    }

    /**
     * 抽取可见文本，供 WebOutputCleaned 的 text 相似度分支使用。
     *
     * ⚠️ 必须与上游**逐字对齐**：上游的实时输出路径是
     *   WebProcessor.java:3033  Document doc = Jsoup.parse(page);
     *   WebProcessor.java:3169  out.text = doc.text();
     * 故此处同样用 Jsoup.parse(html).text()，而不用自写的正则——自写版本
     * 会构成一处不必要的偏离，可能改变 _compare 的 text 分支。
     */
    private static String stripTags(String html) {
        if (html == null) {
            return "";
        }
        try {
            return org.jsoup.Jsoup.parse(html).text();
        } catch (Throwable t) {
            // 仅在 jsoup 不可用时退化；正常路径不应走到这里
            return html.replaceAll("<[^>]+>", " ").replaceAll("\\s+", " ").trim();
        }
    }

    private static boolean isLoginAction(Action a) {
        if (a == null) {
            return false;
        }
        String m = a.getMethod();
        if (m == null || !"post".equalsIgnoreCase(m.trim())) {
            return false;
        }
        String u = a.getElementURL();
        if (u == null || u.isEmpty()) {
            return false;
        }
        SystemConfig sc = WebProcessor.getSysConfig();
        return sc != null && sc.isLoginURL(u);
    }

    // ------------------------------------------------------------------
    // 纯委托式计数器
    // ------------------------------------------------------------------
    // ⚠️ 这些覆盖**不改变任何判定**：全部 `return super.xxx(...)`。
    // 目的只是记录"谓词被调用了几次 / 其中几次为真"，是 instrumentation
    // 而不是 substitution。申报纪律：凡本文件出现 super 调用的方法，
    // 判定权在父类（即 MST-wi 原实现）。
    public static int nCrtgUrl = 0, nCrtgUrlTrue = 0;
    public static int nCrtgInput = 0, nCrtgInputTrue = 0;
    public static int nSupervisor = 0, nSupervisorTrue = 0;
    public static int nUcrc = 0, nUcrcTrue = 0;

    /**
     * 逐格证据：`"结果|用户|URL" -> 次数`。
     * 这是本实验最重要的一份原始记录 —— 它直接说明**真谓词**在哪些格上判了什么。
     */
    public static final java.util.LinkedHashMap<String, Integer> CRTG_CELLS =
            new java.util.LinkedHashMap<String, Integer>();
    private static final int CELL_CAP = 4000;

    private static void noteCell(Object user, String url, boolean res) {
        if (CRTG_CELLS.size() >= CELL_CAP) {
            return;
        }
        String who = (user == null) ? "-"
                : (user instanceof Account ? String.valueOf(((Account) user).getUsername())
                                           : String.valueOf(user));
        String k = (res ? "true" : "false") + "|" + who + "|" + url;
        Integer c = CRTG_CELLS.get(k);
        CRTG_CELLS.put(k, (c == null) ? 1 : c + 1);
    }

    @Override
    public boolean cannotReachThroughGUI(Object user, String url) {
        boolean r = super.cannotReachThroughGUI(user, url);
        nCrtgUrl++;
        if (r) {
            nCrtgUrlTrue++;
        }
        noteCell(user, url, r);
        return r;
    }

    @Override
    public boolean cannotReachThroughGUI(Object user, Input input) {
        boolean r = super.cannotReachThroughGUI(user, input);
        nCrtgInput++;
        if (r) {
            nCrtgInputTrue++;
        }
        if (input != null) {
            for (Action a : input.actions()) {
                noteCell(user, a.getUrl(), r);
            }
        }
        return r;
    }

    @Override
    public boolean isSupervisorOf(Object u1, Object u2) {
        boolean r = super.isSupervisorOf(u1, u2);
        nSupervisor++;
        if (r) {
            nSupervisorTrue++;
        }
        return r;
    }

    @Override
    public boolean userCanRetrieveContent(Object user, Object output) {
        boolean r = super.userCanRetrieveContent(user, output);
        nUcrc++;
        if (r) {
            nUcrcTrue++;
        }
        return r;
    }

    // ------------------------------------------------------------------
    // 唯一被替换的两个方法
    // ------------------------------------------------------------------
    @Override
    public Output Output(Input input) {
        if (input == null) {
            return null;
        }
        WebInputCrawlJax wi = (WebInputCrawlJax) input;
        if (outputCache.containsKey(wi)) {
            return outputCache.get(wi);
        }

        WebOutputSequence seq = new WebOutputSequence();

        // ---- 会话身份（关键） -------------------------------------------------
        // 原文引擎用 WebDriver **回放**输入：身份由登录动作确立，并延续到后续动作
        // （同一浏览器会话）。而 WebInputCrawlJax.changeCredential 只改写**带凭证
        // 的那个动作**（WebInputCrawlJax.java:325-329，见 containCredential 判断），
        // 后续点击动作的 user 字段仍是原用户。
        // 因此若按「每个动作自己的 user」取凭证，凭证替换后的输入会以**原身份**
        // 重新抓取 ⇒ 响应与源输入逐字相同 ⇒ 触发假告警（实测：主体自己仓库
        // bob/s1..s3 上也报出告警，即为此故）。
        // 故此处维护一个会话级身份：登录动作更新它，其余动作沿用它。
        Account session = null;
        for (Action a : wi.actions()) {
            WebOutputCleaned c = new WebOutputCleaned();
            if (isLoginAction(a)) {
                if (a.getUser() instanceof Account) {
                    session = (Account) a.getUser();
                }
                c.html = LOGIN_PLACEHOLDER;
                c.originalHtml = LOGIN_PLACEHOLDER;
                c.text = LOGIN_PLACEHOLDER;
                c.statusCode = 200;
                c.resultedUrl = a.getElementURL();
                c.realRequestedUrl = a.getElementURL();
            } else {
                String url = a.getElementURL();
                if (url == null || url.trim().isEmpty()) {
                    url = a.getUrl();
                }
                Account u = session;
                if (u == null && a.getUser() instanceof Account) {
                    u = (Account) a.getUser();
                }
                HttpResult r = httpGet(url, u);
                c.html = r.body;
                c.originalHtml = r.body;
                c.text = stripTags(r.body);
                c.statusCode = r.status;
                c.resultedUrl = r.finalUrl;
                c.realRequestedUrl = url;
            }
            seq.add(c, "", null);
        }

        outputCache.put(wi, seq);
        return seq;
    }

    @Override
    public Output Output(Input input, int pos) {
        Output full = Output(input);
        if (full == null) {
            return null;
        }
        ArrayList<Object> l = ((WebOutputSequence) full).getOutputSequence();
        if (l == null || l.isEmpty()) {
            return null;
        }
        int p = pos;
        if (p < 0) {
            p = 0;
        }
        if (p >= l.size()) {
            p = l.size() - 1;
        }
        WebOutputSequence res = new WebOutputSequence();
        res.add(l.get(p), "", null);
        return res;
    }
}

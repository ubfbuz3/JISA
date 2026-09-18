package smrl.mr.crawljax;

import java.io.FileReader;
import java.io.FileWriter;
import java.io.Writer;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;

import smrl.mr.language.Input;
import smrl.mr.language.MR;

/**
 * 在原生 MST-wi 引擎上执行 OTG_AUTHZ_* 家族。
 *
 * 用法：
 *   java -cp "<classes>;<jar>" smrl.mr.crawljax.RunAuthzMRs <config.json> <out.json> <pairing.json|-> [base|augmented]
 *
 * 为什么需要 pairing.json：
 *   `MR.run()` 的默认路径（`MR.extractCost_test == true`）把 Input 数据按
 *   `LEN / 160` 切分，每个分片只留 `chunksSize` 条（`MrDataDB.setSplit`）。
 *   因此若只有 4 条输入，分片几乎全空，`Input(1)/Input(2)` 拿不到可比较的一对，
 *   MR 体根本不会被执行（实测 count 全 0）。
 *
 *   解决办法不是改它的代码，而是**按它的分片粒度供给数据**：
 *   把输入列表组织成「[基输入, 该基输入经引擎自身 changeCredential 派生出的输入]」
 *   的两条一组，并让总数 ≥ 320 ⇒ chunksSize ≥ 2 ⇒ 每组恰好一个分片。
 *
 * ⚠️ 申报纪律：派生输入由**引擎自己的** `WebInputCrawlJax.changeCredential` 产生，
 *    不是我们手工构造的等价物。配对关系由驱动脚本给定并写进结果文件。
 */
public class RunAuthzMRs {

    private static final String[] AUTHZ = {
            "smrl.mr.owasp.OTG_AUTHZ_001",
            "smrl.mr.owasp.OTG_AUTHZ_001b",
            "smrl.mr.owasp.OTG_AUTHZ_001b2",
            "smrl.mr.owasp.OTG_AUTHZ_002",
            "smrl.mr.owasp.OTG_AUTHZ_002a",
            "smrl.mr.owasp.OTG_AUTHZ_002b",
            "smrl.mr.owasp.OTG_AUTHZ_002c",
            "smrl.mr.owasp.OTG_AUTHZ_002d",
            "smrl.mr.owasp.OTG_AUTHZ_002e",
            "smrl.mr.owasp.OTG_AUTHZ_003",
            "smrl.mr.owasp.OTG_AUTHZ_004",
    };

    public static void main(String[] args) throws Exception {
        if (args.length < 3) {
            System.err.println("usage: RunAuthzMRs <config.json> <out.json> <pairing.json|-> [base|augmented]");
            System.exit(2);
        }
        String configFile = args[0];
        String outJson = args[1];
        String pairingFile = args[2];
        String mode = args.length > 3 ? args[3].trim().toLowerCase() : "augmented";

        Gson gson = new GsonBuilder().setPrettyPrinting().create();
        Map<String, Object> report = new LinkedHashMap<String, Object>();
        report.put("mode", mode);
        report.put("config", configFile);
        report.put("pairing", pairingFile);

        // 1) 构造 provider（尚未注入扩充输入）
        GiteaHttpProvider provider = new GiteaHttpProvider(configFile);

        @SuppressWarnings("unchecked")
        List<Input> base = (List<Input>) provider.load("Input");
        if (base == null) {
            base = new ArrayList<Input>();
        }
        @SuppressWarnings("unchecked")
        List<Account> users = (List<Account>) provider.load("User");
        if (users == null) {
            users = new ArrayList<Account>();
        }
        Map<String, Account> byName = new LinkedHashMap<String, Account>();
        List<String> userNames = new ArrayList<String>();
        for (Account u : users) {
            byName.put(u.getUsername(), u);
            userNames.add(u.getUsername());
        }
        report.put("base_inputs", base.size());
        report.put("users", userNames);

        // 2) 读配对表
        Map<String, String> pairing = new LinkedHashMap<String, String>();
        if (!"-".equals(pairingFile)) {
            JsonObject po = gson.fromJson(new FileReader(pairingFile), JsonObject.class);
            if (po != null) {
                for (Map.Entry<String, JsonElement> e : po.entrySet()) {
                    pairing.put(e.getKey(), e.getValue().getAsString());
                }
            }
        }
        report.put("pairing_entries", pairing.size());

        // 3) 交错组织数据视图：[基, 派生], [基, 派生], ...
        List<Input> view = new ArrayList<Input>();
        List<Map<String, Object>> groups = new ArrayList<Map<String, Object>>();
        int derived = 0, failed = 0;
        if ("augmented".equals(mode)) {
            for (Input b : base) {
                String id = (b instanceof WebInputCrawlJax)
                        ? ((WebInputCrawlJax) b).getDBid() : null;
                view.add(b);
                Map<String, Object> g = new LinkedHashMap<String, Object>();
                g.put("base", id);
                String partner = (id != null) ? pairing.get(id) : null;
                g.put("partner", partner);
                Account pu = (partner == null) ? null : byName.get(partner);
                if (pu == null) {
                    g.put("derived", "no_partner");
                    groups.add(g);
                    continue;
                }
                try {
                    Input d = provider.changeCredentials(b, pu);
                    if (d != null && !d.equals(b)) {
                        view.add(d);
                        derived++;
                        g.put("derived", "ok");
                    } else {
                        failed++;
                        g.put("derived", "null_or_same");
                    }
                } catch (Throwable t) {
                    failed++;
                    // 记录**消息与首帧**而不是只有类名：这个 NPE 来自上游
                    // WebProcessor.changeCredential:496 的 userParam.isEmpty()，
                    // 仅凭类名无法定位。注意上游代码不得修改，只能在此诊断。
                    StringBuilder m = new StringBuilder(t.getClass().getSimpleName());
                    m.append(": ").append(t.getMessage());
                    StackTraceElement[] st = t.getStackTrace();
                    if (st != null && st.length > 0) {
                        m.append(" @ ").append(st[0].toString());
                    }
                    g.put("derived", m.toString());
                }
                groups.add(g);
            }
        } else {
            view.addAll(base);
        }
        report.put("derived_inputs", derived);
        report.put("derive_failed", failed);
        report.put("input_view_size", view.size());
        report.put("chunk_size_floor_div_160", view.size() / 160);
        report.put("groups_sample", groups.size() > 6 ? groups.subList(0, 6) : groups);

        provider.setAugmentedInputs(view);

        // 4) 逐条执行
        List<Map<String, Object>> rows = new ArrayList<Map<String, Object>>();
        for (String cn : AUTHZ) {
            Map<String, Object> row = new LinkedHashMap<String, Object>();
            row.put("mr", cn);
            try {
                Class.forName(cn);
            } catch (Throwable t) {
                row.put("status", "class_not_found");
                rows.add(row);
                continue;
            }
            int before = GiteaHttpProvider.httpCallCount();
            long t0 = System.currentTimeMillis();
            try {
                MR mr = (MR) Class.forName(cn).newInstance();
                mr.setProvider(provider);
                mr.run();
                LinkedList<String> fails = mr.getFailures();
                row.put("status", "executed");
                row.put("fired", fails.size());
                List<String> samples = new ArrayList<String>();
                for (int i = 0; i < fails.size() && i < 8; i++) {
                    String s = fails.get(i);
                    samples.add(s.length() > 600 ? s.substring(0, 600) : s);
                }
                row.put("failure_samples", samples);
            } catch (Throwable t) {
                row.put("status", "error");
                row.put("error", t.getClass().getName() + ": " + t.getMessage());
                StackTraceElement[] st = t.getStackTrace();
                if (st != null && st.length > 0) {
                    row.put("error_at", st[0].toString());
                }
            }
            row.put("http_calls", GiteaHttpProvider.httpCallCount() - before);
            row.put("ms", System.currentTimeMillis() - t0);
            rows.add(row);
        }
        report.put("mrs", rows);

        // 5) 计数器
        Map<String, Object> c = new LinkedHashMap<String, Object>();
        c.put("cannotReachThroughGUI_url_calls", GiteaHttpProvider.nCrtgUrl);
        c.put("cannotReachThroughGUI_url_true", GiteaHttpProvider.nCrtgUrlTrue);
        c.put("cannotReachThroughGUI_input_calls", GiteaHttpProvider.nCrtgInput);
        c.put("cannotReachThroughGUI_input_true", GiteaHttpProvider.nCrtgInputTrue);
        c.put("isSupervisorOf_calls", GiteaHttpProvider.nSupervisor);
        c.put("isSupervisorOf_true", GiteaHttpProvider.nSupervisorTrue);
        c.put("userCanRetrieveContent_calls", GiteaHttpProvider.nUcrc);
        c.put("userCanRetrieveContent_true", GiteaHttpProvider.nUcrcTrue);
        c.put("http_calls_total", GiteaHttpProvider.httpCallCount());
        c.put("http_memo_hits", GiteaHttpProvider.memoHitCount());
        report.put("counters", c);

        // 6) 逐格证据：真谓词在哪些 (用户,URL) 上判了什么
        report.put("crtg_cells", GiteaHttpProvider.CRTG_CELLS);

        Writer w = new FileWriter(outJson);
        gson.toJson(report, w);
        w.close();

        System.out.println("=== DONE ===");
        System.out.println("fired_total=" + totalFired(rows));
        System.out.println("http_calls_total=" + GiteaHttpProvider.httpCallCount());
    }

    private static int totalFired(List<Map<String, Object>> rows) {
        int n = 0;
        for (Map<String, Object> r : rows) {
            Object f = r.get("fired");
            if (f instanceof Integer) {
                n += (Integer) f;
            }
        }
        return n;
    }
}

"""Gitea 1.22.6 侧的 M1 普查（与 Gogs 使用**同一张模式表**，以便真正可比）
========================================================================
Block 10 原来的 M1 数字取自 `run_real.py` 的 Gitea 形正则表（253 路径 / 15 授予 /
8 非管理员）。跨实现比较时那样会变成"两边各用各的写法"，因此这里用
`m1_census.SHARED_PATTERNS` 把 Gitea 侧**重算一遍**，与 Gogs 侧对齐。

输出的 `results/m1_matched_gitea.json` 只用于**跨实现对照表**；
正文原有的 Gitea M1 数字（取自 run_real.py）保持不变。

用法: python m1_gitea_swagger.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gitea_lab as gtl
import m1_census as mc

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "results"
RESULTS.mkdir(parents=True, exist_ok=True)


def main():
    t0 = time.time()
    cfg = gtl.write_config()
    print("[A]", gtl.ensure_migrated(cfg), flush=True)
    with gtl.Server(cfg) as srv:
        print(f"[A] gitea={gtl.version()} ready_ms={srv.ready_ms}", flush=True)
        cl = gtl.Client(user=gtl.ADMIN_USER, password=gtl.ADMIN_PASS, label="root")
        st, sw = cl.get("/swagger.v1.json", timeout=60)
        if st != 200 or not isinstance(sw, dict):
            raise SystemExit(f"swagger 不可读 status={st}")

        paths = sw.get("paths", {})
        pwm: dict[str, list[str]] = {}
        adm: dict[str, bool] = {}
        for p, ops in paths.items():
            pwm[p] = [m for m in ops
                      if isinstance(m, str) and m.lower() in ("post", "put", "patch", "delete")]
            adm[p] = p.startswith("/admin")

        cens = mc.census(
            pwm, adm,
            source_label="Gitea 1.22.6 · 运行时 /swagger.v1.json",
            denominator_label="swagger paths（全部，含只读端点）")
        cens["meta"] = {
            "gitea_version": gtl.GITEA_VERSION,
            "swagger_paths_total": len(paths),
            "note": ("本表用 m1_census.SHARED_PATTERNS 重算，目的是与 Gogs 侧可比；"
                     "正文原有的 Gitea M1 数字（run_real.py 的 Gitea 形正则表）不改。"),
            "elapsed_s": round(time.time() - t0, 1),
        }
        out = RESULTS / "m1_matched_gitea.json"
        out.write_text(json.dumps(cens, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"路径总数 {cens['denominator_entries']} · 命中 {cens['matched_rows_total']} · "
              f"授予 {cens['grant_endpoints_total']} · 非站点管理员 "
              f"{cens['grant_endpoints_without_site_admin']}", flush=True)
        for e in cens["endpoints"]:
            print(f"  {e['direction']:<6} {str(e['methods']):<26} {e['endpoint']:<56}"
                  f" {'SITE-ADMIN' if e['requires_site_admin'] else ''}", flush=True)
        print("->", out, flush=True)


if __name__ == "__main__":
    main()

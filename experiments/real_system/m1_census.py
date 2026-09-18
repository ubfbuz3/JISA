"""
M1 · 授权授予机制空间普查（**跨实现共用**）
============================================
为什么单独抽出来：Gitea 侧的分母取自运行时 `/swagger.v1.json`，Gogs 侧的分母取自
钉死版本的**路由表源码**（Gogs 没有 swagger 端点）。两者的路径形状也不同
（`{owner}/{repo}` vs `{username}/{reponame}`；Gogs 的团队端点挂在 `/admin/**` 下）。
若各用各的正则表，得到的数字**不可比**，也容易被质疑"是在挑对自己有利的写法"。

⇒ 本模块把两边的路径**归一化到同一形状**，再用**同一张模式表**普查：
   1. `{username}`→`{owner}`、`{reponame}`→`{repo}`、`{orgname}`→`{org}`、`{teamid}`→`{id}`
   2. 允许可选的 `/admin` 前导（**不删除**，以便另行统计"是否要求站点管理员"）

判据（与 Block 10 一致，未改）：
  端点计入当且仅当：在不修改被测系统代码的前提下，能使某 (主体, 对象) 的访问权限
  从否变为是；方向由该端点**实际可用**的 HTTP 方法推出（方法集 ⊆ {DELETE} ⇒ 撤销，不算授予）。
"""

from __future__ import annotations

import re

# --------------------------------------------------------------------------
# 归一化
# --------------------------------------------------------------------------
def normalize_path(p: str) -> str:
    """**结构化**归一化：把每个路径参数名整体抹掉（`{owner}`→`{}`），并去掉版本前缀。

    ⚠️ 不要做"名字别名映射"（初版把 `{username}`→`{owner}`）：
    Gitea 的 `/orgs/{org}/members/{username}` 会被改写成 `…/members/{owner}`，
    于是 `…/members/{username}` 这条模式**匹配不上**，团队/成员类端点整片漏掉，
    M1 会得到一个偏低但看不出错的数字（真实踩到）。
    只保留结构 ⇒ 两系统的路径差异全部落在"结构"这一层，模式表才真的中性。
    """
    p = re.sub(r"\{[^}]*\}", "{}", p)
    for pre in ("/api/v1", "/v1"):
        if p.startswith(pre):
            p = p[len(pre):]
    return p or "/"


# --------------------------------------------------------------------------
# 共用模式表（覆盖两系统的路径形状；一律用 `{}` 表示"任意路径参数"）
#    每条 = (正则, 类别, 人话说明)
# --------------------------------------------------------------------------
SHARED_PATTERNS: list[tuple[str, str, str]] = [
    # ---- 仓库级 ----
    (r"^/repos/\{\}/\{\}/collaborators/\{\}$",
     "repo_collaborator", "仓库级：把某用户设为协作者（PUT 授予 / DELETE 撤销）"),
    (r"^/repos/\{\}/\{\}/keys$",
     "repo_deploy_key", "仓库级：部署密钥（授予持有者读/写）"),
    (r"^/repos/\{\}/\{\}/transfer$",
     "repo_transfer", "仓库级：转移所有权（把对象交给另一主体）"),
    (r"^/repos/\{\}/\{\}$",
     "repo_properties", "仓库级：改属性（私有→公开即向所有人授予）"),
    # ---- 团队级（Gitea 在 /teams/**；Gogs 在 /admin/teams/** ⇒ 用 (?:/admin)? 容纳）----
    (r"^(?:/admin)?/teams/\{\}/members/\{\}$",
     "team_member", "团队级：用户加入团队"),
    (r"^(?:/admin)?/teams/\{\}/repos(?:/\{\})?/\{\}$",
     "team_repo", "团队级：仓库挂到团队"),
    # ---- 组织级 ----
    (r"^(?:/admin)?/orgs/\{\}/teams$",
     "org_team_create", "组织级：新建团队（授权单位本身）"),
    (r"^/orgs/\{\}/members/\{\}$",
     "org_member", "组织级：用户加入/移出组织"),
    (r"^/orgs$",
     "org_create", "组织级：新建组织（站点管理员通道）"),
    (r"^/user/orgs$",
     "org_create_self", "组织级：自建组织（普通用户通道）"),
    (r"^/(?:admin/orgs/\{\}|org/\{\}|orgs/\{\})/repos$",
     "org_repo_create", "组织级：在组织内建仓"),
    # ---- 站点级 ----
    (r"^/admin/users$",
     "site_user_create", "站点级：建用户"),
    (r"^/admin/users/\{\}/(?:orgs|repos)$",
     "site_create_as_user", "站点级：以某用户名义建组织/仓库"),
    # ------------------------------------------------------------------
    # GitLab 形状（Block 13 追加；与上面条目零交集——Gitea/Gogs 的归一化路径
    # 不以 /projects、/groups 开头 ⇒ 追加不影响既有两系统的任何数字）
    # ------------------------------------------------------------------
    # ---- 仓库级 ----
    (r"^/projects/\{\}/members$",
     "repo_collaborator", "GitLab 仓库级：加项目成员（= 协作者）"),
    (r"^/projects/\{\}/members(?:/all)?/\{\}$",
     "repo_collaborator", "GitLab 仓库级：改/移除项目成员、批准访问请求"),
    (r"^/projects/\{\}/(?:access_requests/\{\}/approve|invitations)$",
     "repo_collaborator", "GitLab 仓库级：邀请/批准成员"),
    (r"^/projects/\{\}/share$",
     "repo_share_group", "GitLab 仓库级：与组共享（组内成员全体获得访问）"),
    (r"^/projects/\{\}/deploy_keys$",
     "repo_deploy_key", "GitLab 仓库级：部署密钥（授予持有者读/写）"),
    (r"^/projects/\{\}/deploy_keys/\{\}$",
     "repo_deploy_key", "GitLab 仓库级：改/移除部署密钥"),
    (r"^/projects/\{\}/deploy_tokens$",
     "repo_deploy_token", "GitLab 仓库级：部署令牌（授予读/写）"),
    (r"^/projects/\{\}/transfer$",
     "repo_transfer", "GitLab 仓库级：转移所有权"),
    (r"^/projects/\{\}$",
     "repo_properties", "GitLab 仓库级：改属性（私有→公开即向所有人授予）"),
    # ---- 组织（组）级 ----
    (r"^/groups/\{\}/members$",
     "org_member", "GitLab 组织级：加组成员（组继承 = GitLab 的唯一团队机制）"),
    (r"^/groups/\{\}/members(?:/all)?/\{\}$",
     "org_member", "GitLab 组织级：改/移除组成员"),
    (r"^/groups/\{\}/(?:access_requests/\{\}/approve|invitations)$",
     "org_member", "GitLab 组织级：邀请/批准成员"),
    (r"^/groups/\{\}/share$",
     "org_share_group", "GitLab 组织级：与另一个组共享组"),
    (r"^/groups/\{\}/(?:deploy_keys|deploy_tokens)$",
     "org_deploy_token", "GitLab 组织级：组级部署密钥/令牌"),
    (r"^/groups$",
     "org_create", "GitLab 组织级：新建组"),
    (r"^/groups/\{\}/projects$",
     "org_repo_create", "GitLab 组织级：在组内建仓"),
    # ---- 站点级 ----
    (r"^/users$",
     "site_user_create", "GitLab 站点级：建用户（管理员专用）"),
]


def classify(path: str) -> list[tuple[str, str]]:
    """返回 [(类别, 说明)]，可能命中多条。"""
    p = normalize_path(path)
    return [(cat, desc) for pat, cat, desc in SHARED_PATTERNS if re.match(pat, p)]


# --------------------------------------------------------------------------
# 普查
# --------------------------------------------------------------------------
def census(paths_with_methods: dict[str, list[str]],
           admin_flags: dict[str, bool] | None = None,
           source_label: str = "", denominator_label: str = "") -> dict:
    """paths_with_methods: {path: [methods]}（只需 POST/PUT/PATCH/DELETE 中有值的项即可）
    admin_flags: {path: bool} 该路径是否要求站点管理员（Gitea 用 `/admin` 前缀推，
                 Gogs 用路由表源码的 `reqAdmin()` 推）
    """
    admin_flags = admin_flags or {}
    endpoints: list[dict] = []
    seen: set[tuple[str, str]] = set()

    for path, methods in paths_with_methods.items():
        ms = sorted({m.upper() for m in methods
                     if m.upper() in ("POST", "PUT", "PATCH", "DELETE")})
        if not ms:
            continue
        for cat, desc in classify(path):
            key = (normalize_path(path), cat)
            if key in seen:
                continue
            seen.add(key)
            endpoints.append({
                "endpoint": normalize_path(path),
                "methods": ms,
                "category": cat,
                "kind": desc,
                "direction": "revoke" if set(ms) <= {"DELETE"} else "grant",
                "requires_site_admin": bool(admin_flags.get(path, False)),
            })

    grants = [e for e in endpoints if e["direction"] == "grant"]
    by_cat: dict[str, int] = {}
    for e in grants:
        by_cat[e["category"]] = by_cat.get(e["category"], 0) + 1

    return {
        "source": source_label,
        "denominator": denominator_label,
        "denominator_entries": len(paths_with_methods),
        "matched_rows_total": len(endpoints),
        "grant_endpoints_total": len(grants),
        "revoke_endpoints_total": len(endpoints) - len(grants),
        "grant_endpoints_without_site_admin": sum(
            1 for e in grants if not e["requires_site_admin"]),
        "grant_categories": by_cat,
        "endpoints": sorted(endpoints, key=lambda e: (e["category"], e["endpoint"])),
        "predicate": ("端点计入当且仅当：在不修改被测系统代码的前提下，能使某 (主体, 对象) "
                      "的访问权限从否变为是；方向由该端点实际可用的 HTTP 方法推出"
                      "（方法集 ⊆ {DELETE} ⇒ 撤销，不算授予）。"
                      "两系统路径已归一化后用同一张模式表普查。"),
    }

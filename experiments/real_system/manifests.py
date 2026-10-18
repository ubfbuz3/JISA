"""
Ledger -> PolicyModel builders, one per lab.

Each builder consumes the *recorded setup transactions* (phase A) and the
out-of-band mutations (phase C) and returns a PolicyModel whose `expected()`
is the authoritative E.  Nothing here touches a probe response.

Kept separate from the runners so the same code path can be replayed offline
against saved JSON (see validate_entitlement_gitea.py).
"""

from __future__ import annotations

from entitlement import PolicyModel


def gitea_model(report_A: dict, report_C: dict, *, repos, teams, org: str,
                admin_user: str) -> PolicyModel:
    """Gitea lab: user repos + org teams + collaborator grants + visibility."""
    m = PolicyModel()
    m.add_org(org, "dave", "org created by dave")

    for owner, name, private, _isorg, _creator in repos:
        m.add_repo(f"{owner}/{name}", owner, private, "phaseA repo creation")

    m.add_site_admin(admin_user, "gitea_lab.ADMIN_USER")

    for team, perm in teams.items():
        m.add_team(team, perm, "phaseA team creation")

    # baseline grants (phase A) -- these are the transactions we executed
    m.add_team_member("dev", "bob", "phaseA baseline team dev += bob")
    m.add_team_repo("dev", f"{org}/t1", "phaseA baseline dev += acme/t1")
    m.add_collaborator("alice/r1", "bob", "read",
                       "phaseA baseline in-band share alice/r1 <- bob")

    # out-of-band mutations (phase C)
    for mut in report_C.get("mutations", []):
        kind = mut.get("mutation", "")
        obj = mut.get("object")
        subj = mut.get("subject")
        src = f"phaseC:{kind}"
        if kind.startswith("admin_grant_collaborator") and obj and subj:
            m.add_collaborator(obj, subj, "read", src)
        elif kind.startswith("team_grant_repo") and obj:
            team = kind.rsplit("team ", 1)[-1].strip()
            if team in teams:
                m.add_team_repo(team, obj, src)
        elif kind.startswith("admin_flip_visibility") and obj:
            m.set_visibility(obj, "-> public" not in kind, src)
        elif kind.startswith("admin_add_org_member") and subj:
            m.add_org_member(org, subj, src)
        elif kind.startswith("admin_add_team_member") and subj:
            team = kind.split(":", 1)[1].split("<-", 1)[0].strip()
            if team in teams:
                m.add_team_member(team, subj, src)
    return m



# ---------------------------------------------------------------------------
# Gogs 0.14.3 -- same topology as Gitea; no visibility PATCH, no add-org-member
# ---------------------------------------------------------------------------
def gogs_model(report_C: dict, *, repos, teams, org: str,
               admin_user: str) -> PolicyModel:
    m = PolicyModel()
    m.add_org(org, "dave", "org created by dave")
    for owner, name, private, _isorg, _creator in repos:
        m.add_repo(f"{owner}/{name}", owner, private, "phaseA repo creation")
    m.add_site_admin(admin_user, "gogs_lab.ADMIN_USER")
    for team, perm in teams.items():
        m.add_team(team, perm, "phaseA team creation")

    m.add_team_member("dev", "bob", "phaseA baseline team dev += bob")
    m.add_team_repo("dev", f"{org}/t1", "phaseA baseline dev += repo t1")
    m.add_collaborator("alice/r1", "bob", "read",
                       "phaseA baseline in-band share alice/r1 <- bob")

    for mut in report_C.get("mutations", []):
        kind = mut.get("mutation", "")
        obj = mut.get("object")
        subj = mut.get("subject")
        src = f"phaseC:{kind}"
        if kind.startswith(("admin_grant_collaborator",
                            "owner_grant_collaborator")) and obj and subj:
            m.add_collaborator(obj, subj, "read", src)
        elif kind.startswith("team_grant_repo") and obj:
            team = kind.rsplit("team ", 1)[-1].strip()
            if team in teams:
                m.add_team_repo(team, obj, src)
        elif kind.startswith("admin_add_team_member") and subj:
            team = kind.split(":", 1)[1].split("<-", 1)[0].strip()
            if team in teams:
                m.add_team_member(team, subj, src)
    return m


# ---------------------------------------------------------------------------
# GitLab -- group membership inherits to every project of the group
# ---------------------------------------------------------------------------
ROLE_TO_PERM = {"guest": "read", "reporter": "read", "developer": "write",
                "maintainer": "admin", "owner": "admin"}


def _role(text: str, default: str = "read") -> str:
    """Extract `(Reporter)` / `(Developer)` from a mutation label."""
    if "(" in text and text.rstrip().endswith(")"):
        role = text.rsplit("(", 1)[1].rstrip(")").strip().lower()
        return ROLE_TO_PERM.get(role, default)
    return default


def gitlab_model(report_C: dict, *, repos, org: str, admin_user: str,
                 baselines: list[str]) -> PolicyModel:
    m = PolicyModel()
    m.add_org(org, "dave", "group created by dave")
    for owner, name, private, _isorg, _creator in repos:
        m.add_repo(f"{owner}/{name}", owner, private, "phaseA project creation")
    m.add_site_admin(admin_user, "gitlab_lab.ADMIN_USER")

    # the group behaves like a team: membership inherits to all its projects
    m.add_team(f"group:{org}", "read", "phaseA group")
    m.add_team_repo(f"group:{org}", f"{org}/t1", "phaseA group project")
    m.add_team_repo(f"group:{org}", f"{org}/t2", "phaseA group project")
    for base in baselines:
        if base.startswith("group:") and "<-" in base:
            who = base.split("<-", 1)[1].split("(")[0].strip()
            m.add_team_member(f"group:{org}", who, f"phaseA baseline {base}")
        elif base.startswith("project:") and "<-" in base:
            head, who = base.split("<-", 1)
            obj = head.split(":", 1)[1].strip()
            m.add_collaborator(obj, who.split("(")[0].strip(),
                               _role(base), f"phaseA baseline {base}")

    for mut in report_C.get("mutations", []):
        kind = mut.get("mutation", "")
        obj = mut.get("object")
        subj = mut.get("subject")
        src = f"phaseC:{kind}"
        if kind.startswith(("admin_grant_member", "owner_grant_member")) and obj and subj:
            m.add_collaborator(obj, subj, _role(kind), src)
        elif kind.startswith("org_owner_grant_group") and subj:
            m.add_team_member(f"group:{org}", subj, src)
        elif kind.startswith("visibility_flip") and obj:
            m.set_visibility(obj, "->public" not in kind.replace(" ", ""), src)
    return m

def rebuild_gitea_from_report(rep: dict, *, repos, teams, org: str,
                              admin_user: str) -> PolicyModel:
    """Convenience wrapper for replaying a saved real_system.json."""
    return gitea_model(rep.get("phaseA_topology", {}),
                       rep.get("phaseC_mutations", {}),
                       repos=repos, teams=teams, org=org,
                       admin_user=admin_user)

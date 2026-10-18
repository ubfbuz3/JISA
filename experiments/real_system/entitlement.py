"""
A-pack (resubmission): independent expected-entitlement model  ·  schema v1
==========================================================================

Why this module exists
----------------------
The first submission used

    granted = (http_status == 200)
    truth_map[...] = granted
    authorized    = granted
    false_proof   = alarm and authorized

i.e. the *observed effect* Y was written straight into the *expected
entitlement* E.  That is unsound in general: for a genuine BOLA defect
E = deny while Y = 200, so the old chain would have marked a true positive
"authorized" and then counted the alarm as a false proof.  On Gitea (a
correct system) E and Y happen to coincide, which is exactly why the defect
went unnoticed.

This module derives E from an explicit ledger built ONLY from

  (1) the lab topology the runner itself created (recorded setup transactions),
  (2) documented inheritance rules -- owner / site admin / public /
      collaborator / org-team,
  (3) out-of-band mutations, each entered as one grant event.

It never reads a probe response.  `Decision.basis` carries the rule chain so
every label can be traced back to an external justification.

Cell schema (what the runner must persist, one row per
(object, subject, action, policy_version))
------------------------------------------------------------
  expected_entitlement : allow | deny | unknown      (E)
  expected_basis       : [rule, ...]                 (why E)
  expected_channel     : owner|site_admin|public|collaborator|team|none
  expected_alt_channels: [...]                       (multi-label support)
  observed_effect      : what the request actually did (Y) -- filled by caller
  oracle_answer        : what the introspection surface said (O)
  oracle_independence  : independent | shared | unknown
  raw_alarm            : MR fired (A)
  promotion            : A promoted to violation-proven (H), H => A
  abstain_reason       : unreadable | covering | version_mismatch | none
  policy_version       : monotonic authorisation version at decision time

`E` is `unknown` when the ledger is incomplete for that cell -- the caller must
then report it as unknown rather than guessing allow/deny.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# action / permission lattice -------------------------------------------------
RANK = {"none": 0, "read": 1, "write": 2, "admin": 3}
ACTION_NEED = {"read": 1, "write": 2, "admin": 3}

ANON = "anonymous"


def covers(permission: str | None, action: str) -> bool:
    """True if holding `permission` is enough to perform `action`."""
    return RANK.get(permission or "none", 0) >= ACTION_NEED[action]


@dataclass
class Decision:
    value: str                      # allow | deny | unknown
    channel: str = "none"           # strongest granting channel
    basis: list[str] = field(default_factory=list)
    alternatives: list[str] = field(default_factory=list)

    @property
    def allowed(self) -> bool:
        return self.value == "allow"

    def as_dict(self) -> dict:
        return {"expected_entitlement": self.value,
                "expected_channel": self.channel,
                "expected_basis": list(self.basis),
                "expected_alt_channels": list(self.alternatives)}


class PolicyModel:
    """A deliberately small, auditable model of the lab's authorisation state.

    It models only the mechanisms the labs actually exercise.  Anything it does
    not model must surface as `unknown` rather than as a silent deny.
    """

    def __init__(self) -> None:
        self.owner_of: dict[str, str] = {}
        self.org_owner: dict[str, str] = {}
        self.private: dict[str, bool] = {}
        self.site_admins: set[str] = set()
        self.collaborators: dict[tuple[str, str], str] = {}
        self.team_members: dict[str, set[str]] = {}
        self.team_repos: dict[str, set[str]] = {}
        self.team_perm: dict[str, str] = {}
        self.org_members: dict[str, set[str]] = {}
        self.restricted: dict[str, bool] = {}
        self.ledger: list[dict] = []
        self.unmodelled: set[str] = set()

    # -- builders (each call is one recorded transaction) --------------------
    def _log(self, kind: str, detail: str, source: str) -> None:
        self.ledger.append({"kind": kind, "detail": detail, "source": source})

    def add_repo(self, obj: str, owner: str, private: bool, source: str) -> None:
        self.owner_of[obj] = owner
        self.private[obj] = bool(private)
        self._log("repo", f"{obj} owner={owner} private={private}", source)

    def add_owner(self, obj: str, subject: str, source: str) -> None:
        self.owner_of[obj] = subject
        self._log("owner", f"{obj} owner={subject}", source)

    def add_org(self, org: str, owner: str, source: str) -> None:
        self.org_owner[org] = owner
        self._log("org", f"{org} owner={owner}", source)

    def add_site_admin(self, subject: str, source: str) -> None:
        self.site_admins.add(subject)
        self._log("site_admin", subject, source)

    def add_collaborator(self, obj: str, subject: str, permission: str,
                         source: str) -> None:
        self.collaborators[(obj, subject)] = permission
        self._log("collaborator", f"{obj} {subject}={permission}", source)

    def add_team(self, team: str, permission: str, source: str) -> None:
        self.team_perm[team] = permission
        self.team_members.setdefault(team, set())
        self.team_repos.setdefault(team, set())
        self._log("team", f"{team} perm={permission}", source)

    def add_team_member(self, team: str, subject: str, source: str) -> None:
        self.team_members.setdefault(team, set()).add(subject)
        self._log("team_member", f"{team} += {subject}", source)

    def add_team_repo(self, team: str, obj: str, source: str) -> None:
        self.team_repos.setdefault(team, set()).add(obj)
        self._log("team_repo", f"{team} += {obj}", source)

    def add_org_member(self, org: str, subject: str, source: str) -> None:
        self.org_members.setdefault(org, set()).add(subject)
        self._log("org_member", f"{org} += {subject}", source)

    def set_visibility(self, obj: str, private: bool, source: str) -> None:
        self.private[obj] = bool(private)
        self._log("visibility", f"{obj} private={private}", source)

    def set_restricted(self, subject: str, restricted: bool, source: str) -> None:
        self.restricted[subject] = bool(restricted)
        self._log("restricted", f"{subject}={restricted}", source)

    # -- inference ----------------------------------------------------------
    def expected(self, obj: str, subject: str, action: str = "read") -> Decision:
        """Derive E(obj, subject, action) from the ledger only."""
        if action not in ACTION_NEED:
            raise ValueError(f"unknown action {action!r}")
        if obj not in self.owner_of:
            return Decision("unknown", "none", [f"object {obj} not in ledger"])

        grants: list[tuple[str, str, int]] = []   # (channel, reason, strength)

        # 1. object owner (for org repos the org owner acts as owner)
        owner = self.owner_of[obj]
        if subject == owner:
            grants.append(("owner", f"owner of {obj}", 100))

        # 1b. org owner inherits admin over every repository the org owns
        if owner in self.org_owner and subject == self.org_owner[owner]:
            grants.append(("org_owner", f"owner of org {owner}", 95))

        # 2. site administrator
        if subject in self.site_admins:
            grants.append(("site_admin", "site administrator", 90))

        # 3. public read
        if not self.private.get(obj, True) and action == "read":
            grants.append(("public", f"{obj} is public", 80))

        # 4. explicit collaborator grant
        perm = self.collaborators.get((obj, subject))
        if perm and covers(perm, action):
            grants.append(("collaborator", f"collaborator {perm}", 70))

        # 5. org team inheritance
        for team, members in self.team_members.items():
            if subject not in members:
                continue
            if obj not in self.team_repos.get(team, set()):
                continue
            tperm = self.team_perm.get(team, "none")
            if covers(tperm, action):
                grants.append(("team", f"team {team} {tperm}", 60))

        if not grants:
            # a missing object model is unknown; a modelled object with no grant
            # is a genuine deny
            return Decision("deny", "none", [f"no granting channel for {action}"])

        grants.sort(key=lambda g: -g[2])
        channels = sorted({g[0] for g in grants})
        return Decision("allow", grants[0][0],
                        [g[1] for g in grants], channels)

    # -- audit --------------------------------------------------------------
    def summary(self) -> dict:
        return {"objects": len(self.owner_of),
                "collaborator_grants": len(self.collaborators),
                "teams": {t: {"perm": self.team_perm[t],
                              "members": sorted(self.team_members[t]),
                              "repos": sorted(self.team_repos[t])}
                          for t in self.team_perm},
                "site_admins": sorted(self.site_admins),
                "ledger_entries": len(self.ledger),
                "unmodelled": sorted(self.unmodelled)}


# ---------------------------------------------------------------------------
# verdict helpers -- the definitions the paper must use
# ---------------------------------------------------------------------------
def classify(expected: str, observed_allow: bool, alarm: bool,
             promotion: bool) -> dict:
    """Map (E, Y, A, H) to the reporting categories.

    A true positive requires BOTH
        E = deny   (the request was not entitled)  and
        Y = allow  (the request actually succeeded),
    because a BOLA violation is an unauthorised access that *happened*.  An
    alarm on a correctly-refused request (E=deny, Y=deny) is a correct policy
    observation, not evidence of a vulnerability -- scoring it as a TP would
    inflate purely observational methods such as `direct_only`.

    A false proof requires E = allow: the method claimed `violation-proven`
    for an access that was legitimate.

    `promotion => alarm` is asserted rather than assumed.
    """
    if promotion and not alarm:
        raise ValueError("promotion without a raw alarm (H => A violated)")

    if not alarm:
        return {"category": "no_alarm", "true_positive": False,
                "false_proof": False}

    if expected == "unknown":
        return {"category": "unscored_unknown_entitlement",
                "true_positive": False, "false_proof": False}

    if expected == "allow":
        return {"category": "false_proof" if promotion else "alarm_on_legitimate",
                "true_positive": False, "false_proof": bool(promotion)}

    # expected == deny
    if observed_allow:
        return {"category": "true_positive" if promotion else "alarm_on_denied",
                "true_positive": bool(promotion), "false_proof": False}
    return {"category": "alarm_on_denied_not_exploitable",
            "true_positive": False, "false_proof": False}

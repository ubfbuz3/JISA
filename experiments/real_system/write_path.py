"""
Write-path truth (Y for write) · 状态码不算数，只认实际状态变化
================================================================

A 包此前只测读：`Y = status == 200` 对读是合理的（响应体就是被读对象），
对写则**不成立**——服务端可能返回 200 却忽略字段，也可能返回 403 但旁路写入。

本模块用**文件内容**做写探针（三个 forge 都有 contents API，语义一致）：

1. 确认目标路径在仓库中不存在（基线）；
2. 以**被测主体**凭证写入唯一文件 `wb-probe-<hex>.txt`，内容 = 同一标记；
   记录状态码（仅作诊断，**不参与 Y**）；
3. 以**拥有者**凭证复读该文件：只有内容逐字节等于标记，才记 `Y_write = allow`；
4. 以拥有者凭证删除该文件，并复读确认 404（恢复现场）。

`E_write` 来自授权台账（`PolicyModel.expected(obj, subject, "write")`），
与 Y 严格分离。

对正确系统，E 与 Y 必须一致；不一致只有两种解释：
  - E=deny, Y=allow  → 真实的越权写（漏洞证据，正是 vulnerable/fixed 配对要抓的）
  - E=allow, Y=deny  → 台账建模缺口，必须查

角色分层（不混在一起统计）：
  cross  换凭证写入 —— 主统计
  owner  拥有者写自己的仓库 —— 非管理员阳性控制（必须真的改变内容并成功恢复）
  admin  站点管理员 —— sanity check

用法（由三个 runner 在阶段 G 之后调用）：

    rep["phaseH_write_path"] = wp.run(
        cl, policy, ALL_OBJS, subjects,
        owner_cred_for=lambda o: OBJ_CREDENTIAL[o],
        write_file=..., read_file=..., delete_file=...,
        system="Gitea", admin_user=ADMIN_USER)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass


@dataclass
class WriteCell:
    object: str
    subject: str
    role: str                          # cross | owner | admin
    expected: str
    expected_channel: str
    expected_basis: list[str]
    observed: str                      # allow / deny —— 由内容复读决定
    write_status: int                  # 仅诊断
    changed: bool
    restored: bool
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "object": self.object, "subject": self.subject, "role": self.role,
            "expected_entitlement": self.expected,
            "expected_channel": self.expected_channel,
            "expected_basis": self.expected_basis,
            "observed_effect": self.observed,
            "write_status": self.write_status,
            "content_changed": self.changed,
            "restored": self.restored,
            "note": self.note,
        }


def run(clients, policy, objects, subjects, owner_cred_for,
        write_file, read_file, delete_file, system: str,
        admin_user: str, restore_supported: bool = True) -> dict:
    """执行写路径探测并返回可落盘报告。

    write_file(obj, subj, path, text) -> status
    read_file(obj, subj, path)        -> (status, text|None)
    delete_file(obj, owner, path)     -> bool（True = 已删除且复读 404）
    """
    rows: list[WriteCell] = []
    errors: list[dict] = []

    for obj in objects:
        owner = owner_cred_for(obj)
        for subj in subjects:
            role = ("owner" if subj == owner else
                    "admin" if subj == admin_user else "cross")
            marker = f"wb-probe-{uuid.uuid4().hex[:10]}"
            path = f"{marker}.txt"

            st0, txt0 = read_file(obj, owner, path)
            if st0 == 200:
                errors.append({"object": obj, "subject": subj, "stage": "baseline",
                               "status": st0, "note": "probe path already exists"})
                continue

            st = write_file(obj, subj, path, marker)
            st_v, txt_v = read_file(obj, owner, path)
            changed = bool(st_v == 200 and txt_v == marker)

            restored = False
            if changed and restore_supported:
                restored = delete_file(obj, owner, path)
                if not restored:
                    errors.append({"object": obj, "subject": subj,
                                   "stage": "restore", "status": st_v})

            dec = policy.expected(obj, subj, "write")
            rows.append(WriteCell(
                object=obj, subject=subj, role=role,
                expected=dec.value, expected_channel=dec.channel,
                expected_basis=list(dec.basis),
                observed="allow" if changed else "deny",
                write_status=st, changed=changed, restored=restored,
                note="" if changed else (
                    "transport-error (no response; Y recorded from content, not status)"
                    if st == 0 else "denied" if st >= 400 else
                    "server accepted but state unchanged"),
            ))

    stat = [r for r in rows if r.role == "cross"]
    agreed = sum(1 for r in stat if (r.expected == "allow") == (r.observed == "allow"))
    mism = [r.as_dict() for r in stat
            if (r.expected == "allow") != (r.observed == "allow")]
    unauthorized = [r.as_dict() for r in stat
                    if r.expected == "deny" and r.observed == "allow"]
    owner_rows = [r.as_dict() for r in rows if r.role == "owner"]
    admin_rows = [r.as_dict() for r in rows if r.role == "admin"]

    return {
        "system": system,
        "protocol": ("create unique file as subject -> re-read as owner "
                     "(byte compare) -> delete as owner -> verify 404"),
        "target": "repository file contents",
        "restore_supported": restore_supported,
        "restore_note": ("" if restore_supported else
                         "this forge's contents API exposes no DELETE; the probe file is "
                         "left in a disposable lab instance and Y is still content-verified"),
        "marker_prefix": "wb-probe-",
        "cells": [r.as_dict() for r in rows],
        "summary": {
            "pairs": len(stat),
            "e_eq_y": agreed,
            "mismatches": mism,
            "unauthorized_writes": unauthorized,
            # status 0 = 传输失败，不能与"接受/拒绝"比较；单独留在 note 里
            "status_code_disagrees_with_content": [
                r.as_dict() for r in rows
                if r.write_status != 0 and (r.write_status < 400) != r.changed],
            "owner_sanity": {
                "rows": len(owner_rows),
                "all_observed": all(r["observed_effect"] == "allow"
                                    for r in owner_rows) if owner_rows else None,
                "all_restored": (all(r["restored"] for r in owner_rows)
                                 if owner_rows and restore_supported else None),
            },
            "admin_sanity": {
                "rows": len(admin_rows),
                "all_observed": all(r["observed_effect"] == "allow"
                                    for r in admin_rows) if admin_rows else None,
                "all_restored": (all(r["restored"] for r in admin_rows)
                                 if admin_rows and restore_supported else None),
            },
            "errors": errors,
        },
    }

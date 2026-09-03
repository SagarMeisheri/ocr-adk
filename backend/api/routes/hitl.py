"""Deterministic Human-in-the-Loop (HITL) Write Safety Gate Routes.

Enforces zero autonomous AI writes to Tally Prime.
Every write operation (Ledgers, Stock Items, Purchase Vouchers, Bank Vouchers, MCP write actions)
must be explicitly approved by a human operator before being posted to Tally.
"""

from __future__ import annotations
import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from ..storage import HitlStore

router = APIRouter(prefix="/api/hitl", tags=["Deterministic Human-in-the-Loop Gate"])


class RejectPayload(BaseModel):
    reason: Optional[str] = "Rejected by accountant"
    reviewer: Optional[str] = "Accountant"


class ApprovePayload(BaseModel):
    reviewer: Optional[str] = "Accountant"


class ExternalWritePayload(BaseModel):
    action_type: str
    target_company: Optional[str] = "Active Tally Company"
    description: str
    payload_xml: str
    payload_json: Optional[Dict[str, Any]] = None


@router.get("/pending")
def list_pending_approvals():
    """Lists all write actions currently quarantined awaiting explicit human approval."""
    return {"pending_approvals": HitlStore.list_pending_approvals()}


@router.post("/stage-external-write")
def stage_external_write(payload: ExternalWritePayload):
    """Stages an external write action (e.g. from MCP tools) into the HITL quarantine."""
    ref_id = f"mcp_{uuid.uuid4().hex[:8]}"
    approval_id = HitlStore.stage_write_action(
        action_type=payload.action_type,
        reference_id=ref_id,
        target_company=payload.target_company or "Active Tally Company",
        description=payload.description,
        payload_xml=payload.payload_xml,
        payload_json=payload.payload_json,
    )
    return {
        "status": "QUARANTINED_IN_HITL",
        "approval_id": approval_id,
        "message": f"Write action '{payload.action_type}' quarantined in TrulyTally HITL Gate. Explicit human approval required before writing to Tally Prime.",
    }


@router.post("/{approval_id}/approve")
def approve_write_action(approval_id: str, payload: ApprovePayload = ApprovePayload()):
    """Human operator signs off on a staged write action, releasing it to Tally."""
    record = HitlStore.approve_action(approval_id, user=payload.reviewer or "Accountant")
    if not record:
        raise HTTPException(status_code=404, detail="Approval record not found")

    return {
        "status": "approved",
        "approval_id": approval_id,
        "action_type": record["action_type"],
        "message": f"Write action approved by {payload.reviewer}. Released to Tally sync queue.",
    }


@router.post("/{approval_id}/reject")
def reject_write_action(approval_id: str, payload: RejectPayload = RejectPayload()):
    """Human operator rejects the proposed write action."""
    HitlStore.reject_action(approval_id, user=payload.reviewer or "Accountant", reason=payload.reason or "Rejected")
    return {
        "status": "rejected",
        "approval_id": approval_id,
        "message": "Write action rejected. Will not be sent to Tally.",
    }


@router.post("/batch-approve")
def batch_approve_actions(approval_ids: List[str], reviewer: str = "Accountant"):
    """Approves multiple staged write actions in a single click."""
    approved_count = 0
    for app_id in approval_ids:
        rec = HitlStore.approve_action(app_id, user=reviewer)
        if rec:
            approved_count += 1

    return {
        "status": "success",
        "approved_count": approved_count,
        "message": f"{approved_count} write action(s) approved and queued for Tally sync.",
    }

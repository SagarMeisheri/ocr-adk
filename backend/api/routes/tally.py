"""TallyPrime Integration & Sync Routes with Deterministic HITL Write Safety."""

from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..storage import InvoiceStore, TallyConnectorStore, HitlStore
from ...tally_bridge.xml_builder import (
    generate_ledger_creation_xml,
    generate_stock_item_creation_xml,
)

router = APIRouter(prefix="/api/tally", tags=["Tally Prime Integration"])


class SyncReportPayload(BaseModel):
    invoice_id: str
    success: bool
    voucher_number: Optional[str] = None
    tally_response: Optional[str] = None
    error_message: Optional[str] = None


class HeartbeatPayload(BaseModel):
    client_id: str
    tally_online: bool
    company_name: str
    error: Optional[str] = None


@router.get("/status")
def get_tally_connection_status():
    """Returns the live connection state of the local Tally connector and active company."""
    status = TallyConnectorStore.get_latest_connector_status()
    return status


@router.post("/invoices/{invoice_id}/sync")
def sync_single_invoice(invoice_id: str, direct_approve: bool = False):
    """Stages or syncs an invoice to TallyPrime under the deterministic HITL safety gate."""
    inv = InvoiceStore.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    tally_xml = inv.get("tally_xml")
    if not tally_xml:
        raise HTTPException(
            status_code=400, detail="Tally XML has not been generated for this invoice"
        )

    # Generate auto-creation XMLs for missing masters if needed
    auto_masters_xml = []
    inv_data = inv.get("invoice_data")
    if inv_data:
        if inv_data.get("auto_create_party_ledger"):
            supplier = inv_data.get("supplier", {})
            party_name = inv_data.get("matched_tally_party_ledger") or supplier.get(
                "name"
            )
            if party_name:
                m_xml = generate_ledger_creation_xml(
                    name=party_name,
                    parent="Sundry Creditors",
                    gstin=supplier.get("gstin"),
                    state=supplier.get("state"),
                    address=supplier.get("address"),
                )
                auto_masters_xml.append(m_xml)
                # Stage master creation in HITL gate
                HitlStore.stage_write_action(
                    action_type="CREATE_LEDGER",
                    reference_id=invoice_id,
                    description=f"Auto-create Sundry Creditor: {party_name} (GSTIN: {supplier.get('gstin', 'N/A')})",
                    payload_xml=m_xml,
                )

        if inv_data.get("auto_create_stock_items"):
            for item in inv_data.get("line_items", []):
                item_name = item.get("matched_tally_stock_item") or item.get(
                    "description"
                )
                if item_name:
                    s_xml = generate_stock_item_creation_xml(
                        name=item_name,
                        base_units=item.get("unit", "Nos"),
                        hsn_code=item.get("hsn_sac"),
                        gst_rate=item.get("gst_rate", 18.0),
                    )
                    auto_masters_xml.append(s_xml)
                    # Stage stock item creation in HITL gate
                    HitlStore.stage_write_action(
                        action_type="CREATE_STOCK_ITEM",
                        reference_id=invoice_id,
                        description=f"Auto-create Stock Item: {item_name} (HSN: {item.get('hsn_sac', 'N/A')})",
                        payload_xml=s_xml,
                    )

    # Stage Purchase Voucher in HITL gate
    desc = f"Purchase Voucher #{inv.get('invoice_number', 'N/A')} from {inv.get('party_name', 'Vendor')} (₹{inv.get('grand_total', 0.0):.2f})"
    approval_id = HitlStore.stage_write_action(
        action_type="POST_PURCHASE_VOUCHER",
        reference_id=invoice_id,
        description=desc,
        payload_xml=tally_xml,
        payload_json=inv_data,
    )

    if direct_approve:
        # User explicitly clicked from Review Studio
        HitlStore.approve_action(approval_id, user="Accountant (Studio)")
        InvoiceStore.update_sync_status(invoice_id, status="syncing")
        return {
            "status": "approved",
            "message": "Invoice approved and released to Tally Prime sync queue.",
            "invoice_id": invoice_id,
            "approval_id": approval_id,
        }

    return {
        "status": "staged",
        "message": "Invoice staged for deterministic human review before write.",
        "invoice_id": invoice_id,
        "approval_id": approval_id,
    }


@router.post("/invoices/batch-sync")
def batch_sync_ready_invoices():
    """Stages all 'auto_ready' invoices in the HITL approval queue for bulk human sign-off."""
    ready_invoices = InvoiceStore.list_invoices(triage_filter="auto_ready")
    staged_count = 0

    for inv in ready_invoices:
        if inv.get("sync_status") != "synced" and inv.get("tally_xml"):
            desc = f"Purchase Voucher #{inv.get('invoice_number', 'N/A')} from {inv.get('party_name', 'Vendor')} (₹{inv.get('grand_total', 0.0):.2f})"
            HitlStore.stage_write_action(
                action_type="POST_PURCHASE_VOUCHER",
                reference_id=inv["id"],
                description=desc,
                payload_xml=inv["tally_xml"],
                payload_json=inv.get("invoice_data"),
            )
            staged_count += 1

    return {
        "status": "success",
        "staged_count": staged_count,
        "message": f"{staged_count} high-confidence vouchers staged for Human-in-the-Loop review and approval.",
    }


# Connector Daemon Communication Endpoints
@router.post("/connector/heartbeat")
def connector_heartbeat(payload: HeartbeatPayload):
    """Heartbeat endpoint for tally_connector.py daemon."""
    TallyConnectorStore.record_heartbeat(
        client_id=payload.client_id,
        tally_online=payload.tally_online,
        company_name=payload.company_name,
        error=payload.error,
    )
    return {"status": "ack"}


@router.get("/connector/pending-sync")
def get_pending_sync_queue():
    """Called by tally_connector.py to fetch human-approved vouchers to post to Port 9000."""
    pending = TallyConnectorStore.get_pending_sync_items()
    return {"pending_vouchers": pending}


@router.post("/connector/report-sync")
def report_sync_result(report: SyncReportPayload):
    """Called by tally_connector.py after attempting to post to Port 9000."""
    TallyConnectorStore.remove_from_pending(report.invoice_id)
    new_status = "synced" if report.success else "failed"
    InvoiceStore.update_sync_status(
        id=report.invoice_id,
        status=new_status,
        voucher_number=report.voucher_number,
        error_message=report.error_message,
    )
    return {"status": "recorded"}

"""Bank Statement Processing and Reconciliation Routes."""

from __future__ import annotations
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from pydantic import BaseModel

from ...adk_engine.extractor import HybridExtractor
from ...tally_bridge.xml_builder import (
    generate_tally_bank_payment_voucher_xml,
    generate_tally_bank_receipt_voucher_xml,
    generate_tally_bank_contra_voucher_xml,
)
from ..storage import BankStore, HitlStore

router = APIRouter(prefix="/api/banking", tags=["Bank Statement Processing"])

UPLOAD_DIR = Path("uploads") / "banking"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

extractor = HybridExtractor()


class UpdateTransactionPayload(BaseModel):
    suggested_voucher_type: Optional[str] = None
    matched_counter_ledger: Optional[str] = None
    approval_status: Optional[str] = None


@router.post("/upload")
async def upload_bank_statement(file: UploadFile = File(...)):
    """Uploads and parses single or multi-page bank statement PDFs."""
    statement_id = str(uuid.uuid4())
    ext = Path(file.filename or "statement.pdf").suffix.lower()
    saved_filename = f"bank_{statement_id}{ext}"
    target_path = UPLOAD_DIR / saved_filename

    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        statement = extractor.extract_bank_statement(str(target_path))
        statement.id = statement_id

        BankStore.save_statement(
            statement_id=statement_id,
            filename=file.filename or saved_filename,
            filepath=str(target_path),
            statement_data=statement.model_dump(),
            raw_markdown=statement.raw_markdown,
        )

        return {
            "status": "success",
            "statement_id": statement_id,
            "bank_name": statement.bank_name,
            "account_number": statement.account_number,
            "transaction_count": len(statement.transactions),
            "total_debits": statement.total_debits,
            "total_credits": statement.total_credits,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process bank statement: {str(e)}"
        )


@router.get("/statements")
def list_bank_statements():
    """Lists all uploaded bank statements."""
    return {"statements": BankStore.list_statements()}


@router.get("/statements/{statement_id}")
def get_bank_statement_details(statement_id: str):
    """Fetches statement summary and all extracted transaction rows."""
    st = BankStore.get_statement_with_transactions(statement_id)
    if not st:
        raise HTTPException(status_code=404, detail="Bank statement not found")
    return st


@router.put("/transactions/{txn_id}")
def update_bank_transaction(txn_id: str, payload: UpdateTransactionPayload):
    """Allows accountant to change counter-ledger or voucher type."""
    BankStore.update_transaction(txn_id, payload.model_dump(exclude_none=True))
    return {"status": "success", "txn_id": txn_id}


@router.post("/transactions/{txn_id}/stage-for-sync")
def stage_transaction_for_sync(txn_id: str, statement_id: str = Body(..., embed=True)):
    """Deterministically stages a single bank transaction into the HITL approval queue."""
    st = BankStore.get_statement_with_transactions(statement_id)
    if not st:
        raise HTTPException(status_code=404, detail="Statement not found")

    txn_dict = next((t for t in st["transactions"] if t["id"] == txn_id), None)
    if not txn_dict:
        raise HTTPException(status_code=404, detail="Transaction not found")

    from ...adk_engine.models import BankTransaction

    txn = BankTransaction.model_validate(txn_dict)
    bank_ledger = st.get("tally_bank_ledger") or "Bank Account"

    # Generate appropriate voucher XML
    if txn.suggested_voucher_type == "Contra":
        xml_payload = generate_tally_bank_contra_voucher_xml(
            txn, bank_ledger=bank_ledger
        )
        action_type = "POST_BANK_CONTRA"
    elif txn.withdrawal_dr > 0:
        xml_payload = generate_tally_bank_payment_voucher_xml(
            txn, bank_ledger=bank_ledger
        )
        action_type = "POST_BANK_PAYMENT"
    else:
        xml_payload = generate_tally_bank_receipt_voucher_xml(
            txn, bank_ledger=bank_ledger
        )
        action_type = "POST_BANK_RECEIPT"

    desc = f"{txn.suggested_voucher_type} Voucher: {txn.narration[:40]} (₹{txn.withdrawal_dr or txn.deposit_cr:.2f})"

    approval_id = HitlStore.stage_write_action(
        action_type=action_type,
        reference_id=txn_id,
        description=desc,
        payload_xml=xml_payload,
        payload_json=txn.model_dump(),
    )

    BankStore.update_transaction(txn_id, {"approval_status": "staged"})

    return {
        "status": "staged",
        "approval_id": approval_id,
        "message": "Transaction staged for deterministic human approval before writing to Tally.",
    }


@router.post("/statements/{statement_id}/stage-all-for-sync")
def stage_all_transactions_for_sync(statement_id: str):
    """Stages all transactions from a bank statement into the HITL approval queue."""
    st = BankStore.get_statement_with_transactions(statement_id)
    if not st:
        raise HTTPException(status_code=404, detail="Statement not found")

    from ...adk_engine.models import BankTransaction

    staged_count = 0
    bank_ledger = st.get("tally_bank_ledger") or "Bank Account"

    for t_dict in st["transactions"]:
        if t_dict.get("approval_status") != "synced":
            txn = BankTransaction.model_validate(t_dict)
            if txn.suggested_voucher_type == "Contra":
                xml_payload = generate_tally_bank_contra_voucher_xml(
                    txn, bank_ledger=bank_ledger
                )
                action_type = "POST_BANK_CONTRA"
            elif txn.withdrawal_dr > 0:
                xml_payload = generate_tally_bank_payment_voucher_xml(
                    txn, bank_ledger=bank_ledger
                )
                action_type = "POST_BANK_PAYMENT"
            else:
                xml_payload = generate_tally_bank_receipt_voucher_xml(
                    txn, bank_ledger=bank_ledger
                )
                action_type = "POST_BANK_RECEIPT"

            desc = f"{txn.suggested_voucher_type} Voucher: {txn.narration[:40]} (₹{txn.withdrawal_dr or txn.deposit_cr:.2f})"
            HitlStore.stage_write_action(
                action_type=action_type,
                reference_id=txn.id,
                description=desc,
                payload_xml=xml_payload,
                payload_json=txn.model_dump(),
            )
            BankStore.update_transaction(txn.id, {"approval_status": "staged"})
            staged_count += 1

    return {
        "status": "success",
        "staged_count": staged_count,
        "message": f"Staged {staged_count} bank transaction vouchers for human approval.",
    }

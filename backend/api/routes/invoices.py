"""Invoice Management and OCR Extraction Routes."""

from __future__ import annotations
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.responses import Response

from ...adk_engine.models import ExtractedInvoice
from ...adk_engine.workflow import InvoiceProcessingPipeline
from ...adk_engine.validator import validate_extracted_invoice
from ...tally_bridge.xml_builder import generate_tally_purchase_voucher_xml
from ..storage import InvoiceStore, DocumentStore

router = APIRouter(prefix="/api/invoices", tags=["Invoices"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

pipeline = InvoiceProcessingPipeline()


@router.post("/upload")
async def upload_invoices(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
):
    """Batch upload invoices (PDFs, JPGs, PNGs, WhatsApp photos, handwritten bills)."""
    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []

    for file_item in upload_list:
        invoice_id = str(uuid.uuid4())
        ext = Path(file_item.filename or "invoice.pdf").suffix.lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".tiff"]:
            ext = ".pdf"

        saved_filename = f"{invoice_id}{ext}"
        target_path = UPLOAD_DIR / saved_filename

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file_item.file, buffer)

        print(
            f"[ADK Pipeline] Starting processing for {file_item.filename} ({saved_filename})..."
        )

        # Process invoice through Google ADK multi-stage pipeline
        try:
            invoice_obj, tally_xml = pipeline.process_invoice(str(target_path))
            print(
                f"[ADK Pipeline] Successfully extracted {invoice_obj.invoice_number} (Total: ₹{invoice_obj.summary.grand_total})"
            )

            # Store in database
            InvoiceStore.save_invoice(
                id=invoice_id,
                filename=file_item.filename or saved_filename,
                filepath=str(target_path),
                content_type=file_item.content_type or "application/pdf",
                invoice_data=invoice_obj.model_dump(),
                tally_xml=tally_xml,
                status="extracted",
            )

            # Mirror in DocumentStore
            DocumentStore.save_document(
                id=invoice_id,
                filename=file_item.filename or saved_filename,
                filepath=str(target_path),
                content_type=file_item.content_type or "application/pdf",
                doc_type="invoice",
                title=f"Invoice from {invoice_obj.supplier.name}",
                document_number=invoice_obj.invoice_number,
                date=invoice_obj.invoice_date,
                parties={
                    "issuer": invoice_obj.supplier.model_dump(),
                    "recipient": invoice_obj.buyer.model_dump()
                    if invoice_obj.buyer
                    else {},
                },
                summary=invoice_obj.summary.model_dump(),
                items=[i.model_dump() for i in invoice_obj.line_items],
                raw_markdown=invoice_obj.raw_markdown or "",
                confidence_score=invoice_obj.validation.confidence_score
                if invoice_obj.validation
                else 0.95,
                status="extracted",
                tally_xml=tally_xml,
                tags=["invoice", "gst"],
            )

            results.append(
                {
                    "id": invoice_id,
                    "filename": file_item.filename or saved_filename,
                    "status": "extracted",
                    "invoice_number": invoice_obj.invoice_number,
                    "grand_total": invoice_obj.summary.grand_total,
                    "triage_status": invoice_obj.validation.triage_status
                    if invoice_obj.validation
                    else "needs_attention",
                    "confidence_score": invoice_obj.validation.confidence_score
                    if invoice_obj.validation
                    else 0.0,
                }
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"[ADK Pipeline Error] Failed to extract {file_item.filename}: {e}")
            results.append(
                {
                    "id": invoice_id,
                    "filename": file_item.filename or saved_filename,
                    "status": "error",
                    "error": str(e),
                }
            )

    return {"uploaded_count": len(results), "invoices": results, "results": results}


@router.get("")
def list_invoices(
    triage: Optional[str] = Query(
        None,
        description="Filter by triage queue: auto_ready, quick_review, needs_attention, synced",
    )
):
    """Retrieves invoices organized by Tri-Queue triage status."""
    return {"invoices": InvoiceStore.list_invoices(triage_filter=triage)}


@router.get("/{invoice_id}")
def get_invoice(invoice_id: str):
    """Fetches details for a single invoice."""
    inv = InvoiceStore.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@router.put("/{invoice_id}")
def update_invoice(invoice_id: str, updated_data: ExtractedInvoice):
    """Allows accountant to edit invoice fields in Review Studio and recalculates audit checks."""
    existing = InvoiceStore.get_invoice(invoice_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Re-run deterministic tax math validation
    val_result = validate_extracted_invoice(updated_data)
    updated_data.validation = val_result

    # Rebuild Tally XML payload
    new_xml = generate_tally_purchase_voucher_xml(updated_data)

    InvoiceStore.save_invoice(
        id=invoice_id,
        filename=existing["filename"],
        filepath=existing["filepath"],
        content_type=existing["content_type"],
        invoice_data=updated_data.model_dump(),
        tally_xml=new_xml,
        status="verified",
    )

    return {
        "status": "success",
        "invoice_id": invoice_id,
        "validation": val_result.model_dump(),
        "tally_xml": new_xml,
    }


@router.delete("/{invoice_id}")
def delete_invoice(invoice_id: str):
    """Deletes an invoice and its file."""
    inv = InvoiceStore.get_invoice(invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if os.path.exists(inv["filepath"]):
        try:
            os.remove(inv["filepath"])
        except Exception:
            pass

    InvoiceStore.delete_invoice(invoice_id)
    return {"status": "success", "message": f"Invoice {invoice_id} deleted"}


@router.get("/{invoice_id}/download-xml")
def download_tally_xml(invoice_id: str):
    """Downloads the TallyPrime F9 Purchase Voucher XML file directly."""
    inv = InvoiceStore.get_invoice(invoice_id)
    if not inv or not inv.get("tally_xml"):
        raise HTTPException(
            status_code=404, detail="Tally XML not found for this invoice"
        )

    filename = f"tally_voucher_{inv.get('invoice_number', invoice_id)}.xml"
    return Response(
        content=inv["tally_xml"],
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

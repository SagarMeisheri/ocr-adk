"""Unified Document Processing Routes for Invoices, Bank Statements, Receipts, and Bills."""

from __future__ import annotations
import uuid
import shutil
import asyncio
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse

from ...adk_engine.extractor import HybridExtractor
from ...adk_engine.models import ParsedDocument
from ...adk_engine.workflow import UniversalDocumentPipeline, InvoiceProcessingPipeline
from ..storage import DocumentStore, InvoiceStore, BankStore
from .websocket import ws_manager

router = APIRouter(prefix="/api/documents", tags=["Universal Documents"])

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

universal_pipeline = UniversalDocumentPipeline()
invoice_pipeline = InvoiceProcessingPipeline()


@router.post("/upload")
async def upload_documents(
    files: Optional[List[UploadFile]] = File(None),
    file: Optional[UploadFile] = File(None),
):
    """Universal upload endpoint accepting any financial document (PDF, PNG, JPG, JPEG, WEBP)."""
    upload_list: List[UploadFile] = []
    if files:
        upload_list.extend(files)
    if file:
        upload_list.append(file)

    if not upload_list:
        raise HTTPException(status_code=400, detail="No files uploaded")

    results = []
    loop = asyncio.get_event_loop()

    for file_item in upload_list:
        doc_id = str(uuid.uuid4())
        ext = Path(file_item.filename or "document.pdf").suffix.lower()
        if ext not in [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".tiff"]:
            ext = ".pdf"

        saved_filename = f"{doc_id}{ext}"
        target_path = UPLOAD_DIR / saved_filename

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file_item.file, buffer)

        print(
            f"[ADK Engine] Ingesting document: {file_item.filename} -> {saved_filename}"
        )

        def step_callback(step_id: str, status: str, details: dict):
            try:
                if loop.is_running():
                    loop.create_task(
                        ws_manager.broadcast(
                            {
                                "type": "WORKFLOW_STEP_UPDATE",
                                "document_id": doc_id,
                                "filename": file_item.filename or saved_filename,
                                "step_id": step_id,
                                "status": status,
                                "details": details,
                            }
                        )
                    )
            except Exception:
                pass

        try:
            # Process via ADK Universal Visual Transcription Workflow with step events
            parsed_doc, tally_xml, wf = universal_pipeline.process_document(
                file_path=str(target_path),
                doc_id=doc_id,
                filename=file_item.filename or saved_filename,
                step_callback=step_callback,
            )

            # Save in unified DocumentStore with complete workflow execution trace
            DocumentStore.save_document(
                id=doc_id,
                filename=file_item.filename or saved_filename,
                filepath=str(target_path),
                content_type=file_item.content_type or "application/pdf",
                doc_type="document",
                title=parsed_doc.title,
                document_number=parsed_doc.document_number,
                date=parsed_doc.date,
                parties=parsed_doc.parties,
                summary=parsed_doc.summary,
                items=parsed_doc.items,
                raw_markdown=parsed_doc.raw_markdown,
                confidence_score=parsed_doc.confidence_score,
                status="transcribed",
                tally_xml=None,
                tags=parsed_doc.tags,
                workflow_execution=wf.model_dump() if wf else None,
                validation=None,
                thinking_process=parsed_doc.thinking_process,
                thoughts_token_count=parsed_doc.thoughts_token_count or 0,
            )

            print(
                f"[ADK Engine] Transcribed: {parsed_doc.title} ({len(parsed_doc.raw_markdown)} chars markdown)"
            )

            results.append(
                {
                    "id": doc_id,
                    "filename": file_item.filename or saved_filename,
                    "file_url": f"/api/documents/{doc_id}/file",
                    "doc_type": "document",
                    "title": parsed_doc.title,
                    "document_number": parsed_doc.document_number,
                    "date": parsed_doc.date,
                    "raw_markdown": parsed_doc.raw_markdown,
                    "thinking_process": parsed_doc.thinking_process,
                    "thoughts_token_count": parsed_doc.thoughts_token_count or 0,
                    "confidence_score": parsed_doc.confidence_score,
                    "status": "transcribed",
                    "workflow_execution": wf.model_dump() if wf else None,
                }
            )


        except Exception as e:
            import traceback

            traceback.print_exc()
            print(f"[ADK Engine Error] Failed processing {file_item.filename}: {e}")
            results.append(
                {
                    "id": doc_id,
                    "filename": file_item.filename or saved_filename,
                    "status": "error",
                    "error": str(e),
                }
            )

    return {"uploaded_count": len(results), "documents": results, "results": results}


@router.get("/{document_id}/file")
def get_document_file(document_id: str):
    """Streams the source document file (PDF, Image, WebP) directly with correct MIME type."""
    doc = DocumentStore.get_document(document_id)
    filepath = None
    content_type = None

    if doc:
        filepath = doc.get("filepath")
        content_type = doc.get("content_type")
    else:
        # Fallback to InvoiceStore
        inv = InvoiceStore.get_invoice(document_id)
        if inv:
            filepath = inv.get("filepath")
            content_type = inv.get("content_type")

    # If filepath on disk exists, serve it
    if filepath and Path(filepath).exists():
        if not content_type or content_type == "application/octet-stream":
            import mimetypes
            content_type, _ = mimetypes.guess_type(filepath)
        return FileResponse(filepath, media_type=content_type or "application/pdf")

    # Otherwise scan uploads/ for document_id
    matches = list(UPLOAD_DIR.glob(f"{document_id}.*"))
    if matches:
        import mimetypes
        guess_type, _ = mimetypes.guess_type(str(matches[0]))
        return FileResponse(str(matches[0]), media_type=guess_type or "application/pdf")

    raise HTTPException(status_code=404, detail="Source document file not found")


@router.get("/{document_id}/workflow")
def get_document_workflow(document_id: str):
    """Retrieve detailed execution trace of the ADK workflow graph for a document."""
    doc = DocumentStore.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    wf = doc.get("workflow_execution")
    if not wf:
        from ...adk_engine.workflow import create_initial_workflow_execution
        wf = create_initial_workflow_execution(document_id, doc.get("filename")).model_dump()
        wf["status"] = "completed"
        for s in wf["steps"]:
            s["status"] = "completed"
    return {"document_id": document_id, "workflow": wf}


@router.get("")
def list_documents(
    type: Optional[str] = Query(
        None,
        description="Filter by document type: all, invoice, bank_statement, receipt, bill, other",
    )
):
    """List all extracted documents with optional category filtering."""
    docs = DocumentStore.list_documents(doc_type_filter=type)
    for d in docs:
        d["file_url"] = f"/api/documents/{d['id']}/file"
    return {"documents": docs, "total": len(docs)}


@router.get("/{document_id}")
def get_document(document_id: str):
    """Retrieve full extracted details for a single document."""
    doc = DocumentStore.get_document(document_id)
    if not doc:
        # Fallback to InvoiceStore if created via legacy route
        inv = InvoiceStore.get_invoice(document_id)
        if inv:
            return {
                "id": inv["id"],
                "filename": inv["filename"],
                "filepath": inv["filepath"],
                "file_url": f"/api/documents/{inv['id']}/file",
                "doc_type": "invoice",
                "title": f"Tax Invoice - {inv.get('party_name', 'Supplier')}",
                "document_number": inv.get("invoice_number"),
                "date": inv.get("invoice_date"),
                "summary": {
                    "taxable_value": inv.get("taxable_value", 0.0),
                    "total_tax": inv.get("total_tax", 0.0),
                    "grand_total": inv.get("grand_total", 0.0),
                },
                "parties": {
                    "issuer": {
                        "name": inv.get("party_name"),
                        "tax_id": inv.get("party_gstin"),
                    }
                },
                "items": inv.get("invoice_data", {}).get("line_items", [])
                if inv.get("invoice_data")
                else [],
                "raw_markdown": inv.get("raw_markdown", ""),
                "confidence_score": inv.get("confidence_score", 0.95),
                "status": inv.get("status", "extracted"),
                "tally_xml": inv.get("tally_xml"),
            }
        raise HTTPException(status_code=404, detail="Document not found")
    doc["file_url"] = f"/api/documents/{doc['id']}/file"
    return doc


@router.delete("/{document_id}")
def delete_document(document_id: str):
    """Deletes a document from the store."""
    doc = DocumentStore.get_document(document_id)
    if doc and doc.get("filepath"):
        try:
            p = Path(doc["filepath"])
            if p.exists():
                p.unlink()
        except Exception:
            pass
    deleted = DocumentStore.delete_document(document_id)
    InvoiceStore.delete_invoice(document_id)
    return {"status": "deleted", "id": document_id, "success": deleted}

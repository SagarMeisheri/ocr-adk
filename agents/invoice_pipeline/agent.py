"""Google ADK 2.0 Root Agent for Invoice Processing & Validation Pipeline."""

import sys
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from google.adk import Agent
from backend.adk_engine.workflow import (
    UniversalDocumentPipeline,
    DEFAULT_AGENT_TIMEOUT,
    DEFAULT_MAX_VALIDATION_QUERIES,
    make_tool_call_limiter,
)
from backend.adk_engine.validation_tools import (
    calculate,
    calculate_batch,
    query_tally_party_by_gstin,
    query_tally_duplicate_voucher,
    is_tally_connected,
)
from backend.adk_engine.validator import validate_gstin


def validate_invoice_document(file_path: str) -> str:
    """Executes the complete ADK 2.0 multi-stage graph pipeline on an invoice file.

    Performs multimodal OCR, AST batch math proof, GSTIN Luhn checksum, Tally ERP ledger
    matching, duplicate checking, and stages the Tally purchase voucher.

    Args:
        file_path: Relative or absolute path to the invoice document (e.g. 'uploads/sample.webp')

    Returns:
        A structured Markdown report of the complete validation findings.
    """
    path = Path(file_path)
    if not path.exists():
        return f"Error: File not found at path '{file_path}'"

    doc_id = str(uuid.uuid4())
    pipeline = UniversalDocumentPipeline()
    parsed_doc, tally_xml, wf = pipeline.process_document(
        file_path=str(path),
        doc_id=doc_id,
        filename=path.name,
    )

    val = parsed_doc.validation or {}
    math_chk = val.get("math_check") or {}
    tally_chk = val.get("tally_check") or {}
    triage = val.get("triage_status", "unknown").upper()

    report = [
        f"# Invoice Validation Report: {parsed_doc.title}",
        f"- **Document ID**: `{doc_id}`",
        f"- **Confidence**: {parsed_doc.confidence_score * 100:.0f}%",
        f"- **Triage Status**: **{triage}**",
        f"- **Tally Voucher Staged**: {'Yes' if tally_xml else 'No'}",
        "",
        "## Math Verification (AST Proof)",
        f"- Status: {'PASSED' if math_chk.get('is_valid') else 'DISCREPANCY DETECTED'}",
        f"- Calculated Total: ₹{math_chk.get('calculated_grand_total', 0.0):,.2f}",
        f"- Discrepancy Amount: ₹{math_chk.get('discrepancy_amount', 0.0):,.2f}",
        "",
        "## Tally & GST Compliance",
        f"- Status: {'Online / Verified' if tally_chk.get('tally_connection_mode') != 'offline' else 'Offline / Skipped'}",
        f"- Supplier GSTIN: `{val.get('supplier_gstin_check', {}).get('gstin', 'N/A')}`",
        f"- Matched Ledger: `{tally_chk.get('party_ledger_name') or 'Auto-Create (Offline)'}`",
        f"- Duplicate Voucher: {'YES' if tally_chk.get('duplicate_invoice_found') else 'NO'}",
    ]

    return "\n".join(report)


tally_online = is_tally_connected()
pipeline_tools = [
    validate_invoice_document,
    calculate_batch,
    calculate,
    validate_gstin,
]
if tally_online:
    pipeline_tools.extend([
        query_tally_party_by_gstin,
        query_tally_duplicate_voucher,
    ])

invoice_pipeline_agent = Agent(
    name="invoice_pipeline_agent",
    description="Google ADK 2.0 universal invoice processing and validation agent",
    instruction=(
        "You are the Invoice Pipeline Agent. When given an invoice file path, call the "
        "validate_invoice_document tool to execute the multi-stage OCR and AST math validation workflow. "
        + (
            "Verify Tally ledgers, duplicate vouchers, and GSTIN checksums using available Tally tools."
            if tally_online
            else "Tally ERP and GSTIN validations are turned off because Tally is offline. Only AST math validations are active to conserve Gemini API calls."
        )
    ),
    tools=pipeline_tools,
    before_tool_callback=make_tool_call_limiter(DEFAULT_MAX_VALIDATION_QUERIES),
)

root_agent = invoice_pipeline_agent

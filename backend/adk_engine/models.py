"""Data models for Indian GST Invoice OCR, Multi-Page Bank Statements, and Tally integration."""

from __future__ import annotations
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import date, datetime
import uuid


class InvoiceParty(BaseModel):
    name: str = Field(..., description="Legal business or trade name")
    gstin: Optional[str] = Field(None, description="15-character Indian GSTIN")
    pan: Optional[str] = Field(
        None, description="10-character Indian Permanent Account Number"
    )
    address: Optional[str] = Field(None, description="Registered business address")
    state: Optional[str] = Field(
        None, description="State name e.g. Maharashtra, Karnataka"
    )
    state_code: Optional[str] = Field(
        None, description="2-digit GST state code e.g. 27, 29"
    )
    phone: Optional[str] = Field(None, description="Contact phone or WhatsApp number")
    email: Optional[str] = Field(None, description="Billing email address")


class InvoiceLineItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    description: str = Field(..., description="Item or service description")
    hsn_sac: Optional[str] = Field(None, description="4, 6, or 8 digit HSN/SAC code")
    quantity: float = Field(default=1.0, description="Billed quantity")
    unit: str = Field(
        default="Nos", description="Unit of measurement e.g. Nos, Kgs, Pcs, Box"
    )
    rate: float = Field(default=0.0, description="Unit rate/price before tax")
    discount: float = Field(default=0.0, description="Discount amount")
    taxable_value: float = Field(
        default=0.0, description="Taxable amount after discount"
    )
    gst_rate: float = Field(
        default=18.0, description="GST slab percentage e.g. 0, 5, 12, 18, 28"
    )
    cgst_amount: float = Field(default=0.0, description="Central GST amount")
    sgst_amount: float = Field(default=0.0, description="State GST amount")
    igst_amount: float = Field(default=0.0, description="Integrated GST amount")
    cess_amount: float = Field(default=0.0, description="Cess amount if applicable")
    total_amount: float = Field(
        default=0.0, description="Line item total including taxes"
    )
    matched_tally_stock_item: Optional[str] = Field(
        None, description="Matched Tally Stock Item name"
    )
    matched_tally_purchase_ledger: Optional[str] = Field(
        None, description="Matched Tally Purchase ledger"
    )


class InvoiceSummary(BaseModel):
    total_taxable_value: float = Field(default=0.0, description="Sum of taxable values")
    total_cgst: float = Field(default=0.0, description="Total CGST")
    total_sgst: float = Field(default=0.0, description="Total SGST")
    total_igst: float = Field(default=0.0, description="Total IGST")
    total_cess: float = Field(default=0.0, description="Total Cess")
    round_off: float = Field(default=0.0, description="Round off adjustment amount")
    grand_total: float = Field(default=0.0, description="Final payable invoice amount")


class MathValidationDetail(BaseModel):
    is_valid: bool = True
    line_item_math_valid: bool = True
    tax_math_valid: bool = True
    grand_total_math_valid: bool = True
    intra_inter_state_valid: bool = True
    calculated_taxable: float = 0.0
    calculated_taxes: float = 0.0
    calculated_grand_total: float = 0.0
    discrepancy_amount: float = 0.0
    notes: List[str] = Field(default_factory=list)


class GstinValidationDetail(BaseModel):
    gstin: Optional[str] = None
    is_valid_format: bool = False
    is_checksum_valid: bool = False
    state_code: Optional[str] = None
    pan: Optional[str] = None
    state_name: Optional[str] = None
    error_message: Optional[str] = None


class ValidationResult(BaseModel):
    is_fully_valid: bool = False
    supplier_gstin_check: GstinValidationDetail = Field(
        default_factory=GstinValidationDetail
    )
    buyer_gstin_check: GstinValidationDetail = Field(
        default_factory=GstinValidationDetail
    )
    math_check: MathValidationDetail = Field(default_factory=MathValidationDetail)
    confidence_score: float = Field(
        default=0.0, description="Overall confidence 0.0 - 1.0"
    )
    triage_status: Literal[
        "auto_ready", "quick_review", "needs_attention"
    ] = "needs_attention"
    warnings: List[str] = Field(default_factory=list)


class ExtractedInvoice(BaseModel):
    invoice_number: Optional[str] = Field(None, description="Invoice or Bill number")
    invoice_date: Optional[str] = Field(None, description="Invoice date (YYYY-MM-DD)")
    due_date: Optional[str] = Field(None, description="Payment due date (YYYY-MM-DD)")
    place_of_supply: Optional[str] = Field(None, description="Place of supply state")
    is_reverse_charge: bool = Field(
        default=False, description="Whether reverse charge is applicable"
    )
    document_type: Literal[
        "tax_invoice",
        "bill_of_supply",
        "cash_memo",
        "delivery_challan",
        "handwritten_bill",
    ] = "tax_invoice"

    supplier: InvoiceParty
    buyer: Optional[InvoiceParty] = None

    line_items: List[InvoiceLineItem] = Field(default_factory=list)
    summary: InvoiceSummary = Field(default_factory=InvoiceSummary)

    raw_text: Optional[str] = None
    raw_markdown: Optional[str] = None
    validation: Optional[ValidationResult] = None
    matched_tally_party_ledger: Optional[str] = None
    auto_create_party_ledger: bool = True
    auto_create_stock_items: bool = True


# ==========================================
# Bank Statement Models (Multi-Page PDFs)
# ==========================================


class BankTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    transaction_date: str = Field(..., description="Transaction date (YYYY-MM-DD)")
    narration: str = Field(..., description="Transaction narration / description")
    chq_ref_no: Optional[str] = Field(
        None, description="Cheque or reference/UTR number"
    )
    withdrawal_dr: float = Field(default=0.0, description="Debit / withdrawal amount")
    deposit_cr: float = Field(default=0.0, description="Credit / deposit amount")
    balance: float = Field(default=0.0, description="Closing balance after transaction")
    suggested_voucher_type: Literal[
        "Payment", "Receipt", "Contra", "Journal"
    ] = "Payment"
    matched_counter_ledger: Optional[str] = Field(
        None, description="Suggested counterparty or expense/income ledger"
    )
    approval_status: Literal["staged", "approved", "rejected", "synced"] = "staged"


class BankStatement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    bank_name: str = Field(
        default="Bank Account", description="e.g. HDFC Bank, ICICI Bank, SBI"
    )
    account_number: Optional[str] = Field(
        None, description="Account number (masked or unmasked)"
    )
    account_type: str = Field(
        default="Current Account", description="Savings or Current"
    )
    tally_bank_ledger: str = Field(
        default="Bank Account", description="Tally Ledger name for this bank account"
    )
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    opening_balance: float = 0.0
    closing_balance: float = 0.0
    total_debits: float = 0.0
    total_credits: float = 0.0
    transactions: List[BankTransaction] = Field(default_factory=list)
    raw_markdown: Optional[str] = None


# ==========================================
# Deterministic HITL (Human-in-the-Loop) Gate
# ==========================================


class HITLApprovalRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    action_type: Literal[
        "CREATE_LEDGER",
        "CREATE_STOCK_ITEM",
        "POST_PURCHASE_VOUCHER",
        "POST_BANK_PAYMENT",
        "POST_BANK_RECEIPT",
        "POST_BANK_CONTRA",
        "MCP_LEDGER_CREATE_UPDATE",
        "MCP_DELETE_MASTER",
    ]
    reference_id: str = Field(..., description="Invoice ID or Bank Transaction ID")
    target_company: str = Field(default="Active Tally Company")
    description: str = Field(
        ..., description="Human-readable description of what will be written to Tally"
    )
    payload_xml: str = Field(
        ..., description="Exact Tally XML envelope staged for writing"
    )
    payload_json: Optional[Dict[str, Any]] = None
    status: Literal[
        "PENDING_HUMAN_APPROVAL", "APPROVED", "REJECTED", "EXECUTED", "FAILED"
    ] = "PENDING_HUMAN_APPROVAL"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[str] = None
    tally_response_xml: Optional[str] = None
    error_message: Optional[str] = None


class TallySyncStatus(BaseModel):
    status: Literal["pending", "syncing", "synced", "failed"] = "pending"
    synced_at: Optional[str] = None
    voucher_number: Optional[str] = None
    tally_response_xml: Optional[str] = None
    error_message: Optional[str] = None
    auto_created_masters: List[str] = Field(default_factory=list)


class InvoiceRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    original_filepath: str
    content_type: str
    uploaded_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    status: Literal[
        "uploaded", "extracting", "extracted", "verified", "synced", "error"
    ] = "uploaded"
    invoice_data: Optional[ExtractedInvoice] = None
    tally_sync: TallySyncStatus = Field(default_factory=TallySyncStatus)


class ParsedDocument(BaseModel):
    """Unified document representation across invoices, bank statements, receipts, and other docs."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    doc_type: str = Field(
        default="document", description="Document type or category"
    )
    title: str = Field(
        default="Document", description="Document title, vendor or business name"
    )
    document_number: Optional[str] = Field(
        None, description="Invoice #, Receipt #, Txn #, Account #, or Bill #"
    )
    date: Optional[str] = Field(None, description="Document date YYYY-MM-DD")
    parties: Dict[str, Any] = Field(
        default_factory=dict,
        description="Issuer, Counterparty, Bank, or Vendor details",
    )
    summary: Dict[str, Any] = Field(
        default_factory=dict,
        description="Totals, taxes, subtotals, or account balances",
    )
    items: List[Dict[str, Any]] = Field(
        default_factory=list, description="Line items or transaction rows"
    )
    raw_markdown: str = Field(
        default="", description="Markdown representation of extracted tables"
    )
    thinking_process: List[str] = Field(
        default_factory=list,
        description="Reasoning summaries and thought steps emitted by Gemini thinking process",
    )
    thoughts_token_count: Optional[int] = Field(
        default=0,
        description="Total tokens consumed during model reasoning/thinking process",
    )
    confidence_score: float = Field(
        default=0.95, description="Extraction confidence score 0.0 to 1.0"
    )
    tags: List[str] = Field(default_factory=list, description="Categorization tags")
    notes: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    workflow_execution: Optional[WorkflowExecution] = None
    validation: Optional[Dict[str, Any]] = None
    tally_xml: Optional[str] = None



class WorkflowStep(BaseModel):
    """Represents an individual node in the Google ADK workflow graph."""

    step_id: str = Field(..., description="Unique step identifier e.g. document_ingestion")
    name: str = Field(..., description="Human-readable node label")
    stage: int = Field(..., description="Stage sequence number (1-5)")
    status: Literal["pending", "running", "completed", "failed", "skipped"] = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class WorkflowExecution(BaseModel):
    """Execution state and trace of the Google ADK multi-stage graph workflow."""

    workflow_name: str = "google_adk_universal_document_graph"
    document_id: str
    filename: Optional[str] = None
    current_step_id: Optional[str] = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    total_duration_ms: Optional[float] = None
    steps: List[WorkflowStep] = Field(default_factory=list)
    confidence_score: float = 0.0


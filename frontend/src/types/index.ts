export interface InvoiceParty {
  name: string;
  gstin?: string;
  pan?: string;
  address?: string;
  state?: string;
  state_code?: string;
  phone?: string;
  email?: string;
}

export interface InvoiceLineItem {
  id: string;
  description: string;
  hsn_sac?: string;
  quantity: number;
  unit: string;
  rate: number;
  discount: number;
  taxable_value: number;
  gst_rate: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  cess_amount?: number;
  total_amount: number;
  matched_tally_stock_item?: string;
  matched_tally_purchase_ledger?: string;
}

export interface InvoiceSummary {
  total_taxable_value: number;
  total_cgst: number;
  total_sgst: number;
  total_igst: number;
  total_cess: number;
  round_off: number;
  grand_total: number;
}

export interface GstinValidationDetail {
  gstin?: string;
  is_valid_format: boolean;
  is_checksum_valid: boolean;
  state_code?: string;
  pan?: string;
  state_name?: string;
  error_message?: string;
}

export interface MathValidationDetail {
  is_valid: boolean;
  line_item_math_valid: boolean;
  tax_math_valid: boolean;
  grand_total_math_valid: boolean;
  intra_inter_state_valid: boolean;
  calculated_taxable: number;
  calculated_taxes: number;
  calculated_grand_total: number;
  discrepancy_amount: number;
  notes: string[];
}

export interface ReActTrajectoryStep {
  turn: number;
  step_name: string;
  action: string;
  input: Record<string, any>;
  output: Record<string, any>;
  reasoning: string;
}

export interface TallyValidationDetail {
  is_valid: boolean;
  party_ledger_found: boolean;
  party_ledger_name?: string;
  duplicate_invoice_found: boolean;
  existing_voucher_number?: string;
  stock_items_matched_count: number;
  total_stock_items_count: number;
  tally_connection_mode: string;
  notes: string[];
  react_trajectory?: ReActTrajectoryStep[];
}

export interface ValidationResult {
  is_fully_valid: boolean;
  supplier_gstin_check: GstinValidationDetail;
  buyer_gstin_check: GstinValidationDetail;
  math_check: MathValidationDetail;
  tally_check?: TallyValidationDetail;
  reconciliation_notes?: string[];
  revision_count?: number;
  confidence_score: number;
  triage_status: 'auto_ready' | 'quick_review' | 'needs_attention';
  warnings: string[];
  regulatory_audit_snapshot?: Record<string, any>;
  bfsi_compliance_mode?: string;
}

export interface ExtractedInvoice {
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  place_of_supply?: string;
  is_reverse_charge: boolean;
  document_type: string;
  supplier: InvoiceParty;
  buyer?: InvoiceParty;
  line_items: InvoiceLineItem[];
  summary: InvoiceSummary;
  raw_text?: string;
  raw_markdown?: string;
  validation?: ValidationResult;
  matched_tally_party_ledger?: string;
  auto_create_party_ledger: boolean;
  auto_create_stock_items: boolean;
}

export interface InvoiceListItem {
  id: string;
  filename: string;
  filepath: string;
  content_type?: string;
  status: string;
  triage_status: 'auto_ready' | 'quick_review' | 'needs_attention';
  confidence_score: number;
  invoice_number?: string;
  invoice_date?: string;
  party_name?: string;
  party_gstin?: string;
  taxable_value: number;
  total_tax: number;
  grand_total: number;
  sync_status: string;
  voucher_number?: string;
  created_at: string;
  tally_xml?: string;
  raw_markdown?: string;
  invoice_data?: ExtractedInvoice;
}

export interface TallyStatus {
  online: boolean;
  company_name: string;
  last_seen?: string;
  client_id?: string;
  error?: string;
}

// ==========================================
// Bank Statement Types
// ==========================================

export interface BankTransaction {
  id: string;
  statement_id?: string;
  transaction_date: string;
  narration: string;
  chq_ref_no?: string;
  withdrawal_dr: number;
  deposit_cr: number;
  balance: number;
  suggested_voucher_type: 'Payment' | 'Receipt' | 'Contra' | 'Journal';
  matched_counter_ledger?: string;
  approval_status: 'staged' | 'approved' | 'rejected' | 'synced';
}

export interface BankStatement {
  id: string;
  filename: string;
  filepath: string;
  bank_name: string;
  account_number?: string;
  account_type: string;
  tally_bank_ledger: string;
  period_start?: string;
  period_end?: string;
  opening_balance: number;
  closing_balance: number;
  total_debits: number;
  total_credits: number;
  transaction_count: number;
  created_at: string;
  transactions?: BankTransaction[];
  raw_markdown?: string;
}

// ==========================================
// Deterministic HITL Approval Record
// ==========================================

export interface HITLApprovalRecord {
  id: string;
  action_type: 'CREATE_LEDGER' | 'CREATE_STOCK_ITEM' | 'POST_PURCHASE_VOUCHER' | 'POST_BANK_PAYMENT' | 'POST_BANK_RECEIPT' | 'POST_BANK_CONTRA';
  reference_id: string;
  target_company: string;
  description: string;
  payload_xml: string;
  payload_json?: any;
  status: 'PENDING_HUMAN_APPROVAL' | 'APPROVED' | 'REJECTED' | 'EXECUTED';
  created_at: string;
  reviewed_by?: string;
  reviewed_at?: string;
}

// ==========================================
// Universal Parsed Document Types
// ==========================================

export interface ParsedDocument {
  id: string;
  filename: string;
  filepath: string;
  content_type?: string;
  doc_type: 'invoice' | 'bank_statement' | 'receipt' | 'bill' | 'financial_doc' | 'other';
  title: string;
  document_number?: string;
  date?: string;
  parties?: {
    issuer?: Record<string, any>;
    recipient?: Record<string, any>;
    bank?: Record<string, any>;
    [key: string]: any;
  };
  summary?: Record<string, any>;
  items?: Array<Record<string, any>>;
  raw_markdown?: string;
  thinking_process?: string[];
  thoughts_token_count?: number;
  confidence_score: number;
  status: string;
  tally_xml?: string;
  tags?: string[];
  notes?: string;
  created_at?: string;
  file_url?: string;
  workflow_execution?: WorkflowExecution;
  validation?: any;
}


export interface WorkflowStep {
  step_id: string;
  name: string;
  stage: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
  tool_calls_count?: number;
  tool_calls_limit?: number;
  revision_count?: number;
  max_revisions?: number;
  details?: Record<string, any>;
  error?: string;
}

export interface WorkflowExecution {
  workflow_name: string;
  document_id: string;
  filename?: string;
  current_step_id?: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  started_at?: string;
  completed_at?: string;
  total_duration_ms?: number;
  revision_count?: number;
  max_revisions?: number;
  steps: WorkflowStep[];
  confidence_score?: number;
  regulatory_audit_snapshot?: Record<string, any>;
  bfsi_compliance_mode?: string;
}

export interface WorkflowStepUpdate {
  type: 'WORKFLOW_STEP_UPDATE';
  document_id: string;
  filename: string;
  step_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  details?: Record<string, any>;
  timestamp?: string;
}



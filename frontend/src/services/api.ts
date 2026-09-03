import { InvoiceListItem, ExtractedInvoice, TallyStatus, BankStatement, HITLApprovalRecord } from '../types';

const API_BASE = '/api';

export const api = {
  // Invoices
  async listInvoices(filter?: string): Promise<{ invoices: InvoiceListItem[] }> {
    const url = filter ? `${API_BASE}/invoices?filter=${filter}` : `${API_BASE}/invoices`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch invoices');
    return res.json();
  },

  async uploadInvoice(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('files', file);
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/invoices/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async getInvoice(id: string): Promise<any> {
    const res = await fetch(`${API_BASE}/invoices/${id}`);
    if (!res.ok) throw new Error('Failed to fetch invoice');
    return res.json();
  },

  async updateLineItems(id: string, lineItems: any[]): Promise<any> {
    const res = await fetch(`${API_BASE}/invoices/${id}/line-items`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ line_items: lineItems }),
    });
    if (!res.ok) throw new Error('Failed to update line items');
    return res.json();
  },

  async deleteInvoice(id: string): Promise<any> {
    const res = await fetch(`${API_BASE}/invoices/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete invoice');
    return res.json();
  },

  getDownloadXmlUrl(id: string): string {
    return `${API_BASE}/invoices/${id}/tally-xml`;
  },

  // Tally & Sync
  async getTallyStatus(): Promise<TallyStatus> {
    const res = await fetch(`${API_BASE}/tally/status`);
    if (!res.ok) throw new Error('Failed to fetch Tally status');
    return res.json();
  },

  async syncInvoice(id: string, directApprove: boolean = false): Promise<any> {
    const res = await fetch(`${API_BASE}/tally/invoices/${id}/sync?direct_approve=${directApprove}`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to sync invoice to Tally');
    return res.json();
  },

  async batchSync(): Promise<any> {
    const res = await fetch(`${API_BASE}/tally/invoices/batch-sync`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to run batch sync');
    return res.json();
  },

  // ==========================================
  // Bank Statements
  // ==========================================
  async uploadBankStatement(file: File): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/banking/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Bank statement upload failed' }));
      throw new Error(err.detail || 'Bank statement upload failed');
    }
    return res.json();
  },

  async listBankStatements(): Promise<{ statements: BankStatement[] }> {
    const res = await fetch(`${API_BASE}/banking/statements`);
    if (!res.ok) throw new Error('Failed to fetch bank statements');
    return res.json();
  },

  async getBankStatement(id: string): Promise<BankStatement> {
    const res = await fetch(`${API_BASE}/banking/statements/${id}`);
    if (!res.ok) throw new Error('Failed to fetch bank statement');
    return res.json();
  },

  async updateBankTransaction(txnId: string, payload: { suggested_voucher_type?: string; matched_counter_ledger?: string; approval_status?: string }): Promise<any> {
    const res = await fetch(`${API_BASE}/banking/transactions/${txnId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error('Failed to update bank transaction');
    return res.json();
  },

  async stageBankTransaction(txnId: string, statementId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/banking/transactions/${txnId}/stage-for-sync`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ statement_id: statementId }),
    });
    if (!res.ok) throw new Error('Failed to stage transaction');
    return res.json();
  },

  async stageAllBankTransactions(statementId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/banking/statements/${statementId}/stage-all-for-sync`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to stage all transactions');
    return res.json();
  },

  // ==========================================
  // Deterministic HITL Write Safety Gate
  // ==========================================
  async listPendingApprovals(): Promise<{ pending_approvals: HITLApprovalRecord[] }> {
    const res = await fetch(`${API_BASE}/hitl/pending`);
    if (!res.ok) throw new Error('Failed to fetch pending approvals');
    return res.json();
  },

  async approveWriteAction(approvalId: string, reviewer: string = 'Accountant'): Promise<any> {
    const res = await fetch(`${API_BASE}/hitl/${approvalId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer }),
    });
    if (!res.ok) throw new Error('Failed to approve write action');
    return res.json();
  },

  async rejectWriteAction(approvalId: string, reviewer: string = 'Accountant', reason: string = 'Rejected'): Promise<any> {
    const res = await fetch(`${API_BASE}/hitl/${approvalId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer, reason }),
    });
    if (!res.ok) throw new Error('Failed to reject write action');
    return res.json();
  },

  async batchApproveWriteActions(approvalIds: string[], reviewer: string = 'Accountant'): Promise<any> {
    const res = await fetch(`${API_BASE}/hitl/batch-approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_ids: approvalIds, reviewer }),
    });
    if (!res.ok) throw new Error('Failed to batch approve write actions');
    return res.json();
  },
};

// ==========================================
// Named Export Helpers for Components
// ==========================================

export const fetchInvoices = async (filter?: string): Promise<InvoiceListItem[]> => {
  const res = await api.listInvoices(filter);
  return res.invoices;
};

export const fetchTallyStatus = async (): Promise<TallyStatus> => {
  return api.getTallyStatus();
};

export const uploadInvoices = async (files: File[]): Promise<any[]> => {
  const results = [];
  for (const f of files) {
    const res = await api.uploadInvoice(f);
    results.push(res);
  }
  return results;
};

export const updateInvoice = async (id: string, updates: Partial<ExtractedInvoice>): Promise<any> => {
  if (updates.line_items) {
    return api.updateLineItems(id, updates.line_items);
  }
  return { status: 'success' };
};

export const syncSingleInvoiceToTally = async (id: string): Promise<any> => {
  return api.syncInvoice(id, true);
};

export const getTallyXmlDownloadUrl = (id: string): string => {
  return api.getDownloadXmlUrl(id);
};

export const deleteInvoice = async (id: string): Promise<any> => {
  return api.deleteInvoice(id);
};

export const batchSyncReadyInvoices = async (): Promise<any> => {
  return api.batchSync();
};

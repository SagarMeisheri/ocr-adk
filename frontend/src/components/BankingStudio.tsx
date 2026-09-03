import React, { useState, useEffect } from 'react';
import {
  Landmark,
  UploadCloud,
  FileText,
  CheckCircle2,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  Send,
  Loader2,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { BankStatement, BankTransaction } from '../types';

interface BankingStudioProps {
  onApprovalRequested?: () => void;
}

export const BankingStudio: React.FC<BankingStudioProps> = ({ onApprovalRequested }) => {
  const [statements, setStatements] = useState<BankStatement[]>([]);
  const [activeStatement, setActiveStatement] = useState<BankStatement | null>(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stagingTxnId, setStagingTxnId] = useState<string | null>(null);
  const [stagingAll, setStagingAll] = useState(false);

  useEffect(() => {
    loadStatements();
  }, []);

  const loadStatements = async () => {
    try {
      setLoading(true);
      const res = await api.listBankStatements();
      setStatements(res.statements);
      if (res.statements.length > 0 && !activeStatement) {
        loadStatementDetails(res.statements[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadStatementDetails = async (id: string) => {
    try {
      const st = await api.getBankStatement(id);
      setActiveStatement(st);
    } catch (err) {
      console.error(err);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    try {
      setUploading(true);
      const res = await api.uploadBankStatement(files[0]);
      await loadStatements();
      await loadStatementDetails(res.statement_id);
    } catch (err: any) {
      alert(err.message || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleUpdateTxn = async (txnId: string, fields: Partial<BankTransaction>) => {
    if (!activeStatement) return;
    try {
      await api.updateBankTransaction(txnId, fields);
      setActiveStatement({
        ...activeStatement,
        transactions: activeStatement.transactions?.map((t) =>
          t.id === txnId ? { ...t, ...fields } : t
        ),
      });
    } catch (err) {
      console.error(err);
    }
  };

  const handleStageTxn = async (txnId: string) => {
    if (!activeStatement) return;
    try {
      setStagingTxnId(txnId);
      await api.stageBankTransaction(txnId, activeStatement.id);
      handleUpdateTxn(txnId, { approval_status: 'staged' });
      if (onApprovalRequested) onApprovalRequested();
    } catch (err: any) {
      alert(err.message || 'Failed to stage transaction');
    } finally {
      setStagingTxnId(null);
    }
  };

  const handleStageAll = async () => {
    if (!activeStatement) return;
    try {
      setStagingAll(true);
      const res = await api.stageAllBankTransactions(activeStatement.id);
      alert(res.message);
      await loadStatementDetails(activeStatement.id);
      if (onApprovalRequested) onApprovalRequested();
    } catch (err: any) {
      alert(err.message || 'Failed to stage all transactions');
    } finally {
      setStagingAll(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Upload & Statement Selector Header */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-blue-500/20 border border-blue-500/30 flex items-center justify-center text-blue-400">
            <Landmark className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              Multi-Page Bank Statement Studio
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-blue-500/20 text-blue-400 border border-blue-500/30">
                PyPDF + Markdown Engine
              </span>
            </h2>
            <p className="text-sm text-slate-400">
              Auto-extracts hundreds of transaction rows from digital PDF bank statements into Tally Payment, Receipt & Contra vouchers.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <label className="cursor-pointer px-4 py-2 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium text-sm shadow-lg shadow-blue-500/25 flex items-center gap-2 transition-all">
            {uploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
            {uploading ? 'Processing Statement...' : 'Upload Bank Statement (PDF)'}
            <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} disabled={uploading} />
          </label>
        </div>
      </div>

      {/* Main Content Layout */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-blue-400" />
          <span>Loading bank statements...</span>
        </div>
      ) : statements.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl">
          <Landmark className="w-12 h-12 text-slate-500 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white mb-1">No Bank Statements Uploaded Yet</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto mb-6">
            Upload an e-statement PDF from HDFC, ICICI, SBI, Axis, or Kotak. Our PyPDF preprocessor and Gemini Markdown table parser will extract every transaction line.
          </p>
          <label className="cursor-pointer inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm transition-all shadow-lg shadow-blue-600/30">
            <UploadCloud className="w-4 h-4" />
            Upload Sample Statement PDF
            <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
          </label>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Statement Switcher Tabs */}
          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {statements.map((st) => (
              <button
                key={st.id}
                onClick={() => loadStatementDetails(st.id)}
                className={`px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2 transition-all whitespace-nowrap ${
                  activeStatement?.id === st.id
                    ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                    : 'bg-slate-800/40 text-slate-400 hover:text-white border border-slate-700/50'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>{st.bank_name || 'Bank Account'}</span>
                <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-300">
                  {st.transaction_count} txns
                </span>
              </button>
            ))}
          </div>

          {activeStatement && (
            <>
              {/* KPI Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
                <div className="glass-panel p-4 rounded-xl">
                  <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Account</span>
                  <div className="text-sm font-bold text-white mt-1 truncate">{activeStatement.bank_name}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{activeStatement.account_number || 'A/C Primary'}</div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Period</span>
                  <div className="text-sm font-bold text-white mt-1">
                    {activeStatement.period_start} &rarr; {activeStatement.period_end}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">{activeStatement.transaction_count} Transactions</div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Debits (Dr)</span>
                  <div className="text-sm font-bold text-rose-400 mt-1 flex items-center gap-1">
                    <ArrowDownRight className="w-4 h-4" />₹{activeStatement.total_debits.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">Withdrawals / Payments</div>
                </div>

                <div className="glass-panel p-4 rounded-xl">
                  <span className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Credits (Cr)</span>
                  <div className="text-sm font-bold text-emerald-400 mt-1 flex items-center gap-1">
                    <ArrowUpRight className="w-4 h-4" />₹{activeStatement.total_credits.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-xs text-slate-500 mt-0.5">Deposits / Receipts</div>
                </div>

                <div className="glass-panel p-4 rounded-xl flex flex-col justify-center">
                  <button
                    onClick={handleStageAll}
                    disabled={stagingAll}
                    className="w-full py-2 px-3 rounded-lg bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-semibold text-xs flex items-center justify-center gap-1.5 shadow-lg shadow-blue-500/20 transition-all disabled:opacity-50"
                  >
                    {stagingAll ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                    Stage All for Approval
                  </button>
                  <span className="text-[10px] text-center text-slate-400 mt-1">
                    Quarantines in deterministic HITL gate
                  </span>
                </div>
              </div>

              {/* Transactions Reconciliation Grid */}
              <div className="glass-panel rounded-2xl overflow-hidden border border-slate-700/60">
                <div className="p-4 bg-slate-900/60 border-b border-slate-700/60 flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-400" />
                    <span className="text-sm font-semibold text-white">
                      Extracted Transaction Lines ({activeStatement.transactions?.length || 0})
                    </span>
                  </div>
                  <span className="text-xs text-slate-400">
                    Target Bank Ledger in Tally:{' '}
                    <strong className="text-blue-400">{activeStatement.tally_bank_ledger}</strong>
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 font-semibold bg-slate-950/40">
                        <th className="p-3">Date</th>
                        <th className="p-3">Narration / Description</th>
                        <th className="p-3">Chq / Ref</th>
                        <th className="p-3 text-right">Debit (Withdrawal)</th>
                        <th className="p-3 text-right">Credit (Deposit)</th>
                        <th className="p-3 text-right">Balance</th>
                        <th className="p-3">Voucher Type</th>
                        <th className="p-3">Counter Ledger</th>
                        <th className="p-3 text-center">HITL Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-mono">
                      {activeStatement.transactions?.map((txn) => (
                        <tr key={txn.id} className="hover:bg-slate-800/30 transition-colors">
                          <td className="p-3 whitespace-nowrap text-slate-300 font-sans">{txn.transaction_date}</td>
                          <td className="p-3 text-slate-200 max-w-xs truncate font-sans" title={txn.narration}>
                            {txn.narration}
                          </td>
                          <td className="p-3 text-slate-400 whitespace-nowrap font-sans">{txn.chq_ref_no || '-'}</td>
                          <td className="p-3 text-right whitespace-nowrap text-rose-400 font-semibold">
                            {txn.withdrawal_dr > 0
                              ? `₹${txn.withdrawal_dr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                              : '-'}
                          </td>
                          <td className="p-3 text-right whitespace-nowrap text-emerald-400 font-semibold">
                            {txn.deposit_cr > 0
                              ? `₹${txn.deposit_cr.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
                              : '-'}
                          </td>
                          <td className="p-3 text-right whitespace-nowrap text-slate-300">
                            ₹{txn.balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="p-3 font-sans">
                            <select
                              value={txn.suggested_voucher_type}
                              onChange={(e) =>
                                handleUpdateTxn(txn.id, {
                                  suggested_voucher_type: e.target.value as any,
                                })
                              }
                              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                            >
                              <option value="Payment">Payment (F5)</option>
                              <option value="Receipt">Receipt (F6)</option>
                              <option value="Contra">Contra (F4)</option>
                            </select>
                          </td>
                          <td className="p-3 font-sans">
                            <input
                              type="text"
                              defaultValue={txn.matched_counter_ledger || ''}
                              onBlur={(e) => handleUpdateTxn(txn.id, { matched_counter_ledger: e.target.value })}
                              placeholder="e.g. Sundry Creditor / Expense"
                              className="w-48 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-blue-500"
                            />
                          </td>
                          <td className="p-3 text-center font-sans">
                            {txn.approval_status === 'staged' ? (
                              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                                <AlertTriangle className="w-3 h-3" /> Staged
                              </span>
                            ) : txn.approval_status === 'synced' ? (
                              <span className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                                <CheckCircle2 className="w-3 h-3" /> Synced
                              </span>
                            ) : (
                              <button
                                onClick={() => handleStageTxn(txn.id)}
                                disabled={stagingTxnId === txn.id}
                                className="px-2.5 py-1 rounded-lg bg-blue-600/80 hover:bg-blue-600 text-white text-[11px] font-medium transition-all shadow-sm flex items-center gap-1 mx-auto"
                              >
                                {stagingTxnId === txn.id ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  <Send className="w-3 h-3" />
                                )}
                                Stage
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
};

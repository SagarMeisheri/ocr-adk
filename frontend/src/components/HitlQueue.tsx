import React, { useState, useEffect } from 'react';
import {
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Code2,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
  Building2,
  Sparkles,
} from 'lucide-react';
import { api } from '../services/api';
import { HITLApprovalRecord } from '../types';

interface HitlQueueProps {
  onStatusChange?: () => void;
}

export const HitlQueue: React.FC<HitlQueueProps> = ({ onStatusChange }) => {
  const [approvals, setApprovals] = useState<HITLApprovalRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [expandedXmlId, setExpandedXmlId] = useState<string | null>(null);
  const [actionInProgressId, setActionInProgressId] = useState<string | null>(null);
  const [batchApproving, setBatchApproving] = useState(false);

  useEffect(() => {
    loadPendingApprovals();
  }, []);

  const loadPendingApprovals = async () => {
    try {
      setLoading(true);
      const res = await api.listPendingApprovals();
      setApprovals(res.pending_approvals);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      setActionInProgressId(id);
      await api.approveWriteAction(id, 'Head Accountant');
      setApprovals((prev) => prev.filter((a) => a.id !== id));
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      alert(err.message || 'Approval failed');
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleReject = async (id: string) => {
    const reason = prompt('Please enter rejection reason:', 'Unverified entry');
    if (!reason) return;
    try {
      setActionInProgressId(id);
      await api.rejectWriteAction(id, 'Head Accountant', reason);
      setApprovals((prev) => prev.filter((a) => a.id !== id));
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      alert(err.message || 'Rejection failed');
    } finally {
      setActionInProgressId(null);
    }
  };

  const handleBatchApprove = async () => {
    if (approvals.length === 0) return;
    if (!confirm(`Are you sure you want to approve and commit all ${approvals.length} write actions to Tally Prime?`)) {
      return;
    }
    try {
      setBatchApproving(true);
      const ids = approvals.map((a) => a.id);
      const res = await api.batchApproveWriteActions(ids, 'Head Accountant (Batch)');
      alert(res.message);
      setApprovals([]);
      if (onStatusChange) onStatusChange();
    } catch (err: any) {
      alert(err.message || 'Batch approval failed');
    } finally {
      setBatchApproving(false);
    }
  };

  const getActionBadge = (type: string) => {
    switch (type) {
      case 'POST_PURCHASE_VOUCHER':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">Purchase Voucher</span>;
      case 'POST_BANK_PAYMENT':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-rose-500/20 text-rose-300 border border-rose-500/30">Bank Payment</span>;
      case 'POST_BANK_RECEIPT':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Bank Receipt</span>;
      case 'POST_BANK_CONTRA':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30">Bank Contra</span>;
      case 'CREATE_LEDGER':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-sky-500/20 text-sky-300 border border-sky-500/30">Create Ledger</span>;
      case 'CREATE_STOCK_ITEM':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">Create Stock Item</span>;
      case 'MCP_LEDGER_CREATE_UPDATE':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">⚠ MCP Ledger Mutation</span>;
      case 'MCP_DELETE_MASTER':
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-red-600/30 text-red-400 border border-red-500/50">🚨 MCP DELETE MASTER</span>;
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-700 text-slate-300">{type}</span>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Info Panel */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-xl bg-amber-500/20 border border-amber-500/30 flex items-center justify-center text-amber-400">
            <ShieldAlert className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              Deterministic Human-in-the-Loop (HITL) Gate
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-amber-500/20 text-amber-400 border border-amber-500/30">
                Zero Autonomous AI Writes
              </span>
            </h2>
            <p className="text-sm text-slate-400">
              All write operations to Tally Prime are strictly quarantined here. A human accountant must review the exact XML payload and grant explicit sign-off.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadPendingApprovals}
            disabled={loading}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-all"
            title="Refresh Queue"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>

          <button
            onClick={handleBatchApprove}
            disabled={batchApproving || approvals.length === 0}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-semibold text-sm shadow-lg shadow-emerald-600/25 flex items-center gap-2 transition-all disabled:opacity-50"
          >
            {batchApproving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
            Batch Sign &amp; Approve All ({approvals.length})
          </button>
        </div>
      </div>

      {/* Approvals List */}
      {loading ? (
        <div className="p-12 text-center text-slate-400 flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-amber-400" />
          <span>Loading pending approvals...</span>
        </div>
      ) : approvals.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl">
          <CheckCircle2 className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-white mb-1">Zero Pending Writes &bull; All Clear</h3>
          <p className="text-sm text-slate-400 max-w-md mx-auto">
            All proposed purchase vouchers, bank entries, and ledger masters have been processed or none have been staged yet.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {approvals.map((item) => (
            <div
              key={item.id}
              className="glass-panel rounded-2xl p-5 border border-slate-700/60 hover:border-slate-600/80 transition-all"
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    {getActionBadge(item.action_type)}
                    <span className="text-xs text-slate-400 flex items-center gap-1 font-mono">
                      <Building2 className="w-3.5 h-3.5" />
                      {item.target_company}
                    </span>
                    <span className="text-xs text-slate-500">
                      Staged: {new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>

                  <h4 className="text-sm font-semibold text-white">{item.description}</h4>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setExpandedXmlId(expandedXmlId === item.id ? null : item.id)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium border border-slate-700 flex items-center gap-1.5 transition-all"
                  >
                    <Code2 className="w-3.5 h-3.5 text-blue-400" />
                    {expandedXmlId === item.id ? 'Hide XML' : 'Inspect XML'}
                    {expandedXmlId === item.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>

                  <button
                    onClick={() => handleReject(item.id)}
                    disabled={actionInProgressId === item.id}
                    className="px-3 py-1.5 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 border border-rose-500/30 text-xs font-semibold flex items-center gap-1 transition-all disabled:opacity-50"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    Reject
                  </button>

                  <button
                    onClick={() => handleApprove(item.id)}
                    disabled={actionInProgressId === item.id}
                    className="px-4 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold flex items-center gap-1.5 shadow-md shadow-emerald-600/20 transition-all disabled:opacity-50"
                  >
                    {actionInProgressId === item.id ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    )}
                    Approve &amp; Push to Tally
                  </button>
                </div>
              </div>

              {/* XML Diff Viewer */}
              {expandedXmlId === item.id && (
                <div className="mt-4 pt-4 border-t border-slate-800">
                  <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
                    <span className="flex items-center gap-1.5 text-blue-400">
                      <Sparkles className="w-3.5 h-3.5" />
                      TallyPrime Port 9000 Payload Envelope
                    </span>
                    <span>Ready for commit</span>
                  </div>
                  <pre className="p-4 rounded-xl bg-slate-950 text-slate-300 text-xs font-mono overflow-x-auto border border-slate-800/80 max-h-72">
                    <code>{item.payload_xml}</code>
                  </pre>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

import React from 'react';
import { InvoiceListItem } from '../types';
import { CheckCircle2, AlertTriangle, XCircle, Clock, Zap, ArrowRight, Trash2, FileCode } from 'lucide-react';
import { syncSingleInvoiceToTally, deleteInvoice } from '../services/api';

interface TriQueueProps {
  invoices: InvoiceListItem[];
  activeTab: 'all' | 'auto_ready' | 'quick_review' | 'needs_attention' | 'synced';
  onTabChange: (tab: 'all' | 'auto_ready' | 'quick_review' | 'needs_attention' | 'synced') => void;
  onSelectInvoice: (id: string) => void;
  onRefresh: () => void;
  onViewXml: (invoice: InvoiceListItem) => void;
}

export const TriQueue: React.FC<TriQueueProps> = ({
  invoices,
  activeTab,
  onTabChange,
  onSelectInvoice,
  onRefresh,
  onViewXml,
}) => {
  // Compute counts for tab badges
  const counts = {
    all: invoices.length,
    auto_ready: invoices.filter((i) => i.triage_status === 'auto_ready' && i.sync_status !== 'synced').length,
    quick_review: invoices.filter((i) => i.triage_status === 'quick_review' && i.sync_status !== 'synced').length,
    needs_attention: invoices.filter((i) => i.triage_status === 'needs_attention' && i.sync_status !== 'synced').length,
    synced: invoices.filter((i) => i.sync_status === 'synced').length,
  };

  const filteredInvoices = invoices.filter((inv) => {
    if (activeTab === 'all') return true;
    if (activeTab === 'synced') return inv.sync_status === 'synced';
    return inv.triage_status === activeTab && inv.sync_status !== 'synced';
  });

  const handleSync = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await syncSingleInvoiceToTally(id);
      onRefresh();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this invoice?')) {
      await deleteInvoice(id);
      onRefresh();
    }
  };

  return (
    <div className="glass-panel" style={{ margin: '0 24px', padding: '20px' }}>
      
      {/* Triage Tabs */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        borderBottom: '1px solid var(--border-subtle)',
        paddingBottom: '14px',
        marginBottom: '16px',
        flexWrap: 'wrap',
      }}>
        <button
          id="tab-auto-ready"
          onClick={() => onTabChange('auto_ready')}
          className={`btn ${activeTab === 'auto_ready' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '13px', padding: '7px 14px' }}
        >
          <CheckCircle2 size={15} color="#34d399" />
          Auto-Ready (90%+)
          <span style={{
            background: activeTab === 'auto_ready' ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.1)',
            padding: '2px 7px',
            borderRadius: '9999px',
            fontSize: '11px',
            fontWeight: 700,
          }}>
            {counts.auto_ready}
          </span>
        </button>

        <button
          id="tab-quick-review"
          onClick={() => onTabChange('quick_review')}
          className={`btn ${activeTab === 'quick_review' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '13px', padding: '7px 14px' }}
        >
          <AlertTriangle size={15} color="#fbbf24" />
          Quick Review (70-90%)
          <span style={{
            background: activeTab === 'quick_review' ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.1)',
            padding: '2px 7px',
            borderRadius: '9999px',
            fontSize: '11px',
            fontWeight: 700,
          }}>
            {counts.quick_review}
          </span>
        </button>

        <button
          id="tab-needs-attention"
          onClick={() => onTabChange('needs_attention')}
          className={`btn ${activeTab === 'needs_attention' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '13px', padding: '7px 14px' }}
        >
          <XCircle size={15} color="#f87171" />
          Needs Attention (&lt;70%)
          <span style={{
            background: activeTab === 'needs_attention' ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.1)',
            padding: '2px 7px',
            borderRadius: '9999px',
            fontSize: '11px',
            fontWeight: 700,
          }}>
            {counts.needs_attention}
          </span>
        </button>

        <button
          id="tab-synced"
          onClick={() => onTabChange('synced')}
          className={`btn ${activeTab === 'synced' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '13px', padding: '7px 14px' }}
        >
          <Clock size={15} color="#38bdf8" />
          Synced to Tally
          <span style={{
            background: activeTab === 'synced' ? 'rgba(255,255,255,0.25)' : 'rgba(255,255,255,0.1)',
            padding: '2px 7px',
            borderRadius: '9999px',
            fontSize: '11px',
            fontWeight: 700,
          }}>
            {counts.synced}
          </span>
        </button>

        <button
          id="tab-all"
          onClick={() => onTabChange('all')}
          className={`btn ${activeTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ fontSize: '13px', padding: '7px 14px', marginLeft: 'auto' }}
        >
          All Invoices ({counts.all})
        </button>
      </div>

      {/* Invoice List */}
      {filteredInvoices.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 20px', color: 'var(--text-muted)' }}>
          <p style={{ fontSize: '15px', fontWeight: 500 }}>No invoices in this triage queue.</p>
          <p style={{ fontSize: '13px', marginTop: '6px' }}>Upload purchase bills above to automatically categorize them.</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {filteredInvoices.map((inv) => {
            const isSynced = inv.sync_status === 'synced';
            const isSyncing = inv.sync_status === 'syncing';

            return (
              <div
                key={inv.id}
                onClick={() => onSelectInvoice(inv.id)}
                className="glass-panel glass-panel-interactive"
                style={{
                  padding: '14px 20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  borderLeft: `4px solid ${
                    isSynced
                      ? '#10b981'
                      : inv.triage_status === 'auto_ready'
                      ? '#34d399'
                      : inv.triage_status === 'quick_review'
                      ? '#fbbf24'
                      : '#f87171'
                  }`,
                }}
              >
                {/* Left Info: Invoice #, Date, Vendor */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontWeight: 700, fontSize: '15px', color: '#fff' }}>
                        {inv.invoice_number || 'No Invoice #'}{' '}
                      </span>
                      <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                        ({inv.invoice_date || 'No Date'})
                      </span>
                      {inv.party_gstin && (
                        <span className="pill pill-blue" style={{ fontSize: '10px', padding: '2px 6px' }}>
                          {inv.party_gstin}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '3px' }}>
                      {inv.party_name || 'Vendor details pending'}
                    </div>
                  </div>
                </div>

                {/* Center: Financials & Tax Math */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px', textAlign: 'right' }}>
                  <div>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: '#38bdf8' }}>
                      ₹{inv.grand_total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Taxable: ₹{inv.taxable_value.toFixed(2)} | Tax: ₹{inv.total_tax.toFixed(2)}
                    </div>
                  </div>

                  {/* Confidence Pill */}
                  <div>
                    <span
                      className={`pill ${
                        inv.confidence_score >= 0.9
                          ? 'pill-green'
                          : inv.confidence_score >= 0.7
                          ? 'pill-yellow'
                          : 'pill-red'
                      }`}
                      style={{ fontSize: '11px' }}
                    >
                      {Math.round(inv.confidence_score * 100)}% Confidence
                    </span>
                  </div>

                  {/* Sync Status Badge */}
                  <div>
                    {isSynced ? (
                      <span className="pill pill-green" style={{ fontSize: '11px' }}>
                        <CheckCircle2 size={12} /> Synced ({inv.voucher_number || 'Voucher Created'})
                      </span>
                    ) : isSyncing ? (
                      <span className="pill pill-yellow" style={{ fontSize: '11px' }}>
                        <Zap size={12} /> Syncing to Port 9000...
                      </span>
                    ) : (
                      <span className="pill pill-blue" style={{ fontSize: '11px' }}>
                        Pending Sync
                      </span>
                    )}
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {!isSynced && (
                      <button
                        title="Sync this voucher to Tally Prime"
                        onClick={(e) => handleSync(e, inv.id)}
                        disabled={isSyncing}
                        className="btn btn-primary"
                        style={{ padding: '6px 12px', fontSize: '12px' }}
                      >
                        <Zap size={13} /> {isSyncing ? 'Syncing...' : 'Sync'}
                      </button>
                    )}

                    <button
                      title="View Generated Tally XML"
                      onClick={(e) => { e.stopPropagation(); onViewXml(inv); }}
                      className="btn btn-secondary"
                      style={{ padding: '6px 10px' }}
                    >
                      <FileCode size={14} />
                    </button>

                    <button
                      title="Delete Invoice"
                      onClick={(e) => handleDelete(e, inv.id)}
                      className="btn btn-danger"
                      style={{ padding: '6px 10px' }}
                    >
                      <Trash2 size={14} />
                    </button>

                    <ArrowRight size={16} color="var(--text-muted)" />
                  </div>
                </div>

              </div>
            );
          })}
        </div>
      )}

    </div>
  );
};

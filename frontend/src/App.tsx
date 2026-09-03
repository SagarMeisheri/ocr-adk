import React, { useState, useEffect } from 'react';
import { InvoiceListItem, TallyStatus } from './types';
import { api } from './services/api';
import { Header } from './components/Header';
import { UploadZone } from './components/UploadZone';
import { TriQueue } from './components/TriQueue';
import { InvoiceDetail } from './components/InvoiceDetail';
import { TallySyncModal } from './components/TallySyncModal';
import { SettingsModal } from './components/SettingsModal';
import { BankingStudio } from './components/BankingStudio';
import { HitlQueue } from './components/HitlQueue';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'invoices' | 'banking' | 'hitl'>('invoices');
  const [invoices, setInvoices] = useState<InvoiceListItem[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState<string | null>(null);
  const [triageTab, setTriageTab] = useState<'all' | 'auto_ready' | 'quick_review' | 'needs_attention' | 'synced'>('all');
  const [tallyStatus, setTallyStatus] = useState<TallyStatus>({
    online: false,
    company_name: 'Checking...',
  });
  const [pendingHitlCount, setPendingHitlCount] = useState<number>(0);
  const [xmlModalInvoice, setXmlModalInvoice] = useState<InvoiceListItem | null>(null);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showUploadZone, setShowUploadZone] = useState(true);

  const loadData = async () => {
    try {
      const res = await api.listInvoices(triageTab);
      setInvoices(res.invoices);
    } catch (e) {
      console.error('Failed to load invoices:', e);
    }
  };

  const loadTally = async () => {
    try {
      const status = await api.getTallyStatus();
      setTallyStatus(status);
    } catch (e) {
      console.error('Failed to load Tally status:', e);
    }
  };

  const loadHitlCount = async () => {
    try {
      const res = await api.listPendingApprovals();
      setPendingHitlCount(res.pending_approvals.length);
    } catch (e) {
      console.error('Failed to load pending approvals:', e);
    }
  };

  useEffect(() => {
    loadData();
    loadTally();
    loadHitlCount();

    // Periodic heartbeat poll for Tally status and pending approvals every 4s
    const interval = setInterval(() => {
      loadTally();
      loadHitlCount();
      if (activeTab === 'invoices') {
        loadData();
      }
    }, 4000);

    return () => clearInterval(interval);
  }, [triageTab, activeTab]);

  const handleBatchSync = async () => {
    try {
      const res = await api.batchSync();
      alert(res.message);
      loadData();
      loadHitlCount();
      setActiveTab('hitl');
    } catch (err: any) {
      alert(`Batch sync staging failed: ${err.message}`);
    }
  };

  const selectedInvoice = selectedInvoiceId
    ? invoices.find((i) => i.id === selectedInvoiceId) || null
    : null;

  const autoReadyCount = invoices.filter(
    (i) => i.triage_status === 'auto_ready' && i.sync_status !== 'synced'
  ).length;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top App Header */}
      <Header
        tallyStatus={tallyStatus}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setSelectedInvoiceId(null);
        }}
        onRefreshTally={loadTally}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onBatchSync={handleBatchSync}
        readyCount={autoReadyCount}
        pendingHitlCount={pendingHitlCount}
        onNewUpload={() => {
          setSelectedInvoiceId(null);
          setShowUploadZone(true);
        }}
      />

      {/* Main View Area */}
      <main style={{ flex: 1, padding: '0 24px 24px 24px' }}>
        {activeTab === 'banking' ? (
          /* Multi-Page Bank Statement Reconciliation Studio */
          <BankingStudio
            onApprovalRequested={() => {
              loadHitlCount();
            }}
          />
        ) : activeTab === 'hitl' ? (
          /* Deterministic Human-in-the-Loop Write Safety Queue */
          <HitlQueue
            onStatusChange={() => {
              loadHitlCount();
              loadData();
            }}
          />
        ) : selectedInvoice ? (
          /* Side-by-Side Review Studio */
          <InvoiceDetail
            invoice={selectedInvoice}
            onBack={() => setSelectedInvoiceId(null)}
            onUpdated={() => {
              loadData();
              loadHitlCount();
            }}
            onViewXml={(inv) => setXmlModalInvoice(inv)}
          />
        ) : (
          /* Dashboard with Upload Zone & Tri-Queue Triage */
          <div>
            {showUploadZone && (
              <UploadZone
                onUploadSuccess={() => {
                  loadData();
                }}
              />
            )}

            <TriQueue
              invoices={invoices}
              activeTab={triageTab}
              onTabChange={(tab) => setTriageTab(tab)}
              onSelectInvoice={(id) => setSelectedInvoiceId(id)}
              onRefresh={loadData}
              onViewXml={(inv) => setXmlModalInvoice(inv)}
            />
          </div>
        )}
      </main>

      {/* XML Inspection Modal */}
      <TallySyncModal
        invoice={xmlModalInvoice}
        onClose={() => setXmlModalInvoice(null)}
        onSynced={() => {
          loadData();
          loadHitlCount();
        }}
      />

      {/* Settings / Instructions Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        tallyStatus={tallyStatus}
      />

      {/* Footer */}
      <footer style={{
        textAlign: 'center',
        padding: '16px',
        color: 'var(--text-muted)',
        fontSize: '12px',
        borderTop: '1px solid var(--border-subtle)',
        marginTop: 'auto',
      }}>
        TrulyTally AI &copy; 2026 &bull; Google ADK 2.0 &bull; dhananjay1405/tally-mcp-server &bull; Deterministic Human-in-the-Loop Write Safety Gate
      </footer>
    </div>
  );
};

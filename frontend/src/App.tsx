import React, { useState, useEffect } from 'react';
import { ParsedDocument, TallyStatus } from './types';
import { api } from './services/api';
import { Header } from './components/Header';
import { UploadZone } from './components/UploadZone';
import { DocumentQueue } from './components/DocumentQueue';
import { DocumentInspector } from './components/DocumentInspector';
import { SettingsModal } from './components/SettingsModal';
import { HitlQueue } from './components/HitlQueue';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'invoices' | 'banking' | 'hitl'>('invoices');
  const [documents, setDocuments] = useState<ParsedDocument[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<ParsedDocument | null>(null);
  const [docFilter, setDocFilter] = useState<string>('all');
  const [tallyStatus, setTallyStatus] = useState<TallyStatus>({
    online: false,
    company_name: 'Checking...',
  });
  const [pendingHitlCount, setPendingHitlCount] = useState<number>(0);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [showUploadZone, setShowUploadZone] = useState(true);

  const loadData = async () => {
    try {
      const res = await api.listDocuments(docFilter);
      setDocuments(res.documents || []);
    } catch (e) {
      console.error('Failed to load documents:', e);
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
      setPendingHitlCount(res.pending_approvals ? res.pending_approvals.length : 0);
    } catch (e) {
      console.error('Failed to load pending approvals:', e);
    }
  };

  // Load once on mount or when filter/tab changes. Zero background polling loop.
  useEffect(() => {
    loadData();
    loadTally();
    loadHitlCount();
  }, [docFilter, activeTab]);

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

  const invoiceCount = documents.filter((d) => d.doc_type === 'invoice').length;

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Top App Header */}
      <Header
        tallyStatus={tallyStatus}
        activeTab={activeTab}
        onTabChange={(tab) => {
          setActiveTab(tab);
          setSelectedDocument(null);
        }}
        onRefreshTally={loadTally}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onBatchSync={handleBatchSync}
        readyCount={invoiceCount}
        pendingHitlCount={pendingHitlCount}
        onNewUpload={() => {
          setSelectedDocument(null);
          setShowUploadZone(true);
        }}
      />

      {/* Main View Area */}
      <main style={{ flex: 1, padding: '0 24px 24px 24px' }}>
        {activeTab === 'hitl' ? (
          /* Deterministic Human-in-the-Loop Write Safety Queue */
          <HitlQueue
            onStatusChange={() => {
              loadHitlCount();
              loadData();
            }}
          />
        ) : selectedDocument ? (
          /* Full Split-Screen Document Inspector */
          <DocumentInspector
            document={selectedDocument}
            onBack={() => setSelectedDocument(null)}
            onRefresh={() => {
              loadData();
              setSelectedDocument(null);
            }}
          />
        ) : (
          /* Unified Document Studio: Upload Zone & Document Queue */
          <div>
            {showUploadZone && (
              <UploadZone
                onUploadSuccess={() => {
                  loadData();
                }}
              />
            )}

            <DocumentQueue
              documents={documents}
              activeFilter={docFilter}
              onFilterChange={(filter) => setDocFilter(filter)}
              onSelectDocument={(doc) => setSelectedDocument(doc)}
              onRefresh={loadData}
            />
          </div>
        )}
      </main>

      {/* Settings / Instructions Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        tallyStatus={tallyStatus}
      />

      {/* Footer */}
      <footer
        style={{
          textAlign: 'center',
          padding: '16px',
          color: 'var(--text-muted)',
          fontSize: '12px',
          borderTop: '1px solid var(--border-subtle)',
          marginTop: 'auto',
        }}
      >
        TrulyTally AI &copy; 2026 &bull; Google ADK 2.0 &bull; Universal Multimodal Document Studio &bull; Gemini 3.8 Flash
      </footer>
    </div>
  );
};
export default App;

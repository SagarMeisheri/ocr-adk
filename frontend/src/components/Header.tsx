import React from 'react';
import { TallyStatus } from '../types';
import { FileText, Cpu, Zap, Settings, RefreshCw, Layers, Landmark, ShieldAlert } from 'lucide-react';

interface HeaderProps {
  tallyStatus: TallyStatus;
  activeTab: 'invoices' | 'banking' | 'hitl';
  onTabChange: (tab: 'invoices' | 'banking' | 'hitl') => void;
  onRefreshTally: () => void;
  onOpenSettings: () => void;
  onBatchSync: () => void;
  readyCount: number;
  pendingHitlCount: number;
  onNewUpload: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  tallyStatus,
  activeTab,
  onTabChange,
  onRefreshTally,
  onOpenSettings,
  onBatchSync,
  readyCount,
  pendingHitlCount,
  onNewUpload,
}) => {
  return (
    <header className="glass-panel" style={{ margin: '16px 24px', padding: '14px 24px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        
        {/* Brand & Module Navigation */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, #2563eb, #38bdf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 16px rgba(37,99,235,0.4)',
            }}>
              <FileText size={22} color="#fff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h1 className="brand-title" style={{ fontSize: '19px', fontWeight: '800', color: '#fff', margin: 0 }}>
                  TrulyTally<span style={{ color: '#38bdf8' }}>.AI</span>
                </h1>
                <span className="pill pill-blue" style={{ fontSize: '10px', padding: '2px 7px' }}>
                  Document Studio
                </span>
              </div>
              <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: '1px 0 0 0' }}>
                Universal AI Extraction &bull; Invoices, Bank Statements, Receipts &amp; Bills &bull; Gemini 3.8 Flash
              </p>
            </div>
          </div>

          {/* Module Switcher Tabs */}
          <nav style={{ display: 'flex', alignItems: 'center', gap: '6px', background: 'rgba(15, 23, 42, 0.6)', padding: '4px', borderRadius: '12px', border: '1px solid rgba(51, 65, 85, 0.6)' }}>
            <button
              onClick={() => onTabChange('invoices')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: activeTab === 'invoices' ? '#2563eb' : 'transparent',
                color: activeTab === 'invoices' ? '#fff' : 'var(--text-secondary)',
                transition: 'all 0.15s ease',
              }}
            >
              <FileText size={14} /> Documents Studio
            </button>

            <button
              onClick={() => onTabChange('hitl')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '12px',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
                background: activeTab === 'hitl' ? '#2563eb' : 'transparent',
                color: activeTab === 'hitl' ? '#fff' : 'var(--text-secondary)',
                transition: 'all 0.15s ease',
              }}
            >
              <ShieldAlert size={14} /> HITL Safety Gate
              {pendingHitlCount > 0 && (
                <span style={{
                  padding: '1px 6px',
                  borderRadius: '9999px',
                  fontSize: '10px',
                  fontWeight: 700,
                  background: '#f59e0b',
                  color: '#000',
                  marginLeft: '2px',
                }}>
                  {pendingHitlCount}
                </span>
              )}
            </button>
          </nav>
        </div>

        {/* Tally Live Connection Status Pill & Actions */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          
          {/* Tally Status Pill */}
          <div 
            onClick={onOpenSettings}
            title="Click to view Tally connection options or switch to Windows Tally"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '6px 14px',
              borderRadius: '9999px',
              background: tallyStatus.online ? 'rgba(16, 185, 129, 0.12)' : 'rgba(59, 130, 246, 0.12)',
              border: `1px solid ${tallyStatus.online ? 'rgba(16, 185, 129, 0.3)' : 'rgba(59, 130, 246, 0.25)'}`,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
            }}
          >
            <span className={`pulse-dot ${tallyStatus.online ? 'online' : 'online'}`} style={{ background: tallyStatus.online ? '#10b981' : '#38bdf8' }} />
            <div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: tallyStatus.online ? '#34d399' : '#38bdf8' }}>
                {tallyStatus.online ? `Tally: ${tallyStatus.company_name}` : 'Standalone Mode'}
              </div>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                {tallyStatus.online ? 'Port 9000 Live' : 'AI Extraction Active'}
              </div>
            </div>
            <Settings size={13} color="var(--text-muted)" style={{ marginLeft: '4px' }} />
          </div>

          {/* Batch Sync Button (if any auto_ready invoices) */}
          {readyCount > 0 && activeTab === 'invoices' && (
            <button 
              id="batch-sync-btn"
              onClick={onBatchSync}
              className="btn btn-success"
              style={{ padding: '7px 14px', fontSize: '13px' }}
            >
              <Zap size={14} /> Stage Ready ({readyCount})
            </button>
          )}

          {/* New Upload Button */}
          {activeTab === 'invoices' && (
            <button 
              id="new-upload-btn"
              onClick={onNewUpload}
              className="btn btn-primary"
              style={{ padding: '7px 14px', fontSize: '13px' }}
            >
              <Layers size={14} /> Upload Invoices
            </button>
          )}

          {/* Settings Modal Toggle */}
          <button 
            id="settings-modal-btn"
            onClick={onOpenSettings}
            className="btn btn-secondary"
            title="Configure Tally & Gemini API"
            style={{ padding: '7px 10px' }}
          >
            <Settings size={16} />
          </button>

        </div>

      </div>
    </header>
  );
};

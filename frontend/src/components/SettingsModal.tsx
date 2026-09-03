import React, { useState } from 'react';
import { TallyStatus } from '../types';
import { X, Terminal, Server, Key, Check, Copy, ExternalLink, Shield } from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  tallyStatus: TallyStatus;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose, tallyStatus }) => {
  const [copiedCmd, setCopiedCmd] = useState(false);

  if (!isOpen) return null;

  const connectorCommand = 'python tally_connector.py --server http://localhost:8000 --tally-port 9000';

  const copyCommand = () => {
    navigator.clipboard.writeText(connectorCommand);
    setCopiedCmd(true);
    setTimeout(() => setCopiedCmd(false), 2000);
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px',
    }}>
      <div className="glass-panel" style={{
        width: '100%',
        maxWidth: '750px',
        maxHeight: '90vh',
        overflowY: 'auto',
        border: '1px solid var(--border-medium)',
      }}>
        {/* Header */}
        <div style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Server size={20} color="#38bdf8" />
            <h3 style={{ fontSize: '17px', fontWeight: 700, margin: 0, color: '#fff' }}>
              TallyPrime Port 9000 & Connector Configuration
            </h3>
          </div>
          <button onClick={onClose} className="btn btn-secondary" style={{ padding: '6px' }}>
            <X size={16} />
          </button>
        </div>

        {/* Body Content */}
        <div style={{ padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          
          {/* Active Connection Status Card */}
          <div style={{
            background: tallyStatus.online ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${tallyStatus.online ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
            borderRadius: '10px',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: tallyStatus.online ? '#34d399' : '#f87171' }}>
                Status: {tallyStatus.online ? 'TallyPrime Online & Ready' : 'Connector Offline'}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
                {tallyStatus.online ? `Active Company: ${tallyStatus.company_name}` : tallyStatus.error || 'No active heartbeat detected from tally_connector.py'}
              </div>
            </div>
            <span className={`pill ${tallyStatus.online ? 'pill-green' : 'pill-red'}`}>
              Port 9000
            </span>
          </div>

          {/* Section 1: Windows Tally Configuration */}
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
              1. Enable XML Server in TallyPrime (Windows)
            </h4>
            <ol style={{ paddingLeft: '20px', fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.7' }}>
              <li>Open <strong>TallyPrime</strong> on your computer.</li>
              <li>Press <kbd style={{ background: '#1e293b', padding: '2px 6px', borderRadius: '4px' }}>F12</kbd> (Configure) &gt; Select <strong>Advanced Configuration</strong>.</li>
              <li>Set <strong>Tally is acting as</strong>: <code style={{ color: '#38bdf8' }}>Both</code> or <code style={{ color: '#38bdf8' }}>Server</code>.</li>
              <li>Set <strong>Port</strong>: <code style={{ color: '#38bdf8' }}>9000</code>.</li>
              <li>Save and restart TallyPrime when prompted.</li>
            </ol>
          </div>

          {/* Section 2: Run the Local Sync Connector */}
          <div>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', marginBottom: '8px' }}>
              2. Launch the Local Sync Connector Daemon
            </h4>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
              Run this single Python command on the machine running TallyPrime. It creates an outbound TLS link to the web app and posts approved vouchers to <code style={{ color: '#38bdf8' }}>http://localhost:9000</code> without requiring any router port-forwarding:
            </p>

            <div style={{
              background: '#050811',
              padding: '12px 16px',
              borderRadius: '8px',
              border: '1px solid var(--border-subtle)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontFamily: 'monospace',
              fontSize: '13px',
              color: '#38bdf8',
            }}>
              <span>{connectorCommand}</span>
              <button onClick={copyCommand} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '12px' }}>
                {copiedCmd ? <Check size={13} color="#34d399" /> : <Copy size={13} />}
                {copiedCmd ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Section 3: Built-in Virtual Tally Simulator */}
          <div style={{
            background: 'rgba(59, 130, 246, 0.08)',
            border: '1px solid rgba(59, 130, 246, 0.2)',
            borderRadius: '10px',
            padding: '16px',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <Shield size={16} color="#38bdf8" />
              <h4 style={{ fontSize: '14px', fontWeight: 700, color: '#fff', margin: 0 }}>
                Virtual Tally Simulator (For macOS / Linux / Demos)
              </h4>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.5' }}>
              Developing on macOS or deploying on GCP Cloud Run? Run <code style={{ color: '#38bdf8' }}>python backend/tally_bridge/virtual_tally.py</code> to start the simulated TallyPrime HTTP server on Port 9000 with preloaded company ledgers and stock items!
            </p>
          </div>

        </div>

        {/* Footer */}
        <div style={{
          padding: '14px 24px',
          borderTop: '1px solid var(--border-subtle)',
          textAlign: 'right',
        }}>
          <button onClick={onClose} className="btn btn-primary" style={{ padding: '7px 20px' }}>
            Done
          </button>
        </div>

      </div>
    </div>
  );
};

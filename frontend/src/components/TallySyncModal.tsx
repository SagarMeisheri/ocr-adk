import React, { useState } from 'react';
import { InvoiceListItem } from '../types';
import { X, Copy, Check, Zap, Download, FileCode } from 'lucide-react';
import { syncSingleInvoiceToTally, getTallyXmlDownloadUrl } from '../services/api';

interface TallySyncModalProps {
  invoice: InvoiceListItem | null;
  onClose: () => void;
  onSynced: () => void;
}

export const TallySyncModal: React.FC<TallySyncModalProps> = ({ invoice, onClose, onSynced }) => {
  const [copied, setCopied] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);

  if (!invoice) return null;

  const xmlContent = invoice.tally_xml || '<!-- XML Not Generated Yet -->';

  const copyToClipboard = () => {
    navigator.clipboard.writeText(xmlContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSyncNow = async () => {
    setIsSyncing(true);
    try {
      await syncSingleInvoiceToTally(invoice.id);
      alert('Invoice queued for TallyPrime sync! The local connector daemon will post this XML to Port 9000.');
      onSynced();
      onClose();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    } finally {
      setIsSyncing(false);
    }
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
        maxWidth: '850px',
        maxHeight: '90vh',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        border: '1px solid var(--border-medium)',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 24px',
          borderBottom: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <FileCode size={20} color="#38bdf8" />
            <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0, color: '#fff' }}>
              TallyPrime XML Payload: {invoice.invoice_number || invoice.filename}
            </h3>
          </div>
          <button onClick={onClose} className="btn btn-secondary" style={{ padding: '6px' }}>
            <X size={16} />
          </button>
        </div>

        {/* XML Viewer Body */}
        <div style={{ flex: 1, overflow: 'auto', padding: '20px', backgroundColor: '#050811' }}>
          <pre style={{
            fontFamily: 'monospace',
            fontSize: '12px',
            color: '#34d399',
            lineHeight: '1.5',
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}>
            {xmlContent}
          </pre>
        </div>

        {/* Footer */}
        <div style={{
          padding: '16px 24px',
          borderTop: '1px solid var(--border-subtle)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'rgba(15, 23, 42, 0.8)',
        }}>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={copyToClipboard} className="btn btn-secondary" style={{ fontSize: '13px' }}>
              {copied ? <Check size={14} color="#34d399" /> : <Copy size={14} />}
              {copied ? 'Copied XML' : 'Copy XML'}
            </button>
            <a
              href={getTallyXmlDownloadUrl(invoice.id)}
              download
              className="btn btn-secondary"
              style={{ fontSize: '13px', textDecoration: 'none' }}
            >
              <Download size={14} /> Download File
            </a>
          </div>

          <div style={{ display: 'flex', gap: '10px' }}>
            <button onClick={onClose} className="btn btn-secondary" style={{ fontSize: '13px' }}>
              Close
            </button>
            <button
              onClick={handleSyncNow}
              disabled={isSyncing}
              className="btn btn-success"
              style={{ fontSize: '13px', padding: '8px 18px' }}
            >
              <Zap size={14} /> {isSyncing ? 'Posting to Port 9000...' : 'Post to TallyPrime'}
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};

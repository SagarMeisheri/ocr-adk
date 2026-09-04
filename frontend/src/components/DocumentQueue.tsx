import React from 'react';
import { ParsedDocument } from '../types';
import {
  FileText,
  Sparkles,
  Trash2,
  ArrowRight,
  Download,
  Calendar,
  Layers,
} from 'lucide-react';
import { deleteUniversalDocument } from '../services/api';

interface DocumentQueueProps {
  documents: ParsedDocument[];
  activeFilter: string;
  onFilterChange: (filter: string) => void;
  onSelectDocument: (doc: ParsedDocument) => void;
  onRefresh: () => void;
}

export const DocumentQueue: React.FC<DocumentQueueProps> = ({
  documents,
  activeFilter,
  onFilterChange,
  onSelectDocument,
  onRefresh,
}) => {
  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm('Are you sure you want to delete this document?')) {
      await deleteUniversalDocument(id);
      onRefresh();
    }
  };

  const handleDownloadMarkdown = (e: React.MouseEvent, doc: ParsedDocument) => {
    e.stopPropagation();
    const element = document.createElement('a');
    const file = new Blob([doc.raw_markdown || ''], { type: 'text/markdown' });
    element.href = URL.createObjectURL(file);
    element.download = `${(doc.title || doc.filename || 'transcription').replace(/\s+/g, '_')}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div className="glass-panel" style={{ margin: '0 24px', padding: '20px' }}>
      {/* Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
          borderBottom: '1px solid var(--border-subtle)',
          paddingBottom: '16px',
          marginBottom: '20px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <h3 style={{ fontSize: '16px', fontWeight: 700, color: '#fff', margin: 0 }}>
            Transcribed Documents Queue
          </h3>
          <span className="pill pill-blue" style={{ fontSize: '11px' }}>
            {documents.length} Total
          </span>
        </div>

        <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
          High-Fidelity Visual Markdown Transcription Engine
        </div>
      </div>

      {/* Document List */}
      {documents.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '48px 16px', color: 'var(--text-secondary)' }}>
          <Layers size={36} color="var(--text-muted)" style={{ margin: '0 auto 12px auto' }} />
          <h4 style={{ color: '#fff', fontSize: '15px', marginBottom: '4px' }}>No documents uploaded yet</h4>
          <p style={{ fontSize: '13px', margin: 0 }}>
            Upload any invoice, purchase order, receipt, or document above to transcribe into layout-preserved Markdown.
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {documents.map((doc) => {
            const raw = doc.raw_markdown || '';
            const lineCount = raw ? raw.split('\n').length : 0;
            const tableRowsCount = raw ? raw.split('\n').filter(l => l.trim().startsWith('|')).length : 0;
            const ext = doc.filename ? doc.filename.split('.').pop()?.toUpperCase() : 'DOC';

            return (
              <div
                key={doc.id}
                onClick={() => onSelectDocument(doc)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 18px',
                  borderRadius: '10px',
                  background: 'rgba(30, 41, 59, 0.4)',
                  border: '1px solid rgba(51, 65, 85, 0.5)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(30, 41, 59, 0.75)';
                  e.currentTarget.style.borderColor = 'rgba(56, 189, 248, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(30, 41, 59, 0.4)';
                  e.currentTarget.style.borderColor = 'rgba(51, 65, 85, 0.5)';
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div
                    style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '8px',
                      background: 'rgba(56, 189, 248, 0.12)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: '#38bdf8',
                      fontWeight: 700,
                      fontSize: '11px',
                    }}
                  >
                    {ext}
                  </div>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>
                        {doc.title || doc.filename}
                      </span>
                      <span className="pill pill-green" style={{ fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                        <Sparkles size={10} /> Transcribed
                      </span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px', fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      <span>File: <strong style={{ color: 'var(--text-primary)' }}>{doc.filename || 'document'}</strong></span>
                      <span>{lineCount} lines</span>
                      <span>{tableRowsCount} table rows</span>
                      <span style={{ color: '#38bdf8' }}>Layout Preserved</span>
                    </div>
                  </div>
                </div>

                {/* Right Side: Actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <button
                    onClick={(e) => handleDownloadMarkdown(e, doc)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 12px', fontSize: '12px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    title="Download Markdown file"
                  >
                    <Download size={13} /> .md
                  </button>

                  <button
                    onClick={(e) => handleDelete(e, doc.id)}
                    className="btn btn-secondary"
                    style={{ padding: '6px 10px', color: '#f87171' }}
                    title="Delete document"
                  >
                    <Trash2 size={13} />
                  </button>

                  <span style={{ color: 'var(--text-muted)' }}>
                    <ArrowRight size={16} />
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

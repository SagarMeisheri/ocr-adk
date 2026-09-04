import React, { useState } from 'react';
import { ParsedDocument } from '../types';
import {
  ArrowLeft,
  Download,
  Copy,
  Check,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Code,
  FileText,
  Cpu,
  ExternalLink,
  Sparkles,
  Brain,
  Layers,
} from 'lucide-react';
import { WorkflowGraph } from './WorkflowGraph';
import { MarkdownView } from './MarkdownView';

interface DocumentInspectorProps {
  document: ParsedDocument;
  onBack: () => void;
  onRefresh: () => void;
}

export const DocumentInspector: React.FC<DocumentInspectorProps> = ({
  document: doc,
  onBack,
  onRefresh,
}) => {
  const [zoom, setZoom] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [activeTab, setActiveTab] = useState<'markdown' | 'raw' | 'workflow' | 'reasoning'>('markdown');
  const [showQuickThoughts, setShowQuickThoughts] = useState(false);
  const [copied, setCopied] = useState(false);

  const fileUrl = (doc as any).file_url || `/api/documents/${doc.id}/file`;
  const isPdf =
    (doc.filename && doc.filename.toLowerCase().endsWith('.pdf')) ||
    (doc.content_type && doc.content_type === 'application/pdf');

  const rawOutput = doc.raw_markdown || '';
  const linesCount = rawOutput ? rawOutput.split('\n').length : 0;
  const thinkingSteps = doc.thinking_process || [];
  const thoughtTokens = doc.thoughts_token_count || 0;

  const handleCopy = () => {
    navigator.clipboard.writeText(rawOutput);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const element = document.createElement('a');
    const file = new Blob([rawOutput], { type: 'text/markdown;charset=utf-8' });
    element.href = URL.createObjectURL(file);
    element.download = `${(doc.title || doc.filename || 'gemini_transcription').replace(/\s+/g, '_')}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  return (
    <div style={{ margin: '0 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Top Header Bar */}
      <div
        className="glass-panel"
        style={{
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button onClick={onBack} className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '13px' }}>
            <ArrowLeft size={16} /> Back
          </button>

          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '17px', fontWeight: 700, color: '#fff', margin: 0 }}>
                {doc.title || doc.filename}
              </h2>
              <span className="pill pill-green" style={{ fontSize: '11px', textTransform: 'uppercase' }}>
                <Sparkles size={11} style={{ marginRight: '3px' }} /> Transcribed
              </span>
            </div>
            <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
              {linesCount} Lines &bull; {rawOutput.length} Characters &bull; Preserved Visual Layout
            </div>
          </div>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <button
            onClick={handleCopy}
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            {copied ? <Check size={14} style={{ color: '#34d399' }} /> : <Copy size={14} />}
            {copied ? 'Copied!' : 'Copy Markdown'}
          </button>

          <button
            onClick={handleDownload}
            className="btn btn-success"
            style={{ fontSize: '12px', padding: '6px 12px', display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <Download size={14} /> Download .md
          </button>

          <div style={{ display: 'flex', gap: '4px', background: 'rgba(15, 23, 42, 0.6)', padding: '2px', borderRadius: '8px' }}>
            <button
              onClick={() => setActiveTab('markdown')}
              className={`btn ${activeTab === 'markdown' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '12px', padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <FileText size={13} /> Rendered Document
            </button>
            <button
              onClick={() => setActiveTab('raw')}
              className={`btn ${activeTab === 'raw' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '12px', padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Code size={13} /> Raw Source
            </button>
            <button
              onClick={() => setActiveTab('reasoning')}
              className={`btn ${activeTab === 'reasoning' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '12px', padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Brain size={13} style={{ color: activeTab === 'reasoning' ? '#fff' : '#c084fc' }} />
              Reasoning
              {thoughtTokens > 0 && (
                <span
                  style={{
                    fontSize: '10px',
                    background: activeTab === 'reasoning' ? 'rgba(255,255,255,0.2)' : 'rgba(168, 85, 247, 0.25)',
                    color: activeTab === 'reasoning' ? '#fff' : '#d8b4fe',
                    padding: '1px 6px',
                    borderRadius: '10px',
                    fontWeight: 600,
                  }}
                >
                  {thoughtTokens.toLocaleString()}t
                </span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('workflow')}
              className={`btn ${activeTab === 'workflow' ? 'btn-primary' : 'btn-secondary'}`}
              style={{ fontSize: '12px', padding: '5px 12px', display: 'inline-flex', alignItems: 'center', gap: '5px' }}
            >
              <Cpu size={13} /> ADK Workflow
            </button>
          </div>
        </div>
      </div>

      {/* Main Split Screen Workspace */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', minHeight: 'calc(100vh - 220px)' }}>
        {/* Left Pane: Document Preview */}
        <div className="glass-panel" style={{ padding: '16px', display: 'flex', flexDirection: 'column' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '12px',
              paddingBottom: '8px',
              borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                Source Document
              </span>
              <a
                href={fileUrl}
                target="_blank"
                rel="noreferrer"
                className="btn btn-secondary"
                style={{ padding: '2px 7px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                title="Open original document in new browser tab"
              >
                <ExternalLink size={11} /> Open Original
              </a>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.15))}
                className="btn btn-secondary"
                style={{ padding: '4px 8px' }}
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)', minWidth: '40px', textAlign: 'center' }}>
                {Math.round(zoom * 100)}%
              </span>
              <button
                onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
                className="btn btn-secondary"
                style={{ padding: '4px 8px' }}
                title="Zoom In"
              >
                <ZoomIn size={14} />
              </button>
              <button
                onClick={() => setRotation((r) => (r + 90) % 360)}
                className="btn btn-secondary"
                style={{ padding: '4px 8px' }}
                title="Rotate 90°"
              >
                <RotateCw size={14} />
              </button>
            </div>
          </div>

          <div
            style={{
              flex: 1,
              overflow: 'auto',
              background: 'rgba(15, 23, 42, 0.6)',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '560px',
              padding: '12px',
            }}
          >
            {isPdf ? (
              <iframe
                src={`${fileUrl}#toolbar=0&navpanes=0`}
                title="Source PDF Preview"
                style={{
                  width: '100%',
                  height: '100%',
                  minHeight: '560px',
                  border: 'none',
                  borderRadius: '6px',
                  transform: `scale(${zoom}) rotate(${rotation}deg)`,
                  transformOrigin: 'center center',
                  transition: 'transform 0.15s ease',
                }}
              />
            ) : (
              <img
                src={fileUrl}
                alt="Uploaded Document"
                style={{
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                  transform: `scale(${zoom}) rotate(${rotation}deg)`,
                  transformOrigin: 'center center',
                  transition: 'transform 0.15s ease',
                  borderRadius: '6px',
                  boxShadow: '0 4px 20px rgba(0, 0, 0, 0.4)',
                }}
              />
            )}
          </div>
        </div>

        {/* Right Pane: Formatted Gemini Markdown */}
        <div
          className="glass-panel"
          style={{
            padding: '20px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            overflowY: 'auto',
            maxHeight: 'calc(100vh - 220px)',
          }}
        >
          {activeTab === 'reasoning' ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* Header card with thinking statistics */}
              <div
                style={{
                  background: 'linear-gradient(135deg, rgba(88, 28, 135, 0.25) 0%, rgba(30, 27, 75, 0.4) 100%)',
                  border: '1px solid rgba(168, 85, 247, 0.3)',
                  borderRadius: '10px',
                  padding: '16px 20px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <div
                      style={{
                        width: '36px',
                        height: '36px',
                        borderRadius: '8px',
                        background: 'rgba(168, 85, 247, 0.2)',
                        border: '1px solid rgba(168, 85, 247, 0.4)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <Brain size={20} style={{ color: '#c084fc' }} />
                    </div>
                    <div>
                      <h4 style={{ fontSize: '15px', fontWeight: 700, color: '#fff', margin: 0 }}>
                        Gemini Thinking Process &amp; Reasoning
                      </h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: '2px 0 0 0' }}>
                        Internal reasoning executed with thinking level set to low by default
                      </p>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      style={{
                        fontSize: '11px',
                        padding: '4px 10px',
                        borderRadius: '20px',
                        background: 'rgba(168, 85, 247, 0.15)',
                        border: '1px solid rgba(168, 85, 247, 0.3)',
                        color: '#d8b4fe',
                        fontWeight: 600,
                      }}
                    >
                      Thinking: {((doc.workflow_execution?.steps?.find((s) => s.step_id === 'gemini_multimodal_extraction')?.details?.thinking_level) || 'low').toUpperCase()}
                    </span>
                    {thoughtTokens > 0 && (
                      <span
                        style={{
                          fontSize: '11px',
                          padding: '4px 10px',
                          borderRadius: '20px',
                          background: 'rgba(56, 189, 248, 0.15)',
                          border: '1px solid rgba(56, 189, 248, 0.3)',
                          color: '#38bdf8',
                          fontWeight: 600,
                        }}
                      >
                        {thoughtTokens.toLocaleString()} Thought Tokens
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Thought steps list */}
              {thinkingSteps.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {thinkingSteps.map((stepText, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'rgba(15, 23, 42, 0.75)',
                        border: '1px solid rgba(147, 51, 234, 0.25)',
                        borderRadius: '8px',
                        padding: '16px',
                        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '8px',
                          marginBottom: '10px',
                          paddingBottom: '8px',
                          borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
                        }}
                      >
                        <span
                          style={{
                            fontSize: '11px',
                            fontWeight: 700,
                            color: '#c084fc',
                            background: 'rgba(168, 85, 247, 0.15)',
                            padding: '2px 8px',
                            borderRadius: '6px',
                          }}
                        >
                          Step {idx + 1}
                        </span>
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                          Reasoning Summary &amp; Document Analysis
                        </span>
                      </div>
                      <div
                        style={{
                          fontSize: '13px',
                          lineHeight: '1.6',
                          color: '#e2e8f0',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'inherit',
                        }}
                      >
                        {stepText}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  style={{
                    background: 'rgba(15, 23, 42, 0.5)',
                    border: '1px dashed rgba(168, 85, 247, 0.25)',
                    borderRadius: '8px',
                    padding: '28px 20px',
                    textAlign: 'center',
                  }}
                >
                  <Brain size={28} style={{ color: 'var(--text-muted)', marginBottom: '8px' }} />
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 6px 0' }}>
                    {thoughtTokens > 0
                      ? `Model completed reasoning using ${thoughtTokens.toLocaleString()} thought tokens.`
                      : 'No thought summaries emitted for this document.'}
                  </p>
                  <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', margin: 0, maxWidth: '480px', marginInline: 'auto' }}>
                    Gemini 3 and 2.5 thinking models reason internally before responding.
                    With thinking level set to low and thinking summaries enabled, multi-step analysis details appear here.
                  </p>
                </div>
              )}
            </div>
          ) : activeTab === 'workflow' ? (
            <div>
              <h4 style={{ fontSize: '14px', fontWeight: 600, color: '#fff', marginBottom: '14px' }}>
                Google ADK Workflow Execution DAG
              </h4>
              <WorkflowGraph execution={doc.workflow_execution} isLive={false} compact={false} />
            </div>
          ) : activeTab === 'raw' ? (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-secondary)' }}>
                  Raw Markdown Source Code
                </span>
                <button
                  onClick={handleCopy}
                  className="btn btn-secondary"
                  style={{ fontSize: '11px', padding: '3px 8px' }}
                >
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>

              <textarea
                readOnly
                value={rawOutput || 'No output from model.'}
                style={{
                  width: '100%',
                  flex: 1,
                  minHeight: '520px',
                  background: 'rgba(15, 23, 42, 0.85)',
                  border: '1px solid rgba(56, 189, 248, 0.25)',
                  borderRadius: '8px',
                  padding: '16px',
                  fontSize: '12.5px',
                  color: '#38bdf8',
                  fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
                  lineHeight: '1.6',
                  whiteSpace: 'pre',
                  overflow: 'auto',
                  resize: 'none',
                }}
              />
            </div>
          ) : (
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '12px',
                  paddingBottom: '8px',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                <span style={{ fontSize: '13px', fontWeight: 600, color: '#38bdf8', display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={14} /> Transcribed Document
                </span>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                  Rendered Tables, Headings &amp; Layout
                </span>
              </div>

              {thinkingSteps.length > 0 && (
                <div
                  style={{
                    background: 'rgba(88, 28, 135, 0.18)',
                    border: '1px solid rgba(168, 85, 247, 0.25)',
                    borderRadius: '8px',
                    padding: '10px 14px',
                    marginBottom: '14px',
                  }}
                >
                  <div
                    onClick={() => setShowQuickThoughts(!showQuickThoughts)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      userSelect: 'none',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <Brain size={15} style={{ color: '#c084fc' }} />
                      <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#e9d5ff' }}>
                        Gemini Thinking Summary ({thinkingSteps.length} step{thinkingSteps.length === 1 ? '' : 's'})
                      </span>
                      {thoughtTokens > 0 && (
                        <span style={{ fontSize: '11px', color: '#a855f7', background: 'rgba(168, 85, 247, 0.15)', padding: '1px 7px', borderRadius: '12px' }}>
                          {thoughtTokens.toLocaleString()} tokens &bull; Level: Low
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setActiveTab('reasoning');
                        }}
                        className="btn btn-secondary"
                        style={{ fontSize: '11px', padding: '2px 8px', color: '#c084fc' }}
                      >
                        View Full Reasoning &rarr;
                      </button>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {showQuickThoughts ? '▲ Hide' : '▼ View'}
                      </span>
                    </div>
                  </div>

                  {showQuickThoughts && (
                    <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid rgba(168, 85, 247, 0.15)', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {thinkingSteps.map((step, idx) => (
                        <div key={idx} style={{ fontSize: '12px', color: '#cbd5e1', lineHeight: '1.5', background: 'rgba(15, 23, 42, 0.6)', padding: '8px 12px', borderRadius: '6px' }}>
                          <span style={{ color: '#c084fc', fontWeight: 600, marginRight: '6px' }}>Step {idx + 1}:</span>
                          {step}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              <MarkdownView content={rawOutput} />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

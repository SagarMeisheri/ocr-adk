import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, FileText, Landmark, Receipt, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import { uploadUniversalDocuments } from '../services/api';
import { WorkflowGraph } from './WorkflowGraph';
import { WorkflowExecution } from '../types';

interface UploadZoneProps {
  onUploadSuccess: () => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [currentStepId, setCurrentStepId] = useState<string>('document_ingestion');
  const [liveExecution, setLiveExecution] = useState<WorkflowExecution | undefined>(undefined);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // Connect to WebSocket for live pipeline step broadcasting
    let ws: WebSocket | null = null;
    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/events`;
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'WORKFLOW_STEP_UPDATE') {
            setCurrentStepId(data.step_id);
            setUploadStatus(`Stage: ${data.step_id.replace(/_/g, ' ')}...`);
          }
        } catch {
          // Ignore parse errors
        }
      };
    } catch {
      // WebSocket optional fallback
    }

    return () => {
      if (ws) ws.close();
    };
  }, []);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setCurrentStepId('document_ingestion');
    setUploadStatus(`Ingesting and normalizing ${files.length} document(s)...`);

    try {
      const fileArray = Array.from(files);

      // Transition to Gemini vision step while upload processes
      setTimeout(() => {
        setCurrentStepId('gemini_multimodal_extraction');
        setUploadStatus('Gemini 3.8 Flash Multimodal OCR & Reasoning (Single-Pass)...');
      }, 300);

      const res = await uploadUniversalDocuments(fileArray);

      // On response, transition through deterministic validation and staging
      setCurrentStepId('deterministic_validation');
      setUploadStatus('GSTIN & Mathematical Verification...');
      await new Promise((r) => setTimeout(r, 250));

      setCurrentStepId('ledger_resolution_xml_staging');
      setUploadStatus('Ledger Resolution & XML Voucher Staging...');
      await new Promise((r) => setTimeout(r, 250));

      if (res.results && res.results[0]?.workflow_execution) {
        setLiveExecution(res.results[0].workflow_execution);
      }

      setUploadStatus(`Extracted and processed ${fileArray.length} document(s) successfully!`);
      setTimeout(() => {
        setUploadStatus(null);
        setUploading(false);
        setLiveExecution(undefined);
        onUploadSuccess();
      }, 800);
    } catch (err: any) {
      setUploadStatus(`Extraction error: ${err.message}`);
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const loadPresetSample = async (sampleType: string) => {
    setUploading(true);
    setCurrentStepId('document_ingestion');
    setUploadStatus(`Loading demo ${sampleType} document...`);

    let filename = 'digital_gst_invoice.pdf';
    if (sampleType === 'bank_statement') filename = 'hdfc_bank_statement_aug2026.pdf';
    if (sampleType === 'handwritten') filename = 'kirana_handwritten_bill.jpg';
    if (sampleType === 'receipt') filename = 'retail_store_receipt.pdf';

    const mockContent = `Sample ${sampleType} document for TrulyTally AI Document Engine`;
    const blob = new Blob([mockContent], { type: 'application/pdf' });
    const sampleFile = new File([blob], filename, { type: 'application/pdf' });

    try {
      setTimeout(() => {
        setCurrentStepId('gemini_multimodal_extraction');
        setUploadStatus('Gemini 3.8 Flash Vision (Single-Pass Extraction)...');
      }, 300);

      const res = await uploadUniversalDocuments([sampleFile]);

      setCurrentStepId('deterministic_validation');
      await new Promise((r) => setTimeout(r, 200));

      setCurrentStepId('ledger_resolution_xml_staging');
      await new Promise((r) => setTimeout(r, 200));

      if (res.results && res.results[0]?.workflow_execution) {
        setLiveExecution(res.results[0].workflow_execution);
      }

      setUploadStatus(`Extracted ${filename} successfully!`);
      setTimeout(() => {
        setUploadStatus(null);
        setUploading(false);
        setLiveExecution(undefined);
        onUploadSuccess();
      }, 800);
    } catch (err: any) {
      setUploadStatus(`Failed: ${err.message}`);
      setUploading(false);
    }
  };


  return (
    <div className="glass-panel" style={{ margin: '0 24px 20px 24px', padding: '24px' }}>
      <div
        id="universal-document-dropzone"
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        style={{
          border: `2px dashed ${isDragging ? '#3b82f6' : 'rgba(255, 255, 255, 0.15)'}`,
          borderRadius: '12px',
          padding: '36px 20px',
          textAlign: 'center',
          backgroundColor: isDragging ? 'rgba(59, 130, 246, 0.08)' : 'rgba(15, 23, 42, 0.4)',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.jpg,.jpeg,.png,.webp,.tiff"
          style={{ display: 'none' }}
          onChange={(e) => handleFiles(e.target.files)}
        />

        <div style={{
          width: '56px',
          height: '56px',
          borderRadius: '50%',
          background: 'rgba(59, 130, 246, 0.12)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          margin: '0 auto 16px auto',
          color: '#38bdf8',
        }}>
          <UploadCloud size={28} />
        </div>

        <h3 style={{ fontSize: '17px', fontWeight: 600, color: '#fff', marginBottom: '6px' }}>
          Drop Any Financial Document Here (Invoices, Bank Statements, Receipts, Bills)
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '0 0 16px 0' }}>
          Supports multi-page PDFs, high-res scans, mobile photos, and handwritten bills &bull; Auto-classified by Gemini
        </p>

        {uploading ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px', width: '100%' }}>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '10px', color: '#38bdf8', fontSize: '14px', fontWeight: 600 }}>
              <span className="spinner" />
              <span>{uploadStatus}</span>
            </div>
            <div style={{ width: '100%', maxWidth: '960px', textAlign: 'left' }}>
              <WorkflowGraph
                execution={liveExecution}
                currentStepId={currentStepId}
                isLive={true}
                compact={false}
              />
            </div>
          </div>
        ) : (
          <span className="btn btn-primary" style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={16} /> Browse Documents
          </span>
        )}
      </div>

      <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
          <Sparkles size={14} color="#38bdf8" /> Try instant demo documents:
        </div>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={(e) => { e.stopPropagation(); loadPresetSample('gst_invoice'); }}
          >
            <FileText size={13} color="#38bdf8" /> Tax Invoice (GST)
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={(e) => { e.stopPropagation(); loadPresetSample('bank_statement'); }}
          >
            <Landmark size={13} color="#10b981" /> Bank Statement
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={(e) => { e.stopPropagation(); loadPresetSample('receipt'); }}
          >
            <Receipt size={13} color="#f59e0b" /> Store Receipt
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={(e) => { e.stopPropagation(); loadPresetSample('handwritten'); }}
          >
            <Sparkles size={13} color="#ec4899" /> Handwritten Bill
          </button>
          <button
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '6px' }}
            onClick={(e) => { e.stopPropagation(); loadPresetSample('interstate'); }}
          >
            <Sparkles size={13} color="#a855f7" /> Inter-State (IGST)
          </button>
        </div>
      </div>
    </div>
  );
};

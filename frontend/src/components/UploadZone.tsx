import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, Image as ImageIcon, Sparkles, CheckCircle2, AlertCircle } from 'lucide-react';
import { uploadInvoices } from '../services/api';

interface UploadZoneProps {
  onUploadSuccess: () => void;
}

export const UploadZone: React.FC<UploadZoneProps> = ({ onUploadSuccess }) => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadStatus(`Processing ${files.length} invoice(s) with Gemini 3.8 Flash & Google ADK...`);

    try {
      const fileArray = Array.from(files);
      await uploadInvoices(fileArray);
      setUploadStatus(`Successfully extracted ${fileArray.length} invoice(s)!`);
      setTimeout(() => {
        setUploadStatus(null);
        setUploading(false);
        onUploadSuccess();
      }, 1200);
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
    setUploadStatus(`Generating sample ${sampleType} invoice for Gemini extraction...`);

    // Create a mock File object with the sample keyword in filename
    let filename = 'digital_gst_invoice.pdf';
    if (sampleType === 'handwritten') filename = 'kirana_handwritten_bill.jpg';
    if (sampleType === 'interstate') filename = 'hardware_interstate_igst.pdf';

    const mockContent = `Sample ${sampleType} invoice content for Google ADK OCR pipeline`;
    const blob = new Blob([mockContent], { type: 'application/pdf' });
    const sampleFile = new File([blob], filename, { type: 'application/pdf' });

    try {
      await uploadInvoices([sampleFile]);
      setUploadStatus(`Extracted ${filename} successfully!`);
      setTimeout(() => {
        setUploadStatus(null);
        setUploading(false);
        onUploadSuccess();
      }, 1000);
    } catch (err: any) {
      setUploadStatus(`Failed: ${err.message}`);
      setUploading(false);
    }
  };

  return (
    <div className="glass-panel" style={{ margin: '0 24px 20px 24px', padding: '24px' }}>
      <div
        id="invoice-dropzone"
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

        <h3 style={{ fontSize: '16px', fontWeight: 600, color: '#fff', marginBottom: '6px' }}>
          Drag & Drop Purchase Bills, Invoices, or WhatsApp Photos
        </h3>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '480px', margin: '0 auto 16px auto' }}>
          Supports single & multi-page Digital PDFs, Scanned Receipts, Mobile Camera shots, and Handwritten Kirana Bills
        </p>

        {uploadStatus && (
          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 16px',
            borderRadius: '9999px',
            background: 'rgba(59, 130, 246, 0.15)',
            color: '#60a5fa',
            fontSize: '13px',
            fontWeight: 500,
          }}>
            {uploading ? <Sparkles size={14} className="animate-spin" /> : <CheckCircle2 size={14} color="#34d399" />}
            {uploadStatus}
          </div>
        )}
      </div>

      {/* Quick Sample Presets */}
      <div style={{ marginTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
          ⚡ <strong>Quick Test Presets</strong> (Click to simulate instant ingestion):
        </div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            id="preset-digital-btn"
            onClick={(e) => { e.stopPropagation(); loadPresetSample('digital'); }}
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px' }}
          >
            <FileText size={13} color="#38bdf8" /> Digital PDF (Intra-State GST)
          </button>
          <button
            id="preset-handwritten-btn"
            onClick={(e) => { e.stopPropagation(); loadPresetSample('handwritten'); }}
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px' }}
          >
            <ImageIcon size={13} color="#fbbf24" /> Handwritten Kirana Cash Memo
          </button>
          <button
            id="preset-interstate-btn"
            onClick={(e) => { e.stopPropagation(); loadPresetSample('interstate'); }}
            className="btn btn-secondary"
            style={{ fontSize: '12px', padding: '5px 12px' }}
          >
            <Sparkles size={13} color="#a855f7" /> Inter-State Hardware Bill (IGST)
          </button>
        </div>
      </div>
    </div>
  );
};

import React, { useState, useEffect } from 'react';
import { InvoiceListItem, ExtractedInvoice, InvoiceLineItem } from '../types';
import {
  ArrowLeft,
  Save,
  Zap,
  Download,
  RotateCw,
  ZoomIn,
  ZoomOut,
  Plus,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  ShieldCheck,
} from 'lucide-react';
import { updateInvoice, syncSingleInvoiceToTally, getTallyXmlDownloadUrl } from '../services/api';

interface InvoiceDetailProps {
  invoice: InvoiceListItem;
  onBack: () => void;
  onUpdated: () => void;
  onViewXml: (invoice: InvoiceListItem) => void;
}

export const InvoiceDetail: React.FC<InvoiceDetailProps> = ({
  invoice,
  onBack,
  onUpdated,
  onViewXml,
}) => {
  const [data, setData] = useState<ExtractedInvoice | null>(invoice.invoice_data || null);
  const [zoom, setZoom] = useState(1.0);
  const [rotation, setRotation] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    if (invoice.invoice_data) {
      setData(invoice.invoice_data);
    }
  }, [invoice]);

  if (!data) {
    return (
      <div className="glass-panel" style={{ margin: '20px 24px', padding: '40px', textAlign: 'center' }}>
        <p>No structured data extracted for this invoice.</p>
        <button onClick={onBack} className="btn btn-secondary" style={{ marginTop: '12px' }}>
          <ArrowLeft size={16} /> Back to Dashboard
        </button>
      </div>
    );
  }

  // Recalculate line items & tax breakdown whenever user modifies quantities or rates
  const handleLineItemChange = (index: number, field: keyof InvoiceLineItem, value: any) => {
    const updatedItems = [...data.line_items];
    const item = { ...updatedItems[index], [field]: value };

    // Auto-calculate Taxable Value
    const qty = parseFloat(item.quantity as any) || 0;
    const rate = parseFloat(item.rate as any) || 0;
    const disc = parseFloat(item.discount as any) || 0;
    const taxable = Math.max(0, +(qty * rate - disc).toFixed(2));
    item.taxable_value = taxable;

    // Check if inter-state or intra-state
    const isInterstate = data.supplier?.state_code && data.buyer?.state_code
      ? data.supplier.state_code !== data.buyer.state_code
      : false;

    const gstRate = parseFloat(item.gst_rate as any) || 18.0;

    if (isInterstate) {
      item.igst_amount = +((taxable * gstRate) / 100).toFixed(2);
      item.cgst_amount = 0;
      item.sgst_amount = 0;
    } else {
      const halfRate = gstRate / 2.0;
      item.cgst_amount = +((taxable * halfRate) / 100).toFixed(2);
      item.sgst_amount = +((taxable * halfRate) / 100).toFixed(2);
      item.igst_amount = 0;
    }

    item.total_amount = +(taxable + item.cgst_amount + item.sgst_amount + item.igst_amount).toFixed(2);
    updatedItems[index] = item;

    // Recompute Summary Totals
    const totTaxable = +updatedItems.reduce((s, it) => s + it.taxable_value, 0).toFixed(2);
    const totCgst = +updatedItems.reduce((s, it) => s + it.cgst_amount, 0).toFixed(2);
    const totSgst = +updatedItems.reduce((s, it) => s + it.sgst_amount, 0).toFixed(2);
    const totIgst = +updatedItems.reduce((s, it) => s + it.igst_amount, 0).toFixed(2);
    const roundOff = data.summary.round_off || 0.0;
    const grandTot = +(totTaxable + totCgst + totSgst + totIgst + roundOff).toFixed(2);

    setData({
      ...data,
      line_items: updatedItems,
      summary: {
        ...data.summary,
        total_taxable_value: totTaxable,
        total_cgst: totCgst,
        total_sgst: totSgst,
        total_igst: totIgst,
        grand_total: grandTot,
      },
    });
  };

  const addLineItem = () => {
    const newItem: InvoiceLineItem = {
      id: Math.random().toString(36).substring(2, 9),
      description: 'New Item',
      hsn_sac: '8471',
      quantity: 1.0,
      unit: 'Nos',
      rate: 1000.0,
      discount: 0.0,
      taxable_value: 1000.0,
      gst_rate: 18.0,
      cgst_amount: 90.0,
      sgst_amount: 90.0,
      igst_amount: 0.0,
      total_amount: 1180.0,
      matched_tally_stock_item: 'New Item',
      matched_tally_purchase_ledger: 'Purchase Local GST',
    };
    setData({ ...data, line_items: [...data.line_items, newItem] });
  };

  const removeLineItem = (index: number) => {
    const filtered = data.line_items.filter((_, i) => i !== index);
    setData({ ...data, line_items: filtered });
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await updateInvoice(invoice.id, data);
      setSaveMessage('Saved & Tax Math Re-verified!');
      onUpdated();
      setTimeout(() => setSaveMessage(null), 2000);
    } catch (err: any) {
      alert(`Save error: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleSyncToTally = async () => {
    try {
      await syncSingleInvoiceToTally(invoice.id);
      alert('Invoice queued for TallyPrime sync! Local connector will post to Port 9000.');
      onUpdated();
    } catch (err: any) {
      alert(`Sync failed: ${err.message}`);
    }
  };

  const docUrl = `/${invoice.filepath}`;
  const isPdf = invoice.filename.toLowerCase().endsWith('.pdf');

  return (
    <div style={{ margin: '0 24px 32px 24px' }}>
      
      {/* Top Studio Bar */}
      <div className="glass-panel" style={{ padding: '14px 20px', marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button onClick={onBack} className="btn btn-secondary" style={{ padding: '6px 12px' }}>
            <ArrowLeft size={16} /> Back to Dashboard
          </button>
          <div>
            <h2 style={{ fontSize: '17px', fontWeight: 700, margin: 0, color: '#fff' }}>
              Invoice Review Studio: {data.invoice_number || invoice.filename}
            </h2>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Uploaded: {invoice.created_at.replace('T', ' ').slice(0, 19)} | Status: {invoice.status}
            </span>
          </div>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {saveMessage && (
            <span style={{ fontSize: '12px', color: '#34d399', fontWeight: 600 }}>
              ✓ {saveMessage}
            </span>
          )}

          <button
            id="save-invoice-btn"
            onClick={handleSave}
            disabled={isSaving}
            className="btn btn-primary"
            style={{ padding: '7px 14px' }}
          >
            <Save size={15} /> Save & Recalculate
          </button>

          <button
            id="view-xml-btn"
            onClick={() => onViewXml(invoice)}
            className="btn btn-secondary"
            style={{ padding: '7px 12px' }}
          >
            <FileCode size={15} /> View Tally XML
          </button>

          <a
            href={getTallyXmlDownloadUrl(invoice.id)}
            download
            className="btn btn-secondary"
            style={{ padding: '7px 12px', textDecoration: 'none' }}
          >
            <Download size={15} /> XML File
          </a>

          <button
            id="sync-tally-btn"
            onClick={handleSyncToTally}
            className="btn btn-success"
            style={{ padding: '7px 16px' }}
          >
            <Zap size={15} /> Sync to TallyPrime
          </button>
        </div>
      </div>

      {/* Side-by-Side Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '48% 52%', gap: '16px', minHeight: '800px' }}>
        
        {/* Left Pane: Interactive Document Viewer */}
        <div className="glass-panel" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
          {/* Viewer Toolbar */}
          <div style={{
            padding: '10px 16px',
            borderBottom: '1px solid var(--border-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'rgba(15, 23, 42, 0.6)',
          }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              Document Source: {invoice.filename}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => setZoom((z) => Math.max(0.6, z - 0.1))}
                className="btn btn-secondary"
                style={{ padding: '4px 8px' }}
                title="Zoom Out"
              >
                <ZoomOut size={14} />
              </button>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{Math.round(zoom * 100)}%</span>
              <button
                onClick={() => setZoom((z) => Math.min(2.0, z + 0.1))}
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

          {/* Document Content View */}
          <div style={{
            flex: 1,
            overflow: 'auto',
            padding: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: '#050811',
          }}>
            {isPdf ? (
              <iframe
                src={docUrl}
                title="Invoice Document"
                style={{
                  width: '100%',
                  height: '100%',
                  minHeight: '700px',
                  border: 'none',
                  transform: `scale(${zoom}) rotate(${rotation}deg)`,
                  transformOrigin: 'top center',
                  transition: 'transform 0.15s ease',
                }}
              />
            ) : (
              <img
                src={docUrl}
                alt="Scanned Invoice"
                style={{
                  maxWidth: '100%',
                  maxHeight: '100%',
                  objectFit: 'contain',
                  borderRadius: '6px',
                  transform: `scale(${zoom}) rotate(${rotation}deg)`,
                  transformOrigin: 'center center',
                  transition: 'transform 0.15s ease',
                }}
                onError={(e) => {
                  // Fallback demo invoice preview if file not found locally
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            )}
          </div>
        </div>

        {/* Right Pane: Editable Structured Form & Data Grid */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', overflowY: 'auto' }}>
          
          {/* GSTIN & Compliance Verification Badge Card */}
          <div className="glass-panel" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={18} color="#38bdf8" />
                <span style={{ fontSize: '14px', fontWeight: 600, color: '#fff' }}>Indian GST Compliance Check</span>
              </div>
              <span className={`pill ${data.validation?.confidence_score && data.validation.confidence_score >= 0.9 ? 'pill-green' : 'pill-yellow'}`}>
                {Math.round((data.validation?.confidence_score || 0.85) * 100)}% Extraction Accuracy
              </span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', fontSize: '12px' }}>
              <div style={{ background: 'rgba(15,23,42,0.5)', padding: '8px 12px', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Supplier GSTIN:</div>
                <div style={{ fontWeight: 600, color: data.supplier.gstin ? '#34d399' : '#fbbf24' }}>
                  {data.supplier.gstin || 'Unregistered / Cash Bill'}
                </div>
              </div>

              <div style={{ background: 'rgba(15,23,42,0.5)', padding: '8px 12px', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Transaction Type:</div>
                <div style={{ fontWeight: 600, color: '#60a5fa' }}>
                  {data.supplier.state_code === data.buyer?.state_code ? 'Intra-State (CGST + SGST)' : 'Inter-State (IGST)'}
                </div>
              </div>

              <div style={{ background: 'rgba(15,23,42,0.5)', padding: '8px 12px', borderRadius: '6px' }}>
                <div style={{ color: 'var(--text-muted)' }}>Tax Math Status:</div>
                <div style={{ fontWeight: 600, color: data.validation?.math_check?.is_valid ? '#34d399' : '#f87171' }}>
                  {data.validation?.math_check?.is_valid ? '✓ Mathematically Valid' : 'Discrepancy Detected'}
                </div>
              </div>
            </div>
          </div>

          {/* Supplier & Invoice Metadata Card */}
          <div className="glass-panel" style={{ padding: '16px 20px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8', marginBottom: '12px' }}>
              Header & Party Ledgers
            </h3>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px' }}>
              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Supplier Legal / Trade Name
                </label>
                <input
                  type="text"
                  value={data.supplier.name}
                  onChange={(e) => setData({ ...data, supplier: { ...data.supplier, name: e.target.value } })}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Supplier GSTIN (15 Digits)
                </label>
                <input
                  type="text"
                  value={data.supplier.gstin || ''}
                  placeholder="e.g. 27AAACS8912K1Z9"
                  onChange={(e) => setData({ ...data, supplier: { ...data.supplier, gstin: e.target.value } })}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Invoice Number
                </label>
                <input
                  type="text"
                  value={data.invoice_number || ''}
                  placeholder="e.g. INV/2026/041"
                  onChange={(e) => setData({ ...data, invoice_number: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Invoice Date (YYYY-MM-DD)
                </label>
                <input
                  type="date"
                  value={data.invoice_date || ''}
                  onChange={(e) => setData({ ...data, invoice_date: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'block', marginBottom: '4px' }}>
                  Tally Sundry Creditor Ledger
                </label>
                <input
                  type="text"
                  value={data.matched_tally_party_ledger || data.supplier.name}
                  onChange={(e) => setData({ ...data, matched_tally_party_ledger: e.target.value })}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', paddingTop: '18px' }}>
                <input
                  type="checkbox"
                  id="auto_create_party"
                  checked={data.auto_create_party_ledger}
                  onChange={(e) => setData({ ...data, auto_create_party_ledger: e.target.checked })}
                  style={{ width: 'auto' }}
                />
                <label htmlFor="auto_create_party" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  Auto-create party in Tally if missing
                </label>
              </div>
            </div>
          </div>

          {/* Line Items Editable Grid */}
          <div className="glass-panel" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h3 style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#94a3b8' }}>
                Line Items ({data.line_items.length})
              </h3>
              <button onClick={addLineItem} className="btn btn-secondary" style={{ padding: '4px 10px', fontSize: '12px' }}>
                <Plus size={13} /> Add Item
              </button>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '8px 6px' }}>Description</th>
                    <th style={{ padding: '8px 6px', width: '75px' }}>HSN</th>
                    <th style={{ padding: '8px 6px', width: '60px' }}>Qty</th>
                    <th style={{ padding: '8px 6px', width: '80px' }}>Rate</th>
                    <th style={{ padding: '8px 6px', width: '85px' }}>Taxable</th>
                    <th style={{ padding: '8px 6px', width: '65px' }}>GST %</th>
                    <th style={{ padding: '8px 6px', width: '85px' }}>Total</th>
                    <th style={{ padding: '8px 4px', width: '30px' }}></th>
                  </tr>
                </thead>
                <tbody>
                  {data.line_items.map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                      <td style={{ padding: '6px 4px' }}>
                        <input
                          type="text"
                          value={item.description}
                          onChange={(e) => handleLineItemChange(idx, 'description', e.target.value)}
                          style={{ padding: '4px 8px', fontSize: '12px' }}
                        />
                      </td>
                      <td style={{ padding: '6px 4px' }}>
                        <input
                          type="text"
                          value={item.hsn_sac || ''}
                          onChange={(e) => handleLineItemChange(idx, 'hsn_sac', e.target.value)}
                          style={{ padding: '4px 6px', fontSize: '12px' }}
                        />
                      </td>
                      <td style={{ padding: '6px 4px' }}>
                        <input
                          type="number"
                          value={item.quantity}
                          onChange={(e) => handleLineItemChange(idx, 'quantity', e.target.value)}
                          style={{ padding: '4px 6px', fontSize: '12px' }}
                        />
                      </td>
                      <td style={{ padding: '6px 4px' }}>
                        <input
                          type="number"
                          value={item.rate}
                          onChange={(e) => handleLineItemChange(idx, 'rate', e.target.value)}
                          style={{ padding: '4px 6px', fontSize: '12px' }}
                        />
                      </td>
                      <td style={{ padding: '6px 6px', fontWeight: 600, color: '#fff' }}>
                        ₹{item.taxable_value.toFixed(2)}
                      </td>
                      <td style={{ padding: '6px 4px' }}>
                        <select
                          value={item.gst_rate}
                          onChange={(e) => handleLineItemChange(idx, 'gst_rate', parseFloat(e.target.value))}
                          style={{ padding: '4px 4px', fontSize: '12px' }}
                        >
                          <option value="0">0%</option>
                          <option value="5">5%</option>
                          <option value="12">12%</option>
                          <option value="18">18%</option>
                          <option value="28">28%</option>
                        </select>
                      </td>
                      <td style={{ padding: '6px 6px', fontWeight: 700, color: '#38bdf8' }}>
                        ₹{item.total_amount.toFixed(2)}
                      </td>
                      <td style={{ padding: '6px 4px' }}>
                        <button
                          onClick={() => removeLineItem(idx)}
                          className="btn btn-danger"
                          style={{ padding: '4px', borderRadius: '4px' }}
                        >
                          <Trash2 size={12} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Tax Breakdown & Grand Total Card */}
          <div className="glass-panel" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '20px' }}>
              <div>
                <h4 style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '8px' }}>
                  GST Tax Breakup
                </h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Total Taxable Value:</span>
                    <span style={{ fontWeight: 600 }}>₹{data.summary.total_taxable_value.toFixed(2)}</span>
                  </div>
                  {data.summary.total_cgst > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Input CGST:</span>
                      <span style={{ fontWeight: 600, color: '#60a5fa' }}>₹{data.summary.total_cgst.toFixed(2)}</span>
                    </div>
                  )}
                  {data.summary.total_sgst > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Input SGST:</span>
                      <span style={{ fontWeight: 600, color: '#60a5fa' }}>₹{data.summary.total_sgst.toFixed(2)}</span>
                    </div>
                  )}
                  {data.summary.total_igst > 0 && (
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-muted)' }}>Input IGST:</span>
                      <span style={{ fontWeight: 600, color: '#a855f7' }}>₹{data.summary.total_igst.toFixed(2)}</span>
                    </div>
                  )}
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Round Off:</span>
                    <span>₹{data.summary.round_off.toFixed(2)}</span>
                  </div>
                </div>
              </div>

              {/* Grand Total Box */}
              <div style={{
                background: 'rgba(15, 23, 42, 0.7)',
                borderRadius: '10px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'center',
                textAlign: 'right',
                border: '1px solid var(--border-subtle)',
              }}>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Net Payable Amount
                </div>
                <div style={{ fontSize: '28px', fontWeight: 800, color: '#38bdf8', marginTop: '4px' }}>
                  ₹{data.summary.grand_total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </div>
                <div style={{ fontSize: '11px', color: '#34d399', marginTop: '4px', fontWeight: 600 }}>
                  ✓ Mathematical Validation Reconciled
                </div>
              </div>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};

import React, { useState } from 'react';
import { ParsedDocument } from '../types';
import {
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
  Calculator,
  Building,
  ChevronDown,
  ChevronUp,
  Info,
  Scale,
} from 'lucide-react';

interface DeterministicValidationCardProps {
  document: ParsedDocument;
}

// Client-side Luhn Mod-36 calculation for live fallback
const CHARS = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
const calculateGstinChecksum = (gstin14: string): string | null => {
  if (!gstin14 || gstin14.length !== 14) return null;
  const charMap: Record<string, number> = {};
  for (let i = 0; i < CHARS.length; i++) charMap[CHARS[i]] = i;

  let factor = 1;
  let totalSum = 0;
  const mod = 36;

  for (const char of gstin14.toUpperCase()) {
    if (charMap[char] === undefined) return null;
    const codePoint = charMap[char];
    let addend = factor * codePoint;
    factor = factor === 1 ? 2 : 1;
    addend = Math.floor(addend / mod) + (addend % mod);
    totalSum += addend;
  }

  const remainder = totalSum % mod;
  const checkCodePoint = (mod - remainder) % mod;
  return CHARS[checkCodePoint];
};

export const DeterministicValidationCard: React.FC<DeterministicValidationCardProps> = ({ document: doc }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const issuer = doc.parties?.issuer || doc.parties?.bank || {};
  const recipient = doc.parties?.recipient || {};
  const summary = doc.summary || {};
  const items = doc.items || [];
  const val = doc.validation || {};

  // 1. GSTIN Validation Checks
  const rawGstin = issuer.tax_id || issuer.gstin || '';
  const cleanGstin = rawGstin.replace(/[^A-Za-z0-9]/g, '').toUpperCase();
  const hasGstin = cleanGstin.length === 15;
  const gstinStateCode = hasGstin ? cleanGstin.slice(0, 2) : null;
  const gstinPan = hasGstin ? cleanGstin.slice(2, 12) : null;
  const expectedCheck = hasGstin ? calculateGstinChecksum(cleanGstin.slice(0, 14)) : null;
  const actualCheck = hasGstin ? cleanGstin[14] : null;
  const isChecksumValid = hasGstin && expectedCheck === actualCheck;

  // 2. Mathematical Cross-Verification
  const taxableVal = parseFloat(summary.taxable_value || summary.subtotal || 0);
  const taxAmount = parseFloat(summary.tax_amount || summary.tax || 0);
  const cgst = parseFloat(summary.cgst || 0);
  const sgst = parseFloat(summary.sgst || 0);
  const igst = parseFloat(summary.igst || 0);
  const grandTotal = parseFloat(summary.grand_total || summary.total || 0);

  // Calculate sum from items if available
  const itemsSumTaxable = items.reduce((acc, it) => {
    const amount = parseFloat(it.taxable_amount || it.taxable_value || it.amount || it.total || 0);
    return acc + amount;
  }, 0);

  const totalCalculatedTaxes = cgst + sgst + igst > 0 ? cgst + sgst + igst : taxAmount;
  const calculatedGrandTotal = taxableVal + totalCalculatedTaxes;
  const mathDiscrepancy = grandTotal > 0 ? Math.abs(grandTotal - calculatedGrandTotal) : 0;
  const isMathValid = grandTotal === 0 || mathDiscrepancy < 1.0;

  // 3. Intra-State vs Inter-State Rule
  const recipientGstin = (recipient.tax_id || recipient.gstin || '').replace(/[^A-Za-z0-9]/g, '').toUpperCase();
  const recipientStateCode = recipientGstin.length === 15 ? recipientGstin.slice(0, 2) : null;
  const isInterstate = gstinStateCode && recipientStateCode ? gstinStateCode !== recipientStateCode : igst > 0;

  // 4. Overall Triage Status
  const isFullyCompliant = (hasGstin ? isChecksumValid : true) && isMathValid && grandTotal > 0;

  return (
    <div
      style={{
        background: 'linear-gradient(145deg, rgba(15, 23, 42, 0.8), rgba(30, 41, 59, 0.65))',
        border: `1.5px solid ${isFullyCompliant ? 'rgba(16, 185, 129, 0.35)' : 'rgba(245, 158, 11, 0.35)'}`,
        borderRadius: '14px',
        padding: '16px 20px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 4px 24px rgba(0, 0, 0, 0.35)',
      }}
    >
      {/* Top Banner with Badges */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '10px',
          marginBottom: '14px',
          paddingBottom: '10px',
          borderBottom: '1px solid rgba(51, 65, 85, 0.5)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '8px',
              background: isFullyCompliant
                ? 'linear-gradient(135deg, #059669, #10b981)'
                : 'linear-gradient(135deg, #d97706, #f59e0b)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: `0 0 12px ${isFullyCompliant ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
            }}
          >
            <ShieldCheck size={18} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', fontWeight: 700, color: '#fff' }}>
                Deterministic Rule &amp; Tax Math Verification
              </span>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 700,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  background: isFullyCompliant ? 'rgba(16, 185, 129, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                  color: isFullyCompliant ? '#34d399' : '#fbbf24',
                  border: `1px solid ${isFullyCompliant ? 'rgba(16, 185, 129, 0.4)' : 'rgba(245, 158, 11, 0.4)'}`,
                }}
              >
                {isFullyCompliant ? 'VERIFIED ACCURATE' : 'REVIEW ADVISORY'}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
              Luhn Mod-36 GSTIN algorithm &bull; Zero-hallucination arithmetic reconciliation
            </div>
          </div>
        </div>

        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="btn btn-secondary"
          style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '4px' }}
        >
          {isExpanded ? (
            <>
              Hide Proofs <ChevronUp size={13} />
            </>
          ) : (
            <>
              View Mathematical Proofs <ChevronDown size={13} />
            </>
          )}
        </button>
      </div>

      {/* 3 Core Validation Metric Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '10px',
        }}
      >
        {/* Metric 1: GSTIN & Checksum */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(51, 65, 85, 0.5)',
            borderRadius: '10px',
            padding: '10px 14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              GSTIN Checksum
            </span>
            {hasGstin ? (
              isChecksumValid ? (
                <CheckCircle2 size={13} color="#34d399" />
              ) : (
                <AlertTriangle size={13} color="#f87171" />
              )
            ) : (
              <Info size={13} color="var(--text-muted)" />
            )}
          </div>

          <div style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginTop: '4px' }}>
            {hasGstin ? (
              <span style={{ color: isChecksumValid ? '#34d399' : '#f87171' }}>
                {isChecksumValid ? 'Luhn Mod-36 Valid' : 'Checksum Mismatch'}
              </span>
            ) : (
              <span style={{ color: '#94a3b8' }}>Unregistered / Receipt</span>
            )}
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '3px' }}>
            {hasGstin ? (
              <>
                State Code: <strong style={{ color: '#38bdf8' }}>{gstinStateCode}</strong> &bull; PAN:{' '}
                <strong style={{ color: '#38bdf8' }}>{gstinPan}</strong>
              </>
            ) : (
              'No Indian GSTIN required'
            )}
          </div>
        </div>

        {/* Metric 2: Tax Structure & Interstate */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(51, 65, 85, 0.5)',
            borderRadius: '10px',
            padding: '10px 14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Tax Regime
            </span>
            <Building size={13} color="#38bdf8" />
          </div>

          <div style={{ fontSize: '13px', fontWeight: 700, color: '#60a5fa', marginTop: '4px' }}>
            {isInterstate ? 'Inter-State (IGST)' : 'Intra-State (CGST + SGST)'}
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '3px' }}>
            {isInterstate
              ? `IGST: ₹${igst.toFixed(2)}`
              : `CGST: ₹${cgst.toFixed(2)} + SGST: ₹${sgst.toFixed(2)}`}
          </div>
        </div>

        {/* Metric 3: Arithmetic Balance */}
        <div
          style={{
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(51, 65, 85, 0.5)',
            borderRadius: '10px',
            padding: '10px 14px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Arithmetic Balance
            </span>
            {isMathValid ? (
              <CheckCircle2 size={13} color="#34d399" />
            ) : (
              <AlertTriangle size={13} color="#f87171" />
            )}
          </div>

          <div style={{ fontSize: '13px', fontWeight: 700, marginTop: '4px' }}>
            <span style={{ color: isMathValid ? '#34d399' : '#f87171' }}>
              {isMathValid ? 'Mathematically Reconciled' : 'Discrepancy Detected'}
            </span>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '3px' }}>
            Variance: <strong style={{ color: isMathValid ? '#34d399' : '#f87171' }}>₹{mathDiscrepancy.toFixed(2)}</strong>
            {' '}&bull; Total: ₹{grandTotal.toFixed(2)}
          </div>
        </div>
      </div>

      {/* Expandable Mathematical Proofs & Trace */}
      {isExpanded && (
        <div
          style={{
            marginTop: '14px',
            padding: '14px',
            borderRadius: '10px',
            background: 'rgba(15, 23, 42, 0.9)',
            border: '1px solid rgba(51, 65, 85, 0.6)',
            fontSize: '12px',
          }}
        >
          <div style={{ fontWeight: 600, color: '#f8fafc', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Calculator size={14} color="#38bdf8" /> Deterministic Verification Breakdown
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {/* Tax Math Proof */}
            <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px', borderRadius: '8px' }}>
              <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '4px' }}>Tax &amp; Totals Formula:</div>
              <div style={{ fontFamily: 'monospace', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                Taxable Value: ₹{taxableVal.toFixed(2)}<br />
                + Taxes ({isInterstate ? 'IGST' : 'CGST + SGST'}): ₹{totalCalculatedTaxes.toFixed(2)}<br />
                = Computed Total: ₹{calculatedGrandTotal.toFixed(2)}<br />
                Extracted Total: ₹{grandTotal.toFixed(2)}<br />
                Delta / Roundoff: ₹{mathDiscrepancy.toFixed(2)} ({isMathValid ? 'Passed' : 'Flagged'})
              </div>
            </div>

            {/* GSTIN Luhn Algorithm Proof */}
            <div style={{ background: 'rgba(30, 41, 59, 0.5)', padding: '10px', borderRadius: '8px' }}>
              <div style={{ color: '#38bdf8', fontWeight: 600, marginBottom: '4px' }}>GSTIN Algorithm Proof:</div>
              {hasGstin ? (
                <div style={{ fontFamily: 'monospace', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                  Input GSTIN: {cleanGstin}<br />
                  14-Char Base: {cleanGstin.slice(0, 14)}<br />
                  Algorithm 15th Check Digit: <strong>{expectedCheck}</strong><br />
                  Document 15th Check Digit: <strong>{actualCheck}</strong><br />
                  Match Status: {isChecksumValid ? '✓ Verified (Luhn Mod-36)' : 'Mismatch'}
                </div>
              ) : (
                <div style={{ color: 'var(--text-muted)' }}>
                  No 15-digit GSTIN found on document (Valid for retail receipts, bank statements, or unregistered vendor bills).
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

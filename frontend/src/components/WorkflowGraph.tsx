import React, { useState } from 'react';
import { WorkflowStep, WorkflowExecution } from '../types';
import {
  FileCode,
  Sparkles,
  ShieldCheck,
  Building2,
  Send,
  CheckCircle2,
  Clock,
  AlertCircle,
  Loader2,
  ChevronRight,
  Info,
  Layers,
  Cpu,
  Calculator,
  Database,
  RotateCcw,
  Zap,
} from 'lucide-react';

interface WorkflowGraphProps {
  execution?: WorkflowExecution;
  currentStepId?: string;
  isLive?: boolean;
  compact?: boolean;
  onSelectStep?: (step: WorkflowStep) => void;
}

const DEFAULT_STEPS: Array<{
  step_id: string;
  name: string;
  stage: number;
  description: string;
  icon: any;
  execution_pattern: string;
}> = [
  {
    step_id: 'document_ingestion',
    name: 'Ingestion & Normalization',
    stage: 1,
    description: 'Deterministic PyMuPDF parsing, SHA-256 fingerprinting & format validation',
    icon: FileCode,
    execution_pattern: 'Deterministic Single-Pass',
  },
  {
    step_id: 'gemini_multimodal_extraction',
    name: 'Gemini Multimodal Transcription',
    stage: 2,
    description: 'Markdown transcription & dynamic validation checklist generation',
    icon: Sparkles,
    execution_pattern: 'Single-Turn Structured',
  },
  {
    step_id: 'math_validation_agent',
    name: 'Math Validation Agent',
    stage: 3,
    description: 'Single-turn AST calculate_batch verifying line items & totals (max 50 calls)',
    icon: Calculator,
    execution_pattern: 'Single-Turn AST Batch',
  },
  {
    step_id: 'tally_validation_agent',
    name: 'Tally & ERP Agent',
    stage: 3,
    description: 'Bounded ReAct 3-turn lookup (exact GSTIN -> PAN fallback -> duplicate check)',
    icon: Database,
    execution_pattern: 'Bounded ReAct (Max 3 Turns)',
  },
  {
    step_id: 'reconciliation_revision_agent',
    name: 'Maker-Checker Escalation',
    stage: 3,
    description: 'BFSI Strict Dual Control: Autonomous mutation disabled, discrepancies held for HITL',
    icon: ShieldCheck,
    execution_pattern: 'Strict Maker-Checker',
  },
  {
    step_id: 'validation_synthesis_triage',
    name: 'Compliance Triage & Staging',
    stage: 4,
    description: 'Aggregating agent findings, confidence scoring & voucher staging',
    icon: Layers,
    execution_pattern: 'Immutable Audit Staging',
  },
];

export const WorkflowGraph: React.FC<WorkflowGraphProps> = ({
  execution,
  currentStepId,
  isLive = false,
  compact = false,
  onSelectStep,
}) => {
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);

  // Merge execution steps with default spec
  const steps = DEFAULT_STEPS.map((def) => {
    const existing = execution?.steps?.find((s) => s.step_id === def.step_id);
    let status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped' = 'pending';

    if (existing) {
      status = existing.status;
    } else if (currentStepId) {
      if (currentStepId === def.step_id) {
        status = 'running';
      } else {
        const currentDef = DEFAULT_STEPS.find((d) => d.step_id === currentStepId);
        if (currentDef && def.stage < currentDef.stage) {
          status = 'completed';
        }
      }
    }

    return {
      ...def,
      status,
      duration_ms: existing?.duration_ms,
      details: existing?.details,
      error: existing?.error,
      started_at: existing?.started_at,
      completed_at: existing?.completed_at,
    };
  });

  const activeStep = steps.find((s) => s.step_id === (selectedStepId || currentStepId)) || steps[0];

  return (
    <div
      style={{
        background: 'linear-gradient(145deg, rgba(15, 23, 42, 0.75), rgba(30, 41, 59, 0.6))',
        border: '1px solid rgba(56, 189, 248, 0.2)',
        borderRadius: '16px',
        padding: compact ? '14px 18px' : '22px 24px',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
      }}
    >
      {/* Header with Title and ADK Badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: compact ? '14px' : '20px',
          flexWrap: 'wrap',
          gap: '8px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '28px',
              height: '28px',
              borderRadius: '8px',
              background: 'linear-gradient(135deg, #0284c7, #38bdf8)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 12px rgba(56, 189, 248, 0.5)',
            }}
          >
            <Cpu size={16} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: compact ? '13px' : '15px', fontWeight: 700, color: '#f8fafc' }}>
                Google ADK 2.0 Multi-Stage Graph Workflow
              </span>
              {isLive && (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: '4px',
                    fontSize: '11px',
                    padding: '2px 8px',
                    borderRadius: '9999px',
                    background: 'rgba(56, 189, 248, 0.15)',
                    color: '#38bdf8',
                    border: '1px solid rgba(56, 189, 248, 0.3)',
                    fontWeight: 600,
                  }}
                >
                  <span
                    style={{
                      width: '6px',
                      height: '6px',
                      borderRadius: '50%',
                      background: '#38bdf8',
                      boxShadow: '0 0 8px #38bdf8',
                      animation: 'pulse 1.5s infinite',
                    }}
                  />
                  Live Execution
                </span>
              )}
            </div>
            {!compact && (
              <p style={{ margin: '2px 0 0 0', fontSize: '12px', color: 'var(--text-muted)' }}>
                Deterministic Directed Acyclic Graph (DAG) execution across vision, rules &amp; Tally Prime integration
              </p>
            )}
          </div>
        </div>

        {execution?.total_duration_ms && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              color: '#34d399',
              background: 'rgba(16, 185, 129, 0.1)',
              border: '1px solid rgba(16, 185, 129, 0.3)',
              padding: '4px 10px',
              borderRadius: '8px',
              fontWeight: 600,
            }}
          >
            <Clock size={13} />
            Total: {execution.total_duration_ms}ms
          </div>
        )}
      </div>

      {/* Interactive Horizontal DAG Nodes */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
          gap: '12px',
          position: 'relative',
        }}
      >
        {steps.map((step, idx) => {
          const Icon = step.icon;
          const isRunning = step.status === 'running';
          const isCompleted = step.status === 'completed';
          const isFailed = step.status === 'failed';
          const isSelected = selectedStepId === step.step_id;

          let borderColor = 'rgba(51, 65, 85, 0.5)';
          let bgColor = 'rgba(15, 23, 42, 0.5)';
          let iconColor = 'var(--text-muted)';
          let statusText = 'Pending';

          if (isRunning) {
            borderColor = '#38bdf8';
            bgColor = 'linear-gradient(135deg, rgba(2, 132, 199, 0.25), rgba(56, 189, 248, 0.1))';
            iconColor = '#38bdf8';
            statusText = 'Processing...';
          } else if (isCompleted) {
            borderColor = 'rgba(16, 185, 129, 0.5)';
            bgColor = 'rgba(6, 78, 59, 0.2)';
            iconColor = '#34d399';
            statusText = 'Done';
          } else if (isFailed) {
            borderColor = '#ef4444';
            bgColor = 'rgba(127, 29, 29, 0.2)';
            iconColor = '#ef4444';
            statusText = 'Failed';
          }

          return (
            <div
              key={step.step_id}
              onClick={() => {
                setSelectedStepId(step.step_id);
                if (onSelectStep) onSelectStep(step as any);
              }}
              style={{
                position: 'relative',
                background: bgColor,
                border: `1.5px solid ${isSelected ? '#38bdf8' : borderColor}`,
                borderRadius: '12px',
                padding: compact ? '10px 12px' : '14px',
                cursor: 'pointer',
                transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
                transform: isRunning ? 'scale(1.02)' : 'scale(1)',
                boxShadow: isRunning
                  ? '0 0 20px rgba(56, 189, 248, 0.35), inset 0 0 12px rgba(56, 189, 248, 0.15)'
                  : isSelected
                  ? '0 0 16px rgba(56, 189, 248, 0.25)'
                  : 'none',
              }}
            >
              {/* Stage Number & Status Badge */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    color: isRunning ? '#38bdf8' : 'var(--text-muted)',
                  }}
                >
                  Stage 0{step.stage}
                </span>

                {isRunning ? (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '10px',
                      fontWeight: 700,
                      color: '#38bdf8',
                      background: 'rgba(56, 189, 248, 0.2)',
                      padding: '2px 6px',
                      borderRadius: '9999px',
                    }}
                  >
                    <Loader2 size={10} style={{ animation: 'spin 1s linear infinite' }} />
                    Active
                  </span>
                ) : isCompleted ? (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '10px',
                      fontWeight: 700,
                      color: '#34d399',
                      background: 'rgba(16, 185, 129, 0.2)',
                      padding: '2px 6px',
                      borderRadius: '9999px',
                    }}
                  >
                    <CheckCircle2 size={10} />
                    Done
                  </span>
                ) : isFailed ? (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '10px',
                      fontWeight: 700,
                      color: '#ef4444',
                      background: 'rgba(239, 68, 68, 0.2)',
                      padding: '2px 6px',
                      borderRadius: '9999px',
                    }}
                  >
                    <AlertCircle size={10} />
                    Error
                  </span>
                ) : (
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Waiting</span>
                )}
              </div>

              {/* Node Icon & Label */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                <div
                  style={{
                    width: '28px',
                    height: '28px',
                    borderRadius: '8px',
                    background: isRunning ? 'rgba(56, 189, 248, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: iconColor,
                    flexShrink: 0,
                  }}
                >
                  <Icon size={16} />
                </div>
                <div style={{ overflow: 'hidden' }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      color: isRunning ? '#fff' : isCompleted ? '#e2e8f0' : 'var(--text-secondary)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {step.name}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '2px' }}>
                    <span
                      style={{
                        fontSize: '9px',
                        padding: '1px 5px',
                        borderRadius: '4px',
                        background: 'rgba(56, 189, 248, 0.12)',
                        color: '#7dd3fc',
                        border: '1px solid rgba(56, 189, 248, 0.25)',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {step.execution_pattern}
                    </span>
                  </div>
                </div>
              </div>

              {/* Timing or Description */}
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
                {step.duration_ms ? (
                  <span style={{ color: '#34d399', fontWeight: 600 }}>{step.duration_ms} ms</span>
                ) : (
                  <span style={{ fontSize: '10px' }}>{step.description.slice(0, 32)}...</span>
                )}
              </div>

              {/* Flow Arrow to next node (if not last) */}
              {idx < steps.length - 1 && (
                <div
                  style={{
                    display: 'none', // Shown on large desktop if needed
                    position: 'absolute',
                    right: '-10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    zIndex: 10,
                  }}
                >
                  <ChevronRight size={16} color={isCompleted ? '#34d399' : '#475569'} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Detailed Step Inspector Drawer (when not in compact mode) */}
      {!compact && activeStep && (
        <div
          style={{
            marginTop: '18px',
            padding: '14px 18px',
            borderRadius: '10px',
            background: 'rgba(15, 23, 42, 0.6)',
            border: '1px solid rgba(51, 65, 85, 0.4)',
            display: 'flex',
            alignItems: 'flex-start',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', fontWeight: 700, color: '#38bdf8' }}>
                Stage {activeStep.stage}: {activeStep.name}
              </span>
              <span
                className={`pill ${
                  activeStep.status === 'completed'
                    ? 'pill-green'
                    : activeStep.status === 'running'
                    ? 'pill-blue'
                    : 'pill-gray'
                }`}
                style={{ fontSize: '10px', padding: '1px 6px' }}
              >
                {activeStep.status}
              </span>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: 'var(--text-secondary)' }}>
              {activeStep.description}
            </p>
          </div>

          {activeStep.details && Object.keys(activeStep.details).length > 0 && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                flexWrap: 'wrap',
              }}
            >
              {Object.entries(activeStep.details).map(([k, v]) => (
                <div
                  key={k}
                  style={{
                    background: 'rgba(30, 41, 59, 0.8)',
                    padding: '3px 8px',
                    borderRadius: '6px',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    border: '1px solid rgba(51, 65, 85, 0.5)',
                  }}
                >
                  <strong style={{ color: '#cbd5e1' }}>{k}:</strong>{' '}
                  <span style={{ color: '#38bdf8' }}>{String(v)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

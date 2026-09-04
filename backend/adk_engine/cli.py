"""Standalone CLI Runner for Google ADK 2.0 Multi-Stage Invoice Workflow.

Enables end-to-end execution, debugging, and OpenTelemetry trace validation
locally from the terminal outside the web app.

Usage:
    uv run python -m backend.adk_engine.cli <file_path> [--otel] [--save-trace <path>]
"""

from __future__ import annotations
import argparse
import json
import os
import sys
import time
import uuid
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.adk_engine.workflow import UniversalDocumentPipeline
from backend.adk_engine.otel_tracer import (
    init_tracer,
    get_collected_spans,
    save_traces_to_json,
    clear_collected_spans,
)

# ANSI Color Codes
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}{CYAN}   🚀 Google ADK 2.0 Multi-Stage Graph Pipeline & Observability Runner{RESET}")
    print(f"{BOLD}{CYAN}{'='*80}{RESET}\n")


def format_step_callback(step_id: str, status: str, details: dict):
    stage_colors = {
        "running": YELLOW,
        "completed": GREEN,
        "failed": RED,
    }
    color = stage_colors.get(status, RESET)
    status_label = f"[{status.upper()}]"
    print(f"  {color}➜{RESET} Step {BOLD}{step_id:<32}{RESET} {color}{status_label:<12}{RESET}")


def run_cli():
    parser = argparse.ArgumentParser(
        description="Google ADK 2.0 Invoice Workflow CLI Runner & Validator"
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default=None,
        help="Path to invoice image or PDF file (e.g. uploads/sample.webp)",
    )
    parser.add_argument(
        "--otel",
        action="store_true",
        help="Enable OpenTelemetry span printing and JSON trace export",
    )
    parser.add_argument(
        "--save-trace",
        default=None,
        help="Optional destination path for exported trace JSON file",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce BFSI strict Maker-Checker mode (disables autonomous OCR mutation)",
    )
    args = parser.parse_args()

    print_banner()

    # Determine file to validate
    file_path = args.file_path
    if not file_path:
        # Check uploads directory for existing sample documents
        uploads_dir = Path("uploads")
        if uploads_dir.exists():
            candidates = sorted(
                list(uploads_dir.glob("*.webp")) + list(uploads_dir.glob("*.png")) + list(uploads_dir.glob("*.pdf")),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if candidates:
                file_path = str(candidates[0])
                print(f"{DIM}No file provided. Auto-selecting latest upload: {file_path}{RESET}\n")
            else:
                print(f"{RED}Error: No document files found in uploads/. Please specify a file_path.{RESET}")
                sys.exit(1)
        else:
            print(f"{RED}Error: Please specify a file_path to validate.{RESET}")
            sys.exit(1)

    if not os.path.exists(file_path):
        print(f"{RED}Error: File not found: {file_path}{RESET}")
        sys.exit(1)

    if args.strict:
        os.environ["BFSI_STRICT_MAKER_CHECKER"] = "true"

    clear_collected_spans()
    if args.otel:
        init_tracer(enable_console_export=False)

    doc_id = str(uuid.uuid4())
    print(f"{BOLD}Target Document:{RESET} {file_path}")
    print(f"{BOLD}Document ID:{RESET}     {doc_id}")
    print(f"{BOLD}File Size:{RESET}       {os.path.getsize(file_path):,} bytes")
    print(f"{BOLD}OpenTelemetry:{RESET}   {'ENABLED (GenAI Semantic Conventions)' if args.otel else 'Disabled'}")
    print(f"{BOLD}BFSI Strict Mode:{RESET}{os.getenv('BFSI_STRICT_MAKER_CHECKER', 'true')}\n")

    print(f"{BOLD}{CYAN}--- Executing Pipeline Stages ---{RESET}")
    pipeline = UniversalDocumentPipeline()
    start_wall = time.time()

    try:
        parsed_doc, tally_xml, wf = pipeline.process_document(
            file_path=file_path,
            doc_id=doc_id,
            filename=Path(file_path).name,
            step_callback=format_step_callback,
        )
    except Exception as exc:
        print(f"\n{RED}{BOLD}Pipeline Execution Failed:{RESET} {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    duration = time.time() - start_wall

    print(f"\n{BOLD}{GREEN}✓ Pipeline Completed in {duration:.2f}s (Workflow duration: {wf.total_duration_ms}ms){RESET}\n")

    # Display Stage Summaries
    print(f"{BOLD}{CYAN}{'='*80}{RESET}")
    print(f"{BOLD}1. INGESTION & EXTRACTION RESULTS{RESET}")
    print(f"   • Title:            {parsed_doc.title}")
    print(f"   • Document Type:    {parsed_doc.doc_type}")
    print(f"   • Confidence Score: {parsed_doc.confidence_score * 100:.0f}%")
    print(f"   • Markdown Chars:   {len(parsed_doc.raw_markdown):,}")
    print(f"   • Validation Tasks: {len(parsed_doc.validation_plan)} dynamic tasks generated")

    val_res = parsed_doc.validation or {}
    math_chk = val_res.get("math_check") or {}
    tally_chk = val_res.get("tally_check") or {}
    gstin_chk = val_res.get("supplier_gstin_check") or {}
    audit_snapshot = val_res.get("regulatory_audit_snapshot") or {}

    print(f"\n{BOLD}2. ADK MATH VALIDATION AGENT (AST Arithmetic Proof){RESET}")
    is_math_valid = math_chk.get("is_valid", False)
    status_icon = f"{GREEN}PASSED{RESET}" if is_math_valid else f"{RED}DISCREPANCY DETECTED{RESET}"
    print(f"   • Arithmetic Status:      {status_icon}")
    print(f"   • Calculated Grand Total: ₹{math_chk.get('calculated_grand_total', 0.0):,.2f}")
    print(f"   • Discrepancy Amount:     ₹{math_chk.get('discrepancy_amount', 0.0):,.2f}")
    print(f"   • Line Items Valid:       {math_chk.get('line_item_math_valid')}")
    print(f"   • Tax Calculations Valid: {math_chk.get('tax_math_valid')}")

    math_audit = audit_snapshot.get("ast_math_proof", {}).get("audit", [])
    if math_audit:
        print(f"   • Evaluated AST Equations ({len(math_audit)} total):")
        for eq in math_audit[:5]:
            match_mark = f"{GREEN}✓{RESET}" if eq.get("is_match") else f"{RED}✗{RESET}"
            print(f"     {match_mark} {eq.get('query')} = {eq.get('result')} (stated: {eq.get('stated_value')})")
        if len(math_audit) > 5:
            print(f"     ... and {len(math_audit) - 5} more equations in batch")

    print(f"\n{BOLD}3. ADK TALLY & GST VALIDATION AGENT (ERP ReAct Trajectory){RESET}")
    print(f"   • Supplier GSTIN:     {gstin_chk.get('gstin') or 'N/A'}")
    print(f"   • Luhn Checksum:      {GREEN if gstin_chk.get('is_checksum_valid') else RED}{gstin_chk.get('is_checksum_valid')}{RESET} ({gstin_chk.get('state_name') or 'N/A'})")
    print(f"   • Matched Ledger:     {tally_chk.get('party_ledger_name') or 'Auto-Create on Sync'}")
    print(f"   • Duplicate Voucher:  {RED + 'YES (DUPLICATE)' if tally_chk.get('duplicate_invoice_found') else GREEN + 'NO (CLEAN)'}{RESET}")

    react_turns = audit_snapshot.get("erp_react_trajectory", [])
    if react_turns:
        print(f"   • ReAct Trajectory ({len(react_turns)} turns):")
        for turn in react_turns:
            print(f"     Turn {turn.get('turn')}: {turn.get('step_name')} ➜ {turn.get('action_result')}")

    print(f"\n{BOLD}4. BFSI COMPLIANCE TRIAGE & STAGING GATE{RESET}")
    triage = val_res.get("triage_status", "unknown").upper()
    triage_color = GREEN if triage == "AUTO_READY" else (YELLOW if triage == "QUICK_REVIEW" else RED)
    print(f"   • Triage Status:       {triage_color}{triage}{RESET}")
    print(f"   • Overall Confidence:  {val_res.get('confidence_score', 0.0) * 100:.0f}%")
    print(f"   • Tally XML Voucher:   {GREEN + 'STAGED READY FOR SYNC' if tally_xml else RED + 'NOT STAGED'}{RESET}")
    print(f"   • SHA-256 Digest:      {DIM}{audit_snapshot.get('document_sha256')}{RESET}")
    print(f"   • Maker-Checker State: {audit_snapshot.get('maker_checker_status')}")

    # OpenTelemetry Spans Summary
    spans = get_collected_spans()
    if args.otel:
        print(f"\n{BOLD}5. OPENTELEMETRY TRACE & SPAN AUDIT{RESET}")
        print(f"   • Total Spans Captured: {len(spans)}")
        trace_id = spans[0]["context"]["trace_id"] if spans else "N/A"
        print(f"   • Trace ID:             {CYAN}{trace_id}{RESET}")
        print(f"\n   {'Span Name':<42} {'Duration':<12} {'Operation / Role'}")
        print(f"   {'-'*75}")
        for s in spans:
            op_name = s["attributes"].get("gen_ai.operation.name", s["attributes"].get("gen_ai.agent.mode", ""))
            print(f"   {s['name']:<42} {s['duration_ms']:>8.2f} ms   {op_name}")

        trace_out = args.save_trace or f"traces/trace_{doc_id}.json"
        saved_file = save_traces_to_json(trace_out)
        print(f"\n   {GREEN}✓ Full OpenTelemetry trace saved to:{RESET} {saved_file}")

    print(f"\n{BOLD}{CYAN}{'='*80}{RESET}\n")


if __name__ == "__main__":
    run_cli()

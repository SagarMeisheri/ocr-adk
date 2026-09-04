"""Unit and integration tests for ADK 2.0 Parallel Workflow and Deterministic Validation Tools."""

import unittest
from backend.adk_engine.models import (
    ExtractedInvoice,
    InvoiceParty,
    InvoiceLineItem,
    InvoiceSummary,
    ValidationTask,
)
from backend.adk_engine.validation_tools import (
    calculate,
    generate_math_queries_for_invoice,
    verify_line_item_math,
    verify_tax_calculations,
    verify_grand_total_equation,
    execute_deterministic_math_suite,
    query_tally_party_by_gstin,
    query_tally_duplicate_voucher,
    execute_tally_compliance_suite,
)
from backend.adk_engine.extractor import generate_document_validation_plan
from backend.adk_engine.workflow import (
    UniversalDocumentPipeline,
    ADK_WORKFLOW_STEPS_SPEC,
    math_validation_agent,
    tally_validation_agent,
)
from backend.tally_bridge.virtual_tally import GLOBAL_TALLY_STATE


class TestAdk2ValidationTools(unittest.TestCase):
    """Test deterministic arithmetic, AST calculator tool, and Tally database validation tools."""

    def test_safe_ast_calculator_arithmetic(self):
        """Tests that the AST calculator tool computes valid expressions with precision."""
        self.assertEqual(calculate("5 * 200 - 50"), "950.0")
        self.assertEqual(calculate("round(1497.0 * 0.18, 2)"), "269.46")
        self.assertEqual(calculate("sum([100, 200, 300])"), "600.0")
        self.assertEqual(calculate("round(1000 + 180 + 0, 2)"), "1180.0")
        self.assertEqual(calculate("abs(-50.5)"), "50.5")

    def test_safe_ast_calculator_security_rejection(self):
        """Tests that the AST calculator tool strictly blocks arbitrary code execution."""
        # Function call injection
        res1 = calculate("__import__('os').system('ls')")
        self.assertIn("Calculation Error: Security", res1)

        # File access injection
        res2 = calculate("open('/etc/passwd').read()")
        self.assertIn("Calculation Error: Security", res2)

        # Attribute lookup injection
        res3 = calculate("(1).__class__.__bases__")
        self.assertIn("Calculation Error: Security", res3)

        # Eval injection
        res4 = calculate("eval('1 + 1')")
        self.assertIn("Calculation Error: Security", res4)

    def test_dynamic_math_queries_and_audit(self):
        """Tests that queries are generated dynamically and evaluated via the calculate tool."""
        items = [
            {"description": "AI Module", "quantity": 3.0, "rate": 500.0, "discount": 0.0, "taxable_value": 1500.0, "gst_rate": 18.0, "cgst_amount": 135.0, "sgst_amount": 135.0}
        ]
        summary = {"total_taxable_value": 1500.0, "total_cgst": 135.0, "total_sgst": 135.0, "grand_total": 1770.0}
        
        detail, audit = execute_deterministic_math_suite(items, summary)
        self.assertTrue(detail.is_valid)
        self.assertTrue(detail.line_item_math_valid)
        self.assertGreaterEqual(len(audit), 3)
        self.assertTrue(all(a["is_match"] for a in audit))
        # Ensure query strings exist in audit
        queries_run = [a["query"] for a in audit]
        self.assertTrue(any("3.0 * 500.0" in q for q in queries_run))

    def test_line_item_math_multiplication_valid(self):
        """Checks amount = quantity x rate (- discount) succeeds when arithmetic matches."""
        items = [
            {"description": "Module A", "quantity": 5.0, "rate": 200.0, "discount": 50.0, "taxable_value": 950.0},
            {"description": "Module B", "quantity": 2.0, "rate": 1500.0, "discount": 0.0, "taxable_value": 3000.0},
        ]
        result = verify_line_item_math(items)
        self.assertTrue(result["is_valid"])
        self.assertEqual(len(result["discrepancies"]), 0)
        self.assertEqual(result["total_calculated_taxable"], 3950.0)

    def test_line_item_math_multiplication_mismatch(self):
        """Checks amount = quantity x rate flags line item discrepancy."""
        items = [
            # 5 * 200 - 0 should be 1000.0, but extracted taxable_value is 1200.0
            {"description": "Defective Row", "quantity": 5.0, "rate": 200.0, "discount": 0.0, "taxable_value": 1200.0}
        ]
        result = verify_line_item_math(items)
        self.assertFalse(result["is_valid"])
        self.assertIn("Math mismatch", result["discrepancies"][0])
        self.assertIn("round(5.0 * 200.0", result["discrepancies"][0])
        self.assertIn("Diff: ₹200.00", result["discrepancies"][0])

    def test_tax_calculations_intra_and_inter_state(self):
        """Tests CGST/SGST vs IGST calculation logic."""
        items = [
            {
                "description": "Cloud Service",
                "taxable_value": 1000.0,
                "gst_rate": 18.0,
                "cgst_amount": 90.0,
                "sgst_amount": 90.0,
                "igst_amount": 0.0,
            }
        ]
        # Intra-state: should have CGST + SGST
        intra_res = verify_tax_calculations(items, is_inter_state=False)
        self.assertTrue(intra_res["is_valid"])
        self.assertEqual(intra_res["total_calculated_taxes"], 180.0)

        # Inter-state with incorrect CGST/SGST should flag error
        inter_res = verify_tax_calculations(items, is_inter_state=True)
        self.assertFalse(inter_res["is_valid"])
        self.assertTrue(any("Inter-state sale should not charge CGST/SGST" in d for d in inter_res["discrepancies"]))

    def test_grand_total_equation(self):
        """Checks grand total balance equation."""
        res_valid = verify_grand_total_equation(
            taxable_sum=1000.0,
            taxes_sum=180.0,
            cess_sum=0.0,
            round_off=0.0,
            stated_grand_total=1180.0,
        )
        self.assertTrue(res_valid["is_valid"])

        res_invalid = verify_grand_total_equation(
            taxable_sum=1000.0,
            taxes_sum=180.0,
            cess_sum=0.0,
            round_off=0.0,
            stated_grand_total=1250.0,
        )
        self.assertFalse(res_invalid["is_valid"])
        self.assertEqual(res_invalid["discrepancy_amount"], 70.0)

    def test_tally_party_lookup_virtual_simulator(self):
        """Tests Tally ledger lookup against virtual simulator state."""
        # Syscom Cloud Infrastructure Ltd has GSTIN '27AAACS8912K1Z9' in virtual Tally
        res = query_tally_party_by_gstin(gstin="27AAACS8912K1Z9")
        self.assertTrue(res["found"])
        self.assertEqual(res["matched_ledger"], "Syscom Cloud Infrastructure Ltd")

        # Unknown party
        unknown = query_tally_party_by_gstin(gstin="27XYZAB9999Z1Z1")
        self.assertFalse(unknown["found"])

    def test_tally_duplicate_voucher_check(self):
        """Tests duplicate voucher detection."""
        # Add a voucher into GLOBAL_TALLY_STATE
        GLOBAL_TALLY_STATE.add_voucher(ref="DUP-INV-999", party="Test Supplier", amount=5000.0, xml_body="<VOUCHER/>")

        dup_check = query_tally_duplicate_voucher(invoice_number="DUP-INV-999")
        self.assertTrue(dup_check["is_duplicate"])
        self.assertIsNotNone(dup_check["existing_voucher"])

        new_check = query_tally_duplicate_voucher(invoice_number="BRAND-NEW-INV-001")
        self.assertFalse(new_check["is_duplicate"])


class TestAdk2WorkflowExecution(unittest.TestCase):
    """Test dynamic validation plan generation and ADK 2.0 pipeline execution."""

    def test_dynamic_validation_plan_generation(self):
        """Verifies that markdown with tables and taxes emits a dynamic validation checklist."""
        sample_markdown = """
| Item | Qty | Rate | Taxable | GST % | Total |
| Cloud Node | 2 | 500 | 1000 | 18% | 1180 |

Supplier GSTIN: 27AAACS8912K1Z9
Buyer GSTIN: 27AAACA1234A1Z5
Grand Total: ₹1,180.00
"""
        plan = generate_document_validation_plan(sample_markdown, "Invoice from Syscom")
        rule_ids = [t.rule_id for t in plan]

        self.assertIn("math_line_item_multiplication", rule_ids)
        self.assertIn("math_taxable_subtotal", rule_ids)
        self.assertIn("compliance_gstin_checksum", rule_ids)
        self.assertIn("math_tax_rates", rule_ids)
        self.assertIn("tally_party_lookup", rule_ids)
        self.assertIn("math_grand_total", rule_ids)
        self.assertIn("tally_duplicate_check", rule_ids)

    def test_workflow_steps_spec(self):
        """Verifies ADK 2.0 workflow stages are configured."""
        step_ids = [s["step_id"] for s in ADK_WORKFLOW_STEPS_SPEC]
        self.assertIn("document_ingestion", step_ids)
        self.assertIn("gemini_multimodal_extraction", step_ids)
        self.assertIn("math_validation_agent", step_ids)
        self.assertIn("tally_validation_agent", step_ids)
        self.assertIn("validation_synthesis_triage", step_ids)

    def test_math_queries_call_limit_enforced(self):
        """Verifies that query call limits are strictly enforced on the math agent."""
        items = [
            {"description": f"Item {i}", "quantity": 10.0, "rate": 100.0, "amount": 1000.0}
            for i in range(10)
        ]
        summary = {"taxable_amount": 10000.0, "cgst_amount": 900.0, "sgst_amount": 900.0, "total_amount": 11800.0}

        # Run with limit of 3 queries
        detail, audit = execute_deterministic_math_suite(
            line_items=items,
            summary_data=summary,
            max_queries=3,
        )

        self.assertLessEqual(len(audit), 3)
        self.assertTrue(any("Safety Limit" in n for n in detail.notes))

    def test_adk_workflow_graph_initialized(self):
        """Verifies that ADK 2.0 Workflow graph compiles with cyclic revision edges and task mode."""
        from backend.adk_engine.workflow import adk_workflow_graph, math_validation_agent, tally_validation_agent
        self.assertIsNotNone(adk_workflow_graph)
        self.assertEqual(len(adk_workflow_graph.edges), 7)
        self.assertEqual(math_validation_agent.mode, "task")
        self.assertEqual(tally_validation_agent.mode, "task")
        self.assertEqual(math_validation_agent.timeout, 45.0)
        self.assertIsNotNone(math_validation_agent.before_tool_callback)
        self.assertIsNotNone(tally_validation_agent.before_tool_callback)

    def test_calculate_batch_single_call(self):
        """Verifies that calculate_batch executes multiple calculations in one call."""
        from backend.adk_engine.validation_tools import calculate_batch
        expressions = {
            "line_1": "10 * 150",
            "line_2": "5 * 200 - 50",
            "subtotal": "1500 + 950",
            "tax_cgst": "round(2450 * 0.09, 2)",
        }
        res = calculate_batch(expressions)
        self.assertFalse(res["has_errors"])
        self.assertEqual(res["total_computed"], 4)
        self.assertEqual(res["results"]["line_1"]["value"], 1500.0)
        self.assertEqual(res["results"]["line_2"]["value"], 950.0)
        self.assertEqual(res["results"]["subtotal"]["value"], 2450.0)
        self.assertEqual(res["results"]["tax_cgst"]["value"], 220.5)

    def test_tally_bounded_react_trajectory(self):
        """Verifies that execute_tally_compliance_suite captures 3-turn ReAct trajectory."""
        from backend.adk_engine.validation_tools import execute_tally_compliance_suite
        sup, buy, tally = execute_tally_compliance_suite(
            supplier_gstin="27AAACS1234A1Z5",
            buyer_gstin="27BBBCS5678B1Z6",
            invoice_number="INV-2026-BFSI-01",
            supplier_name="Acme Industrial Corp",
        )
        self.assertIsNotNone(tally.react_trajectory)
        self.assertEqual(len(tally.react_trajectory), 3)
        # Turn 1: exact GSTIN check
        self.assertEqual(tally.react_trajectory[0]["turn"], 1)
        self.assertEqual(tally.react_trajectory[0]["step_name"], "exact_gstin_checksum_and_ledger_lookup")
        # Turn 2: PAN and fuzzy vendor fallback
        self.assertEqual(tally.react_trajectory[1]["turn"], 2)
        self.assertEqual(tally.react_trajectory[1]["step_name"], "pan_and_fuzzy_vendor_fallback")
        # Turn 3: anti-fraud duplicate voucher check
        self.assertEqual(tally.react_trajectory[2]["turn"], 3)
        self.assertEqual(tally.react_trajectory[2]["step_name"], "anti_fraud_duplicate_voucher_check")

    def test_compute_document_sha256(self):
        """Verifies that compute_document_sha256 returns valid 64-character hex hash."""
        from backend.adk_engine.validation_tools import compute_document_sha256
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as tf:
            tf.write(b"BFSI Non-Repudiation Audit Payload")
            temp_path = tf.name

        sha = compute_document_sha256(temp_path)
        self.assertEqual(len(sha), 64)
        self.assertTrue(all(c in "0123456789abcdefABCDEF" for c in sha))

    def test_otel_tracer_spans_and_export(self):
        """Verifies OpenTelemetry tracing spans are collected with GenAI semantic conventions."""
        import tempfile
        from pathlib import Path
        from backend.adk_engine.otel_tracer import (
            trace_workflow,
            trace_stage,
            trace_agent,
            get_collected_spans,
            save_traces_to_json,
            clear_collected_spans,
        )

        clear_collected_spans()

        with trace_workflow("test_workflow", "doc-123", {"source": "unit_test"}):
            with trace_stage("Stage 1", "step_ingestion"):
                pass
            with trace_agent("math_agent", "task", {"items": 5}):
                pass

        spans = get_collected_spans()
        self.assertEqual(len(spans), 3)

        span_names = [s["name"] for s in spans]
        self.assertIn("invoke_node step_ingestion", span_names)
        self.assertIn("invoke_agent math_agent", span_names)
        self.assertIn("invoke_workflow test_workflow", span_names)

        # Verify attributes
        agent_span = next(s for s in spans if "math_agent" in s["name"])
        self.assertEqual(agent_span["attributes"]["gen_ai.operation.name"], "invoke_agent")
        self.assertEqual(agent_span["attributes"]["gen_ai.agent.name"], "math_agent")

        # Test export to JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tf:
            trace_json_path = tf.name
        saved_path = save_traces_to_json(trace_json_path)
        self.assertTrue(Path(saved_path).exists())

    def test_invoice_pipeline_agent_tool_registration(self):
        """Verifies agents/invoice_pipeline root_agent registers all required tools."""
        from agents.invoice_pipeline.agent import root_agent
        self.assertIsNotNone(root_agent)
        self.assertEqual(root_agent.name, "invoice_pipeline_agent")
        tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in root_agent.tools]
        self.assertIn("validate_invoice_document", tool_names)
        self.assertIn("calculate_batch", tool_names)
        self.assertIn("calculate", tool_names)
        self.assertIn("validate_gstin", tool_names)

    def test_document_ingestion_and_image_stripping(self):
        """Verifies ingestion resolves paths and extraction outputs pure markdown without image payload."""
        from backend.adk_engine.workflow import (
            document_ingestion_node,
            gemini_multimodal_extraction_node,
            final_staging_node,
            extract_file_path_from_node_input,
        )

        # Test string path normalization
        dummy_path = "uploads/test_invoice.png"
        Path("uploads").mkdir(parents=True, exist_ok=True)
        Path(dummy_path).write_bytes(b"dummy image bytes")

        res_path = extract_file_path_from_node_input(dummy_path)
        self.assertEqual(res_path, dummy_path)

        # Ingestion node passes string path
        ingest_res = document_ingestion_node(node_input=dummy_path)
        self.assertEqual(ingest_res, dummy_path)

        # Extraction node returns string markdown (not binary image/dict)
        extract_res = gemini_multimodal_extraction_node(node_input=dummy_path)
        self.assertIsInstance(extract_res, str)
        self.assertFalse(isinstance(extract_res, (bytes, bytearray)))

        # Final staging node appends AST Math Proof
        final_res = final_staging_node(node_input=extract_res)
        self.assertIn("Deterministic AST Math Proof", final_res)
        self.assertIn("PASS", final_res)

        # Cleanup
        if Path(dummy_path).exists():
            Path(dummy_path).unlink()

    def test_tally_validation_node_offline_skips_llm(self):
        """Verifies tally_validation_node cleanly skips when Tally is offline to save Gemini API calls."""
        from backend.adk_engine.workflow import tally_validation_node
        res = tally_validation_node(node_input="sample markdown")
        self.assertIsInstance(res, dict)
        self.assertIn("status", res)
        # In test environment where port 9000 is closed, status should be 'skipped'
        self.assertEqual(res["status"], "skipped")
        self.assertEqual(res["tally_connection_mode"], "offline")


if __name__ == "__main__":
    unittest.main()



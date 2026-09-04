"""Unit tests for Indian GSTIN Luhn mod-36 checksum and tax math verification."""

import unittest
from backend.adk_engine.validator import (
    calculate_gstin_checksum,
    validate_gstin,
    validate_tax_math,
    validate_extracted_invoice,
)
from backend.adk_engine.models import (
    ExtractedInvoice,
    InvoiceParty,
    InvoiceLineItem,
    InvoiceSummary,
)


class TestValidator(unittest.TestCase):
    def test_gstin_checksum_valid(self):
        # 27AAPFU0939F1ZV is a real valid Maharashtra GSTIN
        check_char = calculate_gstin_checksum("27AAPFU0939F1Z")
        self.assertEqual(check_char, "V")

        detail = validate_gstin("27AAPFU0939F1ZV")
        self.assertTrue(detail.is_valid_format)
        self.assertTrue(detail.is_checksum_valid)
        self.assertEqual(detail.state_code, "27")
        self.assertEqual(detail.state_name, "Maharashtra")
        self.assertEqual(detail.pan, "AAPFU0939F")

        # Also test another valid prefix
        check_char2 = calculate_gstin_checksum("27AAACS8912K1Z")
        self.assertEqual(check_char2, "2")
        detail2 = validate_gstin("27AAACS8912K1Z2")
        self.assertTrue(detail2.is_checksum_valid)

    def test_gstin_checksum_invalid(self):
        detail = validate_gstin("27AAPFU0939F1Z9")
        self.assertTrue(detail.is_valid_format)
        self.assertFalse(detail.is_checksum_valid)
        self.assertIn("Checksum mismatch", detail.error_message)

    def test_gstin_missing_for_unregistered_vendor(self):
        detail = validate_gstin(None)
        self.assertFalse(detail.is_valid_format)
        self.assertFalse(detail.is_checksum_valid)

    def test_intra_state_tax_math(self):
        invoice = ExtractedInvoice(
            invoice_number="INV-001",
            invoice_date="2026-09-01",
            supplier=InvoiceParty(
                name="Alpha Corp",
                gstin="27AAPFU0939F1ZV",
                state="Maharashtra",
                state_code="27",
            ),
            buyer=InvoiceParty(
                name="Apex Tech",
                gstin="27AAACA1234A1ZK",
                state="Maharashtra",
                state_code="27",
            ),
            line_items=[
                InvoiceLineItem(
                    description="Consulting Service",
                    hsn_sac="9983",
                    quantity=10.0,
                    unit="Hrs",
                    rate=1000.0,
                    discount=0.0,
                    taxable_value=10000.0,
                    gst_rate=18.0,
                    cgst_amount=900.0,
                    sgst_amount=900.0,
                    igst_amount=0.0,
                    total_amount=11800.0,
                )
            ],
            summary=InvoiceSummary(
                total_taxable_value=10000.0,
                total_cgst=900.0,
                total_sgst=900.0,
                total_igst=0.0,
                round_off=0.0,
                grand_total=11800.0,
            ),
        )

        result = validate_extracted_invoice(invoice)
        self.assertTrue(result.is_fully_valid)
        self.assertEqual(result.triage_status, "auto_ready")
        self.assertGreaterEqual(result.confidence_score, 0.90)
        self.assertTrue(result.math_check.is_valid)
        self.assertTrue(result.math_check.intra_inter_state_valid)

    def test_inter_state_tax_math(self):
        invoice = ExtractedInvoice(
            invoice_number="INV-002",
            invoice_date="2026-09-01",
            supplier=InvoiceParty(
                name="Bangalore Circuits",
                gstin="29ABCDE1234F1ZW",
                state="Karnataka",
                state_code="29",
            ),
            buyer=InvoiceParty(
                name="Apex Tech",
                gstin="27AAACA1234A1ZK",
                state="Maharashtra",
                state_code="27",
            ),
            line_items=[
                InvoiceLineItem(
                    description="Microcontroller Unit",
                    hsn_sac="8542",
                    quantity=2.0,
                    unit="Nos",
                    rate=5000.0,
                    discount=0.0,
                    taxable_value=10000.0,
                    gst_rate=18.0,
                    cgst_amount=0.0,
                    sgst_amount=0.0,
                    igst_amount=1800.0,
                    total_amount=11800.0,
                )
            ],
            summary=InvoiceSummary(
                total_taxable_value=10000.0,
                total_cgst=0.0,
                total_sgst=0.0,
                total_igst=1800.0,
                round_off=0.0,
                grand_total=11800.0,
            ),
        )

        result = validate_extracted_invoice(invoice)
        self.assertTrue(result.math_check.intra_inter_state_valid)
        self.assertTrue(result.math_check.grand_total_math_valid)
        self.assertEqual(result.triage_status, "auto_ready")

    def test_math_discrepancy_detected(self):
        invoice = ExtractedInvoice(
            invoice_number="INV-ERR",
            invoice_date="2026-09-01",
            supplier=InvoiceParty(name="Test Vendor"),
            line_items=[
                InvoiceLineItem(
                    description="Item",
                    quantity=1.0,
                    rate=100.0,
                    taxable_value=100.0,
                    gst_rate=18.0,
                    cgst_amount=9.0,
                    sgst_amount=9.0,
                    total_amount=118.0,
                )
            ],
            summary=InvoiceSummary(
                total_taxable_value=100.0,
                total_cgst=9.0,
                total_sgst=9.0,
                grand_total=500.0,  # Big mismatch
            ),
        )

        result = validate_extracted_invoice(invoice)
        self.assertFalse(result.math_check.grand_total_math_valid)
        self.assertEqual(result.triage_status, "needs_attention")
        self.assertLess(result.confidence_score, 0.70)


if __name__ == "__main__":
    unittest.main()

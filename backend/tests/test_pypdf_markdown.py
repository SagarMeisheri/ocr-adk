"""Unit tests for PyPDF preprocessor and Markdown Table Parser."""

import unittest
from backend.adk_engine.markdown_parser import (
    parse_markdown_tables,
    parse_invoice_line_items_from_markdown,
    parse_bank_transactions_from_markdown,
    clean_number,
)
from backend.adk_engine.pypdf_preprocessor import PyPdfPreprocessor


class TestPyPdfMarkdownParser(unittest.TestCase):

    def test_clean_number(self):
        self.assertEqual(clean_number("₹ 1,500.50"), 1500.50)
        self.assertEqual(clean_number("Rs. 25,000.00"), 25000.00)
        self.assertEqual(clean_number("(450.00)"), -450.00)
        self.assertEqual(clean_number("1200.00 Dr"), -1200.00)
        self.assertEqual(clean_number("1200.00 Cr"), 1200.00)
        self.assertEqual(clean_number(""), 0.0)

    def test_parse_invoice_markdown_table(self):
        sample_md = """
Here is the invoice breakdown:

| Description | HSN | Qty | Unit | Rate | Taxable | GST % | CGST | SGST | Total |
|-------------|-----|-----|------|------|---------|-------|------|------|-------|
| Dell XPS 15 Laptop | 8471 | 2 | Nos | ₹ 1,20,000.00 | ₹ 2,40,000.00 | 18% | 21,600.00 | 21,600.00 | 2,83,200.00 |
| Wireless Ergonomic Mouse | 8471 | 5 | Nos | 1,500.00 | 7,500.00 | 18% | 675.00 | 675.00 | 8,850.00 |

Total Amount Payable: ₹ 2,92,050.00
"""
        items = parse_invoice_line_items_from_markdown(sample_md)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0].description, "Dell XPS 15 Laptop")
        self.assertEqual(items[0].quantity, 2.0)
        self.assertEqual(items[0].rate, 120000.00)
        self.assertEqual(items[0].taxable_value, 240000.00)
        self.assertEqual(items[0].cgst_amount, 21600.00)
        self.assertEqual(items[0].total_amount, 283200.00)

        self.assertEqual(items[1].description, "Wireless Ergonomic Mouse")
        self.assertEqual(items[1].quantity, 5.0)
        self.assertEqual(items[1].total_amount, 8850.00)

    def test_parse_bank_statement_markdown_table(self):
        sample_bank_md = """
### HDFC Bank Statement Transactions
| Txn Date | Narration | Chq/Ref No | Withdrawal (Dr) | Deposit (Cr) | Balance |
|----------|-----------|------------|-----------------|--------------|---------|
| 2026-08-01 | NEFT-DELL COMPUTERS INDIA | UTR89123456 | ₹ 2,83,200.00 | 0.00 | 5,16,800.00 |
| 2026-08-04 | RTGS-CLIENT INVOICE CLEARANCE | UTR11223344 | 0.00 | 10,00,000.00 | 15,16,800.00 |
| 2026-08-10 | ATM CASH WDL FORT BRANCH | ATM9021 | 25,000.00 | 0.00 | 14,91,800.00 |
| 2026-08-25 | BANK CONSOLIDATED CHARGES | CHG001 | 750.00 | 0.00 | 14,91,050.00 |
"""
        txns = parse_bank_transactions_from_markdown(sample_bank_md)
        self.assertEqual(len(txns), 4)

        # Debit transaction -> Payment
        self.assertEqual(txns[0].transaction_date, "2026-08-01")
        self.assertEqual(txns[0].withdrawal_dr, 283200.00)
        self.assertEqual(txns[0].deposit_cr, 0.0)
        self.assertEqual(txns[0].suggested_voucher_type, "Payment")

        # Credit transaction -> Receipt
        self.assertEqual(txns[1].transaction_date, "2026-08-04")
        self.assertEqual(txns[1].withdrawal_dr, 0.0)
        self.assertEqual(txns[1].deposit_cr, 1000000.00)
        self.assertEqual(txns[1].suggested_voucher_type, "Receipt")

        # Cash withdrawal -> Contra
        self.assertEqual(txns[2].suggested_voucher_type, "Contra")

        # Bank charges auto-ledger matching
        self.assertEqual(txns[3].matched_counter_ledger, "Bank Charges")

    def test_pypdf_non_pdf_handling(self):
        info = PyPdfPreprocessor.inspect_pdf("sample.png")
        self.assertFalse(info["is_pdf"])
        self.assertFalse(info["is_digital_text"])


if __name__ == "__main__":
    unittest.main()

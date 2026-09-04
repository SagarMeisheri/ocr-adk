"""Unit tests for Bank Payment, Receipt, and Contra Voucher XML Generation."""

import unittest
from backend.adk_engine.models import BankTransaction
from backend.tally_bridge.xml_builder import (
    generate_tally_bank_payment_voucher_xml,
    generate_tally_bank_receipt_voucher_xml,
    generate_tally_bank_contra_voucher_xml,
)


class TestBankVouchers(unittest.TestCase):
    def test_payment_voucher_xml(self):
        txn = BankTransaction(
            transaction_date="2026-08-01",
            narration="Payment to Dell Computers for laptops",
            chq_ref_no="UTR123456",
            withdrawal_dr=283200.00,
            deposit_cr=0.0,
            balance=500000.00,
            suggested_voucher_type="Payment",
            matched_counter_ledger="Dell Computers India Pvt Ltd",
        )
        xml_str = generate_tally_bank_payment_voucher_xml(
            txn, bank_ledger="HDFC Bank Current A/c", company_name="Apex Ltd"
        )

        self.assertIn('<VOUCHER VCHTYPE="Payment" ACTION="Create">', xml_str)
        self.assertIn("<DATE>20260801</DATE>", xml_str)
        self.assertIn(
            "<NARRATION>Payment to Dell Computers for laptops</NARRATION>", xml_str
        )
        self.assertIn("<LEDGERNAME>Dell Computers India Pvt Ltd</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>-283200.00</AMOUNT>", xml_str)
        self.assertIn("<LEDGERNAME>HDFC Bank Current A/c</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>283200.00</AMOUNT>", xml_str)
        self.assertIn("<INSTRUMENTNUMBER>UTR123456</INSTRUMENTNUMBER>", xml_str)

    def test_receipt_voucher_xml(self):
        txn = BankTransaction(
            transaction_date="2026-08-04",
            narration="Client payment from Infosys",
            chq_ref_no="UTR998877",
            withdrawal_dr=0.0,
            deposit_cr=1000000.00,
            balance=1500000.00,
            suggested_voucher_type="Receipt",
            matched_counter_ledger="Infosys Limited",
        )
        xml_str = generate_tally_bank_receipt_voucher_xml(
            txn, bank_ledger="ICICI Bank Current A/c"
        )

        self.assertIn('<VOUCHER VCHTYPE="Receipt" ACTION="Create">', xml_str)
        self.assertIn("<DATE>20260804</DATE>", xml_str)
        self.assertIn("<LEDGERNAME>ICICI Bank Current A/c</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>-1000000.00</AMOUNT>", xml_str)
        self.assertIn("<LEDGERNAME>Infosys Limited</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>1000000.00</AMOUNT>", xml_str)

    def test_contra_voucher_xml(self):
        txn = BankTransaction(
            transaction_date="2026-08-10",
            narration="ATM cash withdrawal for office petty cash",
            withdrawal_dr=25000.00,
            deposit_cr=0.0,
            balance=1475000.00,
            suggested_voucher_type="Contra",
        )
        xml_str = generate_tally_bank_contra_voucher_xml(
            txn, bank_ledger="HDFC Bank Current A/c", dest_ledger="Cash"
        )

        self.assertIn('<VOUCHER VCHTYPE="Contra" ACTION="Create">', xml_str)
        self.assertIn("<DATE>20260810</DATE>", xml_str)
        self.assertIn("<LEDGERNAME>Cash</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>-25000.00</AMOUNT>", xml_str)
        self.assertIn("<LEDGERNAME>HDFC Bank Current A/c</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>25000.00</AMOUNT>", xml_str)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for TallyPrime XML Voucher and Master Generator."""

import unittest
import xml.etree.ElementTree as ET
from backend.tally_bridge.xml_builder import (
    generate_tally_purchase_voucher_xml,
    generate_ledger_creation_xml,
    generate_stock_item_creation_xml,
    format_tally_date,
)
from backend.adk_engine.models import (
    ExtractedInvoice,
    InvoiceParty,
    InvoiceLineItem,
    InvoiceSummary,
)


class TestXmlBuilder(unittest.TestCase):

    def test_format_tally_date(self):
        self.assertEqual(format_tally_date("2026-09-03"), "20260903")
        self.assertEqual(format_tally_date("2026/08/15"), "20260815")
        self.assertEqual(format_tally_date("20260903"), "20260903")

    def test_generate_ledger_creation_xml(self):
        xml_str = generate_ledger_creation_xml(
            name="Global Supplies Ltd",
            parent="Sundry Creditors",
            gstin="27AAPFU0939F1ZV",
            state="Maharashtra"
        )
        self.assertIn('<LEDGER NAME="Global Supplies Ltd" ACTION="Create">', xml_str)
        self.assertIn("<PARENT>Sundry Creditors</PARENT>", xml_str)
        self.assertIn("<PARTYGSTIN>27AAPFU0939F1ZV</PARTYGSTIN>", xml_str)
        self.assertIn("<LEDSTATENAME>Maharashtra</LEDSTATENAME>", xml_str)

    def test_generate_stock_item_creation_xml(self):
        xml_str = generate_stock_item_creation_xml(
            name="Industrial Sensor Node",
            base_units="Nos",
            hsn_code="90318000",
            gst_rate=18.0
        )
        self.assertIn('<STOCKITEM NAME="Industrial Sensor Node" ACTION="Create">', xml_str)
        self.assertIn("<BASEUNITS>Nos</BASEUNITS>", xml_str)
        self.assertIn("<HSNCODE>90318000</HSNCODE>", xml_str)

    def test_generate_purchase_voucher_xml(self):
        invoice = ExtractedInvoice(
            invoice_number="INV/9001",
            invoice_date="2026-09-02",
            supplier=InvoiceParty(
                name="Apex Components India",
                gstin="27AAPFU0939F1ZV",
                state="Maharashtra"
            ),
            line_items=[
                InvoiceLineItem(
                    description="Power Supply Unit",
                    quantity=2.0,
                    unit="Nos",
                    rate=2500.0,
                    taxable_value=5000.0,
                    gst_rate=18.0,
                    cgst_amount=450.0,
                    sgst_amount=450.0,
                    total_amount=5900.0,
                    matched_tally_stock_item="Power Supply Unit",
                    matched_tally_purchase_ledger="Purchase Local GST"
                )
            ],
            summary=InvoiceSummary(
                total_taxable_value=5000.0,
                total_cgst=450.0,
                total_sgst=450.0,
                total_igst=0.0,
                round_off=0.0,
                grand_total=5900.0
            ),
            matched_tally_party_ledger="Apex Components India"
        )

        xml_str = generate_tally_purchase_voucher_xml(invoice, company_name="My Company Ltd")

        self.assertIn("<TALLYREQUEST>Import Data</TALLYREQUEST>", xml_str)
        self.assertIn("<SVCURRENTCOMPANY>My Company Ltd</SVCURRENTCOMPANY>", xml_str)
        self.assertIn('<VOUCHER VCHTYPE="Purchase" ACTION="Create"', xml_str)
        self.assertIn("<DATE>20260902</DATE>", xml_str)
        self.assertIn("<REFERENCE>INV/9001</REFERENCE>", xml_str)
        self.assertIn("<PARTYLEDGERNAME>Apex Components India</PARTYLEDGERNAME>", xml_str)
        self.assertIn("<STOCKITEMNAME>Power Supply Unit</STOCKITEMNAME>", xml_str)
        self.assertIn("<AMOUNT>-5000.00</AMOUNT>", xml_str)
        self.assertIn("<ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>", xml_str)
        self.assertIn("<AMOUNT>5900.00</AMOUNT>", xml_str)
        self.assertIn("<LEDGERNAME>Input CGST 9%</LEDGERNAME>", xml_str)
        self.assertIn("<AMOUNT>-450.00</AMOUNT>", xml_str)


if __name__ == "__main__":
    unittest.main()

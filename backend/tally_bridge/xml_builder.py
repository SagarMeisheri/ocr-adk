"""TallyPrime XML Envelope and Voucher Builder.

Supports:
1. Purchase Invoices (F9) with multi-rate GST
2. Bank Payment Vouchers (F5)
3. Bank Receipt Vouchers (F6)
4. Bank Contra Vouchers (F4)
5. Master creation (Sundry Creditors, Debtors, Stock Items)
"""

from __future__ import annotations
import xml.sax.saxutils as saxutils
from datetime import datetime
from typing import Optional, List, Dict, Any
from ..adk_engine.models import ExtractedInvoice, InvoiceLineItem, BankTransaction


def escape_xml(val: Optional[str]) -> str:
    """Escapes special characters for XML."""
    if not val:
        return ""
    return saxutils.escape(str(val))


def format_tally_date(date_str: Optional[str]) -> str:
    """Converts 'YYYY-MM-DD' or common formats to Tally's 'YYYYMMDD'."""
    if not date_str:
        return datetime.now().strftime("%Y%m%d")
    clean = date_str.replace("-", "").replace("/", "").strip()
    if len(clean) == 8 and clean.isdigit():
        return clean
    try:
        dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return dt.strftime("%Y%m%d")
    except Exception:
        return datetime.now().strftime("%Y%m%d")


def build_company_list_request_xml() -> str:
    """XML request to fetch open companies from Tally Prime."""
    return """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>List of Companies</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""


def build_master_export_request_xml(master_type: str = "List of Ledgers") -> str:
    """XML request to export existing Masters (Ledgers or Stock Items) from Tally."""
    return f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>{escape_xml(master_type)}</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""


def generate_ledger_creation_xml(
    name: str,
    parent: str = "Sundry Creditors",
    gstin: Optional[str] = None,
    state: Optional[str] = None,
    address: Optional[str] = None,
    company_name: Optional[str] = None,
) -> str:
    """Generates Tally XML to create a new Ledger (e.g. Sundry Creditor)."""
    company_xml = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company_name else ""
    gstin_xml = f"<PARTYGSTIN>{escape_xml(gstin)}</PARTYGSTIN>" if gstin else ""
    state_xml = f"<LEDSTATENAME>{escape_xml(state)}</LEDSTATENAME>" if state else ""
    addr_xml = f"<ADDRESS.LIST><ADDRESS>{escape_xml(address)}</ADDRESS></ADDRESS.LIST>" if address else ""

    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>All Masters</REPORTNAME>
        {company_xml}
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <LEDGER NAME="{escape_xml(name)}" ACTION="Create">
            <NAME>{escape_xml(name)}</NAME>
            <PARENT>{escape_xml(parent)}</PARENT>
            <ISBILLWISEON>Yes</ISBILLWISEON>
            <COUNTRYNAME>India</COUNTRYNAME>
            {gstin_xml}
            {state_xml}
            {addr_xml}
          </LEDGER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


def generate_stock_item_creation_xml(
    name: str,
    base_units: str = "Nos",
    hsn_code: Optional[str] = None,
    gst_rate: float = 18.0,
    company_name: Optional[str] = None,
) -> str:
    """Generates Tally XML to create a new Stock Item."""
    company_xml = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company_name else ""
    hsn_xml = f"<HSNCODE>{escape_xml(hsn_code)}</HSNCODE>" if hsn_code else ""

    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>All Masters</REPORTNAME>
        {company_xml}
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <STOCKITEM NAME="{escape_xml(name)}" ACTION="Create">
            <NAME>{escape_xml(name)}</NAME>
            <BASEUNITS>{escape_xml(base_units)}</BASEUNITS>
            <GSTAPPLICABLE>&#4; Applicable</GSTAPPLICABLE>
            <GSTTYPESUPPLY>Goods</GSTTYPESUPPLY>
            {hsn_xml}
          </STOCKITEM>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


def generate_tally_purchase_voucher_xml(
    invoice: ExtractedInvoice,
    company_name: Optional[str] = None,
) -> str:
    """Builds a complete, standard TallyPrime F9 Purchase Voucher XML envelope."""
    date_formatted = format_tally_date(invoice.invoice_date)
    ref_number = invoice.invoice_number or f"BILL-{date_formatted}"
    supplier_name = invoice.matched_tally_party_ledger or invoice.supplier.name
    supplier_gstin = invoice.supplier.gstin or ""
    supplier_state = invoice.supplier.state or ""

    company_xml = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company_name else ""

    inventory_entries_xml = []
    for item in invoice.line_items:
        stock_name = item.matched_tally_stock_item or item.description
        purchase_ledger = item.matched_tally_purchase_ledger or "Purchase Local GST"
        qty_unit = f"{item.quantity:.2f} {item.unit}"
        rate_str = f"{item.rate:.2f}/{item.unit}"
        taxable_neg = -abs(item.taxable_value)

        inventory_entries_xml.append(f"""            <ALLINVENTORYENTRIES.LIST>
              <STOCKITEMNAME>{escape_xml(stock_name)}</STOCKITEMNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <RATE>{escape_xml(rate_str)}</RATE>
              <ACTUALQTY>{escape_xml(qty_unit)}</ACTUALQTY>
              <BILLEDQTY>{escape_xml(qty_unit)}</BILLEDQTY>
              <AMOUNT>{taxable_neg:.2f}</AMOUNT>
              <ACCOUNTINGALLOCATIONS.LIST>
                <LEDGERNAME>{escape_xml(purchase_ledger)}</LEDGERNAME>
                <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
                <AMOUNT>{taxable_neg:.2f}</AMOUNT>
              </ACCOUNTINGALLOCATIONS.LIST>
            </ALLINVENTORYENTRIES.LIST>""")

    grand_total_pos = abs(invoice.summary.grand_total)
    party_ledger_xml = f"""            <LEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(supplier_name)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{grand_total_pos:.2f}</AMOUNT>
              <BILLALLOCATIONS.LIST>
                <NAME>{escape_xml(ref_number)}</NAME>
                <BILLTYPE>New Ref</BILLTYPE>
                <AMOUNT>{grand_total_pos:.2f}</AMOUNT>
              </BILLALLOCATIONS.LIST>
            </LEDGERENTRIES.LIST>"""

    tax_entries_xml = []
    if invoice.summary.total_cgst > 0:
        tax_entries_xml.append(f"""            <LEDGERENTRIES.LIST>
              <LEDGERNAME>Input CGST 9%</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>{-abs(invoice.summary.total_cgst):.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>""")

    if invoice.summary.total_sgst > 0:
        tax_entries_xml.append(f"""            <LEDGERENTRIES.LIST>
              <LEDGERNAME>Input SGST 9%</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>{-abs(invoice.summary.total_sgst):.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>""")

    if invoice.summary.total_igst > 0:
        tax_entries_xml.append(f"""            <LEDGERENTRIES.LIST>
              <LEDGERNAME>Input IGST 18%</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>{-abs(invoice.summary.total_igst):.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>""")

    if abs(invoice.summary.round_off) >= 0.01:
        ro_val = invoice.summary.round_off
        ro_deemed = "Yes" if ro_val < 0 else "No"
        ro_amt = -abs(ro_val) if ro_val < 0 else abs(ro_val)
        tax_entries_xml.append(f"""            <LEDGERENTRIES.LIST>
              <LEDGERNAME>Round Off</LEDGERNAME>
              <ISDEEMEDPOSITIVE>{ro_deemed}</ISDEEMEDPOSITIVE>
              <AMOUNT>{ro_amt:.2f}</AMOUNT>
            </LEDGERENTRIES.LIST>""")

    all_inv_str = "\n".join(inventory_entries_xml)
    all_tax_str = "\n".join(tax_entries_xml)

    return f"""<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Import Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        {company_xml}
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Purchase" ACTION="Create" OBJVIEW="Invoice Voucher View">
            <DATE>{date_formatted}</DATE>
            <VOUCHERTYPENAME>Purchase</VOUCHERTYPENAME>
            <REFERENCE>{escape_xml(ref_number)}</REFERENCE>
            <REFERENCEDATE>{date_formatted}</REFERENCEDATE>
            <PARTYLEDGERNAME>{escape_xml(supplier_name)}</PARTYLEDGERNAME>
            <PARTYNAME>{escape_xml(supplier_name)}</PARTYNAME>
            <PARTYGSTIN>{escape_xml(supplier_gstin)}</PARTYGSTIN>
            <STATENAME>{escape_xml(supplier_state)}</STATENAME>
            <ISINVOICE>Yes</ISINVOICE>
{all_inv_str}
{party_ledger_xml}
{all_tax_str}
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


# ==========================================
# Bank Statement Voucher XML Generators
# ==========================================

def generate_tally_bank_payment_voucher_xml(
    txn: BankTransaction,
    bank_ledger: str = "Bank Account",
    company_name: Optional[str] = None,
) -> str:
    """Generates Tally F5 Payment Voucher for bank withdrawals/debits."""
    date_formatted = format_tally_date(txn.transaction_date)
    counter_ledger = txn.matched_counter_ledger or "Sundry Creditors"
    amount = abs(txn.withdrawal_dr)
    company_xml = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company_name else ""
    ref_tag = f"<INSTRUMENTNUMBER>{escape_xml(txn.chq_ref_no)}</INSTRUMENTNUMBER>" if txn.chq_ref_no else ""

    return f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        {company_xml}
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Payment" ACTION="Create">
            <DATE>{date_formatted}</DATE>
            <VOUCHERTYPENAME>Payment</VOUCHERTYPENAME>
            <NARRATION>{escape_xml(txn.narration)}</NARRATION>
            <!-- Debit: Expense or Creditor -->
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(counter_ledger)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <!-- Credit: Bank Ledger -->
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(bank_ledger)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{amount:.2f}</AMOUNT>
              <BANKALLOCATIONS.LIST>
                <PAYMENTMODE>Transacted</PAYMENTMODE>
                {ref_tag}
                <AMOUNT>{amount:.2f}</AMOUNT>
              </BANKALLOCATIONS.LIST>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


def generate_tally_bank_receipt_voucher_xml(
    txn: BankTransaction,
    bank_ledger: str = "Bank Account",
    company_name: Optional[str] = None,
) -> str:
    """Generates Tally F6 Receipt Voucher for bank deposits/credits."""
    date_formatted = format_tally_date(txn.transaction_date)
    counter_ledger = txn.matched_counter_ledger or "Sundry Debtors"
    amount = abs(txn.deposit_cr)
    company_xml = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company_name else ""
    ref_tag = f"<INSTRUMENTNUMBER>{escape_xml(txn.chq_ref_no)}</INSTRUMENTNUMBER>" if txn.chq_ref_no else ""

    return f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        {company_xml}
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Receipt" ACTION="Create">
            <DATE>{date_formatted}</DATE>
            <VOUCHERTYPENAME>Receipt</VOUCHERTYPENAME>
            <NARRATION>{escape_xml(txn.narration)}</NARRATION>
            <!-- Debit: Bank Ledger -->
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(bank_ledger)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{amount:.2f}</AMOUNT>
              <BANKALLOCATIONS.LIST>
                <PAYMENTMODE>Transacted</PAYMENTMODE>
                {ref_tag}
                <AMOUNT>-{amount:.2f}</AMOUNT>
              </BANKALLOCATIONS.LIST>
            </ALLLEDGERENTRIES.LIST>
            <!-- Credit: Customer or Income -->
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(counter_ledger)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""


def generate_tally_bank_contra_voucher_xml(
    txn: BankTransaction,
    bank_ledger: str = "Bank Account",
    dest_ledger: str = "Cash",
    company_name: Optional[str] = None,
) -> str:
    """Generates Tally F4 Contra Voucher for cash withdrawals/transfers."""
    date_formatted = format_tally_date(txn.transaction_date)
    amount = abs(txn.withdrawal_dr) if txn.withdrawal_dr > 0 else abs(txn.deposit_cr)
    company_xml = f"<STATICVARIABLES><SVCURRENTCOMPANY>{escape_xml(company_name)}</SVCURRENTCOMPANY></STATICVARIABLES>" if company_name else ""

    return f"""<ENVELOPE>
  <HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER>
  <BODY>
    <IMPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>Vouchers</REPORTNAME>
        {company_xml}
      </REQUESTDESC>
      <REQUESTDATA>
        <TALLYMESSAGE xmlns:UDF="TallyUDF">
          <VOUCHER VCHTYPE="Contra" ACTION="Create">
            <DATE>{date_formatted}</DATE>
            <VOUCHERTYPENAME>Contra</VOUCHERTYPENAME>
            <NARRATION>{escape_xml(txn.narration)}</NARRATION>
            <!-- Debit: Cash or Destination Bank -->
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(dest_ledger)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>Yes</ISDEEMEDPOSITIVE>
              <AMOUNT>-{amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
            <!-- Credit: Source Bank -->
            <ALLLEDGERENTRIES.LIST>
              <LEDGERNAME>{escape_xml(bank_ledger)}</LEDGERNAME>
              <ISDEEMEDPOSITIVE>No</ISDEEMEDPOSITIVE>
              <AMOUNT>{amount:.2f}</AMOUNT>
            </ALLLEDGERENTRIES.LIST>
          </VOUCHER>
        </TALLYMESSAGE>
      </REQUESTDATA>
    </IMPORTDATA>
  </BODY>
</ENVELOPE>"""

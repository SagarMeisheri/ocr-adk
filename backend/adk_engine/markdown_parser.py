"""Deterministic Markdown Table Parser for Purchase Invoices and Bank Statements."""

from __future__ import annotations
import re
from typing import List, Dict, Any, Optional, Tuple
from .models import InvoiceLineItem, InvoiceSummary, BankTransaction


def clean_number(val: Optional[str]) -> float:
    """Sanitizes string monetary values into clean floats."""
    if not val:
        return 0.0
    s = str(val).strip()
    # Remove currency symbols and formatting
    s = re.sub(r'[₹$€,]', '', s)
    s = re.sub(r'(?i)rs\.?', '', s).strip()

    # Handle negative in parenthesis: (100.00) -> -100.00
    if s.startswith('(') and s.endswith(')'):
        s = '-' + s[1:-1]

    # Handle trailing Dr/Cr
    is_dr = bool(re.search(r'(?i)\s*dr$', s))
    s = re.sub(r'(?i)\s*(cr|dr)$', '', s).strip()

    try:
        n = float(s)
        return -abs(n) if is_dr else n
    except ValueError:
        return 0.0


def parse_markdown_tables(markdown_text: str) -> List[List[List[str]]]:
    """Finds and parses all Markdown pipe tables from text into 2D rows."""
    tables: List[List[List[str]]] = []
    current_table: List[List[str]] = []
    in_table = False

    for line in markdown_text.splitlines():
        trimmed = line.strip()
        if trimmed.startswith('|') and trimmed.endswith('|'):
            # Check if this is a separator line like |---|---|
            if re.match(r'^\|[\s\-:|]+\|$', trimmed):
                continue
            cells = [c.strip() for c in trimmed[1:-1].split('|')]
            current_table.append(cells)
            in_table = True
        else:
            if in_table and current_table:
                tables.append(current_table)
                current_table = []
                in_table = False

    if in_table and current_table:
        tables.append(current_table)

    return tables


def parse_invoice_line_items_from_markdown(markdown_text: str) -> List[InvoiceLineItem]:
    """Extracts InvoiceLineItems from the first matching line items markdown table."""
    tables = parse_markdown_tables(markdown_text)
    items: List[InvoiceLineItem] = []

    for table in tables:
        if len(table) < 2:
            continue
        headers = [h.lower() for h in table[0]]

        # Check if table looks like invoice line items
        has_desc = any(h in headers for h in ["description", "item", "particulars", "product", "item name"])
        has_val = any(h in headers for h in ["taxable", "rate", "amount", "total", "qty", "quantity"])

        if not (has_desc and has_val):
            continue

        # Map column indices
        col_map: Dict[str, int] = {}
        for idx, h in enumerate(headers):
            if any(k in h for k in ["description", "item name", "product", "particulars"]):
                col_map.setdefault("description", idx)
            elif any(k in h for k in ["hsn", "sac"]):
                col_map.setdefault("hsn", idx)
            elif any(k in h for k in ["qty", "quantity"]):
                col_map.setdefault("qty", idx)
            elif any(k in h for k in ["unit", "uom"]):
                col_map.setdefault("unit", idx)
            elif any(k in h for k in ["rate", "price", "unit price"]):
                col_map.setdefault("rate", idx)
            elif any(k in h for k in ["discount", "disc"]):
                col_map.setdefault("discount", idx)
            elif any(k in h for k in ["taxable", "taxable value", "taxable amt"]):
                col_map.setdefault("taxable", idx)
            elif any(k in h for k in ["gst %", "gst rate", "tax %"]):
                col_map.setdefault("gst_rate", idx)
            elif "cgst" in h:
                col_map.setdefault("cgst", idx)
            elif "sgst" in h:
                col_map.setdefault("sgst", idx)
            elif "igst" in h:
                col_map.setdefault("igst", idx)
            elif any(k in h for k in ["total", "total amount", "net amount"]):
                col_map.setdefault("total", idx)

        # Parse rows
        for row in table[1:]:
            if len(row) <= max(col_map.values(), default=0):
                continue
            desc = row[col_map.get("description", 0)].strip()
            if not desc or desc.lower().startswith("total"):
                continue

            hsn = row[col_map["hsn"]].strip() if "hsn" in col_map else None
            qty = clean_number(row[col_map["qty"]]) if "qty" in col_map else 1.0
            unit = row[col_map["unit"]].strip() if "unit" in col_map else "Nos"
            rate = clean_number(row[col_map["rate"]]) if "rate" in col_map else 0.0
            disc = clean_number(row[col_map["discount"]]) if "discount" in col_map else 0.0
            taxable = clean_number(row[col_map["taxable"]]) if "taxable" in col_map else round((qty * rate) - disc, 2)
            gst_rate = clean_number(row[col_map["gst_rate"]]) if "gst_rate" in col_map else 18.0

            cgst = clean_number(row[col_map["cgst"]]) if "cgst" in col_map else 0.0
            sgst = clean_number(row[col_map["sgst"]]) if "sgst" in col_map else 0.0
            igst = clean_number(row[col_map["igst"]]) if "igst" in col_map else 0.0

            total = clean_number(row[col_map["total"]]) if "total" in col_map else round(taxable + cgst + sgst + igst, 2)

            items.append(InvoiceLineItem(
                description=desc,
                hsn_sac=hsn,
                quantity=max(1.0, qty),
                unit=unit or "Nos",
                rate=rate,
                discount=disc,
                taxable_value=taxable,
                gst_rate=gst_rate,
                cgst_amount=cgst,
                sgst_amount=sgst,
                igst_amount=igst,
                total_amount=total
            ))

        if items:
            break

    return items


def parse_bank_transactions_from_markdown(markdown_text: str) -> List[BankTransaction]:
    """Extracts BankTransaction list from bank statement markdown table(s)."""
    tables = parse_markdown_tables(markdown_text)
    transactions: List[BankTransaction] = []

    for table in tables:
        if len(table) < 2:
            continue
        headers = [h.lower() for h in table[0]]

        # Detect bank statement headers
        is_bank_table = any(k in headers for k in ["withdrawal", "deposit", "balance", "narration", "particulars", "dr", "cr"])
        if not is_bank_table:
            continue

        col_map: Dict[str, int] = {}
        for idx, h in enumerate(headers):
            if any(k in h for k in ["txn date", "transaction date", "value date", "date"]):
                col_map.setdefault("date", idx)
            elif any(k in h for k in ["narration", "description", "particulars", "remarks"]):
                col_map.setdefault("narration", idx)
            elif any(k in h for k in ["chq", "cheque", "ref", "utr"]):
                col_map.setdefault("ref", idx)
            elif any(k in h for k in ["withdrawal", "debit", "dr"]):
                col_map.setdefault("dr", idx)
            elif any(k in h for k in ["deposit", "credit", "cr"]):
                col_map.setdefault("cr", idx)
            elif any(k in h for k in ["balance", "bal"]):
                col_map.setdefault("balance", idx)

        for row in table[1:]:
            if len(row) <= max(col_map.values(), default=0):
                continue
            date_str = row[col_map.get("date", 0)].strip()
            # Must look like a date
            if not date_str or not re.search(r'\d', date_str):
                continue

            narration = row[col_map.get("narration", 1)].strip() if "narration" in col_map else "Transaction"
            ref = row[col_map["ref"]].strip() if "ref" in col_map else None
            dr = abs(clean_number(row[col_map["dr"]])) if "dr" in col_map else 0.0
            cr = abs(clean_number(row[col_map["cr"]])) if "cr" in col_map else 0.0
            bal = clean_number(row[col_map["balance"]]) if "balance" in col_map else 0.0

            # Determine Voucher Type
            narr_lower = narration.lower()
            if any(k in narr_lower for k in ["atm cash", "cash wdl", "cash deposit", "transfer to self"]):
                vch_type = "Contra"
            elif dr > 0:
                vch_type = "Payment"
            else:
                vch_type = "Receipt"

            # Auto suggest counter ledger based on Indian bank narrations
            suggested_ledger = None
            if "charges" in narr_lower or "chg" in narr_lower or "gst" in narr_lower:
                suggested_ledger = "Bank Charges"
            elif "interest" in narr_lower or "int.pd" in narr_lower:
                suggested_ledger = "Bank Interest Income"
            elif "salary" in narr_lower or "sal" in narr_lower:
                suggested_ledger = "Salary & Wages"

            transactions.append(BankTransaction(
                transaction_date=date_str,
                narration=narration,
                chq_ref_no=ref,
                withdrawal_dr=dr,
                deposit_cr=cr,
                balance=bal,
                suggested_voucher_type=vch_type,
                matched_counter_ledger=suggested_ledger,
            ))

    return transactions

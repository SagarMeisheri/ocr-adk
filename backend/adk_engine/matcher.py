"""Tally Master Matcher: Matches extracted parties and items against Tally Prime Masters."""

from __future__ import annotations
import difflib
from typing import List, Dict, Any, Optional, Tuple
from .models import ExtractedInvoice, InvoiceLineItem


# Default Tax Ledger Name Mapping for Indian GST in TallyPrime
TAX_LEDGER_MAP = {
    # (Rate, TaxType) -> Ledger Name
    (5.0, "CGST"): "Input CGST 2.5%",
    (5.0, "SGST"): "Input SGST 2.5%",
    (5.0, "IGST"): "Input IGST 5%",
    (12.0, "CGST"): "Input CGST 6%",
    (12.0, "SGST"): "Input SGST 6%",
    (12.0, "IGST"): "Input IGST 12%",
    (18.0, "CGST"): "Input CGST 9%",
    (18.0, "SGST"): "Input SGST 9%",
    (18.0, "IGST"): "Input IGST 18%",
    (28.0, "CGST"): "Input CGST 14%",
    (28.0, "SGST"): "Input SGST 14%",
    (28.0, "IGST"): "Input IGST 28%",
}


class TallyMasterMatcher:
    """Fuzzy matches extracted invoice details against cached Tally Prime masters."""

    def __init__(
        self,
        existing_ledgers: Optional[List[str]] = None,
        existing_stock_items: Optional[List[str]] = None,
        existing_purchase_ledgers: Optional[List[str]] = None,
    ):
        self.existing_ledgers = existing_ledgers or [
            "Sundry Creditors",
            "Purchase Local GST",
            "Purchase Interstate GST",
            "Input CGST 9%",
            "Input SGST 9%",
            "Input IGST 18%",
            "Input CGST 6%",
            "Input SGST 6%",
            "Input IGST 12%",
            "Round Off",
        ]
        self.existing_stock_items = existing_stock_items or []
        self.existing_purchase_ledgers = existing_purchase_ledgers or [
            "Purchase Local GST",
            "Purchase Interstate GST",
            "Purchase Exempt",
        ]

    def find_best_match(self, query: str, candidates: List[str], cutoff: float = 0.65) -> Optional[Tuple[str, float]]:
        """Finds closest match from a list of strings using SequenceMatcher."""
        if not query or not candidates:
            return None

        query_clean = query.strip().lower()
        best_match = None
        best_ratio = 0.0

        for candidate in candidates:
            cand_clean = candidate.strip().lower()
            # Exact match check
            if query_clean == cand_clean:
                return (candidate, 1.0)

            # Substring match bonus
            if query_clean in cand_clean or cand_clean in query_clean:
                ratio = 0.85
            else:
                ratio = difflib.SequenceMatcher(None, query_clean, cand_clean).ratio()

            if ratio > best_ratio and ratio >= cutoff:
                best_ratio = ratio
                best_match = candidate

        return (best_match, best_ratio) if best_match else None

    def match_party(self, party_name: str) -> Tuple[Optional[str], bool]:
        """Returns (matched_ledger_name, is_new_ledger)."""
        match = self.find_best_match(party_name, self.existing_ledgers, cutoff=0.70)
        if match:
            return match[0], False
        return party_name.strip(), True

    def match_stock_item(self, item_description: str) -> Tuple[Optional[str], bool]:
        """Returns (matched_stock_item_name, is_new_item)."""
        match = self.find_best_match(item_description, self.existing_stock_items, cutoff=0.70)
        if match:
            return match[0], False
        return item_description.strip(), True

    def resolve_purchase_ledger(self, gst_rate: float, is_interstate: bool) -> str:
        """Determines standard Tally purchase account."""
        if is_interstate:
            return "Purchase Interstate GST"
        return "Purchase Local GST"

    def match_and_enrich_invoice(self, invoice: ExtractedInvoice) -> ExtractedInvoice:
        """Enriches the extracted invoice with matched Tally ledgers and stock items."""
        # 1. Match Party Ledger
        matched_party, is_new_party = self.match_party(invoice.supplier.name)
        invoice.matched_tally_party_ledger = matched_party
        invoice.auto_create_party_ledger = is_new_party

        # 2. Determine if interstate
        is_interstate = False
        if invoice.supplier and invoice.supplier.state_code and invoice.buyer and invoice.buyer.state_code:
            is_interstate = (invoice.supplier.state_code != invoice.buyer.state_code)

        # 3. Match Line Items
        for item in invoice.line_items:
            matched_item, is_new_item = self.match_stock_item(item.description)
            item.matched_tally_stock_item = matched_item
            item.matched_tally_purchase_ledger = self.resolve_purchase_ledger(item.gst_rate, is_interstate)

        return invoice

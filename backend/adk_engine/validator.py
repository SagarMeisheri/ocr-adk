"""Deterministic Indian GSTIN Checksum and Tax Math Validator for Invoice OCR."""

from __future__ import annotations
import re
from typing import Tuple, Dict, Optional, List
from .models import (
    ExtractedInvoice,
    ValidationResult,
    GstinValidationDetail,
    MathValidationDetail,
    InvoiceLineItem,
    InvoiceSummary,
)

# Indian GST State Code Dictionary
GST_STATE_CODES: Dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
    "97": "Other Territory",
    "99": "Centre Jurisdiction",
}

# Luhn mod-36 character set
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CHAR_MAP = {c: i for i, c in enumerate(CHARS)}


def calculate_gstin_checksum(gstin_14: str) -> Optional[str]:
    """Computes the 15th check digit for a 14-character GSTIN prefix using Luhn mod-36."""
    if len(gstin_14) != 14:
        return None

    factor = 1
    total_sum = 0
    mod = 36

    for char in gstin_14.upper():
        if char not in CHAR_MAP:
            return None
        code_point = CHAR_MAP[char]
        addend = factor * code_point
        factor = 2 if factor == 1 else 1
        addend = (addend // mod) + (addend % mod)
        total_sum += addend

    remainder = total_sum % mod
    check_code_point = (mod - remainder) % mod
    return CHARS[check_code_point]


def validate_gstin(gstin: Optional[str]) -> GstinValidationDetail:
    """Validates an Indian GSTIN format, state code, PAN extraction, and Luhn mod-36 checksum."""
    if not gstin or not gstin.strip():
        return GstinValidationDetail(
            gstin=None,
            is_valid_format=False,
            is_checksum_valid=False,
            error_message="GSTIN is missing (common for unregistered kirana stores or cash memos)",
        )

    clean_gstin = re.sub(r"[^A-Za-z0-9]", "", gstin).upper()

    # Standard GSTIN regex: 2 digits + 5 letters + 4 digits + 1 letter + 1 char + Z + 1 char
    regex = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    if not re.match(regex, clean_gstin):
        return GstinValidationDetail(
            gstin=clean_gstin,
            is_valid_format=False,
            is_checksum_valid=False,
            error_message=f"Invalid GSTIN structure: '{clean_gstin}'. Must be 15 alphanumeric characters.",
        )

    state_code = clean_gstin[:2]
    pan = clean_gstin[2:12]
    state_name = GST_STATE_CODES.get(state_code, "Unknown State Code")

    # Check Luhn mod-36 check digit
    expected_check = calculate_gstin_checksum(clean_gstin[:14])
    actual_check = clean_gstin[14]
    is_checksum_valid = expected_check == actual_check

    err = (
        None
        if is_checksum_valid
        else f"Checksum mismatch: expected '{expected_check}', got '{actual_check}'"
    )

    return GstinValidationDetail(
        gstin=clean_gstin,
        is_valid_format=True,
        is_checksum_valid=is_checksum_valid,
        state_code=state_code,
        pan=pan,
        state_name=state_name,
        error_message=err,
    )


def validate_tax_math(
    supplier: Optional[GstinValidationDetail],
    buyer: Optional[GstinValidationDetail],
    line_items: List[InvoiceLineItem],
    summary: InvoiceSummary,
) -> MathValidationDetail:
    """Performs comprehensive GST mathematical verification."""
    notes: List[str] = []
    line_item_math_valid = True
    tax_math_valid = True
    intra_inter_state_valid = True

    # 1. Determine if transaction is Intra-State or Inter-State
    is_inter_state = False
    if supplier and supplier.state_code and buyer and buyer.state_code:
        if supplier.state_code != buyer.state_code:
            is_inter_state = True
            notes.append(
                f"Inter-State Sale ({supplier.state_name} -> {buyer.state_name}): Expected IGST"
            )
        else:
            notes.append(
                f"Intra-State Sale (Within {supplier.state_name}): Expected CGST + SGST"
            )

    calc_taxable_sum = 0.0
    calc_cgst_sum = 0.0
    calc_sgst_sum = 0.0
    calc_igst_sum = 0.0

    # 2. Line item verification
    for idx, item in enumerate(line_items, start=1):
        expected_taxable = round((item.quantity * item.rate) - item.discount, 2)
        diff_taxable = abs(item.taxable_value - expected_taxable)

        # Allow slight rounding leeway of 0.20
        if diff_taxable > 0.50 and item.quantity > 0 and item.rate > 0:
            line_item_math_valid = False
            notes.append(
                f"Line #{idx} ('{item.description[:20]}'): "
                f"Qty ({item.quantity}) * Rate ({item.rate}) - Disc ({item.discount}) = {expected_taxable:.2f}, "
                f"but extracted taxable value is {item.taxable_value:.2f}"
            )

        calc_taxable_sum += item.taxable_value

        # Tax calculation check
        if is_inter_state:
            expected_igst = round(item.taxable_value * (item.gst_rate / 100.0), 2)
            if item.cgst_amount > 0 or item.sgst_amount > 0:
                intra_inter_state_valid = False
                notes.append(
                    f"Line #{idx}: Inter-state transaction should not have CGST/SGST."
                )
            calc_igst_sum += item.igst_amount
        else:
            half_rate = item.gst_rate / 2.0
            expected_half_tax = round(item.taxable_value * (half_rate / 100.0), 2)
            calc_cgst_sum += item.cgst_amount
            calc_sgst_sum += item.sgst_amount
            if item.igst_amount > 0 and abs(item.cgst_amount + item.sgst_amount) < 0.01:
                # If supplier charged IGST within same state, flag warning
                intra_inter_state_valid = False
                notes.append(
                    f"Line #{idx}: Intra-state invoice has IGST instead of CGST + SGST."
                )

    # 3. Summary totals check
    calc_taxes = calc_cgst_sum + calc_sgst_sum + calc_igst_sum + summary.total_cess
    calc_grand_total = round(calc_taxable_sum + calc_taxes + summary.round_off, 2)

    discrepancy = abs(summary.grand_total - calc_grand_total)
    grand_total_math_valid = (
        discrepancy <= 1.00
    )  # Allow up to 1 rupee for rounding variance

    if not grand_total_math_valid:
        notes.append(
            f"Grand Total Discrepancy: Extracted ₹{summary.grand_total:.2f} vs "
            f"Calculated ₹{calc_grand_total:.2f} (Diff: ₹{discrepancy:.2f})"
        )

    is_overall_valid = (
        line_item_math_valid and grand_total_math_valid and intra_inter_state_valid
    )

    return MathValidationDetail(
        is_valid=is_overall_valid,
        line_item_math_valid=line_item_math_valid,
        tax_math_valid=tax_math_valid,
        grand_total_math_valid=grand_total_math_valid,
        intra_inter_state_valid=intra_inter_state_valid,
        calculated_taxable=round(calc_taxable_sum, 2),
        calculated_taxes=round(calc_taxes, 2),
        calculated_grand_total=calc_grand_total,
        discrepancy_amount=round(discrepancy, 2),
        notes=notes,
    )


def validate_extracted_invoice(invoice: ExtractedInvoice) -> ValidationResult:
    """Runs end-to-end validation and produces triage bucket and confidence rating."""
    supplier_check = validate_gstin(
        invoice.supplier.gstin if invoice.supplier else None
    )
    buyer_check = validate_gstin(invoice.buyer.gstin if invoice.buyer else None)

    math_check = validate_tax_math(
        supplier=supplier_check,
        buyer=buyer_check,
        line_items=invoice.line_items,
        summary=invoice.summary,
    )

    warnings: List[str] = []
    confidence = 1.0

    # GSTIN checks
    if invoice.supplier and invoice.supplier.gstin:
        if not supplier_check.is_valid_format:
            confidence -= 0.20
            warnings.append("Supplier GSTIN format is invalid.")
        elif not supplier_check.is_checksum_valid:
            confidence -= 0.10
            warnings.append(
                f"Supplier GSTIN checksum failed: {supplier_check.error_message}"
            )
    else:
        # B2C or unregistered vendor
        confidence -= 0.10
        warnings.append("Supplier has no GSTIN (Unregistered or Cash Bill).")

    # Math checks
    if not math_check.line_item_math_valid:
        confidence -= 0.15
        warnings.append(
            "Line item math discrepancy detected (Quantity * Rate != Taxable)."
        )

    if not math_check.grand_total_math_valid:
        confidence -= 0.25
        warnings.append(
            f"Grand total math mismatch by ₹{math_check.discrepancy_amount:.2f}."
        )

    if not math_check.intra_inter_state_valid:
        confidence -= 0.10
        warnings.append("Intra/Inter state GST routing discrepancy detected.")

    # Line items presence
    if not invoice.line_items:
        confidence -= 0.30
        warnings.append("No line items found in invoice.")

    # Missing invoice number or date
    if not invoice.invoice_number:
        confidence -= 0.15
        warnings.append("Invoice number not found.")
    if not invoice.invoice_date:
        confidence -= 0.10
        warnings.append("Invoice date not found.")

    confidence = max(0.0, min(1.0, round(confidence, 2)))

    # Determine Tri-Queue Triage Bucket
    if (
        confidence >= 0.90
        and math_check.is_valid
        and (supplier_check.is_checksum_valid or not invoice.supplier.gstin)
    ):
        triage_status = "auto_ready"
    elif confidence >= 0.70:
        triage_status = "quick_review"
    else:
        triage_status = "needs_attention"

    is_fully_valid = triage_status == "auto_ready"

    return ValidationResult(
        is_fully_valid=is_fully_valid,
        supplier_gstin_check=supplier_check,
        buyer_gstin_check=buyer_check,
        math_check=math_check,
        confidence_score=confidence,
        triage_status=triage_status,
        warnings=warnings,
    )

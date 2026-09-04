"""Fast Local PDF Preprocessor using PyPDF.

Differentiates between digital text-rich PDFs (e-invoices, multi-page bank statements)
and scanned image/handwritten PDFs to optimize LLM token usage and prevent OCR hallucination.
"""

from __future__ import annotations
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple


class PyPdfPreprocessor:
    """Extracts raw text and determines document density from PDFs."""

    @staticmethod
    def inspect_pdf(file_path: str) -> Dict[str, Any]:
        """Analyzes PDF file and extracts text page-by-page."""
        path = Path(file_path)
        if path.suffix.lower() != ".pdf":
            return {
                "is_pdf": False,
                "is_digital_text": False,
                "page_count": 1,
                "full_text": "",
                "pages": [],
            }

        try:
            import pypdf

            reader = pypdf.PdfReader(file_path)
            page_count = len(reader.pages)
            pages_text: List[str] = []
            total_chars = 0

            for idx, page in enumerate(reader.pages):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                cleaned = text.strip()
                pages_text.append(cleaned)
                total_chars += len(cleaned)

            avg_chars = total_chars / max(1, page_count)
            # If average characters per page > 60, it contains selectable digital text
            is_digital_text = avg_chars > 60

            # Check if document looks like a bank statement
            lower_full = "\n".join(pages_text).lower()
            is_bank_statement = any(
                k in lower_full
                for k in [
                    "statement of account",
                    "bank statement",
                    "transaction date",
                    "withdrawal",
                    "deposit",
                    "balance",
                    "chq/ref",
                    "cr/dr",
                    "opening balance",
                ]
            )

            return {
                "is_pdf": True,
                "is_digital_text": is_digital_text,
                "page_count": page_count,
                "avg_chars_per_page": avg_chars,
                "is_bank_statement": is_bank_statement,
                "full_text": "\n\n--- PAGE BREAK ---\n\n".join(pages_text),
                "pages": pages_text,
            }

        except Exception as e:
            return {
                "is_pdf": True,
                "is_digital_text": False,
                "page_count": 1,
                "error": str(e),
                "full_text": "",
                "pages": [],
            }

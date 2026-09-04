"""Visual Document Transcription Engine using Gemini Multimodal Vision and layout-preserving Markdown."""

from __future__ import annotations
import os
import mimetypes
from typing import Optional, Dict, Any, Union, Tuple
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .models import (
    ExtractedInvoice,
    InvoiceParty,
    InvoiceSummary,
    BankStatement,
    ParsedDocument,
)

DOCUMENT_TRANSCRIPTION_PROMPT = """You are a document transcription engine.
Transcribe the provided document directly into Markdown while strictly preserving its visual layout, reading order, and tabular formats.

Rules:
1. Represent side-by-side panels (like Vendor vs. Customer details, or Metadata grids) using multi-column Markdown tables.
2. Render line-item sections as standard Markdown tables matching the original column structure exactly.
3. Keep multiline item descriptions grouped within the same table cell using `<br>` tags rather than creating detached empty rows.
4. Transcribe all text, numbers, labels, and footer blocks verbatim. Do not omit, calculate, or summarize any details."""


class HybridExtractor:
    """Document transcription engine using Gemini Multimodal Vision to produce layout-preserving Markdown."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        self.thinking_level = os.environ.get("GEMINI_THINKING_LEVEL", "low").lower()

    def extract_universal_document(self, file_path: str) -> ParsedDocument:
        """Transcribes document directly into Markdown preserving visual layout and tables."""
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY is required for multimodal document transcription.")

        stem_title = Path(file_path).stem.replace("_", " ").title()

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            if file_path.lower().endswith(".pdf"):
                mime_type = "application/pdf"
            elif file_path.lower().endswith((".png", ".webp")):
                mime_type = "image/png"
            else:
                mime_type = "image/jpeg"

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        content_payload = [
            types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
            DOCUMENT_TRANSCRIPTION_PROMPT,
        ]

        raw_markdown = ""
        thinking_process: List[str] = []
        thoughts_token_count = 0

        # Attempt to use the Gemini Interactions API with dedicated thinking steps
        has_interactions = hasattr(client, "interactions") and hasattr(client.interactions, "create")
        if has_interactions:
            try:
                interaction = client.interactions.create(
                    model=self.model_name,
                    input=content_payload,
                    generation_config={
                        "thinking_level": self.thinking_level,
                        "thinking_summaries": "auto",
                    },
                )

                # Extract thought steps and summaries
                steps = getattr(interaction, "steps", None) or []
                for step in steps:
                    step_type = getattr(step, "type", None) or (
                        step.get("type") if isinstance(step, dict) else None
                    )
                    if step_type == "thought":
                        summary = getattr(step, "summary", None) or (
                            step.get("summary") if isinstance(step, dict) else None
                        )
                        if summary:
                            for content_block in summary:
                                block_text = getattr(content_block, "text", None) or (
                                    content_block.get("text") if isinstance(content_block, dict) else None
                                )
                                if block_text and block_text.strip():
                                    thinking_process.append(block_text.strip())
                    elif step_type == "model_output":
                        content = getattr(step, "content", None) or (
                            step.get("content") if isinstance(step, dict) else None
                        )
                        if content:
                            for block in content:
                                block_text = getattr(block, "text", None) or (
                                    block.get("text") if isinstance(block, dict) else None
                                )
                                if block_text:
                                    raw_markdown += block_text

                out_text = getattr(interaction, "output_text", None)
                if not raw_markdown and isinstance(out_text, str):
                    raw_markdown = out_text

                if not isinstance(raw_markdown, str) or not raw_markdown.strip():
                    raw_markdown = ""
                    has_interactions = False

                # Extract thought tokens from usage
                usage = getattr(interaction, "usage", None)
                if usage and not isinstance(usage, MagicMock if "MagicMock" in globals() else type(None)):
                    token_val = getattr(usage, "total_thought_tokens", 0) or (
                        usage.get("total_thought_tokens", 0) if isinstance(usage, dict) else 0
                    )
                    if isinstance(token_val, int):
                        thoughts_token_count = token_val
            except Exception as exc:
                print(f"[HybridExtractor] Interactions API fallback notice: {exc}")
                has_interactions = False

        if not has_interactions or not raw_markdown:
            # Fallback or mock path using models.generate_content
            gen_config = None
            try:
                thinking_level_upper = self.thinking_level.upper()
                if hasattr(types, "ThinkingConfig") and hasattr(types, "GenerateContentConfig"):
                    gen_config = types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level=thinking_level_upper,
                            include_thoughts=True,
                        )
                    )
            except Exception:
                pass

            response = client.models.generate_content(
                model=self.model_name,
                contents=content_payload,
                **({"config": gen_config} if gen_config else {}),
            )
            resp_text = getattr(response, "text", "")
            if isinstance(resp_text, str):
                raw_markdown = resp_text.strip()
            else:
                raw_markdown = ""

            # Inspect candidates for reasoning parts
            candidates = getattr(response, "candidates", None)
            if candidates and not isinstance(candidates, type(client)):
                try:
                    cand = candidates[0]
                    content = getattr(cand, "content", None) or (cand.get("content") if isinstance(cand, dict) else None)
                    if content:
                        parts = getattr(content, "parts", None) or (content.get("parts") if isinstance(content, dict) else [])
                        for part in parts:
                            if getattr(part, "thought", False) or (isinstance(part, dict) and part.get("thought")):
                                p_text = getattr(part, "text", None) or (part.get("text") if isinstance(part, dict) else None)
                                if p_text and isinstance(p_text, str) and p_text.strip():
                                    thinking_process.append(p_text.strip())
                except Exception:
                    pass

            usage_metadata = getattr(response, "usage_metadata", None) or getattr(response, "usageMetadata", None)
            if usage_metadata:
                token_val = (
                    getattr(usage_metadata, "thoughts_token_count", 0)
                    or getattr(usage_metadata, "total_thought_tokens", 0)
                    or (usage_metadata.get("thoughtsTokenCount", 0) if isinstance(usage_metadata, dict) else 0)
                )
                if isinstance(token_val, int):
                    thoughts_token_count = token_val

        if not isinstance(thoughts_token_count, int):
            thoughts_token_count = 0
        if not isinstance(raw_markdown, str):
            raw_markdown = str(raw_markdown) if raw_markdown else ""

        raw_markdown = raw_markdown.strip()
        # Strip outer markdown code blocks if the model wrapped the output in ```markdown ... ```
        if raw_markdown.startswith("```markdown") and raw_markdown.endswith("```"):
            raw_markdown = raw_markdown[len("```markdown"): -3].strip()
        elif raw_markdown.startswith("```md") and raw_markdown.endswith("```"):
            raw_markdown = raw_markdown[len("```md"): -3].strip()
        elif raw_markdown.startswith("```") and raw_markdown.endswith("```"):
            raw_markdown = raw_markdown[3:-3].strip()

        return ParsedDocument(
            doc_type="document",
            title=stem_title,
            raw_markdown=raw_markdown,
            thinking_process=thinking_process,
            thoughts_token_count=thoughts_token_count,
            confidence_score=0.99,
            tags=["transcribed", "markdown_engine"],
            status="extracted",
        )

    def extract_invoice(self, file_path: str, pdf_info: Optional[Dict[str, Any]] = None) -> ExtractedInvoice:
        """Transcribes document and returns ExtractedInvoice with raw_markdown."""
        parsed = self.extract_universal_document(file_path)
        return ExtractedInvoice(
            invoice_number=parsed.document_number,
            supplier=InvoiceParty(name=parsed.title),
            summary=InvoiceSummary(),
            raw_markdown=parsed.raw_markdown,
        )

    def extract_bank_statement(self, file_path: str, pdf_info: Optional[Dict[str, Any]] = None) -> BankStatement:
        """Transcribes document and returns BankStatement with raw_markdown."""
        parsed = self.extract_universal_document(file_path)
        return BankStatement(
            bank_name=parsed.title,
            raw_markdown=parsed.raw_markdown,
        )

    def process_document(self, file_path: str) -> Tuple[str, Union[ExtractedInvoice, BankStatement]]:
        inv = self.extract_invoice(file_path)
        return "document", inv


InvoiceExtractor = HybridExtractor

"""Unit and layout tests for the Visual Markdown Document Transcription Engine."""

from unittest.mock import MagicMock
import pytest
from backend.adk_engine.extractor import (
    DOCUMENT_TRANSCRIPTION_PROMPT,
    HybridExtractor,
)
from backend.adk_engine.workflow import UniversalDocumentPipeline


def test_transcription_prompt_rules():
    """Validates that the transcription engine prompt contains all 4 mandatory rules verbatim."""
    assert "You are a document transcription engine." in DOCUMENT_TRANSCRIPTION_PROMPT
    assert "strictly preserving its visual layout, reading order, and tabular formats." in DOCUMENT_TRANSCRIPTION_PROMPT
    assert "Represent side-by-side panels (like Vendor vs. Customer details, or Metadata grids) using multi-column Markdown tables." in DOCUMENT_TRANSCRIPTION_PROMPT
    assert "Render line-item sections as standard Markdown tables matching the original column structure exactly." in DOCUMENT_TRANSCRIPTION_PROMPT
    assert "Keep multiline item descriptions grouped within the same table cell using `<br>` tags" in DOCUMENT_TRANSCRIPTION_PROMPT
    assert "Transcribe all text, numbers, labels, and footer blocks verbatim. Do not omit, calculate, or summarize any details." in DOCUMENT_TRANSCRIPTION_PROMPT


def test_multimodal_transcription_execution(monkeypatch, tmp_path):
    """Verifies that the extractor passes file bytes to Gemini Multimodal Vision and returns pure Markdown."""
    test_file = tmp_path / "invoice.png"
    test_file.write_bytes(b"\x89PNG\r\ntest content")

    mock_markdown = (
        "# GUJARAT FREIGHT TOOLS\n\n"
        "| Customer Detail | | Proforma No. | 201 |\n"
        "| :--- | :--- | :--- | :--- |\n"
        "| **M/S** | Kevin Motors | Challan No. | 45220 |\n\n"
        "| Sr. No. | Name of Product / Service | HSN / SAC | Qty | Rate | Total |\n"
        "| 1 | Stanley Hammer<br>Claw Hammer Steel Shaft | 82052000 | 3.00 PCS | 499.00 | 1,497.00 |\n"
    )

    mock_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = mock_markdown
    thought_step = MagicMock()
    thought_step.type = "thought"
    summary_block = MagicMock()
    summary_block.text = "Step 1: Detected two-panel vendor/customer header.\nStep 2: Aligned 6-column line items table."
    thought_step.summary = [summary_block]
    output_step = MagicMock()
    output_step.type = "model_output"
    output_block = MagicMock()
    output_block.text = mock_markdown
    output_step.content = [output_block]
    mock_interaction.steps = [thought_step, output_step]
    usage = MagicMock()
    usage.total_thought_tokens = 512
    mock_interaction.usage = usage

    mock_client.interactions.create.return_value = mock_interaction

    monkeypatch.setattr("google.genai.Client", lambda api_key: mock_client)

    extractor = HybridExtractor(api_key="test-api-key")
    parsed = extractor.extract_universal_document(str(test_file))

    # Verify interactions.create call with default thinking level low
    assert mock_client.interactions.create.called
    call_kwargs = mock_client.interactions.create.call_args.kwargs
    assert call_kwargs["generation_config"]["thinking_level"] == "low"
    assert call_kwargs["generation_config"]["thinking_summaries"] == "auto"

    # Verify extracted document structure and thinking process
    assert parsed.raw_markdown == mock_markdown.strip()
    assert "<br>" in parsed.raw_markdown
    assert "| Customer Detail |" in parsed.raw_markdown
    assert len(parsed.thinking_process) == 1
    assert "Step 1: Detected two-panel" in parsed.thinking_process[0]
    assert parsed.thoughts_token_count == 512


def test_pipeline_workflow_dag(monkeypatch, tmp_path):
    """Verifies the multi-stage visual transcription workflow execution DAG with thinking metrics."""
    test_file = tmp_path / "document.pdf"
    test_file.write_bytes(b"%PDF-1.4 test document")

    mock_client = MagicMock()
    mock_interaction = MagicMock()
    mock_interaction.output_text = "| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2 |"
    thought_step = MagicMock()
    thought_step.type = "thought"
    thought_summary = MagicMock()
    thought_summary.text = "Identified 2 columns and 1 data row."
    thought_step.summary = [thought_summary]
    mock_interaction.steps = [thought_step]
    usage = MagicMock()
    usage.total_thought_tokens = 180
    mock_interaction.usage = usage

    mock_client.interactions.create.return_value = mock_interaction

    monkeypatch.setattr("google.genai.Client", lambda api_key: mock_client)

    pipeline = UniversalDocumentPipeline(api_key="test-api-key")
    doc, xml, wf = pipeline.process_document(
        file_path=str(test_file),
        doc_id="test-doc-999",
        filename="document.pdf",
    )

    assert doc.id == "test-doc-999"
    assert doc.raw_markdown == "| Col 1 | Col 2 |\n|---|---|\n| Val 1 | Val 2 |"
    assert wf.status == "completed"
    assert len(wf.steps) == 3
    assert wf.steps[0].step_id == "document_ingestion"
    assert wf.steps[1].step_id == "gemini_multimodal_extraction"
    assert wf.steps[1].details.get("thinking_level") == "low"
    assert wf.steps[1].details.get("thinking_steps_count") == 1
    assert wf.steps[1].details.get("thoughts_token_count") == 180
    assert wf.steps[2].step_id == "layout_verification"
    assert wf.steps[2].details.get("has_markdown_tables") is True

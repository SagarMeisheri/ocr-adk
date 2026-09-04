"""Pytest configuration and global fixtures for OCR ADK tests.
Ensures zero live network calls to Gemini or external endpoints during testing.
"""

import pytest
from unittest.mock import MagicMock


MOCK_UNIVERSAL_LLM_TEXT = """```json
{
  "doc_type": "invoice",
  "title": "Tax Invoice - Apex Technologies",
  "document_number": "INV-2026-001",
  "date": "2026-08-15",
  "parties": {
    "issuer": {
      "name": "Apex Technologies India Pvt Ltd",
      "tax_id": "27AAPCA1234F1Z5",
      "address": "Bandra Kurla Complex, Mumbai, Maharashtra 400051"
    },
    "recipient": {
      "name": "Truly Logistics Solutions",
      "tax_id": "27BBBCB5678G1Z2",
      "address": "Hinjewadi Phase 1, Pune, Maharashtra 411057"
    }
  },
  "summary": {
    "taxable_value": 10000.0,
    "tax_amount": 1800.0,
    "cgst": 900.0,
    "sgst": 900.0,
    "igst": 0.0,
    "grand_total": 11800.0,
    "currency": "INR"
  },
  "tags": ["invoice", "tax_invoice"],
  "notes": "Automated test mock"
}
```

### Line Items Breakdown
| Description | HSN | Qty | Unit | Rate | Taxable | GST % | CGST | SGST | Total |
|-------------|-----|-----|------|------|---------|-------|------|------|-------|
| IT Consulting & Implementation | 998313 | 1 | Unit | 10000.00 | 10000.00 | 18% | 900.00 | 900.00 | 11800.00 |
"""


@pytest.fixture(autouse=True)
def mock_gemini_genai_client(monkeypatch):
    """Global autouse fixture intercepting google.genai.Client to prevent live API calls."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_UNIVERSAL_LLM_TEXT
    mock_client.models.generate_content.return_value = mock_response

    # Setup mock for Gemini Interactions API with thinking steps
    mock_interaction = MagicMock()
    mock_interaction.output_text = MOCK_UNIVERSAL_LLM_TEXT
    thought_step = MagicMock()
    thought_step.type = "thought"
    summary_block = MagicMock()
    summary_block.text = "Analyzing document visual layout, side-by-side vendor/customer blocks, and item table lines."
    thought_step.summary = [summary_block]
    output_step = MagicMock()
    output_step.type = "model_output"
    output_block = MagicMock()
    output_block.text = MOCK_UNIVERSAL_LLM_TEXT
    output_step.content = [output_block]
    mock_interaction.steps = [thought_step, output_step]

    usage_mock = MagicMock()
    usage_mock.total_thought_tokens = 320
    mock_interaction.usage = usage_mock

    mock_client.interactions.create.return_value = mock_interaction

    try:
        import google.genai as genai
        monkeypatch.setattr(genai, "Client", lambda *args, **kwargs: mock_client)
    except ImportError:
        pass

    yield mock_client

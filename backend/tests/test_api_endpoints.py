"""Integration tests for FastAPI endpoints and Tally connector communications."""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.storage import init_db

client = TestClient(app)


class TestApiEndpoints(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_health_endpoint(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["adk_version"], "2.0")

    def test_list_invoices_empty(self):
        response = client.get("/api/invoices")
        self.assertEqual(response.status_code, 200)
        self.assertIn("invoices", response.json())

    def test_tally_connector_heartbeat(self):
        # Simulate a heartbeat from tally_connector.py
        heartbeat_payload = {
            "client_id": "test-client-01",
            "tally_online": True,
            "company_name": "Apex Technologies India Pvt Ltd",
            "error": None,
        }
        hb_resp = client.post("/api/tally/connector/heartbeat", json=heartbeat_payload)
        self.assertEqual(hb_resp.status_code, 200)
        self.assertEqual(hb_resp.json()["status"], "ack")

        # Now verify /api/tally/status reflects the online connector
        status_resp = client.get("/api/tally/status")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertTrue(status_data["online"])
        self.assertEqual(status_data["company_name"], "Apex Technologies India Pvt Ltd")

    def test_batch_sync_empty_queue(self):
        response = client.post("/api/tally/invoices/batch-sync")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

    @patch("google.genai.Client")
    def test_documents_endpoints(self, mock_client_cls):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = """```json
{
  "doc_type": "invoice",
  "title": "Mock Tax Invoice",
  "document_number": "INV-TEST-001",
  "date": "2026-08-15",
  "parties": {
    "issuer": {"name": "Apex Technologies India Pvt Ltd", "tax_id": "27AAPCA1234F1Z5"},
    "recipient": {"name": "Truly Logistics Solutions", "tax_id": "27BBBCB5678G1Z2"}
  },
  "summary": {
    "taxable_value": 10000.0,
    "tax_amount": 1800.0,
    "cgst": 900.0,
    "sgst": 900.0,
    "igst": 0.0,
    "grand_total": 11800.0
  }
}
```

| Description | HSN | Qty | Unit | Rate | Taxable | GST % | CGST | SGST | Total |
|---|---|---|---|---|---|---|---|---|---|
| IT Support Services | 9983 | 1 | Nos | 10000.00 | 10000.00 | 18% | 900.00 | 900.00 | 11800.00 |
"""
        mock_client.models.generate_content.return_value = mock_response
        mock_interaction = MagicMock()
        mock_interaction.output_text = mock_response.text
        thought_step = MagicMock()
        thought_step.type = "thought"
        summary_block = MagicMock()
        summary_block.text = "Identified tabular structure and GST fields."
        thought_step.summary = [summary_block]
        mock_interaction.steps = [thought_step]
        usage = MagicMock()
        usage.total_thought_tokens = 256
        mock_interaction.usage = usage
        mock_client.interactions.create.return_value = mock_interaction
        mock_client_cls.return_value = mock_client

        # 1. List documents
        list_resp = client.get("/api/documents")
        self.assertEqual(list_resp.status_code, 200)
        self.assertIn("documents", list_resp.json())

        # 2. Upload a test document (e.g. receipt / invoice)
        test_content = b"%PDF-1.4 Mock universal document content"
        files = {"file": ("test_receipt.pdf", test_content, "application/pdf")}
        upload_resp = client.post("/api/documents/upload", files=files)
        self.assertEqual(upload_resp.status_code, 200)
        upload_data = upload_resp.json()
        self.assertGreaterEqual(upload_data["uploaded_count"], 1)
        doc_id = upload_data["documents"][0]["id"]

        # 3. Retrieve document by ID
        get_resp = client.get(f"/api/documents/{doc_id}")
        self.assertEqual(get_resp.status_code, 200)
        doc_data = get_resp.json()
        self.assertIn(
            doc_data["doc_type"],
            ["invoice", "bank_statement", "receipt", "bill", "financial_doc", "document", "other"],
        )
        self.assertIn("thinking_process", doc_data)
        self.assertIn("thoughts_token_count", doc_data)
        self.assertEqual(doc_data["thoughts_token_count"], 256)
        self.assertEqual(len(doc_data["thinking_process"]), 1)

        # 4. Delete document
        del_resp = client.delete(f"/api/documents/{doc_id}")
        self.assertEqual(del_resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()

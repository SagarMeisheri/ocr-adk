"""Integration tests for FastAPI endpoints and Tally connector communications."""

import unittest
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
            "error": None
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


if __name__ == "__main__":
    unittest.main()

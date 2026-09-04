"""Unit tests for Deterministic Human-in-the-Loop (HITL) Write Safety Gate."""

import unittest
from fastapi.testclient import TestClient
from backend.api.main import app
from backend.api.storage import init_db, HitlStore, TallyConnectorStore

client = TestClient(app)


class TestHitlGate(unittest.TestCase):
    def setUp(self):
        init_db()
        from backend.api.storage import get_db_connection

        conn = get_db_connection()
        conn.execute(
            "DELETE FROM hitl_approval_queue WHERE reference_id IN ('INV-TEST-001', 'TXN-TEST-002')"
        )
        conn.execute(
            "DELETE FROM pending_sync_queue WHERE invoice_id IN ('INV-TEST-001', 'TXN-TEST-002')"
        )
        conn.commit()
        conn.close()

    def test_deterministic_staging_blocks_autonomous_write(self):
        # 1. Stage a purchase voucher write action
        approval_id = HitlStore.stage_write_action(
            action_type="POST_PURCHASE_VOUCHER",
            reference_id="INV-TEST-001",
            description="Purchase Voucher #INV-TEST-001 from Acme Corp (₹5,900.00)",
            payload_xml="<ENVELOPE><VOUCHER>...</VOUCHER></ENVELOPE>",
            payload_json={"grand_total": 5900.0},
        )

        # 2. Verify write is in PENDING_HUMAN_APPROVAL state
        pending_list = HitlStore.list_pending_approvals()
        staged_item = next((p for p in pending_list if p["id"] == approval_id), None)
        self.assertIsNotNone(staged_item)
        self.assertEqual(staged_item["status"], "PENDING_HUMAN_APPROVAL")

        # 3. Verify it is NOT in the Tally sync queue yet (zero autonomous AI writes)
        pending_sync = TallyConnectorStore.get_pending_sync_items()
        synced_item = next(
            (s for s in pending_sync if s["invoice_id"] == "INV-TEST-001"), None
        )
        self.assertIsNone(
            synced_item, "Unapproved write action should NEVER be in sync queue!"
        )

        # 4. Explicit human approval via API
        resp = client.post(
            f"/api/hitl/{approval_id}/approve",
            json={"reviewer": "Senior Accountant CA Sharma"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "approved")

        # 5. NOW it must be released into the Tally sync queue
        pending_sync = TallyConnectorStore.get_pending_sync_items()
        released_item = next(
            (s for s in pending_sync if s["invoice_id"] == "INV-TEST-001"), None
        )
        self.assertIsNotNone(
            released_item, "Approved write action must be released to Tally sync queue!"
        )

    def test_rejection_prevents_write(self):
        approval_id = HitlStore.stage_write_action(
            action_type="POST_BANK_PAYMENT",
            reference_id="TXN-TEST-002",
            description="Payment to Unrecognized Vendor (₹50,000.00)",
            payload_xml="<ENVELOPE><VOUCHER>Payment</VOUCHER></ENVELOPE>",
        )

        resp = client.post(
            f"/api/hitl/{approval_id}/reject",
            json={"reviewer": "Audit Lead", "reason": "Duplicate transaction"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "rejected")

        # Must not be in pending approvals anymore
        pending_list = HitlStore.list_pending_approvals()
        self.assertIsNone(
            next((p for p in pending_list if p["id"] == approval_id), None)
        )

        # Must NOT be in sync queue
        pending_sync = TallyConnectorStore.get_pending_sync_items()
        self.assertIsNone(
            next((s for s in pending_sync if s["invoice_id"] == "TXN-TEST-002"), None)
        )


if __name__ == "__main__":
    unittest.main()

"""Unit tests for Virtual TallyPrime HTTP simulator."""

import unittest
from backend.tally_bridge.virtual_tally import GLOBAL_TALLY_STATE


class TestVirtualTally(unittest.TestCase):
    def test_virtual_tally_state(self):
        self.assertEqual(
            GLOBAL_TALLY_STATE.active_company, "Apex Technologies India Pvt Ltd"
        )
        self.assertEqual(GLOBAL_TALLY_STATE.company_gstin, "27AAACA1234A1Z5")
        self.assertGreater(len(GLOBAL_TALLY_STATE.ledgers), 0)
        self.assertGreater(len(GLOBAL_TALLY_STATE.stock_items), 0)

    def test_virtual_tally_add_voucher(self):
        vch_num = GLOBAL_TALLY_STATE.add_voucher(
            ref="REF-TEST-99",
            party="Test Vendor",
            amount=1000.0,
            xml_body="<ENVELOPE>...</ENVELOPE>",
        )
        self.assertTrue(vch_num.startswith("VCH-2026-"))
        self.assertEqual(GLOBAL_TALLY_STATE.vouchers[-1]["reference"], "REF-TEST-99")


if __name__ == "__main__":
    unittest.main()

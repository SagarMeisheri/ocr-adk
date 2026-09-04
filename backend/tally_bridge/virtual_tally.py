"""Virtual TallyPrime HTTP Simulator (Port 9000).

Emulates Tally Prime XML Server for macOS/Linux local development and automated testing.
"""

from __future__ import annotations
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json


class VirtualTallyState:
    """In-memory store of simulated Tally companies, masters, and imported vouchers."""

    def __init__(self):
        self.active_company = "Apex Technologies India Pvt Ltd"
        self.company_gstin = "27AAACA1234A1Z5"
        self.ledgers: List[Dict[str, Any]] = [
            {"name": "Sundry Creditors", "parent": "Current Liabilities"},
            {"name": "Purchase Local GST", "parent": "Purchase Accounts"},
            {"name": "Purchase Interstate GST", "parent": "Purchase Accounts"},
            {"name": "Input CGST 9%", "parent": "Duties & Taxes"},
            {"name": "Input SGST 9%", "parent": "Duties & Taxes"},
            {"name": "Input IGST 18%", "parent": "Duties & Taxes"},
            {"name": "Input CGST 2.5%", "parent": "Duties & Taxes"},
            {"name": "Input SGST 2.5%", "parent": "Duties & Taxes"},
            {"name": "Input IGST 5%", "parent": "Duties & Taxes"},
            {"name": "Round Off", "parent": "Indirect Expenses"},
            {
                "name": "Syscom Cloud Infrastructure Ltd",
                "parent": "Sundry Creditors",
                "gstin": "27AAACS8912K1Z9",
            },
        ]
        self.stock_items: List[Dict[str, Any]] = [
            {
                "name": "Dedicated Cloud Server Hosting",
                "units": "Month",
                "hsn": "998315",
            },
            {
                "name": "Edge AI Compute Accelerator Module",
                "units": "Nos",
                "hsn": "84715000",
            },
            {"name": "Managed SSL Certificate", "units": "Nos", "hsn": "998319"},
        ]
        self.vouchers: List[Dict[str, Any]] = []
        self.voucher_counter = 100

    def add_voucher(self, ref: str, party: str, amount: float, xml_body: str) -> str:
        self.voucher_counter += 1
        vch_num = f"VCH-2026-{self.voucher_counter:04d}"
        self.vouchers.append(
            {
                "voucher_number": vch_num,
                "reference": ref,
                "party": party,
                "amount": amount,
                "raw_xml": xml_body,
            }
        )
        return vch_num


GLOBAL_TALLY_STATE = VirtualTallyState()


class VirtualTallyRequestHandler(BaseHTTPRequestHandler):
    """Handles XML HTTP requests exactly like on-premise TallyPrime."""

    def _set_headers(self, content_type: str = "text/xml"):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers("text/plain")

    def do_GET(self):
        if self.path == "/health" or self.path == "/status":
            self._set_headers("application/json")
            status_payload = {
                "tally_status": "online",
                "mode": "virtual_simulator",
                "active_company": GLOBAL_TALLY_STATE.active_company,
                "company_gstin": GLOBAL_TALLY_STATE.company_gstin,
                "ledger_count": len(GLOBAL_TALLY_STATE.ledgers),
                "stock_item_count": len(GLOBAL_TALLY_STATE.stock_items),
                "imported_vouchers_count": len(GLOBAL_TALLY_STATE.vouchers),
                "vouchers": GLOBAL_TALLY_STATE.vouchers[-5:],  # last 5 vouchers
            }
            self.wfile.write(json.dumps(status_payload).encode("utf-8"))
        else:
            self._set_headers("text/html")
            self.wfile.write(b"<h3>Virtual TallyPrime Server (Port 9000) Active</h3>")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8", errors="replace")

        # 1. Company List Query
        if "List of Companies" in post_data:
            response_xml = f"""<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <STATUS>1</STATUS>
  </HEADER>
  <BODY>
    <DATA>
      <COLLECTION>
        <COMPANY>
          <NAME>{GLOBAL_TALLY_STATE.active_company}</NAME>
          <COMPANYNUMBER>10001</COMPANYNUMBER>
          <STARTINGFROM>20260401</STARTINGFROM>
        </COMPANY>
      </COLLECTION>
    </DATA>
  </BODY>
</ENVELOPE>"""
            self._set_headers("text/xml")
            self.wfile.write(response_xml.encode("utf-8"))
            return

        # 2. Ledgers Query
        if "List of Ledgers" in post_data:
            ledger_tags = "\n".join(
                f"<LEDGER><NAME>{l['name']}</NAME><PARENT>{l.get('parent', '')}</PARENT></LEDGER>"
                for l in GLOBAL_TALLY_STATE.ledgers
            )
            response_xml = f"""<ENVELOPE>
  <HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER>
  <BODY><DATA><COLLECTION>{ledger_tags}</COLLECTION></DATA></BODY>
</ENVELOPE>"""
            self._set_headers("text/xml")
            self.wfile.write(response_xml.encode("utf-8"))
            return

        # 3. Stock Items Query
        if "List of Stock Items" in post_data:
            item_tags = "\n".join(
                f"<STOCKITEM><NAME>{i['name']}</NAME><BASEUNITS>{i.get('units', 'Nos')}</BASEUNITS></STOCKITEM>"
                for i in GLOBAL_TALLY_STATE.stock_items
            )
            response_xml = f"""<ENVELOPE>
  <HEADER><VERSION>1</VERSION><STATUS>1</STATUS></HEADER>
  <BODY><DATA><COLLECTION>{item_tags}</COLLECTION></DATA></BODY>
</ENVELOPE>"""
            self._set_headers("text/xml")
            self.wfile.write(response_xml.encode("utf-8"))
            return

        # 4. Master Creation: Ledger
        if "<LEDGER" in post_data and 'ACTION="Create"' in post_data:
            name_match = re.search(r"<NAME>(.*?)</NAME>", post_data)
            ledger_name = name_match.group(1) if name_match else "New Ledger"
            GLOBAL_TALLY_STATE.ledgers.append(
                {"name": ledger_name, "parent": "Sundry Creditors"}
            )
            response_xml = """<RESPONSE>
  <CREATED>1</CREATED>
  <ALTERED>0</ALTERED>
  <ERRORS>0</ERRORS>
</RESPONSE>"""
            self._set_headers("text/xml")
            self.wfile.write(response_xml.encode("utf-8"))
            return

        # 5. Master Creation: Stock Item
        if "<STOCKITEM" in post_data and 'ACTION="Create"' in post_data:
            name_match = re.search(r"<NAME>(.*?)</NAME>", post_data)
            item_name = name_match.group(1) if name_match else "New Item"
            GLOBAL_TALLY_STATE.stock_items.append({"name": item_name, "units": "Nos"})
            response_xml = """<RESPONSE>
  <CREATED>1</CREATED>
  <ALTERED>0</ALTERED>
  <ERRORS>0</ERRORS>
</RESPONSE>"""
            self._set_headers("text/xml")
            self.wfile.write(response_xml.encode("utf-8"))
            return

        # 6. Voucher Import: Purchase Voucher (F9)
        if 'VCHTYPE="Purchase"' in post_data or "<VOUCHER" in post_data:
            ref_match = re.search(r"<REFERENCE>(.*?)</REFERENCE>", post_data)
            ref_str = ref_match.group(1) if ref_match else "UNKNOWN_REF"

            party_match = re.search(
                r"<PARTYLEDGERNAME>(.*?)</PARTYLEDGERNAME>", post_data
            )
            party_str = party_match.group(1) if party_match else "Vendor"

            vch_num = GLOBAL_TALLY_STATE.add_voucher(ref_str, party_str, 0.0, post_data)

            response_xml = f"""<RESPONSE>
  <CREATED>1</CREATED>
  <ALTERED>0</ALTERED>
  <ERRORS>0</ERRORS>
  <VOUCHERNUMBER>{vch_num}</VOUCHERNUMBER>
  <LASTVCHID>{GLOBAL_TALLY_STATE.voucher_counter}</LASTVCHID>
</RESPONSE>"""
            self._set_headers("text/xml")
            self.wfile.write(response_xml.encode("utf-8"))
            return

        # Default fallback response
        response_xml = """<RESPONSE><CREATED>1</CREATED><ALTERED>0</ALTERED><ERRORS>0</ERRORS></RESPONSE>"""
        self._set_headers("text/xml")
        self.wfile.write(response_xml.encode("utf-8"))

    def log_message(self, format, *args):
        # Keep terminal clean, suppress default HTTP logging
        pass


def run_virtual_tally(port: int = 9000, host: str = "127.0.0.1") -> HTTPServer:
    """Starts the virtual Tally HTTP server."""
    server = HTTPServer((host, port), VirtualTallyRequestHandler)
    return server


def start_virtual_tally_background(
    port: int = 9000, host: str = "127.0.0.1"
) -> threading.Thread:
    """Runs virtual Tally in a daemon thread."""
    server = run_virtual_tally(port, host)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    print("Starting Virtual TallyPrime HTTP server on port 9000...")
    server = run_virtual_tally(9000)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\nVirtual Tally stopped.")

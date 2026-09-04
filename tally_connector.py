"""TrulyTally Local TallyPrime Sync Connector Daemon.

Run this lightweight script on the machine running Tally Prime (Windows/Mac/Linux).
It securely connects to the TrulyTally Web App via outbound connection,
receives approved vouchers, posts them directly to Tally on Port 9000,
and reports sync status back in real-time.

Usage:
    python tally_connector.py --server http://localhost:8000 --tally-port 9000
"""

from __future__ import annotations
import sys
import time
import json
import argparse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime


def query_local_tally(xml_payload: str, tally_host: str = "127.0.0.1", tally_port: int = 9000) -> tuple[bool, str]:
    """Posts an XML payload to the local Tally Prime server on Port 9000."""
    url = f"http://{tally_host}:{tally_port}"
    req = urllib.request.Request(
        url,
        data=xml_payload.encode("utf-8"),
        headers={"Content-Type": "text/xml;charset=utf-8"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            return True, body
    except urllib.error.URLError as e:
        return False, f"Cannot reach TallyPrime at {url}: {e.reason}"
    except Exception as e:
        return False, f"Tally request failed: {str(e)}"


def get_tally_company_info(tally_host: str = "127.0.0.1", tally_port: int = 9000) -> tuple[bool, dict]:
    """Checks Tally connection and gets active company name."""
    req_xml = """<ENVELOPE>
  <HEADER>
    <VERSION>1</VERSION>
    <TALLYREQUEST>Export</TALLYREQUEST>
    <TYPE>Data</TYPE>
    <ID>List of Companies</ID>
  </HEADER>
  <BODY>
    <DESC>
      <STATICVARIABLES>
        <SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT>
      </STATICVARIABLES>
    </DESC>
  </BODY>
</ENVELOPE>"""
    success, resp = query_local_tally(req_xml, tally_host, tally_port)
    if not success:
        return False, {"error": resp}

    company_name = "Connected (No company loaded)"
    try:
        # Extract company name from XML response
        import re
        match = re.search(r'<NAME>(.*?)</NAME>', resp)
        if match:
            company_name = match.group(1).strip()
    except Exception:
        pass

    return True, {
        "company_name": company_name,
        "raw_response": resp[:200]
    }


def send_backend_heartbeat(server_url: str, client_id: str, tally_status: dict, api_key: str = ""):
    """Notifies the web backend about TallyPrime local availability and active company."""
    url = f"{server_url.rstrip('/')}/api/tally/connector/heartbeat"
    payload = {
        "client_id": client_id,
        "timestamp": datetime.utcnow().isoformat(),
        "tally_online": tally_status.get("online", False),
        "company_name": tally_status.get("company_name", "Unknown"),
        "error": tally_status.get("error"),
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-API-Key": api_key,
        },
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        return {"status": "error", "message": str(e)}


def poll_and_sync_vouchers(server_url: str, client_id: str, tally_host: str, tally_port: int, api_key: str = ""):
    """Polls the backend for pending approved vouchers and posts them to local Tally."""
    url = f"{server_url.rstrip('/')}/api/tally/connector/pending-sync"
    req = urllib.request.Request(
        url,
        headers={"X-API-Key": api_key, "X-Client-ID": client_id},
        method="GET"
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return

    pending_items = data.get("pending_vouchers", [])
    for item in pending_items:
        invoice_id = item["invoice_id"]
        tally_xml = item["tally_xml"]
        auto_masters = item.get("auto_masters_xml", [])

        print(f"\n[Sync] Received invoice {invoice_id} ({item.get('invoice_number', 'N/A')}) for Tally Sync...")

        # 1. Post Auto-create Master XMLs if any
        for master_xml in auto_masters:
            success, m_resp = query_local_tally(master_xml, tally_host, tally_port)
            print(f"  -> Master provisioning result: {'Success' if success else 'Warning'}")

        # 2. Post Voucher XML
        vch_success, vch_resp = query_local_tally(tally_xml, tally_host, tally_port)

        # Parse voucher number or error
        voucher_number = None
        error_msg = None
        if vch_success:
            import re
            num_match = re.search(r'<VOUCHERNUMBER>(.*?)</VOUCHERNUMBER>', vch_resp)
            if num_match:
                voucher_number = num_match.group(1)
            elif "<ERRORS>0</ERRORS>" in vch_resp or "<CREATED>1</CREATED>" in vch_resp:
                voucher_number = f"CREATED-{datetime.now().strftime('%H%M%S')}"
            else:
                error_match = re.search(r'<LINEERROR>(.*?)</LINEERROR>', vch_resp)
                error_msg = error_match.group(1) if error_match else "Tally reported voucher import errors"
        else:
            error_msg = vch_resp

        # 3. Report result back to backend
        report_url = f"{server_url.rstrip('/')}/api/tally/connector/report-sync"
        report_payload = {
            "invoice_id": invoice_id,
            "success": vch_success and not error_msg,
            "voucher_number": voucher_number,
            "tally_response": vch_resp[:1000] if vch_success else None,
            "error_message": error_msg
        }
        report_req = urllib.request.Request(
            report_url,
            data=json.dumps(report_payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "X-API-Key": api_key},
            method="POST"
        )
        try:
            with urllib.request.urlopen(report_req, timeout=5) as r:
                pass
            status_text = f"SUCCESS (Voucher: {voucher_number})" if (vch_success and not error_msg) else f"FAILED ({error_msg})"
            print(f"  -> Sync Completed: {status_text}")
        except Exception as e:
            print(f"  -> Failed to report sync result to backend: {e}")


def main():
    parser = argparse.ArgumentParser(description="TrulyTally Local Sync Daemon for Tally Prime")
    parser.add_argument("--server", default="http://localhost:8000", help="TrulyTally Web App URL")
    parser.add_argument("--tally-host", default="127.0.0.1", help="Tally Prime IP address (default: 127.0.0.1)")
    parser.add_argument("--tally-port", type=int, default=9000, help="Tally Prime Port (default: 9000)")
    parser.add_argument("--api-key", default="default-secret-key", help="Connector Workspace API Key")
    parser.add_argument("--poll-interval", type=float, default=15.0, help="Polling interval in seconds")

    args = parser.parse_args()

    client_id = f"connector-win-{int(time.time())}"
    print("=" * 60)
    print(" TrulyTally AI -> TallyPrime Local Sync Connector")
    print("=" * 60)
    print(f"Target Server:   {args.server}")
    print(f"Tally Address:   http://{args.tally_host}:{args.tally_port}")
    print(f"Client ID:       {client_id}")
    print(f"Status:          Starting polling loop...\n")

    while True:
        try:
            # 1. Check local Tally status
            is_online, info = get_tally_company_info(args.tally_host, args.tally_port)
            status_dict = {
                "online": is_online,
                "company_name": info.get("company_name", "N/A"),
                "error": info.get("error")
            }

            # 2. Send heartbeat to cloud/web platform
            send_backend_heartbeat(args.server, client_id, status_dict, args.api_key)

            # 3. If Tally is online, check and sync pending vouchers
            if is_online:
                poll_and_sync_vouchers(args.server, client_id, args.tally_host, args.tally_port, args.api_key)

        except KeyboardInterrupt:
            print("\n[Shutting down] Tally connector terminated.")
            sys.exit(0)
        except Exception as e:
            # Continue resiliently
            pass

        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()

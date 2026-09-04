"""TrulyTally AI - One-Click Master Launcher.

Starts:
1. Virtual Tally Simulator on Port 9000 (toggleable)
2. FastAPI Backend on Port 8000
3. Local Tally Connector Daemon linking Port 9000 to the backend
"""

import sys
import os
import time
import argparse
import subprocess
import threading
import logging
from pathlib import Path

# Load environment variables from .env if present
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


class HeartbeatLogFilter(logging.Filter):
    """Filters repetitive background heartbeat and polling pings from console."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        noisy_endpoints = [
            "/api/tally/connector/heartbeat",
            "/api/tally/status",
            "/api/hitl/pending",
            "/api/tally-status",
        ]
        return not any(ep in message for ep in noisy_endpoints)


def run_backend(host="127.0.0.1", port=8000):
    """Runs FastAPI backend using uvicorn with filtered access logging."""
    import uvicorn
    from backend.api.main import app

    # Silence repetitive polling pings so real document extraction logs stand out
    logging.getLogger("uvicorn.access").addFilter(HeartbeatLogFilter())

    print(
        f"[Backend] Starting TrulyTally AI Document Server on http://{host}:{port}..."
    )
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_virtual_tally(port=9000):
    """Runs Virtual TallyPrime HTTP simulator."""
    from backend.tally_bridge.virtual_tally import run_virtual_tally as start_tally

    print(
        f"[Virtual Tally] Emulating TallyPrime XML Server on http://127.0.0.1:{port}..."
    )
    server = start_tally(port=port)
    try:
        server.serve_forever()
    except Exception:
        server.server_close()


def run_connector(server_url="http://localhost:8000", tally_port=9000):
    """Runs local sync connector daemon with relaxed polling interval."""
    time.sleep(2.0)  # Wait for backend and tally to initialize
    print(
        f"[Sync Connector] Connecting outbound to {server_url} and local Tally on port {tally_port}..."
    )
    subprocess.run(
        [
            sys.executable,
            "tally_connector.py",
            "--server",
            server_url,
            "--tally-port",
            str(tally_port),
            "--poll-interval",
            "15.0",
        ]
    )


def main():
    parser = argparse.ArgumentParser(
        description="TrulyTally AI Intelligent Document Studio"
    )
    parser.add_argument(
        "--backend-port", type=int, default=8000, help="Backend port (default: 8000)"
    )
    parser.add_argument(
        "--with-tally",
        action="store_true",
        help="Start Virtual Tally simulator and local sync connector daemon",
    )
    parser.add_argument(
        "--tally-port",
        type=int,
        default=9000,
        help="Tally port if --with-tally is enabled (default: 9000)",
    )

    args = parser.parse_args()

    print("=" * 65)
    print(" TrulyTally AI &bull; Intelligent Document Processing Studio")
    print(" Universal Extraction for Invoices, Bank Statements, Receipts & Bills")
    print(" Powered by Google ADK 2.0 & Gemini 3.8 Flash")
    if not args.with_tally:
        print(" Mode: Standalone (Tally sync optional via XML export or --with-tally)")
    else:
        print(" Mode: Live Tally Connector enabled")
    print("=" * 65)

    threads = []

    # Start Tally components only if explicitly requested
    if args.with_tally:
        tally_thread = threading.Thread(
            target=run_virtual_tally, args=(args.tally_port,), daemon=True
        )
        tally_thread.start()
        threads.append(tally_thread)

        connector_thread = threading.Thread(
            target=run_connector,
            args=(f"http://localhost:{args.backend_port}", args.tally_port),
            daemon=True,
        )
        connector_thread.start()
        threads.append(connector_thread)

    # Start Backend in Main Thread
    try:
        run_backend(port=args.backend_port)
    except KeyboardInterrupt:
        print("\nShutting down TrulyTally AI...")
        sys.exit(0)


if __name__ == "__main__":
    main()

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
from pathlib import Path


def run_backend(host="127.0.0.1", port=8000):
    """Runs FastAPI backend using uvicorn."""
    import uvicorn
    from backend.api.main import app
    print(f"[Backend] Starting FastAPI on http://{host}:{port}...")
    uvicorn.run(app, host=host, port=port, log_level="info")


def run_virtual_tally(port=9000):
    """Runs Virtual TallyPrime HTTP simulator."""
    from backend.tally_bridge.virtual_tally import run_virtual_tally as start_tally
    print(f"[Virtual Tally] Emulating TallyPrime XML Server on http://127.0.0.1:{port}...")
    server = start_tally(port=port)
    try:
        server.serve_forever()
    except Exception:
        server.server_close()


def run_connector(server_url="http://localhost:8000", tally_port=9000):
    """Runs local sync connector daemon."""
    time.sleep(1.5)  # Wait for backend and tally to initialize
    print(f"[Sync Connector] Connecting outbound to {server_url} and local Tally on port {tally_port}...")
    subprocess.run([
        sys.executable,
        "tally_connector.py",
        "--server", server_url,
        "--tally-port", str(tally_port)
    ])


def main():
    parser = argparse.ArgumentParser(description="TrulyTally AI Launcher")
    parser.add_argument("--backend-port", type=int, default=8000, help="Backend port (default: 8000)")
    parser.add_argument("--tally-port", type=int, default=9000, help="Tally port (default: 9000)")
    parser.add_argument("--no-virtual-tally", action="store_true", help="Do not start Virtual Tally (use real TallyPrime)")
    parser.add_argument("--no-connector", action="store_true", help="Do not start local connector daemon")

    args = parser.parse_args()

    print("=" * 65)
    print(" TrulyTally AI &bull; Indian GST Invoice OCR & TallyPrime Sync")
    print(" Powered by Google ADK 2.0 & Gemini 3.8 Flash")
    print("=" * 65)

    threads = []

    # 1. Start Virtual Tally if requested
    if not args.no_virtual_tally:
        tally_thread = threading.Thread(target=run_virtual_tally, args=(args.tally_port,), daemon=True)
        tally_thread.start()
        threads.append(tally_thread)

    # 2. Start Local Connector Daemon
    if not args.no_connector:
        connector_thread = threading.Thread(
            target=run_connector,
            args=(f"http://localhost:{args.backend_port}", args.tally_port),
            daemon=True
        )
        connector_thread.start()
        threads.append(connector_thread)

    # 3. Start Backend in Main Thread
    try:
        run_backend(port=args.backend_port)
    except KeyboardInterrupt:
        print("\nShutting down TrulyTally AI...")
        sys.exit(0)


if __name__ == "__main__":
    main()

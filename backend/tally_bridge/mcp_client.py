"""Google ADK 2.0 McpToolset integration for dhananjay1405/tally-mcp-server v7.5."""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any

# Complete list of 19 tools exposed by dhananjay1405/tally-mcp-server
ALL_TALLY_MCP_TOOLS = [
    # Metadata and Schema
    "metadata-collection",
    "query-option-values",
    "metadata-fields",
    # Live Reporting & Data Query
    "query-collection",
    "query-database",
    "list-master",
    "chart-of-accounts",
    "trial-balance",
    "profit-loss",
    "balance-sheet",
    "stock-summary",
    "ledger-balance",
    "stock-item-balance",
    "bills-outstanding",
    "ledger-account",
    "stock-item-account",
    # Context Management
    "set-company",
    "set-period",
    # Write Operations (Enforced with Deterministic HITL Gate)
    "ledger-create-update",
    "delete-master",
]


def get_tally_mcp_toolset(
    tally_host: str = "127.0.0.1",
    tally_port: int = 9000,
    block_write: bool = True,
    mcp_script_path: Optional[str] = None,
) -> Optional[Any]:
    """Creates Google ADK 2.0 McpToolset instance exposing all 19 TallyPrime MCP tools.

    By default, block_write=True ensures that write operations (ledger-create-update, delete-master)
    cannot be autonomously executed by AI, enforcing our deterministic HITL safety gate.
    """
    try:
        from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams
        from mcp import StdioServerParameters

        node_bin = shutil.which("node") or "node"

        if not mcp_script_path:
            bundled = Path(__file__).resolve().parent.parent.parent / "mcp_server" / "tally_mcp" / "dist" / "index.mjs"
            if bundled.exists():
                mcp_script_path = str(bundled)
            else:
                mcp_script_path = "mcp_server/tally_mcp/dist/index.mjs"

        tool_filter = ALL_TALLY_MCP_TOOLS
        if block_write:
            # Strictly remove write tools from AI autonomous execution
            tool_filter = [t for t in ALL_TALLY_MCP_TOOLS if t not in ("ledger-create-update", "delete-master")]

        toolset = McpToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command=node_bin,
                    args=[mcp_script_path],
                    env={
                        "TALLY_HOST": tally_host,
                        "TALLY_PORT": str(tally_port),
                        "BLOCK_WRITE": "1" if block_write else "0",
                        "PATH": os.environ.get("PATH", ""),
                    }
                ),
                timeout=15,
            ),
            tool_filter=tool_filter,
        )
        return toolset

    except Exception as e:
        print(f"[Warning] Failed to initialize Tally McpToolset: {e}")
        return None

"""Google ADK 2.0 Multi-Stage Graph Workflow for Invoice Processing.

Exposes the parallel graph workflow with Ingestion -> Extraction -> Parallel (Math + Tally) -> Join -> Triage -> Revision Loop.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.adk_engine.workflow import adk_workflow_graph

root_agent = adk_workflow_graph

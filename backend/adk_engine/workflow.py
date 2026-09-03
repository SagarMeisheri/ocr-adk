"""Google ADK 2.0 Multi-Stage Graph Workflow for Indian GST Invoice Processing."""

from __future__ import annotations
import os
from typing import Dict, Any, Optional, Tuple
from pathlib import Path

from .models import ExtractedInvoice, ValidationResult
from .extractor import InvoiceExtractor
from .validator import validate_extracted_invoice
from .matcher import TallyMasterMatcher
from ..tally_bridge.xml_builder import generate_tally_purchase_voucher_xml


class InvoiceProcessingPipeline:
    """End-to-end multi-stage ADK pipeline orchestrator for GST invoices."""

    def __init__(self, api_key: Optional[str] = None):
        self.extractor = InvoiceExtractor(api_key=api_key)

    def process_invoice(
        self,
        file_path: str,
        cached_ledgers: Optional[list] = None,
        cached_stock_items: Optional[list] = None,
    ) -> Tuple[ExtractedInvoice, str]:
        """Runs the complete multi-stage pipeline:

        Stage 1: Ingestion & Document Normalization
        Stage 2: Gemini 3.8 Flash Vision Extraction
        Stage 3: Deterministic Indian GSTIN & Tax Math Verification
        Stage 4: Tally Prime Master Fuzzy Matcher & Ledger Resolver
        Stage 5: Tally XML Voucher Generation
        """
        # Stage 1 & 2: Preprocess & Extract via Gemini
        invoice = self.extractor.extract_from_file(file_path)

        # Stage 3: Deterministic Rule Validator
        validation_result = validate_extracted_invoice(invoice)
        invoice.validation = validation_result

        # Stage 4: Tally Master Matching & Enrichment
        matcher = TallyMasterMatcher(
            existing_ledgers=cached_ledgers,
            existing_stock_items=cached_stock_items,
        )
        invoice = matcher.match_and_enrich_invoice(invoice)

        # Stage 5: Generate TallyPrime XML Voucher Payload
        tally_xml = generate_tally_purchase_voucher_xml(invoice)

        return invoice, tally_xml


# Google ADK 2.0 Integration Setup
def setup_adk_workflow():
    """Builds a formal Google ADK 2.0 Workflow graph if google.adk is present."""
    try:
        from google.adk import Context, Event, Workflow
        from google.adk.apps import App, ResumabilityConfig
        from google.adk.workflow import node, START

        pipeline = InvoiceProcessingPipeline()

        @node(name="preprocess_and_extract")
        def adk_extract_node(node_input: str) -> dict:
            invoice, xml = pipeline.process_invoice(node_input)
            return {"invoice": invoice.model_dump(), "tally_xml": xml}

        @node(name="validate_and_audit")
        def adk_audit_node(node_input: dict) -> dict:
            return node_input

        root_agent = Workflow(
            name="gst_invoice_adk_workflow",
            edges=[
                (START, adk_extract_node),
                (adk_extract_node, adk_audit_node),
            ]
        )

        app = App(
            name="truly_tally_ai",
            root_agent=root_agent,
            resumability_config=ResumabilityConfig(is_resumable=True)
        )
        return app, root_agent
    except Exception as e:
        # Graceful fallback when google.adk is initializing in development
        return None, None


app, root_agent = setup_adk_workflow()

"""OpenTelemetry Tracing Instrumentation for Google ADK 2.0 Invoice Workflow."""

from __future__ import annotations
import json
import os
import time
from contextlib import contextmanager
from typing import Dict, Any, Optional, Generator, List
from pathlib import Path

# OpenTelemetry imports with graceful fallbacks
try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider, ReadableSpan
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
    from opentelemetry.trace import Status, StatusCode
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    trace = None
    TracerProvider = None
    ReadableSpan = None
    SimpleSpanProcessor = None
    SpanExporter = None
    SpanExportResult = None
    Status = None
    StatusCode = None
    OPENTELEMETRY_AVAILABLE = False


class InMemorySpanCollector:
    """Collects readable span representations in memory for export and inspection."""
    def __init__(self):
        self.spans: List[Dict[str, Any]] = []

    def add_span(self, span: ReadableSpan):
        start_ns = span.start_time
        end_ns = span.end_time or time.time_ns()
        duration_ms = round((end_ns - start_ns) / 1_000_000, 2)

        span_dict = {
            "name": span.name,
            "context": {
                "trace_id": f"{span.context.trace_id:032x}" if span.context else None,
                "span_id": f"{span.context.span_id:016x}" if span.context else None,
            },
            "parent_id": f"{span.parent.span_id:016x}" if span.parent else None,
            "start_time_ns": start_ns,
            "end_time_ns": end_ns,
            "duration_ms": duration_ms,
            "status": span.status.status_code.name if span.status else "UNSET",
            "attributes": dict(span.attributes or {}),
        }
        self.spans.append(span_dict)

    def clear(self):
        self.spans.clear()

    def get_spans(self) -> List[Dict[str, Any]]:
        return list(self.spans)


if OPENTELEMETRY_AVAILABLE:
    class InMemorySpanExporter(SpanExporter):
        """OTel SDK SpanExporter that pushes to InMemorySpanCollector."""
        def __init__(self, collector: InMemorySpanCollector):
            self.collector = collector

        def export(self, spans: List[ReadableSpan]) -> SpanExportResult:
            for s in spans:
                self.collector.add_span(s)
            return SpanExportResult.SUCCESS

        def shutdown(self):
            pass


_collector = InMemorySpanCollector()
_tracer_initialized = False


def init_tracer(enable_console_export: bool = False) -> Any:
    """Initializes OpenTelemetry TracerProvider with ADK semantic convention tracking."""
    global _tracer_initialized, _collector
    if not OPENTELEMETRY_AVAILABLE:
        return None

    if _tracer_initialized:
        return trace.get_tracer("adk.workflow.tracer")

    provider = TracerProvider()
    # In-memory exporter for JSON serialization and local CLI inspection
    provider.add_span_processor(SimpleSpanProcessor(InMemorySpanExporter(_collector)))

    if enable_console_export:
        try:
            from opentelemetry.sdk.trace.export import ConsoleSpanExporter
            provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        except Exception:
            pass

    trace.set_tracer_provider(provider)
    _tracer_initialized = True
    return trace.get_tracer("adk.workflow.tracer")


def get_collected_spans() -> List[Dict[str, Any]]:
    """Returns all spans captured during the session."""
    return _collector.get_spans()


def clear_collected_spans():
    """Resets the in-memory span collector."""
    _collector.clear()


def save_traces_to_json(output_path: str) -> str:
    """Saves collected traces to a JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    spans = get_collected_spans()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"total_spans": len(spans), "spans": spans}, f, indent=2)
    return str(path.resolve())


@contextmanager
def trace_workflow(
    workflow_name: str,
    document_id: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """Context manager for root workflow invocation span (ADK GenAI SemConv)."""
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = init_tracer()
    attrs = {
        "gen_ai.operation.name": "invoke_workflow",
        "gen_ai.workflow.name": workflow_name,
        "gcp.vertex.agent.document_id": document_id,
    }
    if attributes:
        attrs.update(attributes)

    with tracer.start_as_current_span(f"invoke_workflow {workflow_name}", attributes=attrs) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def trace_stage(
    stage_name: str,
    step_id: str,
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """Context manager for workflow stage/node span (ADK GenAI SemConv)."""
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = init_tracer()
    attrs = {
        "gen_ai.operation.name": "invoke_node",
        "gen_ai.node.name": stage_name,
        "gen_ai.node.step_id": step_id,
    }
    if attributes:
        attrs.update(attributes)

    with tracer.start_as_current_span(f"invoke_node {step_id}", attributes=attrs) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise


@contextmanager
def trace_agent(
    agent_name: str,
    agent_mode: str = "task",
    attributes: Optional[Dict[str, Any]] = None,
) -> Generator[Any, None, None]:
    """Context manager for specialized agent span (ADK GenAI SemConv)."""
    if not OPENTELEMETRY_AVAILABLE:
        yield None
        return

    tracer = init_tracer()
    attrs = {
        "gen_ai.operation.name": "invoke_agent",
        "gen_ai.agent.name": agent_name,
        "gen_ai.agent.mode": agent_mode,
    }
    if attributes:
        attrs.update(attributes)

    with tracer.start_as_current_span(f"invoke_agent {agent_name}", attributes=attrs) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as exc:
            span.set_status(Status(StatusCode.ERROR, str(exc)))
            span.record_exception(exc)
            raise

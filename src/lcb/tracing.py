"""Optional local tracing with Arize Phoenix (OpenInference instrumentation of the Anthropic SDK).
Enable with LCB_PHOENIX=1 and a Phoenix server on localhost:6006 (`phoenix serve`). Nothing leaves the machine. The JSONL files in runs/ stay the source of truth."""
import os


def setup(project: str = "lcb"):
    if os.environ.get("LCB_PHOENIX") != "1": return False
    from phoenix.otel import register
    from openinference.instrumentation.anthropic import AnthropicInstrumentor
    provider = register(project_name=project, endpoint="http://localhost:6006/v1/traces", batch=False)
    AnthropicInstrumentor().instrument(tracer_provider=provider); return True

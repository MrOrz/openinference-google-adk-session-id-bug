"""
PoC: GoogleADKInstrumentor stamps wrong session.id on sub-agent spans.

Expected: all spans in the trace share session.id = SESSION_ID
Actual:   sub-agent invocation and agent_run spans get a different UUID
"""

import asyncio

from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from openinference.instrumentation.google_adk import GoogleADKInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from app.agent import root_agent

APP_NAME = "poc-app"
USER_ID = "test-user"
SESSION_ID = "known-session-id-abc123"


def setup_otel():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    from opentelemetry import trace

    trace.set_tracer_provider(provider)
    GoogleADKInstrumentor().instrument()
    return exporter


async def run():
    exporter = setup_otel()

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
    )

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=types.Content(role="user", parts=[types.Part(text="ping")]),
    ):
        print(f"  → Agent event: {event}")
        print(f"\n{'─' * 70}")

    spans = exporter.get_finished_spans()
    print(f"\n{'─' * 70}")
    print(f"{'SPAN NAME':<40} {'session.id':}")
    print(f"{'─' * 70}")

    bugs = []
    for span in spans:
        attrs = dict(span.attributes or {})
        sid = attrs.get("session.id", "(none)")
        wrong = isinstance(sid, str) and sid != SESSION_ID and sid != "(none)"
        flag = "  ✗ BUG" if wrong else ""
        print(f"{span.name:<40} {sid}{flag}")
        if wrong:
            bugs.append(span.name)

    print(f"{'─' * 70}")
    if bugs:
        print(f"\n❌ BUG CONFIRMED: {len(bugs)} span(s) have wrong session.id:")
        for name in bugs:
            print(f"   - {name}")
        print(f"\nExpected: session.id = {SESSION_ID}")
        print(
            "Root cause: _RunnerRunAsync stamps session.id = ADK-internal sub-session UUID"
        )
        print("            overriding the ambient OTel session from the parent runner.")
    else:
        print("\n✅ All spans have correct session.id — bug not reproduced.")


if __name__ == "__main__":
    asyncio.run(run())

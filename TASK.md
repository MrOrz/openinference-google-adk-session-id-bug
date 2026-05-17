# PoC Plan: Demonstrate GoogleADKInstrumentor session.id Bug

## Goal

Create a minimal standalone project that proves `openinference-instrumentation-google-adk`
stamps sub-agent spans with the wrong `session.id` when sub-agents are invoked via `AgentTool`.
The output will be used to file a bug report on Arize-ai/openinference.

---

## Step 1 — Scaffold project with agents-cli

```bash
agents-cli create poc-session-bug --adk --prototype -k --yes
cd poc-session-bug
```

This generates a minimal ADK project (no CI/CD, no Terraform) using Google AI Studio API key.
After scaffolding, inspect what was created:
- `pyproject.toml` — add two dependencies (see Step 2)
- `poc_session_bug/agent.py` — replace with the two-agent structure (see Step 3)
- `.env` — fill in `GOOGLE_API_KEY`

---

## Step 2 — Add PoC dependencies

Add to `pyproject.toml` under `dependencies`:

```toml
"openinference-instrumentation-google-adk",
"opentelemetry-sdk",
```

Then install:

```bash
agents-cli install
# or: uv sync
```

---

## Step 3 — Create two-agent structure

Replace (or create) `poc_session_bug/agent.py`:

```python
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

sub_agent = LlmAgent(
    name="sub_agent",
    model="gemini-2.0-flash",
    instruction="You are a simple assistant. Reply with exactly: pong",
)

root_agent = LlmAgent(
    name="root_agent",
    model="gemini-2.0-flash",
    instruction="When the user says anything, call the sub_agent tool and return its response.",
    tools=[AgentTool(agent=sub_agent)],
)
```

---

## Step 4 — Write the PoC script

Create `poc.py` at the project root:

```python
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

from poc_session_bug.agent import root_agent

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

    async for _ in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=types.Content(
            role="user", parts=[types.Part(text="ping")]
        ),
    ):
        pass

    spans = exporter.get_finished_spans()
    print(f"\n{'─'*70}")
    print(f"{'SPAN NAME':<40} {'session.id':}")
    print(f"{'─'*70}")

    bugs = []
    for span in spans:
        attrs = dict(span.attributes or {})
        sid = attrs.get("session.id", "(none)")
        wrong = isinstance(sid, str) and sid != SESSION_ID and sid != "(none)"
        flag = "  ✗ BUG" if wrong else ""
        print(f"{span.name:<40} {sid}{flag}")
        if wrong:
            bugs.append(span.name)

    print(f"{'─'*70}")
    if bugs:
        print(f"\n❌ BUG CONFIRMED: {len(bugs)} span(s) have wrong session.id:")
        for name in bugs:
            print(f"   - {name}")
        print(f"\nExpected: session.id = {SESSION_ID}")
        print("Root cause: _RunnerRunAsync stamps session.id = ADK-internal sub-session UUID")
        print("            overriding the ambient OTel session from the parent runner.")
    else:
        print("\n✅ All spans have correct session.id — bug not reproduced.")


if __name__ == "__main__":
    asyncio.run(run())
```

---

## Step 5 — Run the PoC

```bash
python poc.py
```

### Expected output (showing the bug)

```
──────────────────────────────────────────────────────────────────────
SPAN NAME                                session.id
──────────────────────────────────────────────────────────────────────
invocation [poc-app]                     known-session-id-abc123
agent_run [root_agent]                   known-session-id-abc123
invocation [poc-app]                     3f8a2b1c-...  ✗ BUG
agent_run [sub_agent]                    3f8a2b1c-...  ✗ BUG
──────────────────────────────────────────────────────────────────────

❌ BUG CONFIRMED: 2 span(s) have wrong session.id:
   - invocation [poc-app]
   - agent_run [sub_agent]

Expected: session.id = known-session-id-abc123
Root cause: _RunnerRunAsync stamps session.id = ADK-internal sub-session UUID
            overriding the ambient OTel session from the parent runner.
```

---

## Step 6 — File the GitHub issue

URL: https://github.com/Arize-ai/openinference/issues/new

**Title:** `[bug] google-adk: sub-agent spans get wrong session.id when using AgentTool`

**Body template:**

```markdown
## Bug description

When a root agent invokes a sub-agent via `AgentTool`, the sub-agent's
`invocation [*]` and `agent_run [*]` spans are stamped with the ADK-internal
sub-session UUID instead of the user-facing `session_id` passed to the top-level
`runner.run_async()`.

This causes Langfuse (and any OTLP backend using last-write-wins for sessionId)
to assign the trace to the wrong session.

## Root cause

In `_wrappers.py`, `_RunnerRunAsync.__call__`:

```python
# line 93
attributes = dict(get_attributes_from_context())  # ← correct ambient session.id

# line 109-110
if (session_id := kwargs.get("session_id")) is not None:
    attributes[SpanAttributes.SESSION_ID] = session_id  # ← OVERWRITES with ADK-internal UUID
```

When called as a sub-agent, `kwargs["session_id"]` is a new UUID created by ADK's
session service — not the user-facing session. This overwrites the correct
`session.id` that `get_attributes_from_context()` would have pulled from the
parent runner's `using_session()` context.

## Proposed fix

In `_RunnerRunAsync`, only stamp `session.id` if there is no ambient `session.id`
already in the OTel context:

```python
ambient_session = dict(get_attributes_from_context()).get(SpanAttributes.SESSION_ID)
if (session_id := kwargs.get("session_id")) is not None:
    if ambient_session is None:   # top-level runner only
        attributes[SpanAttributes.SESSION_ID] = session_id
```

## Reproduction

[attach poc.py and its output]

## Environment

- openinference-instrumentation-google-adk: <version>
- google-adk: <version>
```

---

## Notes

- No existing issue found for this bug (searched Arize-ai/openinference 2026-05-17)
- `agents-cli` is at v0.1.1; project is in `/Users/morie/workspace/cofacts/ai`
- After filing the issue, link it from PR #56 on cofacts/ai

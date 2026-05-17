# PoC: Reproduce Google ADK session.id bug

This project demonstrates a bug in `openinference-instrumentation-google-adk` where sub-agent spans are stamped with an incorrect `session.id` (an ADK-internal UUID) instead of the user-facing `session_id`.

## Goal

Confirm that when a root agent invokes a sub-agent via `AgentTool`, the sub-agent's `agent_run` and `call_llm` spans do not inherit the correct `session.id` from the parent context.

## Prerequisites

1.  **Install dependencies**:
    ```bash
    uv sync
    ```
2.  **Configure Environment**: Create a `.env` file and set your `GOOGLE_API_KEY`.
    ```bash
    cp .env.sample .env
    # Edit .env and add your GOOGLE_API_KEY
    ```

## Running the PoC

Run the reproduction script using `uv`:

```bash
uv run --env-file .env python poc.py
```

## Results that demonstrates the bug

The script will output a table of spans and their `session.id`. If the bug is present, you will see `✗ BUG` next to sub-agent spans because they use an ADK-internal UUID instead of `known-session-id-abc123`.

```text
──────────────────────────────────────────────────────────────────────
SPAN NAME                                session.id
──────────────────────────────────────────────────────────────────────
call_llm                                 <uuid>  ✗ BUG
agent_run [sub_agent]                    <uuid>  ✗ BUG
invocation [poc-app]                     known-session-id-abc123
execute_tool sub_agent                   known-session-id-abc123
call_llm                                 known-session-id-abc123
call_llm                                 known-session-id-abc123
agent_run [root_agent]                   known-session-id-abc123
invocation [poc-app]                     known-session-id-abc123
──────────────────────────────────────────────────────────────────────

❌ BUG CONFIRMED: 2 span(s) have wrong session.id:
   - call_llm
   - agent_run [sub_agent]
```

## Root Cause

In `openinference-instrumentation-google-adk`, the `_RunnerRunAsync` wrapper stamps the `session.id` using the `session_id` argument passed to the ADK `Runner`. When called for a sub-agent, this argument contains an internal sub-session UUID, which overwrites the correct `session.id` already present in the OpenTelemetry context.

# poc-session-bug

Simple ReAct agent
Agent generated with `agents-cli` version `0.1.1`

## PoC: Reproduce session.id bug

This project contains a reproduction script for a bug in `openinference-instrumentation-google-adk` where sub-agent spans are stamped with the wrong `session.id`.

### Prerequisites

1.  **Configure Environment**: Create a `.env` file and set your `GOOGLE_API_KEY`.
    ```bash
    cp .env.sample .env
    # Edit .env and add your GOOGLE_API_KEY
    ```

### Running the PoC

Run the reproduction script using `uv`:

```bash
uv run python poc.py
```

### Expected Results

The script will output a table of spans and their `session.id`. If the bug is present, you will see `✗ BUG` next to sub-agent spans (like `agent_run [sub_agent]`) because they use an ADK-internal UUID instead of the `known-session-id-abc123` provided to the runner.

```text
──────────────────────────────────────────────────────────────────────
SPAN NAME                                session.id
──────────────────────────────────────────────────────────────────────
...
agent_run [sub_agent]                    <uuid>  ✗ BUG
...
──────────────────────────────────────────────────────────────────────

❌ BUG CONFIRMED: 2 span(s) have wrong session.id:
   - call_llm
   - agent_run [sub_agent]
```

## Project Structure

```
poc-session-bug/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── agent_runtime_app.py    # Agent Runtime application logic
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Agent Runtime                                                                |
| `agents-cli publish gemini-enterprise` | Register deployed agent to Gemini Enterprise                    |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.

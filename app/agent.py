from google.adk.agents import LlmAgent
from google.adk.apps import App
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

app = App(
    root_agent=root_agent,
    name="poc_app",
)

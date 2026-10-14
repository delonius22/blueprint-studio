"""T-01: the AG-UI endpoint at /agent (S4.1) and the answer to PRD OQ-2.

OQ-2 asks whether CopilotKit frontend tools reach nodes of a hand-built
StateGraph. These tests drive the real FastAPI route with AG-UI run inputs, the
way the CopilotKit runtime's HttpAgent does, and show that:

1. a node of a hand-built StateGraph sees the frontend tool's schema in state;
2. the node's call to that tool streams to the client as TOOL_CALL_* events and
   the run ends with the call unanswered (nothing executes it server-side);
3. the next run carries the user's answer as a tool result that reaches the node.
"""

import json
import uuid
from typing import Any

import httpx
from fakes import ScriptedChatModel, tool_call
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from blueprint.app import create_app
from blueprint.graph import build_graph
from blueprint.models import RoleModels
from blueprint.state import DesignState

CONFIRM_STEP = {
    "name": "confirm_step",
    "description": "Ask the user to confirm the current step.",
    "parameters": {
        "type": "object",
        "properties": {"step": {"type": "integer"}, "summary": {"type": "string"}},
        "required": ["step", "summary"],
    },
}


def run_input(
    thread_id: str, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
) -> dict[str, Any]:
    return {
        "threadId": thread_id,
        "runId": str(uuid.uuid4()),
        "state": {},
        "messages": messages,
        "tools": tools,
        "context": [],
        "forwardedProps": {},
    }


async def post_run(app: Any, body: dict[str, Any]) -> list[dict[str, Any]]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://agent") as client:
        response = await client.post("/agent", json=body, headers={"accept": "text/event-stream"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    return [
        json.loads(line.removeprefix("data: "))
        for line in response.text.splitlines()
        if line.startswith("data: ")
    ]


def types(events: list[dict[str, Any]]) -> list[str]:
    return [e["type"] for e in events]


async def test_chat_reply_streams_through_the_agent_endpoint() -> None:
    interview = ScriptedChatModel.with_script(AIMessage("Who are the users of the system?"))
    app = create_app(build_graph(RoleModels(interview, ScriptedChatModel()), InMemorySaver()))

    events = await post_run(
        app,
        run_input(
            "t-stream", [{"id": "u1", "role": "user", "content": "Design a URL shortener"}], []
        ),
    )

    assert types(events)[0] == "RUN_STARTED"
    assert types(events)[-1] == "RUN_FINISHED"
    chunks = [e["delta"] for e in events if e["type"] == "TEXT_MESSAGE_CONTENT"]
    assert len(chunks) > 1, "the reply arrives as several streamed chunks"
    assert "".join(chunks) == "Who are the users of the system?"


def gate_graph(model: ScriptedChatModel, seen: list[list[str]]) -> Any:
    """A hand-built StateGraph whose node binds the frontend tools found in state."""

    async def node(state: DesignState, config: RunnableConfig) -> dict[str, Any]:
        frontend_tools = state["copilotkit"]["actions"]
        seen.append([t["name"] for t in frontend_tools])
        reply = await model.bind_tools(frontend_tools).ainvoke(state["messages"], config)
        return {"messages": [reply]}

    def route(state: DesignState) -> str:
        last = state["messages"][-1]
        return END if isinstance(last, AIMessage) and last.tool_calls else "node"

    builder = StateGraph(DesignState)
    builder.add_node("node", node)
    builder.add_edge(START, "node")
    builder.add_conditional_edges("node", route, {END: END, "node": "node"})
    return builder.compile(checkpointer=InMemorySaver())


async def test_oq2_frontend_tools_reach_a_hand_built_state_graph() -> None:
    model = ScriptedChatModel.with_script(
        tool_call("confirm_step", {"step": 1, "summary": "Requirements are clear"}, "call_1"),
        AIMessage("Step 1 confirmed, on to the data model."),
    )
    seen: list[list[str]] = []
    app = create_app(gate_graph(model, seen))
    user = {"id": "u1", "role": "user", "content": "I think step 1 is done"}

    first = await post_run(app, run_input("t-gate", [user], [CONFIRM_STEP]))

    # 1. the node saw the frontend tool, and bound it to the model
    assert seen == [["confirm_step"]]
    assert model.calls[0].tools == ["confirm_step"]
    # 2. the call streamed to the client and the run ended with it unanswered
    start = next(e for e in first if e["type"] == "TOOL_CALL_START")
    assert start["toolCallName"] == "confirm_step"
    args = "".join(e["delta"] for e in first if e["type"] == "TOOL_CALL_ARGS")
    assert json.loads(args) == {"step": 1, "summary": "Requirements are clear"}
    assert "TOOL_CALL_RESULT" not in types(first)
    assert types(first)[-1] == "RUN_FINISHED"
    assert len(model.calls) == 1

    # 3. the follow-up run carries the user's answer as a tool result
    assistant = {
        "id": "a1",
        "role": "assistant",
        "content": "",
        "toolCalls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "confirm_step", "arguments": args},
            }
        ],
    }
    answer = {"id": "r1", "role": "tool", "toolCallId": "call_1", "content": '{"approved": true}'}
    second = await post_run(app, run_input("t-gate", [user, assistant, answer], [CONFIRM_STEP]))

    results = [m for m in model.calls[1].messages if isinstance(m, ToolMessage)]
    assert [(r.tool_call_id, r.content) for r in results] == [("call_1", '{"approved": true}')]
    reply = "".join(e["delta"] for e in second if e["type"] == "TEXT_MESSAGE_CONTENT")
    assert reply == "Step 1 confirmed, on to the data model."

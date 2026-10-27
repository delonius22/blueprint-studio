"""A scripted OpenAI-compatible Chat Completions server for the end-to-end smoke test (T-20).

It plays both model roles deterministically, answering by content (never by call order) so
that several sessions can run at once. No key and no network are involved: the app's real
OpenAI-compatible client talks to it over HTTP inside the compose network.

The interviewer reacts to commands in the user's message, one per line:
  FR: <statement>                      record a functional requirement
  CMP: <name>                          record a service component
  FM: <scenario>                       record a failure mode
  SPOF: <component id> | <risk> | <mitigation>
  CONFIRM <n>                          ask to confirm step n
Structured outputs are answered from the JSON the app puts in its prompts.
Standard library only; run with ``python -I fake_model.py <port>``.
"""

import json
import re
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

DIMENSIONS = ["communication", "structure", "judgment", "depth", "time"]


def text_of(message: dict[str, Any]) -> str:
    content = message.get("content") or ""
    if isinstance(content, list):
        return " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return str(content)


def json_blocks(text: str) -> list[Any]:
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", text, flags=re.DOTALL)]


def call(name: str, args: dict[str, Any]) -> dict[str, Any]:
    return {"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}


def interviewer(body: dict[str, Any]) -> dict[str, Any]:
    messages = body["messages"]
    names = {t["function"]["name"] for t in body.get("tools", [])}
    last = messages[-1]
    if last["role"] == "tool":
        return {"content": "Recorded. What else should we settle in this step?"}
    system = " ".join(text_of(m) for m in messages if m["role"] == "system")
    marker = "Since your last turn the user edited the canvas directly: "
    if marker in system and last["role"] == "user":
        return {"content": "Noted: " + system.split(marker)[1].split(".")[0] + "."}
    calls = []
    for line in text_of(last).splitlines():
        line = line.strip()
        if line.startswith("FR:") and "upsert_requirement" in names:
            calls.append(call("upsert_requirement", {"statement": line[3:].strip()}))
        elif line.startswith("CMP:") and "upsert_component" in names:
            calls.append(call("upsert_component", {"name": line[4:].strip(), "kind": "service", "responsibility": "Serves requests"}))
        elif line.startswith("FM:") and "upsert_failure_mode" in names:
            calls.append(call("upsert_failure_mode", {"scenario": line[3:].strip(), "behaviour": "Degrades gracefully"}))
        elif line.startswith("SPOF:") and "upsert_spof" in names:
            component, risk, mitigation = (part.strip() for part in line[5:].split("|"))
            calls.append(call("upsert_spof", {"component_id": component, "risk": risk, "mitigation": mitigation}))
        elif line.startswith("CONFIRM") and "confirm_step" in names:
            step = int(line.split()[1])
            calls.append(call("confirm_step", {"step": step, "summary": f"Step {step} is settled."}))
    if calls:
        return {"tool_calls": calls}
    return {"content": "Before any architecture: who are the users, and what read/write ratio do you expect?"}


def structured(name: str, body: dict[str, Any]) -> Any:
    texts = [text_of(m) for m in body["messages"]]
    joined = "\n".join(texts)
    blocks = json_blocks(texts[-1]) if texts else []
    if name == "PingResult":
        return {"ok": True}
    if name == "ImportProposal":  # every sentence of the attached file is a requirement
        attached = joined.split("<untrusted-file>", 1)[-1].split("</untrusted-file>", 1)[0]
        quotes = [line.strip() for line in attached.splitlines() if line.strip().endswith(".")]
        return {"summary": "A short brief.", "functional_requirements": [
            {"quote": q, "locator": "Brief", "updates": None, "weaknesses": [], "statement": q.rstrip(".")}
            for q in quotes]}  # fmt: skip
    if name == "CritiqueDraft":
        return {"strengths": ["Clear scope"], "bottlenecks": ["Capacity is not estimated"], "questions": ["What is the peak load?"]}
    if name == "ScorecardDraft":
        quote = next(line[6:].strip() for line in joined.splitlines() if line.startswith("User: "))
        return {"dimensions": [{"dimension": d, "score": 3, "evidence": [quote], "advice": f"Practise {d}."} for d in DIMENSIONS]}
    if name == "Findings":
        if "one lens only: security" not in texts[0]:
            return {"findings": []}
        return {"findings": [{"lens": "security", "item_ids": ["FR-1"], "severity": "high",
                              "risk": "Anyone can create links without signing in.",
                              "decision_needed": "Who may create links?"}]}
    if name == "MergedGaps":
        return {"gaps": blocks[-1]["findings"]}
    if name == "PrdDraftOut":
        design, gaps = blocks[0], blocks[1]
        return {
            "problem_statement": "Long URLs are hard to share.",
            "goals": ["Short links that always resolve"],
            "users": ["Web users"],
            "features": [{"ref": "f1", "name": "Short links", "description": "Create and resolve short links.",
                          "requirement_ids": [r["id"] for r in design["functional_requirements"]]}],
            "scope": ["Creating and resolving links"],
            "gap_features": [{"gap_id": g["id"], "feature_refs": ["f1"]} for g in gaps],
        }
    if name == "SpecOut":
        prd = blocks[0]
        feature = prd["features"][0]["id"]
        return {
            "solution": "A small web service that issues short codes.",
            "user_stories": [
                {"feature_id": feature, "actor": "a web user", "feature": f"to rely on {r['id']}",
                 "benefit": "the service does what was agreed", "acceptance_criteria": [r["statement"]],
                 "requirement_ids": [r["id"]]}
                for r in prd["functional_requirements"]
            ],
            "implementation_decisions": ["Codes are base62"],
            "further_notes": [],
            "proposed_changes": [{"section": "goals", "kind": "add", "proposed_text": "Links can expire", "reason": "Asked for in the interview"}],
        }
    if name == "SeamsOut":
        draft = blocks[0]
        return {"seams": [{"name": "HTTP API", "description": "Drive the public API end to end",
                           "covers": [s["id"] for s in draft["user_stories"]]}]}
    if name == "TicketsOut":
        prd = blocks[0]
        stories = [s["id"] for s in prd["user_stories"]]
        return {"tickets": [
            {"id": f"t{i}", "title": f"Deliver {story}", "what_to_build": f"Build {story} end to end.",
             "blocked_by": [f"t{i - 1}"] if i else [], "acceptance_criteria": [f"{story} works"], "story_ids": [story], "kind": "slice"}
            for i, story in enumerate(stories)
        ]}
    raise ValueError(f"no scripted answer for {name}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def _send_json(self, payload: Any, status: int = 200) -> None:
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        self._send_json({"data": []})

    def do_POST(self) -> None:
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        tools = body.get("tools") or []
        response_format = body.get("response_format") or {}
        if response_format.get("type") == "json_schema":
            reply: dict[str, Any] = {"content": json.dumps(structured(response_format["json_schema"]["name"], body))}
        elif tools and tools[0]["function"]["name"] == "Ping":
            reply = {"tool_calls": [call("Ping", {"message": "pong"})]}
        elif tools and len(tools) == 1 and body.get("tool_choice"):
            name = tools[0]["function"]["name"]  # tool-calling fallback for structured output
            reply = {"tool_calls": [call(name, structured(name, body))]}
        else:
            reply = interviewer(body)
        usage = {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70}
        base = {"id": "chatcmpl-e2e", "created": int(time.time()), "model": body.get("model")}
        finish = "tool_calls" if reply.get("tool_calls") else "stop"
        if not body.get("stream"):
            message = {"role": "assistant", "content": reply.get("content"), **({"tool_calls": reply["tool_calls"]} if reply.get("tool_calls") else {})}
            self._send_json({**base, "object": "chat.completion", "usage": usage,
                             "choices": [{"index": 0, "message": message, "finish_reason": finish}]})
            return
        self.send_response(200)
        self.send_header("content-type", "text/event-stream")
        self.end_headers()

        def chunk(delta: dict[str, Any], finish_reason: str | None = None, extra: dict[str, Any] | None = None) -> None:
            event = {**base, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}], **(extra or {})}
            self.wfile.write(f"data: {json.dumps(event)}\n\n".encode())
            self.wfile.flush()

        chunk({"role": "assistant", "content": ""})
        for i, tool_call in enumerate(reply.get("tool_calls") or []):
            chunk({"tool_calls": [{"index": i, "id": tool_call["id"], "type": "function", "function": {"name": tool_call["function"]["name"], "arguments": ""}}]})
            chunk({"tool_calls": [{"index": i, "function": {"arguments": tool_call["function"]["arguments"]}}]})
        for word in (reply.get("content") or "").split(" ") if reply.get("content") else []:
            chunk({"content": word + " "})
        chunk({}, finish)
        self.wfile.write(f"data: {json.dumps({**base, 'object': 'chat.completion.chunk', 'choices': [], 'usage': usage})}\n\n".encode())
        self.wfile.write(b"data: [DONE]\n\n")


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", int(sys.argv[1])), Handler).serve_forever()

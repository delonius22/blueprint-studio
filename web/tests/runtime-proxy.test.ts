// T-01: a chat message reaches the agent through the CopilotKit runtime proxy and the
// reply streams back (SPECS S4.3, S4.4); the browser never calls the agent directly.
import { readdirSync, readFileSync, statSync } from "node:fs";
import { createServer, type IncomingMessage, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { join } from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { AGENT_NAME, RUNTIME_PATH } from "../lib/constants";
import { createRuntimeHandler } from "../lib/runtime";

type Received = { path: string; body: { threadId: string; messages: { content: string }[] } };

const REPLY = ["Who ", "are ", "the ", "users?"];
let server: Server;
let agentUrl: string;
const received: Received[] = [];

async function readBody(request: IncomingMessage): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of request) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks).toString("utf8");
}

// A stand-in for the FastAPI AG-UI endpoint: streams a reply as server-sent events.
beforeAll(async () => {
  server = createServer(async (request, response) => {
    const body = JSON.parse(await readBody(request)) as Received["body"] & { runId: string };
    received.push({ path: request.url ?? "", body });
    response.writeHead(200, { "content-type": "text/event-stream" });
    const send = (event: object) => response.write(`data: ${JSON.stringify(event)}\n\n`);
    send({ type: "RUN_STARTED", threadId: body.threadId, runId: body.runId });
    send({ type: "TEXT_MESSAGE_START", messageId: "m1", role: "assistant" });
    for (const delta of REPLY) send({ type: "TEXT_MESSAGE_CONTENT", messageId: "m1", delta });
    send({ type: "TEXT_MESSAGE_END", messageId: "m1" });
    send({ type: "RUN_FINISHED", threadId: body.threadId, runId: body.runId });
    response.end();
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  agentUrl = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
});

afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));

describe("CopilotKit runtime proxy", () => {
  it("lists the blueprint agent", async () => {
    const handler = createRuntimeHandler(agentUrl);
    const response = await handler(new Request(`http://web${RUNTIME_PATH}/info`));
    expect(response.status).toBe(200);
    const info = (await response.json()) as { agents: Record<string, unknown> };
    expect(Object.keys(info.agents)).toContain(AGENT_NAME);
  });

  it("forwards a chat message to AGENT_URL/agent and streams the reply back", async () => {
    const handler = createRuntimeHandler(`${agentUrl}/`);
    const response = await handler(
      new Request(`http://web${RUNTIME_PATH}/agent/${AGENT_NAME}/run`, {
        method: "POST",
        headers: { "content-type": "application/json", accept: "text/event-stream" },
        body: JSON.stringify({
          threadId: "thread-1",
          runId: "run-1",
          state: {},
          messages: [{ id: "u1", role: "user", content: "Design a URL shortener" }],
          tools: [],
          context: [],
          forwardedProps: {},
        }),
      }),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get("content-type")).toMatch(/^text\/event-stream/);

    const deltas: string[] = [];
    const reader = response.body!.pipeThrough(new TextDecoderStream()).getReader();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += value;
    }
    for (const line of buffer.split("\n")) {
      if (!line.startsWith("data: ")) continue;
      const event = JSON.parse(line.slice(6)) as { type: string; delta?: string };
      if (event.type === "TEXT_MESSAGE_CONTENT") deltas.push(event.delta!);
    }

    expect(deltas).toEqual(REPLY);
    expect(received.at(-1)?.path).toBe("/agent");
    expect(received.at(-1)?.body.threadId).toBe("thread-1");
    expect(received.at(-1)?.body.messages.at(-1)?.content).toBe("Design a URL shortener");
  });
});

describe("browser code", () => {
  function sourceFiles(dir: string): string[] {
    return readdirSync(dir).flatMap((name) => {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) return name === "api" ? [] : sourceFiles(path);
      return /\.(ts|tsx)$/.test(name) ? [path] : [];
    });
  }

  it("never addresses the agent service directly", () => {
    const root = join(__dirname, "..");
    const files = [...sourceFiles(join(root, "app")), join(root, "lib", "constants.ts")];
    for (const file of files) {
      const text = readFileSync(file, "utf8");
      expect(text, file).not.toMatch(/AGENT_URL|:8000|\/agent\b/);
    }
    const page = readFileSync(join(root, "app", "page.tsx"), "utf8");
    expect(page).toContain("runtimeUrl={RUNTIME_PATH}");
    expect(RUNTIME_PATH).toBe("/api/copilotkit");
  });
});

// @vitest-environment jsdom
// Document import in the browser (SPEC-document-import §5): the review card decides item by
// item, edits are sent as edits, the canvas shows where an item came from, and the session
// proxy passes file bytes through unchanged.
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import { POST } from "../app/api/sessions/[[...path]]/route";
import { Canvas } from "../components/canvas/Canvas";
import { type CardCandidate, ReviewImportCard } from "../components/gates/ReviewImportCard";
import { EMPTY_DESIGN } from "../lib/state";

afterEach(cleanup);

const candidates: CardCandidate[] = [
  {
    id: "IMP-1",
    file: "brief.md",
    step: 1,
    list: "non_functional_requirements",
    args: { category: "latency", statement: "Redirects are fast" },
    editable: { category: ["latency", "throughput"], statement: "text", target: "number", unit: "text" },
    updates: null,
    current: null,
    locator: "Requirements",
    quote: "Redirects must be fast.",
    weaknesses: [{ code: "missing_target", detail: "No latency target" }],
  },
  {
    id: "IMP-2",
    file: "brief.md",
    step: 1,
    list: "functional_requirements",
    args: { statement: "Users export links" },
    editable: { statement: "text" },
    updates: "FR-1",
    current: { id: "FR-1", statement: "Users shorten URLs" },
    locator: "Requirements",
    quote: "Users export links.",
    weaknesses: [],
  },
];

describe("ReviewImportCard", () => {
  it("shows each item with its quote and sends accepts, edits and rejections", async () => {
    const respond = vi.fn();
    render(<ReviewImportCard args={{ candidates }} status="executing" respond={respond} />);
    expect(screen.getByText(/Redirects must be fast\./)).toBeTruthy();
    expect(screen.getByText("missing target: No latency target")).toBeTruthy();
    expect(screen.getByText(/Replaces FR-1:/)).toBeTruthy();

    await userEvent.type(screen.getByLabelText("target"), "50");
    await userEvent.click(screen.getByRole("checkbox", { name: "Reject IMP-2" }));
    await userEvent.click(screen.getByRole("button", { name: "Record accepted items" }));

    expect(respond).toHaveBeenCalledWith({
      decisions: [
        { candidate_id: "IMP-1", decision: "edit", fields: { target: 50 } },
        { candidate_id: "IMP-2", decision: "reject", fields: {} },
      ],
    });
  });

  it("accepts all as written", async () => {
    const respond = vi.fn();
    render(<ReviewImportCard args={{ candidates }} status="executing" respond={respond} />);
    await userEvent.click(screen.getByRole("button", { name: "Accept all as written" }));
    expect(respond.mock.calls[0][0].decisions.map((d: { decision: string }) => d.decision)).toEqual([
      "accept",
      "accept",
    ]);
  });

  it("shows the decisions once answered", () => {
    const result = JSON.stringify({ decisions: [{ candidate_id: "IMP-1", decision: "edit", fields: {} }] });
    render(<ReviewImportCard args={{ candidates }} status="complete" result={result} />);
    expect(screen.getByText("IMP-1: accepted with edits")).toBeTruthy();
  });
});

describe("Canvas sources", () => {
  it("names the file an imported item came from", () => {
    render(
      <Canvas
        design={{ ...EMPTY_DESIGN, functional_requirements: [{ id: "FR-1", statement: "Shorten URLs" }] }}
        sources={{ "FR-1": "brief.md · Requirements" }}
      />,
    );
    expect(screen.getByText("from brief.md · Requirements")).toBeTruthy();
  });
});

describe("session proxy", () => {
  let server: Server;
  const received: Buffer[] = [];

  beforeAll(async () => {
    server = createServer(async (request, response) => {
      const chunks: Buffer[] = [];
      for await (const chunk of request) chunks.push(chunk as Buffer);
      received.push(Buffer.concat(chunks));
      response.writeHead(201, { "content-type": "application/json" });
      response.end("{}");
    });
    await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
    process.env.AGENT_URL = `http://127.0.0.1:${(server.address() as AddressInfo).port}`;
  });

  afterAll(() => new Promise<void>((resolve) => server.close(() => resolve())));

  it("forwards an uploaded file byte for byte", async () => {
    const bytes = new Uint8Array([0x89, 0x50, 0x4e, 0x47, 0x00, 0xff, 0xfe, 0x80]);
    const response = await POST(
      new Request("http://web/api/sessions/s1/attachments?name=a.png", {
        method: "POST",
        headers: { "content-type": "application/octet-stream" },
        body: bytes,
      }),
    );
    expect(response.status).toBe(201);
    expect([...received[0]]).toEqual([...bytes]);
  });
});

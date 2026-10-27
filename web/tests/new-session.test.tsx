// @vitest-environment jsdom
// Starting a session and attaching files (SPECS S11.1, SPEC-document-import §5): every file
// must be marked as a PRD, a spec or a supporting document before it is uploaded, and the role
// travels with the upload.
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { AttachControl } from "../components/attachments/AttachControl";
import { NewSessionForm } from "../components/sessions/NewSessionForm";
import type { SessionSummary, UploadedAttachment } from "../lib/sessions";

const SESSION: SessionSummary = {
  id: "new-id",
  name: "URL shortener",
  stage: "interview",
  current_step: 1,
  created_at: "2026-10-27T10:00:00Z",
  updated_at: "2026-10-27T10:00:00Z",
};

type Call = { method: string; url: string; body?: unknown };
let calls: Call[];
let respond: (call: Call) => { status: number; body?: unknown };

function uploaded(name: string, role: UploadedAttachment["role"], id = "ATT-1"): UploadedAttachment {
  return { id, name, role, kind: "text", media_type: "text/markdown", size: 3, warnings: [], duplicate: false };
}

beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const body = init?.body instanceof Blob ? "file" : init?.body ? JSON.parse(String(init.body)) : undefined;
      const call = { method: init?.method ?? "GET", url, body };
      calls.push(call);
      const reply = respond(call);
      return new Response(JSON.stringify(reply.body), { status: reply.status });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const brief = () => new File(["# Brief"], "brief.md", { type: "text/markdown" });
const diagram = () => new File(["graph TD"], "arch.mmd", { type: "text/plain" });

describe("NewSessionForm", () => {
  it("creates a named session and opens it", async () => {
    respond = () => ({ status: 201, body: SESSION });
    const onOpen = vi.fn();
    render(<NewSessionForm onOpen={onOpen} />);

    await userEvent.type(screen.getByLabelText("Session name"), "URL shortener");
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));

    await waitFor(() => expect(onOpen).toHaveBeenCalledWith("new-id"));
    expect(calls).toEqual([{ method: "POST", url: "/api/sessions", body: { name: "URL shortener" } }]);
  });

  it("shows the API's error message when a request is rejected", async () => {
    respond = () => ({ status: 422, body: { error: { code: "invalid_request", message: "name: too long" } } });
    render(<NewSessionForm onOpen={() => {}} />);

    await userEvent.type(screen.getByLabelText("Session name"), "x");
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));

    expect((await screen.findByRole("alert")).textContent).toBe("name: too long");
  });

  it("will not start until every file says what it is, then uploads each with its role", async () => {
    respond = ({ url }) =>
      url.includes("/attachments")
        ? { status: 201, body: uploaded(url.includes("brief") ? "brief.md" : "arch.mmd", "prd") }
        : { status: 201, body: SESSION };
    const onOpen = vi.fn();
    render(<NewSessionForm onOpen={onOpen} />);
    await userEvent.type(screen.getByLabelText("Session name"), "URL shortener");
    await userEvent.upload(screen.getByLabelText("Files to attach"), [brief(), diagram()]);

    const briefRow = screen.getByRole("group", { name: /brief\.md/ });
    await userEvent.click(within(briefRow).getByRole("radio", { name: "PRD" }));
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));
    expect((await screen.findByRole("alert")).textContent).toBe("Choose PRD, Spec or Supporting for each file first.");
    expect(calls).toEqual([]);

    await userEvent.click(within(screen.getByRole("group", { name: /arch\.mmd/ })).getByRole("radio", { name: "Supporting" }));
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));

    await waitFor(() => expect(onOpen).toHaveBeenCalledWith("new-id"));
    expect(calls.map((c) => c.url)).toEqual([
      "/api/sessions",
      "/api/sessions/new-id/attachments?name=brief.md&role=prd",
      "/api/sessions/new-id/attachments?name=arch.mmd&role=supporting",
    ]);
  });

  it("keeps the user on the page when a file is refused, with a way into the session", async () => {
    respond = ({ url }) =>
      url.includes("/attachments")
        ? { status: 415, body: { error: { code: "unsupported_type", message: "arch.mmd is not a file the app reads" } } }
        : { status: 201, body: SESSION };
    const onOpen = vi.fn();
    render(<NewSessionForm onOpen={onOpen} />);
    await userEvent.type(screen.getByLabelText("Session name"), "URL shortener");
    await userEvent.upload(screen.getByLabelText("Files to attach"), diagram());
    await userEvent.click(screen.getByRole("radio", { name: "Spec" }));
    await userEvent.click(screen.getByRole("button", { name: "Start session" }));

    expect(await screen.findByText("arch.mmd is not a file the app reads")).toBeTruthy();
    expect(onOpen).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Open the session" }));
    expect(onOpen).toHaveBeenCalledWith("new-id");
  });
});

describe("AttachControl", () => {
  it("attaches only once each chosen file has a role, and can drop a file before attaching", async () => {
    respond = () => ({ status: 201, body: uploaded("brief.md", "spec") });
    const onAttached = vi.fn();
    render(<AttachControl sessionId="s1" accepts={[".md", ".mmd"]} disabled={false} onAttached={onAttached} />);
    expect(screen.queryByRole("button", { name: /^Attach/ })).toBeNull();

    await userEvent.upload(screen.getByLabelText("Files to attach"), [brief(), diagram()]);
    const attach = screen.getByRole("button", { name: "Attach 2 files" });
    expect((attach as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText("Choose PRD, Spec or Supporting for each file first.")).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: "Don't attach arch.mmd" }));
    await userEvent.click(screen.getByRole("radio", { name: "Spec" }));
    await userEvent.click(screen.getByRole("button", { name: "Attach 1 file" }));

    await waitFor(() => expect(onAttached).toHaveBeenCalledWith([uploaded("brief.md", "spec")]));
    expect(calls).toEqual([{ method: "POST", url: "/api/sessions/s1/attachments?name=brief.md&role=spec", body: "file" }]);
    expect(screen.queryByRole("list", { name: "Chosen files" })).toBeNull();
  });
});

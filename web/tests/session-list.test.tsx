// @vitest-environment jsdom
// T-02: the session list shows sessions newest first with name and stage, paginated by
// keyset cursor, and creates, renames and deletes them (SPECS S3, S11.1).
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SessionList } from "../components/sessions/SessionList";
import type { SessionSummary } from "../lib/sessions";

function session(id: string, name: string, stage = "interview", step = 1): SessionSummary {
  const at = "2026-10-14T10:00:00Z";
  return { id, name, stage, current_step: step, created_at: at, updated_at: at };
}

type Call = { method: string; url: string; body?: unknown };
let calls: Call[];
let respond: (call: Call) => { status: number; body?: unknown };

beforeEach(() => {
  calls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const call = {
        method: init?.method ?? "GET",
        url,
        body: init?.body ? JSON.parse(String(init.body)) : undefined,
      };
      calls.push(call);
      const { status, body } = respond(call);
      return new Response(status === 204 ? null : JSON.stringify(body), { status });
    }),
  );
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function names(): string[] {
  const list = screen.getByRole("list", { name: "Your sessions" });
  return within(list)
    .getAllByRole("link")
    .map((link) => link.textContent ?? "");
}

describe("SessionList", () => {
  it("shows the newest page first with name and stage, then loads more by cursor", async () => {
    respond = ({ url }) =>
      url.includes("cursor=c1")
        ? { status: 200, body: { items: [session("3", "Oldest", "complete")], next_cursor: null } }
        : {
            status: 200,
            body: {
              items: [session("1", "Newest", "interview", 2), session("2", "Middle", "prd_signoff")],
              next_cursor: "c1",
            },
          };
    render(<SessionList onOpen={() => {}} />);

    await waitFor(() => expect(names()).toEqual(["Newest", "Middle"]));
    expect(calls[0]).toMatchObject({ method: "GET", url: "/api/sessions?limit=20" });
    expect(screen.getByText("Interview · step 2 of 5")).toBeTruthy();
    expect(screen.getByText("PRD sign-off")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Newest" }).getAttribute("href")).toBe("/s/1");

    await userEvent.click(screen.getByRole("button", { name: "Load more" }));
    await waitFor(() => expect(names()).toEqual(["Newest", "Middle", "Oldest"]));
    expect(calls[1].url).toBe("/api/sessions?limit=20&cursor=c1");
    expect(screen.queryByRole("button", { name: "Load more" })).toBeNull();
  });

  it("creates a named session and opens it", async () => {
    respond = ({ method }) =>
      method === "POST"
        ? { status: 201, body: session("new-id", "URL shortener") }
        : { status: 200, body: { items: [], next_cursor: null } };
    const onOpen = vi.fn();
    render(<SessionList onOpen={onOpen} />);

    await userEvent.type(screen.getByLabelText("Session name"), "URL shortener");
    await userEvent.click(screen.getByRole("button", { name: "New session" }));

    await waitFor(() => expect(onOpen).toHaveBeenCalledWith("new-id"));
    expect(calls.at(-1)).toEqual({ method: "POST", url: "/api/sessions", body: { name: "URL shortener" } });
  });

  it("shows the API's error message when a request is rejected", async () => {
    respond = ({ method }) =>
      method === "POST"
        ? { status: 422, body: { error: { code: "invalid_request", message: "name: too long" } } }
        : { status: 200, body: { items: [], next_cursor: null } };
    render(<SessionList onOpen={() => {}} />);

    await userEvent.type(screen.getByLabelText("Session name"), "x");
    await userEvent.click(screen.getByRole("button", { name: "New session" }));

    expect((await screen.findByRole("alert")).textContent).toBe("name: too long");
  });

  it("renames a session, moving it to the top, and deletes one after confirmation", async () => {
    respond = ({ method, url }) => {
      if (method === "PATCH") return { status: 200, body: session("2", "Renamed") };
      if (method === "DELETE") return { status: 204 };
      void url;
      return { status: 200, body: { items: [session("1", "First"), session("2", "Second")], next_cursor: null } };
    };
    vi.stubGlobal("confirm", vi.fn(() => true));
    render(<SessionList onOpen={() => {}} />);
    await waitFor(() => expect(names()).toEqual(["First", "Second"]));

    await userEvent.click(screen.getByRole("button", { name: "Rename Second" }));
    const input = screen.getByLabelText("New name for Second");
    await userEvent.clear(input);
    await userEvent.type(input, "Renamed");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(names()).toEqual(["Renamed", "First"]));
    expect(calls.at(-1)).toEqual({ method: "PATCH", url: "/api/sessions/2", body: { name: "Renamed" } });

    await userEvent.click(screen.getByRole("button", { name: "Delete First" }));
    await waitFor(() => expect(names()).toEqual(["Renamed"]));
    expect(calls.at(-1)).toMatchObject({ method: "DELETE", url: "/api/sessions/1" });
  });
});

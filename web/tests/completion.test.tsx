// @vitest-environment jsdom
// T-18: the completion view lists every available download with its file name and offers
// "Download all (.zip)", from the agent's listing (SPECS S11.5, S10.3).
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { CompletionView } from "../components/CompletionView";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("lists the available documents and the zip of all of them", async () => {
  const listing = [
    { kind: "prd-v1.0.docx", available: true, reason: null },
    { kind: "prd-v1.1.docx", available: true, reason: null },
    { kind: "prd-v1.2.docx", available: false, reason: "PRD v1.2 has not been approved yet" },
    { kind: "requirements.docx", available: true, reason: null },
    { kind: "user-stories.docx", available: true, reason: null },
    { kind: "context.md", available: true, reason: null },
    { kind: "bundle.zip", available: true, reason: null },
  ];
  const fetch = vi.fn(async () => new Response(JSON.stringify(listing)));
  vi.stubGlobal("fetch", fetch);
  render(<CompletionView sessionId="s1" sessionName="URL shortener" />);

  const all = await screen.findByRole("link", { name: "Download all (.zip)" });
  expect(all.getAttribute("href")).toBe("/api/sessions/s1/downloads/bundle.zip");
  expect(all.getAttribute("download")).toBe("URL shortener - Blueprint.zip");
  const names = within(screen.getByRole("list", { name: "Documents" }))
    .getAllByRole("link")
    .map((a) => a.textContent);
  expect(names).toEqual(["PRD v1.0.docx", "PRD v1.1.docx", "Requirements.docx", "UserStories.docx", "context.md"]);
  expect(fetch).toHaveBeenCalledWith("/api/sessions/s1/downloads", expect.anything());
});

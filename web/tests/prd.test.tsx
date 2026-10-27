// @vitest-environment jsdom
// T-12: the PRD viewer with its version switcher (SPECS S11.2), the sign-off card (S7.3,
// S11.4) and the downloads menu driven by the agent's listing (S10.3).
import { cleanup, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DownloadsMenu } from "../components/workspace/DownloadsMenu";
import { SignOffCard } from "../components/gates/SignOffCard";
import { PrdViewer } from "../components/delivery/PrdViewer";
import { downloadFileName } from "../lib/sessions";
import type { PrdDoc } from "../lib/state";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function doc(problem: string): PrdDoc {
  return {
    problem_statement: problem,
    goals: ["Short links"],
    users: ["Web users"],
    features: [{ id: "F-1", name: "Short links", description: "Create and resolve", requirement_ids: ["FR-1"] }],
    functional_requirements: [{ id: "FR-1", feature_id: "F-1", statement: "Users shorten URLs" }],
    non_functional_requirements: [{ id: "NFR-1", category: "latency", statement: "Fast", metric: "p95", target: 50, unit: "ms" }],
    scope: ["Links"],
    out_of_scope: ["Analytics"],
    open_gaps: [],
    solution: "",
    user_stories: [],
    implementation_decisions: [],
    testing_decisions: [],
    further_notes: [],
  };
}

describe("PrdViewer", () => {
  it("shows the draft awaiting sign-off with every section", () => {
    render(<PrdViewer draft={doc("Draft problem")} versions={[]} stage="prd_signoff" />);
    expect(screen.getByRole("heading", { level: 2 }).textContent).toBe("PRD draft");
    const sections = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(sections).toEqual([
      "Problem Statement", "Goals", "Users and Stakeholders", "Features", "Functional Requirements",
      "Non-Functional Requirements", "Scope", "Out of Scope", "Open Gaps and Accepted Risks",
    ]); // prettier-ignore
    const fr = screen.getAllByRole("table")[0];
    expect(within(fr).getByRole("rowheader").textContent).toBe("FR-1");
    expect(fr.textContent).toContain("F-1: Short links");
  });

  it("switches between the draft and frozen versions", async () => {
    render(
      <PrdViewer
        draft={doc("Working draft")}
        versions={[{ version: "1.0", approved_at: "2026-10-14T12:30:00Z", doc: doc("Signed problem") }]}
        stage="seam_gate"
      />,
    );
    expect(screen.getByText("Working draft")).toBeTruthy();
    await userEvent.selectOptions(screen.getByLabelText("Version"), "1.0");
    expect(screen.getByText("Signed problem")).toBeTruthy();
    expect(screen.getByRole("heading", { level: 2 }).textContent).toContain("PRD v1.0 · approved 2026-10-14 12:30:00 UTC");
  });
});

it("shows the newest frozen version once nothing awaits approval", () => {
  render(
    <PrdViewer
      draft={doc("Same as v1.0")}
      versions={[{ version: "1.0", approved_at: "2026-10-14T12:30:00Z", doc: doc("Signed problem") }]}
      stage="spec_synthesis"
    />,
  );
  expect(screen.getByRole("heading", { level: 2 }).textContent).toContain("PRD v1.0");
});

describe("SignOffCard", () => {
  it("signs off, or requires a reason to send the draft back", async () => {
    const respond = vi.fn();
    render(<SignOffCard args={{ prd: doc("p") }} status="executing" respond={respond} />);
    expect(screen.getByText(/1 features, 1 functional and 1 non-functional/)).toBeTruthy();
    await userEvent.click(screen.getByRole("button", { name: "Request changes" }));
    const send = screen.getByRole("button", { name: "Send back" }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    await userEvent.type(screen.getByLabelText("What should change?"), "Rename F-1");
    await userEvent.click(send);
    expect(respond).toHaveBeenLastCalledWith({ approved: false, reason: "Rename F-1" });
    cleanup();
    render(<SignOffCard args={{ prd: doc("p") }} status="executing" respond={respond} />);
    await userEvent.click(screen.getByRole("button", { name: "Sign off v1.0" }));
    expect(respond).toHaveBeenLastCalledWith({ approved: true });
  });
});

describe("DownloadsMenu", () => {
  it("links the available downloads and gives the reason for the others", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify([
            { kind: "prd-v1.0.docx", available: true, reason: null },
            { kind: "bundle.zip", available: false, reason: "available once the ticket breakdown is approved" },
          ]),
        ),
      ),
    );
    render(<DownloadsMenu sessionId="s 1" sessionName="URL shortener" refreshKey="a" />);
    const link = await screen.findByRole("link", { name: "PRD v1.0.docx" });
    expect(link.getAttribute("href")).toBe("/api/sessions/s%201/downloads/prd-v1.0.docx");
    expect(link.getAttribute("download")).toBe("PRD v1.0.docx");
    await waitFor(() => expect(screen.getByText("Downloads (1)")).toBeTruthy());
    expect(screen.getByText(/URL shortener - Blueprint.zip/).textContent).toContain("available once the ticket breakdown is approved");
  });

  it("names every kind as SPECS S10.2 does", () => {
    expect(downloadFileName("user-stories.docx", "x")).toBe("UserStories.docx");
    expect(downloadFileName("bundle.zip", "My design")).toBe("My design - Blueprint.zip");
  });
});

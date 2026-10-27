// @vitest-environment jsdom
// T-10: the gap register (SPECS S11.2) lists each gap's lens, severity, affected items, risk
// and decision needed.
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { GapRegister } from "../components/review/GapRegister";
import { EMPTY_DESIGN, type Gap, itemLabel } from "../lib/state";

afterEach(cleanup);

const design = {
  ...EMPTY_DESIGN,
  endpoints: [{ id: "EP-1", method: "POST", path: "/urls", request: "", response: "", errors: [] }],
  non_functional_requirements: [{ id: "NFR-1", category: "latency" as const, statement: "Fast redirects" }],
};

it("shows every gap with its fields and affected items by name", () => {
  const gaps: Gap[] = [
    { id: "GAP-1", lens: "security", item_ids: ["EP-1"], risk: "Anyone can create codes", decision_needed: "Who may create codes?", severity: "high", status: "open", resolved_by: [], feature_ids: [] },
    { id: "GAP-2", lens: "efficiency", item_ids: ["NFR-1"], risk: "No cache", decision_needed: "Cache hot codes?", severity: "low", status: "accepted", note: "Fine for v1", resolved_by: [], feature_ids: [] },
  ];
  render(<GapRegister gaps={gaps} design={design} stage="gap_resolution" />);
  const rows = within(screen.getByRole("table")).getAllByRole("row").slice(1);
  expect(rows.map((r) => within(r).getAllByRole("cell").map((c) => c.textContent))).toEqual([
    ["security", "high", "EP-1: POST /urls", "Anyone can create codes", "Who may create codes?", "open"],
    ["efficiency", "low", "NFR-1: Fast redirects", "No cache", "Cache hot codes?", "acceptedNote: Fine for v1"],
  ]);
  expect(within(rows[0]).getByRole("rowheader").textContent).toBe("GAP-1");
  expect(screen.getByText("2 gaps, 1 open.")).toBeTruthy();
});

it("says the review is running while the judges work", () => {
  render(<GapRegister gaps={[]} design={design} stage="design_review" />);
  expect(screen.getByText(/design judges are reviewing/)).toBeTruthy();
});

it("labels any item ID with its name", () => {
  expect(itemLabel(design, "EP-1")).toBe("EP-1: POST /urls");
  expect(itemLabel(design, "CMP-9")).toBe("CMP-9");
});

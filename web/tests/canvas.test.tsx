// @vitest-environment jsdom
// T-03: the canvas shows the Step 1 panels with item IDs (SPECS S11.2, S11.3), and the
// workspace prefers the agent's live state over the REST snapshot.
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { Canvas } from "../components/canvas/Canvas";
import { EMPTY_DESIGN, liveState, type SessionState } from "../lib/state";

afterEach(cleanup);

function panel(title: RegExp) {
  return screen.getByRole("region", { name: title });
}

describe("Canvas", () => {
  it("renders every Step 1 item under its panel with its ID", () => {
    render(
      <Canvas
        design={{
          ...EMPTY_DESIGN,
          functional_requirements: [{ id: "FR-1", statement: "Users shorten a long URL" }],
          non_functional_requirements: [
            { id: "NFR-1", category: "latency", statement: "Fast redirects", metric: "p95", target: 50, unit: "ms" },
          ],
          out_of_scope: [{ id: "OOS-1", text: "Analytics" }],
          capacity_estimates: [
            { id: "EST-1", quantity: "Writes per second", formula: "100M / 86400", result: 1157.4, unit: "writes/s" },
          ],
        }}
      />,
    );
    expect(within(panel(/Functional requirements/)).getByText("FR-1")).toBeTruthy();
    expect(within(panel(/Functional requirements/)).getByText("Users shorten a long URL")).toBeTruthy();
    const nfr = panel(/Non-functional requirements/);
    expect(within(nfr).getByText("NFR-1")).toBeTruthy();
    expect(within(nfr).getByText("p95 50 ms")).toBeTruthy();
    expect(within(panel(/Out of scope/)).getByText("OOS-1")).toBeTruthy();
    const estimates = panel(/Capacity estimates/);
    expect(within(estimates).getByText("100M / 86400")).toBeTruthy();
    expect(estimates.textContent).toContain("= 1157.4 writes/s");
  });

  it("shows empty panels before anything is recorded", () => {
    render(<Canvas design={EMPTY_DESIGN} />);
    expect(screen.getAllByText("Nothing recorded yet.")).toHaveLength(4);
  });
});

describe("liveState", () => {
  const snapshot = { design: EMPTY_DESIGN, stage: "interview", current_step: 1 } as SessionState;

  it("uses the REST snapshot until the agent has sent state", () => {
    expect(liveState({}, snapshot)).toBe(snapshot);
    expect(liveState(undefined, snapshot)).toBe(snapshot);
  });

  it("uses the agent's state once it arrives", () => {
    const design = { ...EMPTY_DESIGN, out_of_scope: [{ id: "OOS-1", text: "x" }] };
    expect(liveState({ design, current_step: 2 }, snapshot)).toMatchObject({ design, current_step: 2 });
  });
});

// @vitest-environment jsdom
// T-08: the scorecard is shown in the workspace, and the canvas has the Step 4-5 panels.
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { Canvas } from "../components/canvas/Canvas";
import { ScorecardPanel } from "../components/review/ScorecardPanel";
import { EMPTY_DESIGN, type Scorecard } from "../lib/state";

afterEach(cleanup);

it("shows five dimension scores with quoted evidence and advice", () => {
  const dimensions = (["communication", "structure", "judgment", "depth", "time"] as const).map((dimension, i) => ({
    dimension,
    score: i + 1 > 4 ? 4 : i + 1,
    evidence: [`quote ${i}`],
    advice: `advice ${i}`,
  }));
  render(<ScorecardPanel scorecard={{ dimensions } as Scorecard} />);
  const section = screen.getByRole("region", { name: "Scorecard" });
  const items = within(section).getAllByRole("listitem");
  expect(items).toHaveLength(5);
  expect(items[2].textContent).toContain("Technical judgment");
  expect(within(items[2]).getByLabelText("score 3 out of 4")).toBeTruthy();
  expect(items[2].textContent).toContain("“quote 2”");
  expect(items[2].textContent).toContain("Advice: advice 2");
});

it("shows SPOFs with their mitigation, signals, trade-offs and extensions", () => {
  render(
    <Canvas
      design={{
        ...EMPTY_DESIGN,
        components: [{ id: "CMP-1", name: "DB", kind: "database", responsibility: "" }],
        spofs: [
          { id: "SPOF-1", component_id: "CMP-1", risk: "single node", mitigation: "replica" },
          { id: "SPOF-2", component_id: "CMP-1", risk: "disk" },
        ],
        observability: [{ id: "OBS-1", kind: "alert", name: "p95 latency", threshold: "> 50 ms" }],
        tradeoffs: [{ id: "TRD-1", decision: "AP", gained: "uptime", sacrificed: "freshness" }],
        extensions: [{ id: "EXT-1", text: "multi-region" }],
      }}
    />,
  );
  const spofs = screen.getByRole("region", { name: /Single points of failure/ });
  expect(spofs.textContent).toContain("DB (CMP-1): single nodeMitigation: replica");
  expect(spofs.textContent).toContain("Mitigation: none yet");
  expect(screen.getByRole("region", { name: /Observability/ }).textContent).toContain("Threshold: > 50 ms");
  expect(screen.getByRole("region", { name: /Trade-offs/ }).textContent).toContain("Gained: uptime · Sacrificed: freshness");
  expect(within(screen.getByRole("region", { name: /Extensions/ })).getByText("EXT-1")).toBeTruthy();
});

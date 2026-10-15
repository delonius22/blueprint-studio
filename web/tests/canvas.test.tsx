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
    expect(screen.getAllByText("Nothing recorded yet.")).toHaveLength(17);
  });
});

describe("Canvas Step 2 panels", () => {
  it("shows entities, relationships, endpoints and storage choices with their IDs", () => {
    render(
      <Canvas
        design={{
          ...EMPTY_DESIGN,
          entities: [
            { id: "ENT-1", name: "User", fields: [{ name: "id", type: "uuid", key: "pk" }], indexes: [] },
            {
              id: "ENT-2",
              name: "Url",
              fields: [{ name: "owner_id", type: "uuid", key: "fk", references: "ENT-1" }],
              indexes: ["owner_id"],
              est_record_bytes: 500,
            },
          ],
          relationships: [{ id: "REL-1", from_entity: "ENT-1", to_entity: "ENT-2", cardinality: "1:N" }],
          endpoints: [
            { id: "EP-1", method: "POST", path: "/urls", request: "{target}", response: "{code}", errors: [] },
          ],
          storage_choices: [
            {
              id: "STO-1",
              data: "URL mappings",
              technology: "Cassandra",
              justification: "",
              rejected_alternatives: ["PostgreSQL"],
              status: "proposed",
            },
          ],
        }}
      />,
    );
    const entities = panel(/^Entities/);
    expect(within(entities).getByText("ENT-2")).toBeTruthy();
    expect(entities.textContent).toContain("owner_id: uuidFK → ENT-1");
    expect(entities.textContent).toContain("~500 bytes per record");
    expect(panel(/Relationships/).textContent).toContain("User (ENT-1) 1:N Url (ENT-2)");
    expect(within(panel(/API endpoints/)).getByText("EP-1")).toBeTruthy();
    const storage = panel(/Storage choices/);
    expect(within(storage).getByText("STO-1")).toBeTruthy();
    expect(within(storage).getByText("proposed")).toBeTruthy();
    expect(storage.textContent).toContain("Rejected: PostgreSQL");
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

describe("Canvas Step 3 panels", () => {
  it("shows the CAP stance, cache policies and failure modes", () => {
    render(
      <Canvas
        design={{
          ...EMPTY_DESIGN,
          cap_stance: { choice: "AP", rationale: "Redirects must stay available" },
          cache_policies: [{ id: "CACHE-1", data: "hot codes", strategy: "cache-aside", eviction: "LRU", ttl_seconds: 3600 }],
          failure_modes: [{ id: "FM-1", scenario: "Primary DB fails", behaviour: "Serve from replicas", recovery: "Promote" }],
        }}
      />,
    );
    expect(panel(/CAP stance/).textContent).toContain("APRedirects must stay available");
    expect(panel(/Cache policies/).textContent).toContain("cache-aside · LRU · TTL 3600 s");
    const failures = panel(/Failure modes/);
    expect(within(failures).getByText("FM-1")).toBeTruthy();
    expect(failures.textContent).toContain("Recovery: Promote");
  });
});

// @vitest-environment jsdom
// T-06: the Mermaid source is a pure function of the design (SPECS S11.3), and the diagram
// panels render it and show the source in a collapsible block.
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AllDiagrams, ArchitectureDiagram, DataModelDiagram, SequenceDiagrams } from "../components/canvas/Diagrams";
import { dataModelToMermaid, designToMermaid } from "../lib/mermaid";
import { type Component, EMPTY_DESIGN, type Flow } from "../lib/state";

afterEach(cleanup);

const kinds: Component["kind"][] = [
  "client", "gateway", "load_balancer", "service", "cache", "queue",
  "database", "object_store", "search", "cdn", "external",
];  // prettier-ignore
const components: Component[] = kinds.map((kind, i) => ({
  id: `CMP-${i + 1}`,
  name: `${kind} node`,
  kind,
  responsibility: "",
}));
const flows: Flow[] = [
  { id: "FLW-1", name: "Resolve", kind: "read", steps: [{ from_component: "CMP-1", to_component: "CMP-4", label: 'GET "/{code}"' }] },
  { id: "FLW-2", name: "Create", kind: "write", steps: [{ from_component: "CMP-4", to_component: "CMP-7", label: "insert" }] },
];

describe("designToMermaid", () => {
  it("gives each component kind its own shape and each flow step one labelled edge", () => {
    const source = designToMermaid({ components, flows });
    expect(source).toBe(
      [
        "flowchart LR",
        "  %% read flows: solid arrows; write flows: dotted arrows",
        '  CMP_1(["CMP-1: client node"])',
        '  CMP_2{{"CMP-2: gateway node"}}',
        '  CMP_3[/"CMP-3: load_balancer node"\\]',
        '  CMP_4["CMP-4: service node"]',
        '  CMP_5("CMP-5: cache node")',
        '  CMP_6[["CMP-6: queue node"]]',
        '  CMP_7[("CMP-7: database node")]',
        '  CMP_8>"CMP-8: object_store node"]',
        '  CMP_9{"CMP-9: search node"}',
        '  CMP_10(("CMP-10: cdn node"))',
        '  CMP_11[/"CMP-11: external node"/]',
        '  CMP_1 -->|"GET #quot;/{code}#quot;"| CMP_4',
        '  CMP_4 -.->|"insert"| CMP_7',
        "",
      ].join("\n"),
    );
  });

  it("is deterministic and depends only on components and flows", () => {
    const first = designToMermaid({ components, flows });
    const second = designToMermaid({ components: structuredClone(components), flows: structuredClone(flows) });
    expect(second).toBe(first);
    const shapes = components.map((c) => designToMermaid({ components: [c], flows: [] }).split("\n")[2]);
    const delimiters = shapes.map((line) => line.replace(/"[^"]*"/, "").replace(/^\s*CMP_\d+/, ""));
    expect(new Set(delimiters).size).toBe(kinds.length);
  });
});

describe("Diagram panels", () => {
  it("renders the SVG and shows the source in a collapsible block", async () => {
    const renderer = vi.fn(async () => '<svg data-testid="diagram"><text>ok</text></svg>');
    render(<ArchitectureDiagram design={{ ...EMPTY_DESIGN, components, flows }} render={renderer} />);

    await waitFor(() => expect(screen.getByTestId("diagram")).toBeTruthy());
    expect(renderer).toHaveBeenCalledWith(expect.stringMatching(/^diagram-/), designToMermaid({ components, flows }));
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("11 components and 2 flows");
    const summary = screen.getByText("Mermaid source");
    expect(summary.tagName).toBe("SUMMARY");
    expect(summary.closest("details")?.textContent).toContain("flowchart LR");
  });

  it("says there is nothing to draw before any component exists", () => {
    const renderer = vi.fn();
    render(<ArchitectureDiagram design={EMPTY_DESIGN} render={renderer} />);
    expect(screen.getByText(/Nothing to draw yet/)).toBeTruthy();
    expect(renderer).not.toHaveBeenCalled();
  });

  it("draws the data model once entities exist", async () => {
    const renderer = vi.fn(async () => "<svg></svg>");
    const design = {
      ...EMPTY_DESIGN,
      entities: [{ id: "ENT-1", name: "Link", fields: [{ name: "code", type: "char(7)", key: "pk" as const }], indexes: [] }],
    };
    render(<DataModelDiagram design={EMPTY_DESIGN} render={renderer} />);
    expect(screen.getByText(/appears once entities are recorded/)).toBeTruthy();
    cleanup();
    render(<DataModelDiagram design={design} render={renderer} />);
    await waitFor(() => expect(renderer).toHaveBeenCalledWith(expect.any(String), dataModelToMermaid(design)));
    expect(screen.getByRole("img").getAttribute("aria-label")).toContain("1 entity and 0 relationships");
  });

  it("draws one sequence diagram per flow", () => {
    render(<SequenceDiagrams design={{ ...EMPTY_DESIGN, components, flows }} render={vi.fn(async () => "<svg></svg>")} />);
    expect(screen.getByRole("heading", { name: "Sequence: FLW-1 Resolve (read)" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Sequence: FLW-2 Create (write)" })).toBeTruthy();
  });

  it("shows every diagram at the end, or nothing when nothing was recorded", () => {
    const renderer = vi.fn(async () => "<svg></svg>");
    const { container } = render(<AllDiagrams design={EMPTY_DESIGN} render={renderer} />);
    expect(container.textContent).toBe("");
    cleanup();
    render(<AllDiagrams design={{ ...EMPTY_DESIGN, components, flows }} render={renderer} />);
    const titles = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titles).toEqual(["Architecture diagram", "Sequence: FLW-1 Resolve (read)", "Sequence: FLW-2 Create (write)"]);
  });
});

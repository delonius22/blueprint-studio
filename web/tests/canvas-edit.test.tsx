// @vitest-environment jsdom
// T-09: every canvas panel supports add, edit and delete, written as a whole design with
// S2.5 IDs from id_counters (SPECS S11.3); the agent validates each write (S2.15).
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Canvas } from "../components/canvas/Canvas";
import { CanvasEditContext, type CanvasEditor } from "../components/canvas/CanvasEdit";
import { addItem, deleteItem, FIELDS, issueId, PREFIXES, parseValues, updateItem } from "../lib/editing";
import { EMPTY_DESIGN, type Design } from "../lib/state";

afterEach(cleanup);
beforeEach(() => vi.stubGlobal("confirm", vi.fn(() => true)));

const design: Design = {
  ...EMPTY_DESIGN,
  functional_requirements: [{ id: "FR-1", statement: "Shorten URLs" }],
  components: [{ id: "CMP-1", name: "API", kind: "service", responsibility: "" }],
  storage_choices: [
    { id: "STO-1", data: "URLs", technology: "Cassandra", justification: "100:1 reads", rejected_alternatives: [], status: "decided" },
  ],
};
const counters = { FR: 2, CMP: 1, STO: 1 }; // FR-2 was deleted earlier

function renderEditable(save = vi.fn()) {
  const editor: CanvasEditor = { design, counters, disabled: false, save };
  render(
    <CanvasEditContext.Provider value={editor}>
      <Canvas design={design} />
    </CanvasEditContext.Provider>,
  );
  return save;
}

describe("editing helpers", () => {
  it("covers every Design list with a prefix and field specs", () => {
    expect(Object.keys(PREFIXES).sort()).toEqual(Object.keys(EMPTY_DESIGN).filter((k) => k !== "cap_stance").sort());
    expect(Object.keys(FIELDS).sort()).toEqual(Object.keys(PREFIXES).sort());
  });

  it("issues the next ID from the counter, so deleted IDs are never reused", () => {
    expect(issueId({ FR: 2 }, "FR")).toEqual({ id: "FR-3", counters: { FR: 3 } });
    const added = addItem(design, counters, "functional_requirements", { statement: "Redirect" });
    expect(added.id).toBe("FR-3");
    expect(added.counters.FR).toBe(3);
    expect(deleteItem(added.design, "functional_requirements", "FR-3").functional_requirements).toHaveLength(1);
    expect(addItem(design, counters, "storage_choices", { data: "d", technology: "t" }).design.storage_choices[1].status).toBe("proposed");
  });

  it("sends a storage choice changed by hand back to proposed", () => {
    const changed = updateItem(design, "storage_choices", "STO-1", { technology: "DynamoDB" });
    expect(changed.storage_choices[0].status).toBe("proposed");
    expect(updateItem(design, "storage_choices", "STO-1", { justification: "x" }).storage_choices[0].status).toBe("decided");
  });

  it("explains what a form is missing before anything is written", () => {
    expect(parseValues("capacity_estimates", { quantity: "QPS", formula: "", result: "abc", unit: "" }).problems).toEqual([
      "Formula is required",
      "Result must be a number",
      "Unit is required",
    ]);
    expect(
      parseValues("entities", { name: "Url", fields: [{ name: "owner", type: "uuid", key: "fk", references: "" }], indexes: "", est_record_bytes: "" })
        .problems,
    ).toEqual(["Fields 1: a foreign key must reference an entity"]);
  });
});

describe("editable canvas", () => {
  it("adds an item with a new ID", async () => {
    const save = renderEditable();
    const panel = screen.getByRole("region", { name: /^Functional requirements/ });
    await userEvent.click(within(panel).getByRole("button", { name: "Add to Functional requirements" }));
    await userEvent.type(within(panel).getByLabelText("Requirement"), "Redirect visitors");
    await userEvent.click(within(panel).getByRole("button", { name: "Save" }));

    const [written, writtenCounters] = save.mock.calls[0];
    expect(written.functional_requirements).toEqual([
      { id: "FR-1", statement: "Shorten URLs" },
      { id: "FR-3", statement: "Redirect visitors" },
    ]);
    expect(writtenCounters).toEqual({ FR: 3, CMP: 1, STO: 1 });
  });

  it("edits and deletes an item by ID", async () => {
    const save = renderEditable();
    await userEvent.click(screen.getByRole("button", { name: "Edit FR-1" }));
    const field = screen.getByLabelText("Requirement");
    await userEvent.clear(field);
    await userEvent.type(field, "Shorten long URLs");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(save.mock.calls[0][0].functional_requirements).toEqual([{ id: "FR-1", statement: "Shorten long URLs" }]);

    await userEvent.click(screen.getByRole("button", { name: "Delete CMP-1" }));
    expect(save.mock.calls[1][0].components).toEqual([]);
    expect(save.mock.calls[1][1]).toEqual(counters);
  });

  it("sets the CAP stance", async () => {
    const save = renderEditable();
    await userEvent.click(screen.getByRole("button", { name: "Set CAP stance" }));
    await userEvent.selectOptions(screen.getByLabelText("Choice"), "AP");
    await userEvent.type(screen.getByLabelText("Rationale"), "Redirects stay up");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(save.mock.calls[0][0].cap_stance).toEqual({ choice: "AP", rationale: "Redirects stay up" });
  });

  it("offers no editing where the canvas is read-only", () => {
    render(<Canvas design={design} />);
    expect(screen.queryByRole("button", { name: /^(Add to|Edit|Delete) / })).toBeNull();
  });
});

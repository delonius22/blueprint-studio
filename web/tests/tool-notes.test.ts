// The interviewer's design tool calls show in the chat as one line each.
import { expect, it } from "vitest";
import { toolNote } from "../lib/tool-notes";

it("names what was recorded, with its statement", () => {
  expect(toolNote({ statement: "Users shorten a long URL" }, '{"recorded": "FR-1"}')).toBe(
    "✓ Recorded FR-1: Users shorten a long URL",
  );
  expect(toolNote({ name: "Link", fields: [] }, '{"recorded": "ENT-1", "note": "x"}')).toBe("✓ Recorded ENT-1: Link");
  expect(toolNote({ choice: "AP", rationale: "r" }, '{"recorded": "cap_stance"}')).toBe("✓ Recorded the CAP stance");
});

it("names decisions, resolutions and deletions", () => {
  expect(toolNote({ id: "STO-1" }, '{"decided": "STO-1"}')).toBe("✓ Decided STO-1");
  expect(toolNote({ gap_id: "GAP-1" }, '{"resolved": "GAP-1"}')).toBe("✓ Resolved GAP-1");
  expect(toolNote({ item_id: "FR-2" }, '{"deleted": "FR-2"}')).toBe("✓ Deleted FR-2");
});

it("shows nothing while running, on failure, or for anything unexpected", () => {
  expect(toolNote({ statement: "x" }, undefined)).toBeNull();
  expect(toolNote({ statement: "x" }, '{"error": "invalid arguments"}')).toBeNull();
  expect(toolNote({}, "not json")).toBeNull();
  expect(toolNote({}, "{}")).toBeNull();
});

it("keeps long statements to one short line", () => {
  const note = toolNote({ statement: `${"word ".repeat(40)}\nend` }, '{"recorded": "FR-3"}');
  expect(note?.length).toBeLessThanOrEqual("✓ Recorded FR-3: ".length + 90);
  expect(note?.endsWith("…")).toBe(true);
});

// @vitest-environment jsdom
// The browser and the downloads draw the same diagrams: web/lib/mermaid.ts and
// agent/src/blueprint/diagrams.py are both checked against agent/tests/expected/diagrams/,
// and every diagram there is valid Mermaid.
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { dataModelToMermaid, designToMermaid, flowToSequence } from "../lib/mermaid";
import { type Design, EMPTY_DESIGN } from "../lib/state";

const EXPECTED = join(__dirname, "..", "..", "agent", "tests", "expected", "diagrams");
const read = (name: string) => readFileSync(join(EXPECTED, name), "utf-8");
const design: Design = { ...EMPTY_DESIGN, ...JSON.parse(read("design.json")) };

describe("the diagrams match the agent's, byte for byte", () => {
  it("architecture", () => expect(designToMermaid(design)).toBe(read("architecture.mmd")));
  it("data model", () => expect(dataModelToMermaid(design)).toBe(read("data-model.mmd")));
  for (const flow of design.flows) {
    it(`sequence of ${flow.id}`, () =>
      expect(flowToSequence(flow, design.components)).toBe(read(`sequence-${flow.id}.mmd`)));
  }
});

describe("every expected diagram is valid Mermaid", () => {
  for (const name of readdirSync(EXPECTED).filter((f) => f.endsWith(".mmd"))) {
    it(name, async () => {
      const { default: mermaid } = await import("mermaid");
      await expect(mermaid.parse(read(name))).resolves.toBeTruthy();
    });
  }
});

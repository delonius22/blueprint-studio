// @vitest-environment jsdom
// T-06: the generated source is valid Mermaid for every component kind and both flow kinds.
import { expect, it } from "vitest";
import { designToMermaid } from "../lib/mermaid";
import type { Component } from "../lib/state";

it("parses with mermaid", async () => {
  const { default: mermaid } = await import("mermaid");
  const kinds: Component["kind"][] = [
    "client", "gateway", "load_balancer", "service", "cache", "queue",
    "database", "object_store", "search", "cdn", "external",
  ];  // prettier-ignore
  const components = kinds.map((kind, i) => ({ id: `CMP-${i + 1}`, name: `${kind} "x" (y)`, kind, responsibility: "" }));
  const source = designToMermaid({
    components,
    flows: [
      { id: "FLW-1", name: "r", kind: "read", steps: [{ from_component: "CMP-1", to_component: "CMP-2", label: "GET /a|b" }] },
      { id: "FLW-2", name: "w", kind: "write", steps: [{ from_component: "CMP-2", to_component: "CMP-7", label: "" }] },
    ],
  });
  await expect(mermaid.parse(source)).resolves.toBeTruthy();
  await expect(mermaid.parse("flowchart LR\n  A[[[")).rejects.toThrow();
});

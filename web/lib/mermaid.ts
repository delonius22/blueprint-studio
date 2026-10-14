// The architecture diagram as Mermaid source (SPECS S11.3, PRD D12): a pure function of the
// components and flows, so the same design always gives the same source.
import type { Component, Design } from "./state";

// Opening and closing delimiters of each component kind's node shape.
const SHAPES: Record<Component["kind"], readonly [string, string]> = {
  client: ['(["', '"])'],
  gateway: ['{{"', '"}}'],
  load_balancer: ['[/"', '"\\]'],
  service: ['["', '"]'],
  cache: ['("', '")'],
  queue: ['[["', '"]]'],
  database: ['[("', '")]'],
  object_store: ['>"', '"]'],
  search: ['{"', '"}'],
  cdn: ['(("', '"))'],
  external: ['[/"', '"/]'],
};

function nodeId(id: string): string {
  return id.replace(/[^A-Za-z0-9]/g, "_");
}

function text(value: string): string {
  return value.replace(/"/g, "#quot;").replace(/\s+/g, " ").trim();
}

export function designToMermaid(design: Pick<Design, "components" | "flows">): string {
  const lines = ["flowchart LR", "  %% read flows: solid arrows; write flows: dotted arrows"];
  for (const component of design.components) {
    const [open, close] = SHAPES[component.kind];
    lines.push(`  ${nodeId(component.id)}${open}${text(`${component.id}: ${component.name}`)}${close}`);
  }
  for (const flow of design.flows) {
    const arrow = flow.kind === "write" ? "-.->" : "-->";
    for (const step of flow.steps) {
      const label = text(step.label);
      const edge = label ? `${arrow}|"${label}"|` : arrow;
      lines.push(`  ${nodeId(step.from_component)} ${edge} ${nodeId(step.to_component)}`);
    }
  }
  return `${lines.join("\n")}\n`;
}

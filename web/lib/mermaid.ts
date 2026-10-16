// The design as Mermaid source (SPECS S11.3, PRD D12): pure functions of the design, so the
// same design always gives the same source. agent/src/blueprint/diagrams.py draws the same
// diagrams for the downloads; both are checked against agent/tests/expected/diagrams/.
import type { Component, Design } from "./state";

type Entity = Design["entities"][number];
type Flow = Design["flows"][number];

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

// Crow's-foot ends of each relationship cardinality.
const CARDINALITY: Record<Design["relationships"][number]["cardinality"], string> = {
  "1:1": "||--||",
  "1:N": "||--o{",
  "N:M": "}o--o{",
};

function nodeId(id: string): string {
  return id.replace(/[^A-Za-z0-9]/g, "_");
}

function text(value: string): string {
  return value.replace(/"/g, "#quot;").replace(/\s+/g, " ").trim();
}

// An ER attribute type or name as Mermaid allows it: letters, digits, '_', '-', '(', ')', '['
// and ']', starting with a letter.
function word(value: string): string {
  const cleaned = value.trim().replace(/[^A-Za-z0-9_()[\]-]/g, "_") || "x";
  return /^[A-Za-z]/.test(cleaned) ? cleaned : `x${cleaned}`;
}

const ENTITY_CODES: Record<string, string> = { "#": "#35;", ";": "#59;" };

// Sequence-diagram text: one line, with '#' and ';' written as entity codes.
function message(value: string): string {
  return value
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[#;]/g, (c) => ENTITY_CODES[c]);
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

function entityLines(entity: Entity): string[] {
  const head = `  ${nodeId(entity.id)}["${text(`${entity.id}: ${entity.name}`)}"]`;
  if (entity.fields.length === 0) return [head];
  const lines = [`${head} {`];
  for (const field of entity.fields) {
    let line = `    ${word(field.type)} ${word(field.name)}`;
    if (field.key !== "none") line += ` ${field.key.toUpperCase()}`;
    if (field.key === "fk" && field.references) line += ` "references ${text(field.references)}"`;
    lines.push(line);
  }
  return [...lines, "  }"];
}

export function dataModelToMermaid(design: Pick<Design, "entities" | "relationships">): string {
  const lines = ["erDiagram"];
  for (const entity of design.entities) lines.push(...entityLines(entity));
  for (const relationship of design.relationships) {
    lines.push(
      `  ${nodeId(relationship.from_entity)} ${CARDINALITY[relationship.cardinality]} ` +
        `${nodeId(relationship.to_entity)} : "${text(relationship.id)}"`,
    );
  }
  return `${lines.join("\n")}\n`;
}

export function flowToSequence(flow: Flow, components: Component[]): string {
  const names = new Map(components.map((c) => [c.id, c.name]));
  const participants: string[] = [];
  for (const step of flow.steps) {
    for (const id of [step.from_component, step.to_component]) {
      if (!participants.includes(id)) participants.push(id);
    }
  }
  const lines = ["sequenceDiagram"];
  for (const id of participants) {
    const name = names.get(id);
    lines.push(`  participant ${nodeId(id)} as ${message(name === undefined ? id : `${id}: ${name}`)}`);
  }
  // Writes are dotted, as in the flowchart.
  const arrow = flow.kind === "write" ? "-->>" : "->>";
  flow.steps.forEach((step, index) => {
    const label = message(step.label) || `step ${index + 1}`;
    lines.push(`  ${nodeId(step.from_component)}${arrow}${nodeId(step.to_component)}: ${label}`);
  });
  return `${lines.join("\n")}\n`;
}

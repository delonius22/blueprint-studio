"use client";

// The design's diagrams (SPECS S11.3): the data model, the architecture and one sequence per
// flow, drawn from the same pure functions the downloads use (agent/src/blueprint/diagrams.py).
import { useMemo } from "react";
import { dataModelToMermaid, designToMermaid, flowToSequence } from "../../lib/mermaid";
import type { MermaidRenderer } from "../../lib/mermaid-render";
import type { Design } from "../../lib/state";
import { DiagramPanel } from "./DiagramPanel";

type Props = { design: Design; render?: MermaidRenderer };

const plural = (count: number, one: string, many = `${one}s`) => `${count} ${count === 1 ? one : many}`;

export function DataModelDiagram({ design, render }: Props) {
  const source = useMemo(() => dataModelToMermaid(design), [design]);
  return (
    <DiagramPanel
      title="Data model diagram"
      source={source}
      description={`Data model diagram of ${plural(design.entities.length, "entity", "entities")} and ${plural(design.relationships.length, "relationship")}`}
      empty={design.entities.length === 0 ? "Nothing to draw yet: the diagram appears once entities are recorded." : null}
      render={render}
    />
  );
}

export function ArchitectureDiagram({ design, render }: Props) {
  const source = useMemo(() => designToMermaid(design), [design]);
  return (
    <DiagramPanel
      title="Architecture diagram"
      source={source}
      description={`Architecture diagram of ${plural(design.components.length, "component")} and ${plural(design.flows.length, "flow")}`}
      empty={design.components.length === 0 ? "Nothing to draw yet: the diagram appears once components are recorded." : null}
      render={render}
    />
  );
}

export function SequenceDiagrams({ design, render }: Props) {
  const flows = design.flows.filter((flow) => flow.steps.length > 0);
  return (
    <>
      {flows.map((flow) => (
        <DiagramPanel
          key={flow.id}
          title={`Sequence: ${flow.id} ${flow.name} (${flow.kind})`}
          source={flowToSequence(flow, design.components)}
          description={`Sequence diagram of the ${flow.kind} flow ${flow.name} in ${plural(flow.steps.length, "step")}`}
          render={render}
        />
      ))}
    </>
  );
}

// Every diagram there is something to draw for: shown with the downloads once the design is done.
export function AllDiagrams({ design, render }: Props) {
  if (design.components.length === 0 && design.entities.length === 0) return null;
  return (
    <section aria-labelledby="all-diagrams-title">
      <h2 id="all-diagrams-title">Diagrams</h2>
      {design.components.length > 0 && <ArchitectureDiagram design={design} render={render} />}
      {design.entities.length > 0 && <DataModelDiagram design={design} render={render} />}
      <SequenceDiagrams design={design} render={render} />
    </section>
  );
}

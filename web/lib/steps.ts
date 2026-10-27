// The five framework steps (PRD G1), as named in the course context.
export const STEP_NAMES: Record<number, string> = {
  1: "Clarify requirements",
  2: "Data & API layer",
  3: "High-level architecture",
  4: "Scale, bottlenecks & reliability",
  5: "Trade-offs & extensions",
};

// Each design list's name as the canvas titles it.
export const LIST_LABELS: Record<string, string> = {
  functional_requirements: "Functional requirements",
  non_functional_requirements: "Non-functional requirements",
  out_of_scope: "Out of scope",
  capacity_estimates: "Capacity estimates",
  entities: "Entities",
  relationships: "Relationships",
  endpoints: "API endpoints",
  storage_choices: "Storage choices",
  components: "Components",
  flows: "Data flows",
  cache_policies: "Cache policies",
  spofs: "Single points of failure",
  failure_modes: "Failure modes",
  observability: "Observability",
  tradeoffs: "Trade-offs",
  extensions: "Extensions",
};

// Session state types (SPECS S2), generated from the agent's OpenAPI document (S3.7).
import type { components } from "./api-schema";

type Schemas = components["schemas"];
export type SessionState = Schemas["SessionState"];
export type Design = Schemas["Design"];
export type Requirement = Schemas["Requirement"];
export type NfrTarget = Schemas["NfrTarget"];
export type Note = Schemas["Note"];
export type Estimate = Schemas["Estimate"];
export type Entity = Schemas["Entity"];
export type Relationship = Schemas["Relationship"];
export type Endpoint = Schemas["Endpoint"];
export type StorageChoice = Schemas["StorageChoice"];
export type Component = Schemas["Component"];
export type Flow = Schemas["Flow"];
export type CachePolicy = Schemas["CachePolicy"];
export type FailureMode = Schemas["FailureMode"];
export type Scorecard = Schemas["Scorecard"];
export type Gap = Schemas["Gap"];
export type PrdDoc = Schemas["PrdDoc"];
export type PrdVersion = Schemas["PrdVersion"];
export type Ticket = Schemas["Ticket"];

/** Build waves: wave n holds the tickets whose blockers are all in earlier waves. */
export function buildWaves(tickets: Ticket[]): Ticket[][] {
  const waves: Ticket[][] = [];
  const placed = new Set<string>();
  let remaining = [...tickets];
  while (remaining.length) {
    const wave = remaining.filter((t) => (t.blocked_by ?? []).every((b) => placed.has(b)));
    if (wave.length === 0) break; // an invalid graph never reaches the browser (S9.3)
    waves.push(wave);
    for (const t of wave) placed.add(t.id);
    remaining = remaining.filter((t) => !placed.has(t.id));
  }
  return waves;
}

/** "EP-1: POST /urls" for any design item ID, or the bare ID if it is unknown. */
export function itemLabel(design: Design, id: string): string {
  for (const list of Object.values(design)) {
    if (!Array.isArray(list)) continue;
    const item = (list as Record<string, unknown>[]).find((i) => i.id === id);
    if (!item) continue;
    const name =
      item.name ?? item.statement ?? item.text ?? item.scenario ?? item.decision ?? item.data ??
      (item.method ? `${item.method} ${item.path}` : undefined) ?? item.quantity ?? item.risk;
    return name ? `${id}: ${String(name)}` : id;
  }
  return id;
}

export const EMPTY_DESIGN: Design = {
  functional_requirements: [],
  non_functional_requirements: [],
  out_of_scope: [],
  capacity_estimates: [],
  entities: [],
  relationships: [],
  endpoints: [],
  storage_choices: [],
  components: [],
  flows: [],
  cap_stance: null,
  cache_policies: [],
  spofs: [],
  failure_modes: [],
  observability: [],
  tradeoffs: [],
  extensions: [],
};

/** The agent's live state, filled with the REST snapshot until the first state event arrives. */
export function liveState(agentState: unknown, fallback: SessionState): SessionState {
  const live = (agentState ?? {}) as Partial<SessionState>;
  return live.design ? { ...fallback, ...live } : fallback;
}

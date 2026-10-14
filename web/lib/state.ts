// Session state types (SPECS S2), generated from the agent's OpenAPI document (S3.7).
import type { components } from "./api-schema";

type Schemas = components["schemas"];
export type SessionState = Schemas["SessionState"];
export type Design = Schemas["Design"];
export type Requirement = Schemas["Requirement"];
export type NfrTarget = Schemas["NfrTarget"];
export type Note = Schemas["Note"];
export type Estimate = Schemas["Estimate"];

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

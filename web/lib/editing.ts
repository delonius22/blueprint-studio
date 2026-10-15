// Direct canvas edits (SPECS S11.3, S2.5, S2.15): field specs for every Design list, ID
// issuance from id_counters, and pure add/update/delete. The agent validates every write.
import type { Design } from "./state";

export type ListName = Exclude<keyof Design, "cap_stance">;
export type Counters = Record<string, number>;
type Item = { id: string } & Record<string, unknown>;

// S2.6: the ID prefix of every Design list.
export const PREFIXES: Record<ListName, string> = {
  functional_requirements: "FR",
  non_functional_requirements: "NFR",
  out_of_scope: "OOS",
  capacity_estimates: "EST",
  entities: "ENT",
  relationships: "REL",
  endpoints: "EP",
  storage_choices: "STO",
  components: "CMP",
  flows: "FLW",
  cache_policies: "CACHE",
  spofs: "SPOF",
  failure_modes: "FM",
  observability: "OBS",
  tradeoffs: "TRD",
  extensions: "EXT",
};

export type FieldKind =
  | "text"
  | "textarea"
  | "number"
  | "integer"
  | "select"
  | "lines"
  | "ref"
  | "entityFields"
  | "flowSteps";

export type FieldSpec = {
  name: string;
  label: string;
  kind: FieldKind;
  optional?: boolean;
  options?: readonly string[];
  refList?: "entities" | "components";
  /** Required in the schema but allowed to be empty (stored as ""). */
  emptyString?: boolean;
};

const NFR_CATEGORIES = ["latency", "throughput", "availability", "durability", "scale", "security", "cost", "other"];
const COMPONENT_KINDS = [
  "client", "gateway", "load_balancer", "service", "cache", "queue",
  "database", "object_store", "search", "cdn", "external",
]; // prettier-ignore

export const FIELDS: Record<ListName, FieldSpec[]> = {
  functional_requirements: [{ name: "statement", label: "Requirement", kind: "textarea" }],
  non_functional_requirements: [
    { name: "category", label: "Category", kind: "select", options: NFR_CATEGORIES },
    { name: "statement", label: "Requirement", kind: "textarea" },
    { name: "metric", label: "Metric", kind: "text", optional: true },
    { name: "target", label: "Target", kind: "number", optional: true },
    { name: "unit", label: "Unit", kind: "text", optional: true },
  ],
  out_of_scope: [{ name: "text", label: "Out of scope", kind: "textarea" }],
  capacity_estimates: [
    { name: "quantity", label: "Quantity", kind: "text" },
    { name: "formula", label: "Formula", kind: "text" },
    { name: "result", label: "Result", kind: "number" },
    { name: "unit", label: "Unit", kind: "text" },
  ],
  entities: [
    { name: "name", label: "Name", kind: "text" },
    { name: "fields", label: "Fields", kind: "entityFields" },
    { name: "indexes", label: "Indexes (one per line)", kind: "lines", optional: true },
    { name: "est_record_bytes", label: "Estimated bytes per record", kind: "integer", optional: true },
  ],
  relationships: [
    { name: "from_entity", label: "From entity", kind: "ref", refList: "entities" },
    { name: "to_entity", label: "To entity", kind: "ref", refList: "entities" },
    { name: "cardinality", label: "Cardinality", kind: "select", options: ["1:1", "1:N", "N:M"] },
  ],
  endpoints: [
    { name: "method", label: "Method", kind: "select", options: ["GET", "POST", "PUT", "PATCH", "DELETE"] },
    { name: "path", label: "Path", kind: "text" },
    { name: "request", label: "Request", kind: "textarea", emptyString: true },
    { name: "response", label: "Response", kind: "textarea", emptyString: true },
    { name: "pagination", label: "Pagination", kind: "text", optional: true },
    { name: "errors", label: "Errors (one per line)", kind: "lines", optional: true },
    { name: "rate_limit", label: "Rate limit", kind: "text", optional: true },
  ],
  storage_choices: [
    { name: "data", label: "Data", kind: "text" },
    { name: "technology", label: "Technology", kind: "text" },
    { name: "justification", label: "Justification", kind: "textarea", emptyString: true },
    { name: "rejected_alternatives", label: "Rejected alternatives (one per line)", kind: "lines", optional: true },
  ],
  components: [
    { name: "name", label: "Name", kind: "text" },
    { name: "kind", label: "Kind", kind: "select", options: COMPONENT_KINDS },
    { name: "responsibility", label: "Responsibility", kind: "textarea", emptyString: true },
  ],
  flows: [
    { name: "name", label: "Name", kind: "text" },
    { name: "kind", label: "Kind", kind: "select", options: ["read", "write"] },
    { name: "steps", label: "Steps", kind: "flowSteps" },
  ],
  cache_policies: [
    { name: "data", label: "Data", kind: "text" },
    { name: "strategy", label: "Strategy", kind: "select", options: ["cache-aside", "read-through", "write-through", "write-back"] },
    { name: "eviction", label: "Eviction", kind: "select", options: ["LRU", "LFU", "TTL-only", "other"] },
    { name: "ttl_seconds", label: "TTL (seconds)", kind: "integer", optional: true },
  ],
  spofs: [
    { name: "component_id", label: "Component", kind: "ref", refList: "components" },
    { name: "risk", label: "Risk", kind: "textarea" },
    { name: "mitigation", label: "Mitigation", kind: "textarea", optional: true },
  ],
  failure_modes: [
    { name: "scenario", label: "Scenario", kind: "textarea" },
    { name: "behaviour", label: "Behaviour", kind: "textarea" },
    { name: "recovery", label: "Recovery", kind: "textarea", optional: true },
  ],
  observability: [
    { name: "kind", label: "Kind", kind: "select", options: ["log", "metric", "trace", "alert", "health-check"] },
    { name: "name", label: "Name", kind: "text" },
    { name: "threshold", label: "Threshold", kind: "text", optional: true },
  ],
  tradeoffs: [
    { name: "decision", label: "Decision", kind: "text" },
    { name: "gained", label: "Gained", kind: "text" },
    { name: "sacrificed", label: "Sacrificed", kind: "text" },
  ],
  extensions: [{ name: "text", label: "Extension", kind: "textarea" }],
};

// --- form values ---------------------------------------------------------------------------

export type EntityFieldRow = { name: string; type: string; key: string; references: string };
export type FlowStepRow = { from_component: string; to_component: string; label: string };
export type FormValue = string | EntityFieldRow[] | FlowStepRow[];
export type FormValues = Record<string, FormValue>;

export function emptyValues(list: ListName): FormValues {
  const values: FormValues = {};
  for (const field of FIELDS[list]) {
    if (field.kind === "entityFields") values[field.name] = [{ name: "id", type: "uuid", key: "pk", references: "" }];
    else if (field.kind === "flowSteps") values[field.name] = [{ from_component: "", to_component: "", label: "" }];
    else if (field.kind === "select") values[field.name] = field.options?.[0] ?? "";
    else values[field.name] = "";
  }
  return values;
}

export function itemValues(list: ListName, item: Item): FormValues {
  const values: FormValues = {};
  for (const field of FIELDS[list]) {
    const value = item[field.name];
    if (field.kind === "entityFields") {
      values[field.name] = ((value as Record<string, unknown>[] | undefined) ?? []).map((f) => ({
        name: String(f.name ?? ""),
        type: String(f.type ?? ""),
        key: String(f.key ?? "none"),
        references: String(f.references ?? ""),
      }));
    } else if (field.kind === "flowSteps") {
      values[field.name] = ((value as FlowStepRow[] | undefined) ?? []).map((s) => ({ ...s }));
    } else if (field.kind === "lines") {
      values[field.name] = ((value as string[] | undefined) ?? []).join("\n");
    } else {
      values[field.name] = value == null ? "" : String(value);
    }
  }
  return values;
}

/** Turn form values into an item's fields, or list the problems a user must fix first. */
export function parseValues(list: ListName, values: FormValues): { fields?: Record<string, unknown>; problems: string[] } {
  const fields: Record<string, unknown> = {};
  const problems: string[] = [];
  for (const spec of FIELDS[list]) {
    const raw = values[spec.name];
    if (spec.kind === "entityFields") {
      const rows = (raw as EntityFieldRow[]).filter((r) => r.name.trim() || r.type.trim());
      if (rows.length === 0) problems.push(`${spec.label}: add at least one field`);
      rows.forEach((r, i) => {
        if (!r.name.trim() || !r.type.trim()) problems.push(`${spec.label} ${i + 1}: name and type are required`);
        if (r.key === "fk" && !r.references) problems.push(`${spec.label} ${i + 1}: a foreign key must reference an entity`);
      });
      fields[spec.name] = rows.map((r) => ({
        name: r.name.trim(),
        type: r.type.trim(),
        key: r.key,
        ...(r.key === "fk" ? { references: r.references } : {}),
      }));
      continue;
    }
    if (spec.kind === "flowSteps") {
      const rows = raw as FlowStepRow[];
      if (rows.length === 0) problems.push(`${spec.label}: add at least one step`);
      rows.forEach((r, i) => {
        if (!r.from_component || !r.to_component) problems.push(`${spec.label} ${i + 1}: choose both components`);
      });
      fields[spec.name] = rows.map((r) => ({ ...r, label: r.label.trim() }));
      continue;
    }
    const text = String(raw ?? "").trim();
    if (spec.kind === "lines") {
      fields[spec.name] = text ? text.split("\n").map((l) => l.trim()).filter(Boolean) : [];
      continue;
    }
    if (!text) {
      if (spec.emptyString) fields[spec.name] = "";
      else if (spec.optional) fields[spec.name] = null;
      else problems.push(`${spec.label} is required`);
      continue;
    }
    if (spec.kind === "number" || spec.kind === "integer") {
      const number = Number(text);
      if (!Number.isFinite(number) || (spec.kind === "integer" && !Number.isInteger(number))) {
        problems.push(`${spec.label} must be ${spec.kind === "integer" ? "a whole number" : "a number"}`);
      } else fields[spec.name] = number;
      continue;
    }
    fields[spec.name] = text;
  }
  return problems.length ? { problems } : { fields, problems };
}

// --- S2.5 IDs and pure updates --------------------------------------------------------------

export function issueId(counters: Counters, prefix: string): { id: string; counters: Counters } {
  const next = (counters[prefix] ?? 0) + 1;
  return { id: `${prefix}-${next}`, counters: { ...counters, [prefix]: next } };
}

export function addItem(design: Design, counters: Counters, list: ListName, fields: Record<string, unknown>) {
  const { id, counters: issued } = issueId(counters, PREFIXES[list]);
  const extra = list === "storage_choices" ? { status: "proposed" } : {};
  const items = [...(design[list] as Item[]), { id, ...fields, ...extra }];
  return { design: { ...design, [list]: items } as Design, counters: issued, id };
}

export function updateItem(design: Design, list: ListName, id: string, fields: Record<string, unknown>): Design {
  const items = (design[list] as Item[]).map((item) => {
    if (item.id !== id) return item;
    const next: Item = { ...item, ...fields };
    // S5.5: a storage choice changed by hand is proposed again until justified.
    if (list === "storage_choices" && (item.data !== next.data || item.technology !== next.technology)) {
      next.status = "proposed";
    }
    return next;
  });
  return { ...design, [list]: items } as Design;
}

export function deleteItem(design: Design, list: ListName, id: string): Design {
  return { ...design, [list]: (design[list] as Item[]).filter((item) => item.id !== id) } as Design;
}

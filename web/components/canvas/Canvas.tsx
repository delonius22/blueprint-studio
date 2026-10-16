// The design canvas (SPECS S11.2, S11.3): one panel per Design list, updated live.
import type { Design, Entity } from "../../lib/state";
import styles from "./Canvas.module.css";
import { CapStancePanel } from "./CapStancePanel";
import { DiagramPanel } from "./DiagramPanel";
import { Panel } from "./Panel";

function num(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toPrecision(6)));
}

function named(items: { id: string; name: string }[], id: string): string {
  const item = items.find((i) => i.id === id);
  return item ? `${item.name} (${id})` : id;
}

function entityName(entities: Entity[], id: string): string {
  const entity = entities.find((e) => e.id === id);
  return entity ? `${entity.name} (${id})` : id;
}

export function Canvas({ design }: { design: Design }) {
  return (
    <div className={styles.canvas}>
      <h2 className="visually-hidden">Design canvas</h2>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Step 1 · Requirements</h3>
        <div className={styles.grid}>
          <Panel
            title="Functional requirements"
            items={design.functional_requirements.map((r) => ({ id: r.id, content: r.statement }))}
          />
          <Panel
            title="Non-functional requirements"
            items={design.non_functional_requirements.map((n) => ({
              id: n.id,
              content: (
                <>
                  <span className={styles.tag}>{n.category}</span> {n.statement}
                  {(n.metric || n.target != null || n.unit) && (
                    <div className={styles.detail}>
                      {[n.metric, n.target != null ? num(n.target) : null, n.unit]
                        .filter(Boolean)
                        .join(" ")}
                    </div>
                  )}
                </>
              ),
            }))}
          />
          <Panel
            title="Out of scope"
            items={design.out_of_scope.map((o) => ({ id: o.id, content: o.text }))}
          />
          <Panel
            title="Capacity estimates"
            items={design.capacity_estimates.map((e) => ({
              id: e.id,
              content: (
                <>
                  {e.quantity}
                  <div className={styles.detail}>
                    <code>{e.formula}</code> = {num(e.result)} {e.unit}
                  </div>
                </>
              ),
            }))}
          />
        </div>
      </div>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Step 2 · Data & API</h3>
        <div className={styles.grid}>
          <Panel
            title="Entities"
            items={design.entities.map((e) => ({
              id: e.id,
              content: (
                <>
                  <strong>{e.name}</strong>
                  <ul className={styles.fields}>
                    {e.fields.map((f) => (
                      <li key={f.name}>
                        <code>{f.name}</code>: {f.type}
                        {f.key !== "none" && <span className={styles.tag}>{f.key.toUpperCase()}</span>}
                        {f.references && <> → {f.references}</>}
                      </li>
                    ))}
                  </ul>
                  {((e.indexes ?? []).length > 0 || e.est_record_bytes != null) && (
                    <div className={styles.detail}>
                      {(e.indexes ?? []).length > 0 && <>Indexes: {(e.indexes ?? []).join(", ")}. </>}
                      {e.est_record_bytes != null && <>~{e.est_record_bytes} bytes per record</>}
                    </div>
                  )}
                </>
              ),
            }))}
          />
          <Panel
            title="Relationships"
            items={design.relationships.map((r) => ({
              id: r.id,
              content: (
                <>
                  {entityName(design.entities, r.from_entity)} <strong>{r.cardinality}</strong>{" "}
                  {entityName(design.entities, r.to_entity)}
                </>
              ),
            }))}
          />
          <Panel
            title="API endpoints"
            items={design.endpoints.map((e) => ({
              id: e.id,
              content: (
                <>
                  <code>
                    {e.method} {e.path}
                  </code>
                  <div className={styles.detail}>
                    Request: {e.request || "—"} · Response: {e.response || "—"}
                    {e.pagination && <> · Pagination: {e.pagination}</>}
                    {(e.errors ?? []).length > 0 && <> · Errors: {(e.errors ?? []).join(", ")}</>}
                    {e.rate_limit && <> · Rate limit: {e.rate_limit}</>}
                  </div>
                </>
              ),
            }))}
          />
          <Panel
            title="Storage choices"
            items={design.storage_choices.map((c) => ({
              id: c.id,
              content: (
                <>
                  {c.data} → <strong>{c.technology}</strong>{" "}
                  <span className={c.status === "decided" ? styles.decided : styles.proposed}>{c.status}</span>
                  {c.justification && <div className={styles.detail}>Why: {c.justification}</div>}
                  {(c.rejected_alternatives ?? []).length > 0 && (
                    <div className={styles.detail}>Rejected: {(c.rejected_alternatives ?? []).join(", ")}</div>
                  )}
                </>
              ),
            }))}
          />
        </div>
      </div>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Step 3 · Architecture</h3>
        <div className={styles.grid}>
          <Panel
            title="Components"
            items={design.components.map((c) => ({
              id: c.id,
              content: (
                <>
                  <strong>{c.name}</strong> <span className={styles.tag}>{c.kind.replace("_", " ")}</span>
                  {c.responsibility && <div className={styles.detail}>{c.responsibility}</div>}
                </>
              ),
            }))}
          />
          <Panel
            title="Data flows"
            items={design.flows.map((f) => ({
              id: f.id,
              content: (
                <>
                  <strong>{f.name}</strong> <span className={styles.tag}>{f.kind}</span>
                  <ol className={styles.steps}>
                    {f.steps.map((step, index) => (
                      <li key={index}>
                        {named(design.components, step.from_component)} →{" "}
                        {named(design.components, step.to_component)}: {step.label}
                      </li>
                    ))}
                  </ol>
                </>
              ),
            }))}
          />
          <CapStancePanel stance={design.cap_stance ?? null} />
          <Panel
            title="Cache policies"
            items={design.cache_policies.map((c) => ({
              id: c.id,
              content: (
                <>
                  {c.data}
                  <div className={styles.detail}>
                    {c.strategy} · {c.eviction}
                    {c.ttl_seconds != null && <> · TTL {c.ttl_seconds} s</>}
                  </div>
                </>
              ),
            }))}
          />
          <Panel
            title="Failure modes"
            items={design.failure_modes.map((f) => ({
              id: f.id,
              content: (
                <>
                  {f.scenario}
                  <div className={styles.detail}>Behaviour: {f.behaviour}</div>
                  {f.recovery && <div className={styles.detail}>Recovery: {f.recovery}</div>}
                </>
              ),
            }))}
          />
          <DiagramPanel design={design} />
        </div>
      </div>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Step 4 · Scale & reliability</h3>
        <div className={styles.grid}>
          <Panel
            title="Single points of failure"
            items={design.spofs.map((s) => ({
              id: s.id,
              content: (
                <>
                  {named(design.components, s.component_id)}: {s.risk}
                  <div className={s.mitigation ? styles.detail : styles.missing}>
                    Mitigation: {s.mitigation || "none yet"}
                  </div>
                </>
              ),
            }))}
          />
          <Panel
            title="Observability"
            items={design.observability.map((o) => ({
              id: o.id,
              content: (
                <>
                  <span className={styles.tag}>{o.kind}</span> {o.name}
                  {o.threshold && <div className={styles.detail}>Threshold: {o.threshold}</div>}
                </>
              ),
            }))}
          />
        </div>
      </div>
      <div className={styles.group}>
        <h3 className={styles.groupTitle}>Step 5 · Trade-offs & extensions</h3>
        <div className={styles.grid}>
          <Panel
            title="Trade-offs"
            items={design.tradeoffs.map((t) => ({
              id: t.id,
              content: (
                <>
                  {t.decision}
                  <div className={styles.detail}>
                    Gained: {t.gained} · Sacrificed: {t.sacrificed}
                  </div>
                </>
              ),
            }))}
          />
          <Panel title="Extensions" items={design.extensions.map((e) => ({ id: e.id, content: e.text }))} />
        </div>
      </div>
    </div>
  );
}

"use client";

// The PRD viewer (SPECS S11.2): the draft and every frozen version, with a version switcher.
import { useState } from "react";
import type { PrdDoc, PrdVersion } from "../../lib/state";
import styles from "./PrdViewer.module.css";

type Props = { draft: PrdDoc | null; versions: PrdVersion[]; stage: string };

const DRAFT = "draft";

function List({ items }: { items: string[] }) {
  return items.length ? (
    <ul>
      {items.map((item, i) => (
        <li key={i}>{item}</li>
      ))}
    </ul>
  ) : (
    <p className={styles.muted}>None.</p>
  );
}

export function PrdViewer({ draft, versions, stage }: Props) {
  // While a draft awaits approval it is shown first; otherwise the newest frozen version.
  const awaiting = draft !== null && ["prd_signoff", "seam_gate"].includes(stage);
  const options = [...(draft && awaiting ? [DRAFT] : []), ...versions.map((v) => v.version).reverse()];
  const [chosen, setChosen] = useState<string | null>(null);
  const selected = chosen && options.includes(chosen) ? chosen : (options[0] ?? null);
  const version = versions.find((v) => v.version === selected) ?? null;
  const doc = selected === DRAFT ? draft : (version?.doc ?? null);

  if (!doc) {
    return (
      <section className={`panel ${styles.viewer}`} aria-labelledby="prd-title">
        <h2 id="prd-title">PRD</h2>
        <p aria-live="polite">The PRD is being drafted from the design record and gap register…</p>
      </section>
    );
  }
  const features = new Map(doc.features.map((f) => [f.id, f.name]));
  const extended = (doc.solution ?? "") !== "" || (doc.user_stories ?? []).length > 0;
  return (
    <section className={`panel ${styles.viewer}`} aria-labelledby="prd-title">
      <div className={styles.top}>
        <h2 id="prd-title">
          PRD {selected === DRAFT ? "draft" : `v${selected}`}
          {version && <span className={styles.muted}> · approved {version.approved_at.replace("T", " ").replace("Z", " UTC")}</span>}
        </h2>
        {options.length > 1 && (
          <label className={styles.switcher}>
            Version{" "}
            <select value={selected ?? ""} onChange={(e) => setChosen(e.target.value)}>
              {options.map((o) => (
                <option key={o} value={o}>
                  {o === DRAFT ? "Draft awaiting approval" : `v${o}`}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <h3>Problem Statement</h3>
      <p>{doc.problem_statement}</p>
      <h3>Goals</h3>
      <List items={doc.goals} />
      <h3>Users and Stakeholders</h3>
      <List items={doc.users} />
      <h3>Features</h3>
      {doc.features.map((f) => (
        <div key={f.id} className={styles.feature}>
          <h4>
            {f.id}: {f.name}
          </h4>
          <p>{f.description}</p>
          <p className={styles.muted}>Requirements: {f.requirement_ids.join(", ")}</p>
        </div>
      ))}
      <h3>Functional Requirements</h3>
      <div className={styles.scroll}>
        <table>
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Feature</th>
              <th scope="col">Requirement</th>
            </tr>
          </thead>
          <tbody>
            {doc.functional_requirements.map((r) => (
              <tr key={r.id}>
                <th scope="row">{r.id}</th>
                <td>
                  {r.feature_id}: {features.get(r.feature_id)}
                </td>
                <td>{r.statement}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Non-Functional Requirements</h3>
      <div className={styles.scroll}>
        <table>
          <thead>
            <tr>
              <th scope="col">ID</th>
              <th scope="col">Category</th>
              <th scope="col">Requirement</th>
              <th scope="col">Metric</th>
              <th scope="col">Target</th>
              <th scope="col">Unit</th>
            </tr>
          </thead>
          <tbody>
            {doc.non_functional_requirements.map((n) => (
              <tr key={n.id}>
                <th scope="row">{n.id}</th>
                <td>{n.category}</td>
                <td>{n.statement}</td>
                <td>{n.metric ?? ""}</td>
                <td>{n.target ?? ""}</td>
                <td>{n.unit ?? ""}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Scope</h3>
      <List items={doc.scope} />
      <h3>Out of Scope</h3>
      <List items={doc.out_of_scope} />
      <h3>Open Gaps and Accepted Risks</h3>
      {doc.open_gaps.length === 0 ? (
        <p className={styles.muted}>None.</p>
      ) : (
        <ul>
          {doc.open_gaps.map((g) => (
            <li key={g.id}>
              <strong>{g.id}</strong> ({g.lens}, {g.severity}; {g.item_ids.join(", ")}; features {(g.feature_ids ?? []).join(", ")}):{" "}
              {g.risk} Decision needed: {g.decision_needed}
              {g.note ? ` Note: ${g.note}` : ""}
            </li>
          ))}
        </ul>
      )}
      {extended && (
        <>
          <h3>Solution</h3>
          <p>{doc.solution}</p>
          <h3>User Stories</h3>
          <ol>
            {(doc.user_stories ?? []).map((s) => (
              <li key={s.id}>
                <strong>{s.id}</strong> ({s.feature_id}; {s.requirement_ids.join(", ")}): As {s.actor}, I want {s.feature},
                so that {s.benefit}
              </li>
            ))}
          </ol>
          <h3>Implementation Decisions</h3>
          <List items={doc.implementation_decisions ?? []} />
          <h3>Testing Decisions</h3>
          <List items={doc.testing_decisions ?? []} />
          <h3>Further Notes</h3>
          <List items={doc.further_notes ?? []} />
        </>
      )}
    </section>
  );
}

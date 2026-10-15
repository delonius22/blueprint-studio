"use client";

// The proposed-changes review (SPECS S8.5, S11.4): approve or reject each change to signed-off
// content (a rejection needs a reason), or accept all.
import { type FormEvent, useId, useState } from "react";
import styles from "./GateCard.module.css";

export type CardChange = {
  id: string;
  section: string;
  target_id?: string | null;
  kind: string;
  current_text?: string | null;
  proposed_text?: string | null;
  reason: string;
};
export type ChangeDecision = { change_id: string; decision: "approved" | "rejected"; reason?: string };

type Props = {
  args: Partial<{ changes: CardChange[] }>;
  status: "inProgress" | "executing" | "complete";
  respond?: (decisions: ChangeDecision[]) => void;
  result?: string;
};

export function ReviewChangesCard({ args, status, respond, result }: Props) {
  const changes = args.changes ?? [];
  const [choices, setChoices] = useState<Record<string, ChangeDecision>>({});
  const formId = useId();

  if (status === "complete") {
    let decided: ChangeDecision[] = [];
    try {
      decided = JSON.parse(result ?? "[]") as ChangeDecision[];
    } catch {
      decided = [];
    }
    return (
      <div className={styles.card} role="group" aria-label="Proposed changes">
        <h3>Proposed changes</h3>
        <ul>
          {decided.map((d) => (
            <li key={d.change_id}>
              {d.change_id}: {d.decision}
              {d.reason ? ` — ${d.reason}` : ""}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const ready = status === "executing" && Boolean(respond);
  const set = (id: string, patch: Partial<ChangeDecision>) =>
    setChoices((current) => {
      const base: ChangeDecision = current[id] ?? { change_id: id, decision: "approved" };
      return { ...current, [id]: { ...base, ...patch } };
    });
  const complete = changes.every((c) => {
    const choice = choices[c.id];
    return choice && (choice.decision === "approved" || (choice.reason ?? "").trim());
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || !respond) return;
    respond(
      changes.map((c) => {
        const choice = choices[c.id];
        return choice.decision === "approved"
          ? { change_id: c.id, decision: "approved" }
          : { change_id: c.id, decision: "rejected", reason: (choice.reason ?? "").trim() };
      }),
    );
  }

  return (
    <form className={styles.card} aria-label="Review the proposed changes" onSubmit={submit}>
      <h3>
        {changes.length} proposed change{changes.length === 1 ? "" : "s"} to signed-off content
      </h3>
      <p className={styles.summary}>Approved changes produce PRD v1.2; rejected ones are dropped.</p>
      {changes.map((change) => {
        const choice = choices[change.id];
        const group = `${formId}-${change.id}`;
        return (
          <fieldset key={change.id} className={styles.gap}>
            <legend>
              {change.id} · {change.kind} · {change.section}
              {change.target_id ? ` · ${change.target_id}` : ""}
            </legend>
            {change.current_text && (
              <p className={styles.summary}>
                <strong>Now:</strong> {change.current_text}
              </p>
            )}
            {change.proposed_text && (
              <p className={styles.summary}>
                <strong>Proposed:</strong> {change.proposed_text}
              </p>
            )}
            <p className={styles.summary}>
              <strong>Why:</strong> {change.reason}
            </p>
            <div className={styles.actions} role="radiogroup" aria-label={`Decision for ${change.id}`}>
              <label>
                <input type="radio" name={group} disabled={!ready} checked={choice?.decision === "approved"} onChange={() => set(change.id, { decision: "approved" })} />{" "}
                Approve
              </label>
              <label>
                <input type="radio" name={group} disabled={!ready} checked={choice?.decision === "rejected"} onChange={() => set(change.id, { decision: "rejected" })} />{" "}
                Reject
              </label>
            </div>
            {choice?.decision === "rejected" && (
              <div className={styles.field}>
                <label htmlFor={`${group}-reason`}>Why reject {change.id}?</label>
                <textarea id={`${group}-reason`} value={choice.reason ?? ""} required disabled={!ready} onChange={(e) => set(change.id, { reason: e.target.value })} />
              </div>
            )}
          </fieldset>
        );
      })}
      {ready && (
        <div className={styles.actions}>
          <button type="submit" className={styles.primary} disabled={!complete}>
            Submit decisions
          </button>
          <button type="button" onClick={() => respond?.(changes.map((c) => ({ change_id: c.id, decision: "approved" as const })))}>
            Accept all changes
          </button>
        </div>
      )}
    </form>
  );
}

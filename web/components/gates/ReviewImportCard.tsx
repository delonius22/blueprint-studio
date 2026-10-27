"use client";

// The import review card (SPEC-document-import §2.5): every item the agent found in the user's
// files, with the quote it came from. Accept, edit or reject each one, or accept all at once;
// nothing from a file is recorded without this answer.
import { type FormEvent, useId, useState } from "react";
import type { CardProps } from "./types";
import { LIST_LABELS } from "../../lib/steps";
import styles from "./GateCard.module.css";

export type CardCandidate = {
  id: string;
  file: string;
  step: number;
  list: string;
  args: Record<string, unknown>;
  // Fields the card can edit: the allowed values of a choice, or "number" or "text".
  editable: Record<string, string[] | "number" | "text">;
  updates: string | null;
  current: Record<string, unknown> | null;
  locator: string;
  quote: string;
  weaknesses: { code: string; detail: string }[];
};
export type ImportDecision = {
  candidate_id: string;
  decision: "accept" | "edit" | "reject";
  fields: Record<string, unknown>;
};

type Props = CardProps<{ candidates: CardCandidate[] }, { decisions: ImportDecision[] }>;

const label = (name: string) => name.replace(/_/g, " ");

function shown(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function Outcome({ result }: { result?: string }) {
  let decided: ImportDecision[] = [];
  try {
    decided = (JSON.parse(result ?? "{}") as { decisions?: ImportDecision[] }).decisions ?? [];
  } catch {
    decided = [];
  }
  const verbs = { accept: "accepted", edit: "accepted with edits", reject: "rejected" };
  return (
    <div className={styles.card} role="group" aria-label="Import review">
      <h3>Import review</h3>
      <ul>
        {decided.map((d) => (
          <li key={d.candidate_id}>
            {d.candidate_id}: {verbs[d.decision]}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ReviewImportCard({ args, status, respond, result }: Props) {
  const candidates = args.candidates ?? [];
  const [rejected, setRejected] = useState<Set<string>>(new Set());
  const [edits, setEdits] = useState<Record<string, Record<string, string>>>({});
  const formId = useId();

  if (status === "complete") return <Outcome result={result} />;
  const ready = status === "executing" && Boolean(respond);

  function toggle(id: string, reject: boolean) {
    setRejected((current) => {
      const next = new Set(current);
      if (reject) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  function edit(id: string, field: string, value: string) {
    setEdits((current) => ({ ...current, [id]: { ...current[id], [field]: value } }));
  }

  function decision(candidate: CardCandidate): ImportDecision {
    if (rejected.has(candidate.id)) return { candidate_id: candidate.id, decision: "reject", fields: {} };
    const changed = Object.entries(edits[candidate.id] ?? {}).filter(
      ([field, value]) => value !== shown(candidate.args[field] ?? ""),
    );
    if (changed.length === 0) return { candidate_id: candidate.id, decision: "accept", fields: {} };
    const fields = Object.fromEntries(
      changed.map(([field, value]) => {
        const number = candidate.editable[field] === "number";
        return [field, number ? (value.trim() === "" ? null : Number(value)) : value];
      }),
    );
    return { candidate_id: candidate.id, decision: "edit", fields };
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    respond?.({ decisions: candidates.map(decision) });
  }

  return (
    <form className={styles.card} aria-label="Review what your files say" onSubmit={submit}>
      <h3>
        {candidates.length} item{candidates.length === 1 ? "" : "s"} from your files
      </h3>
      <p className={styles.summary}>
        Each item quotes the file it came from. Accept it, correct it, or reject it; nothing is recorded until
        you submit.
      </p>
      {candidates.map((c) => {
        const groupId = `${formId}-${c.id}`;
        const fixed = Object.entries(c.args).filter(([field]) => !(field in c.editable));
        return (
          <fieldset key={c.id} className={styles.gap}>
            <legend>
              {c.id} · {LIST_LABELS[c.list] ?? label(c.list)} · Step {c.step}
            </legend>
            <blockquote className={styles.summary} cite={c.locator}>
              “{c.quote || "(read from the image)"}” — {c.file}, {c.locator}
            </blockquote>
            {c.updates && (
              <p className={styles.summary}>
                <strong>Replaces {c.updates}:</strong> {shown(c.current?.statement ?? c.current?.name ?? c.current)}
              </p>
            )}
            {Object.entries(c.editable).map(([field, kind]) => {
              const inputId = `${groupId}-${field}`;
              const value = edits[c.id]?.[field] ?? shown(c.args[field] ?? "");
              const options = Array.isArray(kind) ? kind : null;
              return (
                <div key={field} className={styles.field}>
                  <label htmlFor={inputId}>{label(field)}</label>
                  {options ? (
                    <select
                      id={inputId}
                      value={value}
                      disabled={!ready || rejected.has(c.id)}
                      onChange={(event) => edit(c.id, field, event.target.value)}
                    >
                      {!options.includes(value) && <option value={value}>{value || "(not set)"}</option>}
                      {options.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <input
                      id={inputId}
                      type={kind === "number" ? "number" : "text"}
                      value={value}
                      disabled={!ready || rejected.has(c.id)}
                      onChange={(event) => edit(c.id, field, event.target.value)}
                    />
                  )}
                </div>
              );
            })}
            {fixed.map(([field, value]) => (
              <p key={field} className={styles.summary}>
                <strong>{label(field)}:</strong> {shown(value)}
              </p>
            ))}
            {c.weaknesses.length > 0 && (
              <ul aria-label={`Open points for ${c.id}`}>
                {c.weaknesses.map((w) => (
                  <li key={w.code + w.detail}>
                    {label(w.code)}: {w.detail}
                  </li>
                ))}
              </ul>
            )}
            <label>
              <input
                type="checkbox"
                disabled={!ready}
                checked={rejected.has(c.id)}
                onChange={(event) => toggle(c.id, event.target.checked)}
              />{" "}
              Reject {c.id}
            </label>
          </fieldset>
        );
      })}
      {ready && (
        <div className={styles.actions}>
          <button type="submit" className="go">
            Record accepted items
          </button>
          <button
            type="button"
            onClick={() =>
              respond?.({
                decisions: candidates.map((c) => ({ candidate_id: c.id, decision: "accept" as const, fields: {} })),
              })
            }
          >
            Accept all as written
          </button>
        </div>
      )}
    </form>
  );
}

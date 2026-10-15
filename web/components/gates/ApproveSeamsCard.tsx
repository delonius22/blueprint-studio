"use client";

// The seam check (SPECS S8.3, S11.4): approve the proposed test seams, edited if need be, or
// ask for different ones with feedback.
import { type FormEvent, useId, useState } from "react";
import styles from "./GateCard.module.css";

export type CardSeam = { id?: string; name: string; description: string; covers: string[] };
export type SeamsAnswer = { approved: true; seams: CardSeam[] } | { approved: false; feedback: string };

type Props = {
  args: Partial<{ seams: CardSeam[] }>;
  status: "inProgress" | "executing" | "complete";
  respond?: (answer: SeamsAnswer) => void;
  result?: string;
};

export function ApproveSeamsCard({ args, status, respond, result }: Props) {
  const [seams, setSeams] = useState<CardSeam[] | null>(null);
  const [rejecting, setRejecting] = useState(false);
  const [feedback, setFeedback] = useState("");
  const formId = useId();
  const current = seams ?? args.seams ?? [];

  if (status === "complete") {
    let answer: SeamsAnswer | null = null;
    try {
      answer = JSON.parse(result ?? "") as SeamsAnswer;
    } catch {
      answer = null;
    }
    return (
      <div className={styles.card} role="group" aria-label="Test seams">
        <h3>Test seams</h3>
        <p className={styles.outcome}>
          {answer?.approved ? `Approved ${answer.seams.length || (args.seams ?? []).length} seam(s); PRD v1.1 is frozen.` : `Sent back${answer && !answer.approved ? `: ${answer.feedback}` : "."}`}
        </p>
      </div>
    );
  }

  const ready = status === "executing" && Boolean(respond);
  const update = (index: number, patch: Partial<CardSeam>) =>
    setSeams(current.map((s, i) => (i === index ? { ...s, ...patch } : s)));
  const valid = current.length > 0 && current.every((s) => s.name.trim());

  function approve(event: FormEvent) {
    event.preventDefault();
    if (valid) respond?.({ approved: true, seams: current.map((s) => ({ ...s, name: s.name.trim(), description: s.description.trim() })) });
  }

  function reject(event: FormEvent) {
    event.preventDefault();
    if (feedback.trim()) respond?.({ approved: false, feedback: feedback.trim() });
  }

  if (rejecting && ready) {
    return (
      <form className={styles.card} aria-label="Ask for different seams" onSubmit={reject}>
        <h3>Ask for different seams</h3>
        <div className={styles.field}>
          <label htmlFor={`${formId}-feedback`}>What should change?</label>
          <textarea id={`${formId}-feedback`} value={feedback} required autoFocus onChange={(e) => setFeedback(e.target.value)} />
        </div>
        <div className={styles.actions}>
          <button type="submit" disabled={!feedback.trim()}>
            Send feedback
          </button>
          <button type="button" onClick={() => setRejecting(false)}>
            Back
          </button>
        </div>
      </form>
    );
  }

  return (
    <form className={styles.card} aria-label="Approve the test seams" onSubmit={approve}>
      <h3>Test seams for PRD v1.1</h3>
      <p className={styles.summary}>The fewer and higher the seams, the better. Edit them if needed, then approve.</p>
      {current.map((seam, index) => (
        <fieldset key={seam.id ?? `new-${index}`} className={styles.gap}>
          <legend>{seam.id ?? "New seam"}</legend>
          <div className={styles.field}>
            <label htmlFor={`${formId}-${index}-name`}>Name</label>
            <input id={`${formId}-${index}-name`} value={seam.name} disabled={!ready} onChange={(e) => update(index, { name: e.target.value })} />
          </div>
          <div className={styles.field}>
            <label htmlFor={`${formId}-${index}-description`}>Description</label>
            <textarea
              id={`${formId}-${index}-description`}
              value={seam.description}
              disabled={!ready}
              onChange={(e) => update(index, { description: e.target.value })}
            />
          </div>
          {seam.covers.length > 0 && <p className={styles.outcome}>Covers {seam.covers.join(", ")}</p>}
          {ready && current.length > 1 && (
            <button type="button" onClick={() => setSeams(current.filter((_, i) => i !== index))}>
              Remove {seam.id ?? "this seam"}
            </button>
          )}
        </fieldset>
      ))}
      {ready && (
        <div className={styles.actions}>
          <button type="button" onClick={() => setSeams([...current, { name: "", description: "", covers: [] }])}>
            Add a seam
          </button>
          <button type="submit" className={styles.primary} disabled={!valid}>
            Approve seams
          </button>
          <button type="button" onClick={() => setRejecting(true)}>
            Ask for different seams
          </button>
        </div>
      )}
    </form>
  );
}

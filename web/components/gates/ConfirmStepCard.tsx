"use client";

// The step confirmation card (SPECS S5.7, S11.4): approve, or reject with what is missing.
import { type FormEvent, useId, useState } from "react";
import type { CardProps } from "./types";
import { STEP_NAMES } from "../../lib/steps";
import styles from "./GateCard.module.css";

export type ConfirmStepArgs = { step: number; summary: string };
export type ConfirmStepAnswer = { approved: true } | { approved: false; missing: string };

/** S5.6: a call answered by the graph with blockers never opened a card, so none is shown. */
function isBlocked(result: string | undefined): boolean {
  try {
    const value = JSON.parse(result ?? "") as unknown;
    return Boolean(value && typeof value === "object" && "blockers" in value);
  } catch {
    return false;
  }
}

function parseAnswer(result: string | undefined): ConfirmStepAnswer | null {
  try {
    const value = JSON.parse(result ?? "") as unknown;
    return value && typeof value === "object" && "approved" in value ? (value as ConfirmStepAnswer) : null;
  } catch {
    return null;
  }
}

type Props = CardProps<ConfirmStepArgs, ConfirmStepAnswer>;

export function ConfirmStepCard({ args, status, respond, result }: Props) {
  const [rejecting, setRejecting] = useState(false);
  const [missing, setMissing] = useState("");
  const missingId = useId();
  const step = args.step ?? 0;
  const title = `Confirm Step ${step}: ${STEP_NAMES[step] ?? ""}`.trim();

  if (status === "complete" && isBlocked(result)) return null;
  if (status === "complete") {
    const answer = parseAnswer(result);
    return (
      <div className={styles.card} role="group" aria-label={title}>
        <h3>{title}</h3>
        <p className={styles.outcome}>
          {answer?.approved
            ? `Step ${step} confirmed.`
            : `Step ${step} sent back${answer && !answer.approved ? `: ${answer.missing}` : "."}`}
        </p>
      </div>
    );
  }

  function reject(event: FormEvent) {
    event.preventDefault();
    if (missing.trim()) respond?.({ approved: false, missing: missing.trim() });
  }

  return (
    <div className={styles.card} role="group" aria-label={title}>
      <h3>{title}</h3>
      <p className={styles.summary}>{args.summary ?? "Preparing the summary…"}</p>
      {status === "executing" && respond && !rejecting && (
        <div className={styles.actions}>
          <button type="button" className="go" onClick={() => respond({ approved: true })}>
            Approve step {step}
          </button>
          <button type="button" onClick={() => setRejecting(true)}>
            Not yet
          </button>
        </div>
      )}
      {status === "executing" && respond && rejecting && (
        <form onSubmit={reject} className={styles.field}>
          <label htmlFor={missingId}>What is missing from step {step}?</label>
          <textarea
            id={missingId}
            value={missing}
            required
            autoFocus
            onChange={(event) => setMissing(event.target.value)}
          />
          <div className={styles.actions}>
            <button type="submit" disabled={!missing.trim()}>
              Send back
            </button>
            <button type="button" onClick={() => setRejecting(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

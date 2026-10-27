"use client";

// The PRD sign-off card (SPECS S7.3, S11.4): approve v1.0, or reject it with a reason.
import { type FormEvent, useId, useState } from "react";
import type { CardProps } from "./types";
import type { PrdDoc } from "../../lib/state";
import styles from "./GateCard.module.css";

type SignOffAnswer = { approved: true } | { approved: false; reason: string };

type Props = CardProps<{ prd: PrdDoc }, SignOffAnswer>;

export function SignOffCard({ args, status, respond, result }: Props) {
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const reasonId = useId();
  const prd = args.prd;

  if (status === "complete") {
    let answer: SignOffAnswer | null = null;
    try {
      answer = JSON.parse(result ?? "") as SignOffAnswer;
    } catch {
      answer = null;
    }
    return (
      <div className={styles.card} role="group" aria-label="Sign off PRD v1.0">
        <h3>Sign off PRD v1.0</h3>
        <p className={styles.outcome}>
          {answer?.approved ? "Signed off: PRD v1.0 is frozen." : `Sent back${answer && !answer.approved ? `: ${answer.reason}` : "."}`}
        </p>
      </div>
    );
  }

  function reject(event: FormEvent) {
    event.preventDefault();
    if (reason.trim()) respond?.({ approved: false, reason: reason.trim() });
  }

  return (
    <div className={styles.card} role="group" aria-label="Sign off PRD v1.0">
      <h3>Sign off PRD v1.0</h3>
      {prd ? (
        <p className={styles.summary}>
          {prd.features.length} features, {prd.functional_requirements.length} functional and{" "}
          {prd.non_functional_requirements.length} non-functional requirements, {prd.open_gaps.length} open gaps and
          accepted risks. Read the full draft in the PRD viewer. Once signed off, v1.0 never changes.
        </p>
      ) : (
        <p className={styles.summary}>Preparing the draft…</p>
      )}
      {status === "executing" && respond && !rejecting && (
        <div className={styles.actions}>
          <button type="button" className="go" onClick={() => respond({ approved: true })}>
            Sign off v1.0
          </button>
          <button type="button" onClick={() => setRejecting(true)}>
            Request changes
          </button>
        </div>
      )}
      {status === "executing" && respond && rejecting && (
        <form className={styles.field} onSubmit={reject}>
          <label htmlFor={reasonId}>What should change?</label>
          <textarea id={reasonId} value={reason} required autoFocus onChange={(e) => setReason(e.target.value)} />
          <div className={styles.actions}>
            <button type="submit" disabled={!reason.trim()}>
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

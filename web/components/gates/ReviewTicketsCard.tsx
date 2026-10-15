"use client";

// The ticket review (SPECS S9.4, S11.4): approve the breakdown, or ask for a revision in
// plain words (required).
import { type FormEvent, useId, useState } from "react";
import type { Ticket } from "../../lib/state";
import styles from "./GateCard.module.css";

export type TicketsAnswer = { decision: "approve" } | { decision: "revise"; instructions: string };

type Props = {
  args: Partial<{ tickets: Ticket[] }>;
  status: "inProgress" | "executing" | "complete";
  respond?: (answer: TicketsAnswer) => void;
  result?: string;
};

export function ReviewTicketsCard({ args, status, respond, result }: Props) {
  const [revising, setRevising] = useState(false);
  const [instructions, setInstructions] = useState("");
  const id = useId();
  const tickets = args.tickets ?? [];

  if (status === "complete") {
    let answer: TicketsAnswer | null = null;
    try {
      answer = JSON.parse(result ?? "") as TicketsAnswer;
    } catch {
      answer = null;
    }
    return (
      <div className={styles.card} role="group" aria-label="Ticket breakdown">
        <h3>Ticket breakdown</h3>
        <p className={styles.outcome}>
          {answer?.decision === "approve" ? "Approved." : `Revision requested${answer?.decision === "revise" ? `: ${answer.instructions}` : "."}`}
        </p>
      </div>
    );
  }

  function revise(event: FormEvent) {
    event.preventDefault();
    if (instructions.trim()) respond?.({ decision: "revise", instructions: instructions.trim() });
  }

  return (
    <div className={styles.card} role="group" aria-label="Ticket breakdown">
      <h3>Ticket breakdown</h3>
      <p className={styles.summary}>
        {tickets.length} tickets, numbered in build order. The full breakdown is in the ticket view.
      </p>
      {status === "executing" && respond && !revising && (
        <div className={styles.actions}>
          <button type="button" className={styles.primary} onClick={() => respond({ decision: "approve" })}>
            Approve the tickets
          </button>
          <button type="button" onClick={() => setRevising(true)}>
            Ask for a revision
          </button>
        </div>
      )}
      {status === "executing" && respond && revising && (
        <form className={styles.field} onSubmit={revise}>
          <label htmlFor={id}>What should change? (merge, split or re-edge tickets)</label>
          <textarea id={id} value={instructions} required autoFocus onChange={(e) => setInstructions(e.target.value)} />
          <div className={styles.actions}>
            <button type="submit" disabled={!instructions.trim()}>
              Send revision
            </button>
            <button type="button" onClick={() => setRevising(false)}>
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

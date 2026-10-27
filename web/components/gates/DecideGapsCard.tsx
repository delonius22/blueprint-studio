"use client";

// The gap decisions card (SPECS S6.5, S11.4): answer each gap (text required) or accept it as
// an open risk (optional note), item by item, or accept all at once.
import { type FormEvent, useId, useState } from "react";
import type { CardProps } from "./types";
import styles from "./GateCard.module.css";

export type CardGap = {
  id: string;
  lens: string;
  severity: string;
  item_ids: string[];
  risk: string;
  decision_needed: string;
};
export type GapDecision = { gap_id: string; decision: "answer" | "accept"; text: string };

type Props = CardProps<{ gaps: CardGap[] }, GapDecision[]>;

export function DecideGapsCard({ args, status, respond, result }: Props) {
  const gaps = args.gaps ?? [];
  const [choices, setChoices] = useState<Record<string, GapDecision>>({});
  const formId = useId();

  if (status === "complete") {
    let decided: GapDecision[] = [];
    try {
      decided = JSON.parse(result ?? "[]") as GapDecision[];
    } catch {
      decided = [];
    }
    return (
      <div className={styles.card} role="group" aria-label="Gap decisions">
        <h3>Gap decisions</h3>
        <ul>
          {decided.map((d) => (
            <li key={d.gap_id}>
              {d.gap_id}: {d.decision === "accept" ? "accepted as an open risk" : "answered"}
              {d.text ? ` — ${d.text}` : ""}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  const set = (gapId: string, patch: Partial<GapDecision>) =>
    setChoices((current) => {
      const base: GapDecision = current[gapId] ?? { gap_id: gapId, decision: "answer", text: "" };
      return { ...current, [gapId]: { ...base, ...patch } };
    });
  const complete = gaps.every((g) => {
    const choice = choices[g.id];
    return choice && (choice.decision === "accept" || choice.text.trim());
  });
  const ready = status === "executing" && Boolean(respond);

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!complete || !respond) return;
    respond(gaps.map((g) => ({ ...choices[g.id], text: choices[g.id].text.trim() })));
  }

  return (
    <form className={styles.card} aria-label="Decide the open gaps" onSubmit={submit}>
      <h3>
        {gaps.length} open gap{gaps.length === 1 ? "" : "s"}
      </h3>
      <p className={styles.summary}>Answer each gap, or accept it as an open risk that the PRD will list.</p>
      {gaps.map((gap) => {
        const choice = choices[gap.id];
        const groupId = `${formId}-${gap.id}`;
        return (
          <fieldset key={gap.id} className={styles.gap}>
            <legend>
              {gap.id} · {gap.lens} · {gap.severity}
            </legend>
            <p className={styles.summary}>
              <strong>Risk:</strong> {gap.risk}
              <br />
              <strong>Decision needed:</strong> {gap.decision_needed}
              <br />
              <strong>Affects:</strong> {gap.item_ids.join(", ")}
            </p>
            <div className={styles.actions} role="radiogroup" aria-label={`Decision for ${gap.id}`}>
              <label>
                <input
                  type="radio"
                  name={groupId}
                  disabled={!ready}
                  checked={choice?.decision === "answer"}
                  onChange={() => set(gap.id, { decision: "answer" })}
                />{" "}
                Answer
              </label>
              <label>
                <input
                  type="radio"
                  name={groupId}
                  disabled={!ready}
                  checked={choice?.decision === "accept"}
                  onChange={() => set(gap.id, { decision: "accept" })}
                />{" "}
                Accept as open risk
              </label>
            </div>
            {choice && (
              <div className={styles.field}>
                <label htmlFor={`${groupId}-text`}>
                  {choice.decision === "answer" ? `Your answer to ${gap.id}` : `Note for ${gap.id} (optional)`}
                </label>
                <textarea
                  id={`${groupId}-text`}
                  value={choice.text}
                  required={choice.decision === "answer"}
                  disabled={!ready}
                  onChange={(event) => set(gap.id, { text: event.target.value })}
                />
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
          <button
            type="button"
            onClick={() => respond?.(gaps.map((g) => ({ gap_id: g.id, decision: "accept" as const, text: "" })))}
          >
            Accept all as open risks
          </button>
        </div>
      )}
    </form>
  );
}

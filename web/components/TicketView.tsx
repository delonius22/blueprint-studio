// The ticket view (SPECS S11.2): the breakdown with its blocking edges and build waves.
import { buildWaves, type Ticket } from "../lib/state";
import styles from "./TicketView.module.css";

export function TicketView({ tickets, stage }: { tickets: Ticket[]; stage: string }) {
  if (tickets.length === 0) {
    return (
      <section className={styles.view} aria-labelledby="tickets-title">
        <h2 id="tickets-title">Tickets</h2>
        <p aria-live="polite">The tickets are being planned from the current PRD…</p>
      </section>
    );
  }
  const waves = buildWaves(tickets);
  return (
    <section className={styles.view} aria-labelledby="tickets-title">
      <h2 id="tickets-title">Tickets {stage === "complete" ? "(approved)" : "(awaiting your review)"}</h2>
      <p className={styles.muted}>
        {tickets.length} tickets in {waves.length} build wave{waves.length === 1 ? "" : "s"}:{" "}
        {waves.map((w, i) => `wave ${i + 1}: ${w.map((t) => t.id).join(", ")}`).join("; ")}.
      </p>
      <ol className={styles.tickets}>
        {tickets.map((t) => (
          <li key={t.id} className={styles.ticket}>
            <h3>
              {t.id}: {t.title} <span className={styles.kind}>{t.kind}</span>
            </h3>
            <p className={styles.muted}>
              Blocked by: {(t.blocked_by ?? []).length ? (t.blocked_by ?? []).join(", ") : "nothing"} · Delivers:{" "}
              {t.story_ids.join(", ")}
            </p>
            <p>{t.what_to_build}</p>
            <ul aria-label={`Acceptance criteria for ${t.id}`}>
              {t.acceptance_criteria.map((c, i) => (
                <li key={i}>{c}</li>
              ))}
            </ul>
          </li>
        ))}
      </ol>
    </section>
  );
}

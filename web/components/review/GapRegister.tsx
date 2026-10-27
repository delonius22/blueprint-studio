// The gap register (SPECS S2.9, S11.2): every gap's lens, severity, affected items, risk and
// the decision needed, during design review and gap resolution.
import { type Design, type Gap, itemLabel } from "../../lib/state";
import styles from "./GapRegister.module.css";

export function GapRegister({ gaps, design, stage }: { gaps: Gap[]; design: Design; stage: string }) {
  const open = gaps.filter((g) => g.status === "open").length;
  return (
    <section className={`panel ${styles.register}`} aria-labelledby="gap-register-title">
      <h2 id="gap-register-title">Gap register</h2>
      {stage === "design_review" && gaps.length === 0 ? (
        <p aria-live="polite">The design judges are reviewing the design for security, efficiency and maintainability…</p>
      ) : gaps.length === 0 ? (
        <p>No gaps were found.</p>
      ) : (
        <>
          <p>
            {gaps.length} gap{gaps.length === 1 ? "" : "s"}, {open} open.
          </p>
          <div className={styles.scroll}>
            <table>
              <caption className="visually-hidden">Gaps found by the design review</caption>
              <thead>
                <tr>
                  <th scope="col">ID</th>
                  <th scope="col">Lens</th>
                  <th scope="col">Severity</th>
                  <th scope="col">Affected items</th>
                  <th scope="col">Risk</th>
                  <th scope="col">Decision needed</th>
                  <th scope="col">Status</th>
                </tr>
              </thead>
              <tbody>
                {gaps.map((gap) => (
                  <tr key={gap.id}>
                    <th scope="row">{gap.id}</th>
                    <td>{gap.lens}</td>
                    <td>
                      <span className={styles[gap.severity]}>{gap.severity}</span>
                    </td>
                    <td>
                      <ul className={styles.items}>
                        {gap.item_ids.map((id) => (
                          <li key={id}>{itemLabel(design, id)}</li>
                        ))}
                      </ul>
                    </td>
                    <td>{gap.risk}</td>
                    <td>{gap.decision_needed}</td>
                    <td>
                      {gap.status}
                      {gap.note && <div className={styles.note}>Note: {gap.note}</div>}
                      {(gap.resolved_by ?? []).length > 0 && (
                        <div className={styles.note}>Resolved by {(gap.resolved_by ?? []).join(", ")}</div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}

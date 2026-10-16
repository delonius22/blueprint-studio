"use client";

// The CAP stance: one value per design (SPECS S2.7), as the interviewer recorded it.
import { useId } from "react";
import type { Design } from "../../lib/state";
import styles from "./Canvas.module.css";

type Stance = NonNullable<Design["cap_stance"]>;

export function CapStancePanel({ stance }: { stance: Stance | null }) {
  const id = useId();
  return (
    <section className={styles.panel} aria-labelledby={`${id}-title`}>
      <div className={styles.panelHeader}>
        <h3 id={`${id}-title`}>CAP stance</h3>
      </div>
      {stance ? (
        <ul className={styles.items}>
          <li className={styles.item}>
            <span className={styles.id}>{stance.choice}</span>
            <div className={styles.content}>{stance.rationale}</div>
          </li>
        </ul>
      ) : (
        <p className={styles.empty}>Nothing recorded yet.</p>
      )}
    </section>
  );
}

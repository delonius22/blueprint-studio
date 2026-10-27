// The final scorecard (SPECS S2.8, S5.8, PRD FR-9): five dimensions, each with quoted evidence.
import type { Scorecard } from "../../lib/state";
import styles from "./ScorecardPanel.module.css";

const LABELS: Record<string, string> = {
  communication: "Communication & collaboration",
  structure: "Structured problem-solving",
  judgment: "Technical judgment",
  depth: "Practical depth",
  time: "Time management",
};

export function ScorecardPanel({ scorecard }: { scorecard: Scorecard }) {
  return (
    <section className={`panel ${styles.scorecard}`} aria-labelledby="scorecard-title">
      <h2 id="scorecard-title">Scorecard</h2>
      <ul className={styles.dimensions}>
        {scorecard.dimensions.map((d) => (
          <li key={d.dimension} className={styles.dimension}>
            <h3>
              {LABELS[d.dimension] ?? d.dimension}{" "}
              <span className={styles.score} aria-label={`score ${d.score} out of 4`}>
                {d.score}/4
              </span>
            </h3>
            {d.evidence.map((quote, index) => (
              <blockquote key={index}>“{quote}”</blockquote>
            ))}
            <p>
              <strong>Advice:</strong> {d.advice}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}

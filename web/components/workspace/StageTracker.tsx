// The header's stage tracker (SPECS S11.2): the five steps with current and confirmed ones,
// and the session's stage once the interview is over.
import { stageLabel } from "../../lib/sessions";
import { STEP_NAMES } from "../../lib/steps";
import styles from "./StageTracker.module.css";

type Props = { stage: string; currentStep: number; confirmedSteps: number[] };

export function StageTracker({ stage, currentStep, confirmedSteps }: Props) {
  const interviewing = stage === "interview";
  return (
    <nav aria-label="Progress" className={styles.tracker}>
      <ol>
        {[1, 2, 3, 4, 5].map((step) => {
          const confirmed = confirmedSteps.includes(step);
          const current = interviewing && step === currentStep;
          const status = confirmed ? "confirmed" : current ? "current" : "not started";
          return (
            <li
              key={step}
              aria-current={current ? "step" : undefined}
              className={confirmed ? styles.confirmed : current ? styles.current : styles.upcoming}
            >
              <span aria-hidden="true">{confirmed ? "✓" : step}</span>
              <span className="visually-hidden">
                Step {step}: {STEP_NAMES[step]}, {status}
              </span>
              <span aria-hidden="true" className={styles.name}>
                {STEP_NAMES[step]}
              </span>
            </li>
          );
        })}
      </ol>
      {!interviewing && <p className={styles.stage}>Stage: {stageLabel(stage)}</p>}
    </nav>
  );
}

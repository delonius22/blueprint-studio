// S6.6, S11.6: a persistent warning while the review model is the interview model.
import styles from "./Workspace.module.css";

export function ReviewModelWarning({ distinct }: { distinct: boolean }) {
  if (distinct) return null;
  return (
    <p role="note" className={`panel ${styles.warning}`}>
      The review model is the same as the interview model, so the cross-model design check is not active.
      Configure a different REVIEW_MODEL to enable it.
    </p>
  );
}

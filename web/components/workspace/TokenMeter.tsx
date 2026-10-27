// The per-role token meter (SPECS S11.6, NFR-4): use per role against the session budget,
// with a warning from 80 % of the combined total.
import styles from "./TokenMeter.module.css";

type Props = { used: Record<string, number>; budget: number };

const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 });

export function TokenMeter({ used, budget }: Props) {
  const interview = used.interview ?? 0;
  const review = used.review ?? 0;
  const total = interview + review;
  const ratio = budget > 0 ? total / budget : 1;
  const level = ratio >= 1 ? "exhausted" : ratio >= 0.8 ? "warning" : "ok";
  const percent = Math.min(100, Math.round(ratio * 100));
  return (
    <div className={`${styles.meter} ${styles[level]}`}>
      <span className={styles.label} id="token-meter-label">
        Tokens
      </span>
      <meter
        aria-labelledby="token-meter-label"
        min={0}
        max={budget}
        low={budget * 0.8}
        high={budget * 0.8}
        optimum={0}
        value={Math.min(total, budget)}
      />
      <span className={styles.detail}>
        Interview {compact.format(interview)} · Review {compact.format(review)} of {compact.format(budget)} ({percent}%)
      </span>
      {level !== "ok" && (
        <span role="status" className={styles.flag}>
          {level === "exhausted" ? "Token budget used up" : "Over 80% of the token budget used"}
        </span>
      )}
    </div>
  );
}

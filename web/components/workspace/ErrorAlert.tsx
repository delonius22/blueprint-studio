// The error alert (SPECS S11.6): shows last_error with Retry (when retryable) and Dismiss.
import styles from "./ErrorAlert.module.css";

export type ErrorInfo = { code: string; message: string; retryable: boolean };

type Props = { error: ErrorInfo; onRetry: () => void; onDismiss: () => void; busy?: boolean };

export function ErrorAlert({ error, onRetry, onDismiss, busy = false }: Props) {
  return (
    <div role="alert" className={`panel ${styles.alert}`}>
      <p className={styles.message}>
        <span className={styles.flag}>Error</span> {error.message}
      </p>
      <div className={styles.actions}>
        {error.retryable && (
          <button type="button" onClick={onRetry} disabled={busy}>
            Retry
          </button>
        )}
        <button type="button" onClick={onDismiss} aria-label="Dismiss this message">
          Dismiss
        </button>
      </div>
    </div>
  );
}

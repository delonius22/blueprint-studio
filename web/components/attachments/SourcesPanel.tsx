"use client";

// The session's attached files (SPEC-document-import §5): each with what the user says it is,
// what the agent made of it, how much still waits for a later step, and a remove action.
import { roleLabel } from "../../lib/document-roles";
import { attachmentUrl, type AttachmentListing } from "../../lib/sessions";
import type { SessionState } from "../../lib/state";
import styles from "./Attachments.module.css";

type Props = {
  sessionId: string;
  listing: AttachmentListing["attachments"];
  state: Pick<SessionState, "attachments" | "import_queue">;
  canRemove: boolean;
  onRemove: (attachmentId: string) => void;
};

const STATUS: Record<string, string> = {
  parsed: "waiting to be read",
  imported: "read",
  failed: "could not be read",
  removed: "removed",
};

export function SourcesPanel({ sessionId, listing, state, canRemove, onRemove }: Props) {
  if (listing.length === 0) return null;
  const refs = new Map((state.attachments ?? []).map((a) => [a.id, a]));
  return (
    <section className={`panel ${styles.sources}`} aria-labelledby="sources-title">
      <h3 id="sources-title">Attached files ({listing.length})</h3>
      <ul>
        {listing.map((file) => {
          const ref = refs.get(file.id);
          const waiting = (state.import_queue ?? []).filter((c) => c.attachment_id === file.id);
          const steps = [...new Set(waiting.map((c) => c.step))].sort();
          return (
            <li key={file.id}>
              <a href={attachmentUrl(sessionId, file.id)} target="_blank" rel="noreferrer">
                {file.id}: {file.name}
              </a>
              <span className={styles.roleTag}>{roleLabel(file.role)}</span>
              <span className={styles.hint}>{STATUS[ref?.status ?? "parsed"]}</span>
              {ref?.summary && <div className={styles.hint}>{ref.summary}</div>}
              {steps.length > 0 && (
                <div className={styles.hint}>
                  {waiting.length === 1 ? "1 item waits" : `${waiting.length} items wait`} for Step{steps.length > 1 ? "s" : ""}{" "}
                  {steps.join(", ")}
                </div>
              )}
              {[...new Set([...file.warnings, ...(ref?.warnings ?? [])])].map((w) => (
                <div key={w} className={styles.hint}>
                  Note: {w}
                </div>
              ))}
              {canRemove && (
                <button
                  type="button"
                  aria-label={`Remove ${file.name}`}
                  onClick={() => {
                    if (window.confirm(`Remove ${file.name}? Items already recorded from it stay.`)) onRemove(file.id);
                  }}
                >
                  Remove
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

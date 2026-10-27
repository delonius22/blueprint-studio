"use client";

// Starting a session (SPECS S11.1, SPEC-document-import §5): a name and, optionally, the files
// the user already has. Each file needs a role; they are uploaded once the session exists and
// read when the user sends their first message.
import { type FormEvent, useState } from "react";
import { ApiError, sessionsApi } from "../../lib/sessions";
import { FilePicker, type StagedFile, allLabelled } from "../attachments/FilePicker";
import { uploadStaged } from "../attachments/upload";
import styles from "./SessionList.module.css";

type Failed = { sessionId: string; problems: string[] };

export function NewSessionForm({ onOpen }: { onOpen: (id: string) => void }) {
  const [name, setName] = useState("");
  const [files, setFiles] = useState<StagedFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [failed, setFailed] = useState<Failed | null>(null);
  const unlabelled = files.length > 0 && !allLabelled(files);

  async function start(event: FormEvent) {
    event.preventDefault();
    if (unlabelled) {
      setError("Choose PRD, Spec or Supporting for each file first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const session = await sessionsApi.create(name);
      const { problems } = await uploadStaged(session.id, files);
      if (problems.length) {
        setFailed({ sessionId: session.id, problems });
        return;
      }
      onOpen(session.id);
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : "Something went wrong. Please try again.");
    } finally {
      setBusy(false);
    }
  }

  if (failed) {
    return (
      <div className={styles.form} role="alert">
        <h2>The session was created, but not every file was attached</h2>
        <ul>
          {failed.problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
        <p>You can attach them again from the interview.</p>
        <button type="button" className="go" onClick={() => onOpen(failed.sessionId)}>
          Open the session
        </button>
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={start} aria-labelledby="new-session-title">
      <h2 id="new-session-title">Start a design session</h2>
      <p className={styles.lede}>
        Name it, and bring a PRD, a spec or supporting work if you have one. The interviewer reads your files when you
        send your first message, then asks about whatever they leave unclear.
      </p>
      <div className={styles.field}>
        <label htmlFor="new-session-name">Session name</label>
        <input
          id="new-session-name"
          value={name}
          maxLength={120}
          required
          onChange={(event) => setName(event.target.value)}
          placeholder="e.g. URL shortener"
        />
      </div>
      <div className={styles.field}>
        <span className={styles.label}>Start from your files (optional)</span>
        <FilePicker accepts={[]} disabled={busy} files={files} onChange={setFiles} />
      </div>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      <div>
        <button type="submit" className="go" disabled={busy}>
          {busy ? "Starting…" : "Start session"}
        </button>
      </div>
    </form>
  );
}

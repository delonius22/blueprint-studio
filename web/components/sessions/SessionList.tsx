"use client";

// The session list (SPECS S3.2, S11.1): newest first, keyset-paginated, with rename and
// delete. Sessions are started from NewSessionForm.
import Link from "next/link";
import { type FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError, type SessionSummary, sessionsApi, stageLabel } from "../../lib/sessions";
import styles from "./SessionList.module.css";

const PAGE_SIZE = 20;

function message(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

export function SessionList() {
  const [items, setItems] = useState<SessionSummary[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<{ id: string; name: string } | null>(null);

  const load = useCallback(async (cursor: string | null) => {
    setLoading(true);
    try {
      const page = await sessionsApi.list(PAGE_SIZE, cursor);
      setItems((current) => (cursor ? [...current, ...page.items] : page.items));
      setNextCursor(page.next_cursor);
      setError(null);
    } catch (caught) {
      setError(message(caught));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(null);
  }, [load]);

  async function rename(event: FormEvent) {
    event.preventDefault();
    if (!editing) return;
    try {
      const renamed = await sessionsApi.rename(editing.id, editing.name);
      setItems((current) => [renamed, ...current.filter((s) => s.id !== renamed.id)]);
      setEditing(null);
      setError(null);
    } catch (caught) {
      setError(message(caught));
    }
  }

  async function remove(session: SessionSummary) {
    if (!window.confirm(`Delete "${session.name}"? This cannot be undone.`)) return;
    try {
      await sessionsApi.remove(session.id);
      setItems((current) => current.filter((s) => s.id !== session.id));
    } catch (caught) {
      setError(message(caught));
    }
  }

  return (
    <section className={styles.list} aria-labelledby="sessions-heading">
      <h2 id="sessions-heading">Your sessions</h2>
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
      {!loading && items.length === 0 && !error && <p className={styles.stage}>No sessions yet.</p>}
      <ul aria-labelledby="sessions-heading" className={styles.items}>
        {items.map((session) => (
          <li key={session.id} className={styles.item}>
            {editing?.id === session.id ? (
              <form className={styles.rename} onSubmit={rename}>
                <label htmlFor={`rename-${session.id}`}>New name for {session.name}</label>
                <input
                  id={`rename-${session.id}`}
                  value={editing.name}
                  maxLength={120}
                  required
                  autoFocus
                  onChange={(event) => setEditing({ id: session.id, name: event.target.value })}
                />
                <button type="submit">Save</button>
                <button type="button" onClick={() => setEditing(null)}>
                  Cancel
                </button>
              </form>
            ) : (
              <>
                <div>
                  <Link href={`/s/${session.id}`} className={styles.name}>
                    {session.name}
                  </Link>
                  <span className={styles.stage}>
                    {stageLabel(session.stage, session.current_step)}
                  </span>
                </div>
                <div className={styles.actions}>
                  <button
                    type="button"
                    aria-label={`Rename ${session.name}`}
                    onClick={() => setEditing({ id: session.id, name: session.name })}
                  >
                    Rename
                  </button>
                  <button
                    type="button"
                    aria-label={`Delete ${session.name}`}
                    onClick={() => void remove(session)}
                  >
                    Delete
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
      {nextCursor && (
        <button type="button" disabled={loading} onClick={() => void load(nextCursor)}>
          {loading ? "Loading…" : "Load more"}
        </button>
      )}
    </section>
  );
}

"use client";

// The completion view (SPECS S11.5): every available download with its file name, and
// "Download all (.zip)", rendered from the agent's listing (S10.3) — never recomputed here.
import { useEffect, useState } from "react";
import { type DownloadItem, downloadFileName, downloadUrl, sessionsApi } from "../../lib/sessions";
import styles from "./CompletionView.module.css";

export function CompletionView({ sessionId, sessionName }: { sessionId: string; sessionName: string }) {
  const [items, setItems] = useState<DownloadItem[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    sessionsApi
      .downloads(sessionId)
      .then((listing) => !cancelled && setItems(listing))
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const files = (items ?? []).filter((i) => i.available && i.kind !== "bundle.zip");
  const bundle = (items ?? []).find((i) => i.kind === "bundle.zip" && i.available);
  return (
    <section className={`panel ${styles.completion}`} aria-labelledby="completion-title">
      <h2 id="completion-title">Your design is complete</h2>
      {failed && <p role="alert">The downloads could not be listed. Reload the page to try again.</p>}
      {items === null && !failed && <p aria-live="polite">Listing your documents…</p>}
      {bundle && (
        <p>
          <a className={`go ${styles.all}`} href={downloadUrl(sessionId, bundle.kind)} download={downloadFileName(bundle.kind, sessionName)}>
            Download all (.zip)
          </a>
        </p>
      )}
      {files.length > 0 && (
        <ul className={styles.files} aria-label="Documents">
          {files.map((item) => (
            <li key={item.kind}>
              <a href={downloadUrl(sessionId, item.kind)} download={downloadFileName(item.kind, sessionName)}>
                {downloadFileName(item.kind, sessionName)}
              </a>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

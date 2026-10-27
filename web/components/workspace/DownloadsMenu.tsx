"use client";

// The header's downloads menu (SPECS S11.2, S10.3): availability comes from the agent's listing.
import { useEffect, useState } from "react";
import { type DownloadItem, downloadFileName, downloadUrl, sessionsApi } from "../../lib/sessions";
import styles from "./DownloadsMenu.module.css";

type Props = { sessionId: string; sessionName: string; refreshKey: string };

export function DownloadsMenu({ sessionId, sessionName, refreshKey }: Props) {
  const [items, setItems] = useState<DownloadItem[]>([]);

  useEffect(() => {
    let cancelled = false;
    sessionsApi
      .downloads(sessionId)
      .then((listing) => !cancelled && setItems(listing))
      .catch(() => !cancelled && setItems([]));
    return () => {
      cancelled = true;
    };
  }, [sessionId, refreshKey]);

  const available = items.filter((i) => i.available).length;
  return (
    <details className={styles.menu}>
      <summary>Downloads ({available})</summary>
      <ul className="panel">
        {items.map((item) => (
          <li key={item.kind}>
            {item.available ? (
              <a href={downloadUrl(sessionId, item.kind)} download={downloadFileName(item.kind, sessionName)}>
                {downloadFileName(item.kind, sessionName)}
              </a>
            ) : (
              <span className={styles.unavailable}>
                {downloadFileName(item.kind, sessionName)} <span className={styles.reason}>({item.reason})</span>
              </span>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}

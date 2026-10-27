"use client";

// One canvas panel: a titled, read-only list of design items, each labelled with its ID. The
// interviewer records every item; the user only answers in the chat.
import { createContext, type ReactNode, useContext } from "react";
import styles from "./Canvas.module.css";

type PanelItem = { id: string; content: ReactNode };

// Where each imported item came from, by item ID ("brief.md · p.3"); see SourcesPanel.
export const ItemSources = createContext<Record<string, string>>({});

type Props = { title: string; items: PanelItem[] };

export function Panel({ title, items }: Props) {
  const sources = useContext(ItemSources);
  const headingId = `panel-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <section className={styles.panel} aria-labelledby={headingId}>
      <div className={styles.panelHeader}>
        <h3 id={headingId}>
          {title} <span className={styles.count}>({items.length})</span>
        </h3>
      </div>
      {items.length === 0 ? (
        <p className={styles.empty}>Nothing recorded yet.</p>
      ) : (
        <ul className={styles.items}>
          {items.map((item) => (
            <li key={item.id} className={styles.item}>
              <span className={styles.id}>{item.id}</span>
              <div className={styles.content}>
                {item.content}
                {sources[item.id] && <div className={styles.source}>from {sources[item.id]}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

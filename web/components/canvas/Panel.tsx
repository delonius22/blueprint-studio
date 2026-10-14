// One canvas panel: a titled list of design items, each labelled with its ID (SPECS S11.3).
import type { ReactNode } from "react";
import styles from "./Canvas.module.css";

export type PanelItem = { id: string; content: ReactNode };

export function Panel({ title, items }: { title: string; items: PanelItem[] }) {
  const headingId = `panel-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  return (
    <section className={styles.panel} aria-labelledby={headingId}>
      <h3 id={headingId}>
        {title} <span className={styles.count}>({items.length})</span>
      </h3>
      {items.length === 0 ? (
        <p className={styles.empty}>Nothing recorded yet.</p>
      ) : (
        <ul className={styles.items}>
          {items.map((item) => (
            <li key={item.id} className={styles.item}>
              <span className={styles.id}>{item.id}</span>
              <div className={styles.content}>{item.content}</div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

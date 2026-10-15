"use client";

// The CAP stance: one value per design (SPECS S2.7), edited or cleared in place.
import { type FormEvent, useId, useState } from "react";
import type { Design } from "../../lib/state";
import styles from "./Canvas.module.css";
import { useCanvasEditor } from "./CanvasEdit";

type Stance = NonNullable<Design["cap_stance"]>;

export function CapStancePanel({ stance }: { stance: Stance | null }) {
  const editor = useCanvasEditor();
  const [editing, setEditing] = useState(false);
  const [choice, setChoice] = useState<string>(stance?.choice ?? "CP");
  const [rationale, setRationale] = useState(stance?.rationale ?? "");
  const id = useId();

  function open() {
    setChoice(stance?.choice ?? "CP");
    setRationale(stance?.rationale ?? "");
    setEditing(true);
  }

  function save(event: FormEvent) {
    event.preventDefault();
    if (!editor || !rationale.trim()) return;
    editor.save({ ...editor.design, cap_stance: { choice: choice as Stance["choice"], rationale: rationale.trim() } }, editor.counters);
    setEditing(false);
  }

  return (
    <section className={styles.panel} aria-labelledby={`${id}-title`}>
      <div className={styles.panelHeader}>
        <h3 id={`${id}-title`}>CAP stance</h3>
        {editor && !editing && (
          <div className={styles.itemActions}>
            <button type="button" className={styles.small} disabled={editor.disabled} onClick={open}>
              {stance ? "Edit CAP stance" : "Set CAP stance"}
            </button>
            {stance && (
              <button
                type="button"
                className={styles.small}
                disabled={editor.disabled}
                onClick={() => editor.save({ ...editor.design, cap_stance: null }, editor.counters)}
              >
                Clear CAP stance
              </button>
            )}
          </div>
        )}
      </div>
      {editing ? (
        <form className={styles.form} onSubmit={save} aria-label="Edit CAP stance">
          <div className={styles.formField}>
            <label htmlFor={`${id}-choice`}>Choice</label>
            <select id={`${id}-choice`} value={choice} onChange={(e) => setChoice(e.target.value)}>
              <option value="CP">CP</option>
              <option value="AP">AP</option>
              <option value="mixed">mixed</option>
            </select>
          </div>
          <div className={styles.formField}>
            <label htmlFor={`${id}-rationale`}>Rationale</label>
            <textarea id={`${id}-rationale`} value={rationale} required onChange={(e) => setRationale(e.target.value)} />
          </div>
          <div className={styles.formActions}>
            <button type="submit" disabled={!rationale.trim()}>
              Save
            </button>
            <button type="button" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </div>
        </form>
      ) : stance ? (
        <ul className={styles.items}>
          <li className={styles.item}>
            <span className={styles.id}>{stance.choice}</span>
            <div className={styles.content}>{stance.rationale}</div>
          </li>
        </ul>
      ) : (
        <p className={styles.empty}>Nothing recorded yet.</p>
      )}
    </section>
  );
}

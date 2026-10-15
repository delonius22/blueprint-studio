"use client";

// One canvas panel: a titled list of design items, each labelled with its ID, with add, edit
// and delete when the workspace allows edits (SPECS S11.3).
import { type ReactNode, useState } from "react";
import { addItem, deleteItem, emptyValues, itemValues, type ListName, updateItem } from "../../lib/editing";
import styles from "./Canvas.module.css";
import { useCanvasEditor } from "./CanvasEdit";
import { ItemForm } from "./ItemForm";

export type PanelItem = { id: string; content: ReactNode };

type Props = { title: string; items: PanelItem[]; list?: ListName };

export function Panel({ title, items, list }: Props) {
  const editor = useCanvasEditor();
  const [editing, setEditing] = useState<{ mode: "add" } | { mode: "edit"; id: string } | null>(null);
  const headingId = `panel-${title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
  const editable = Boolean(editor && list);

  function save(fields: Record<string, unknown>) {
    if (!editor || !list || !editing) return;
    if (editing.mode === "add") {
      const next = addItem(editor.design, editor.counters, list, fields);
      editor.save(next.design, next.counters);
    } else {
      editor.save(updateItem(editor.design, list, editing.id, fields), editor.counters);
    }
    setEditing(null);
  }

  function remove(id: string) {
    if (!editor || !list) return;
    if (!window.confirm(`Delete ${id}? Its ID will not be reused.`)) return;
    editor.save(deleteItem(editor.design, list, id), editor.counters);
  }

  const form = (initial: ReturnType<typeof emptyValues>, formTitle: string) =>
    editor && list ? (
      <ItemForm
        list={list}
        title={formTitle}
        initial={initial}
        design={editor.design}
        onSave={save}
        onCancel={() => setEditing(null)}
      />
    ) : null;

  return (
    <section className={styles.panel} aria-labelledby={headingId}>
      <div className={styles.panelHeader}>
        <h3 id={headingId}>
          {title} <span className={styles.count}>({items.length})</span>
        </h3>
        {editable && (
          <button
            type="button"
            className={styles.small}
            aria-label={`Add to ${title}`}
            disabled={editor?.disabled || editing !== null}
            onClick={() => setEditing({ mode: "add" })}
          >
            Add
          </button>
        )}
      </div>
      {items.length === 0 && editing?.mode !== "add" ? (
        <p className={styles.empty}>Nothing recorded yet.</p>
      ) : (
        <ul className={styles.items}>
          {items.map((item) =>
            editing?.mode === "edit" && editing.id === item.id && list && editor ? (
              <li key={item.id}>
                {form(
                  itemValues(list, (editor.design[list] as { id: string }[]).find((i) => i.id === item.id) as never),
                  `Edit ${item.id}`,
                )}
              </li>
            ) : (
              <li key={item.id} className={styles.item}>
                <span className={styles.id}>{item.id}</span>
                <div className={styles.content}>{item.content}</div>
                {editable && (
                  <div className={styles.itemActions}>
                    <button
                      type="button"
                      className={styles.small}
                      aria-label={`Edit ${item.id}`}
                      disabled={editor?.disabled || editing !== null}
                      onClick={() => setEditing({ mode: "edit", id: item.id })}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className={styles.small}
                      aria-label={`Delete ${item.id}`}
                      disabled={editor?.disabled || editing !== null}
                      onClick={() => remove(item.id)}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </li>
            ),
          )}
        </ul>
      )}
      {editing?.mode === "add" && list && form(emptyValues(list), `New item for ${title}`)}
    </section>
  );
}

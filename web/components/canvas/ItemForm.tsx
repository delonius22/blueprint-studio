"use client";

// A form for one design item, built from the list's field specs (lib/editing.ts).
import { type FormEvent, useId, useState } from "react";
import {
  type EntityFieldRow,
  FIELDS,
  type FieldSpec,
  type FlowStepRow,
  type FormValues,
  type ListName,
  parseValues,
} from "../../lib/editing";
import type { Design } from "../../lib/state";
import styles from "./Canvas.module.css";

type Props = {
  list: ListName;
  title: string;
  initial: FormValues;
  design: Design;
  onSave: (fields: Record<string, unknown>) => void;
  onCancel: () => void;
};

function refOptions(design: Design, list: "entities" | "components") {
  return design[list].map((item) => ({ id: item.id, label: `${item.id}: ${item.name}` }));
}

export function ItemForm({ list, title, initial, design, onSave, onCancel }: Props) {
  const [values, setValues] = useState<FormValues>(initial);
  const [problems, setProblems] = useState<string[]>([]);
  const formId = useId();
  const set = (name: string, value: FormValues[string]) => setValues((current) => ({ ...current, [name]: value }));

  function submit(event: FormEvent) {
    event.preventDefault();
    const parsed = parseValues(list, values);
    if (parsed.fields) onSave(parsed.fields);
    else setProblems(parsed.problems);
  }

  function field(spec: FieldSpec) {
    const id = `${formId}-${spec.name}`;
    const label = `${spec.label}${spec.optional ? " (optional)" : ""}`;
    const value = values[spec.name];
    if (spec.kind === "entityFields") return <EntityFields key={spec.name} id={id} design={design} rows={value as EntityFieldRow[]} onChange={(rows) => set(spec.name, rows)} />;
    if (spec.kind === "flowSteps") return <FlowSteps key={spec.name} id={id} design={design} rows={value as FlowStepRow[]} onChange={(rows) => set(spec.name, rows)} />;
    let control;
    if (spec.kind === "select" || spec.kind === "ref") {
      const options =
        spec.kind === "ref" ? refOptions(design, spec.refList ?? "entities") : (spec.options ?? []).map((o) => ({ id: o, label: o }));
      control = (
        <select id={id} value={String(value)} onChange={(e) => set(spec.name, e.target.value)}>
          {spec.kind === "ref" && <option value="">Choose…</option>}
          {options.map((o) => (
            <option key={o.id} value={o.id}>
              {o.label}
            </option>
          ))}
        </select>
      );
    } else if (spec.kind === "textarea" || spec.kind === "lines") {
      control = <textarea id={id} value={String(value)} onChange={(e) => set(spec.name, e.target.value)} />;
    } else {
      control = (
        <input
          id={id}
          inputMode={spec.kind === "number" || spec.kind === "integer" ? "decimal" : undefined}
          value={String(value)}
          onChange={(e) => set(spec.name, e.target.value)}
        />
      );
    }
    return (
      <div key={spec.name} className={styles.formField}>
        <label htmlFor={id}>{label}</label>
        {control}
      </div>
    );
  }

  return (
    <form className={styles.form} onSubmit={submit} aria-label={title}>
      {FIELDS[list].map(field)}
      {problems.length > 0 && (
        <ul role="alert" className={styles.problems}>
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
      <div className={styles.formActions}>
        <button type="submit">Save</button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}

function EntityFields({ id, design, rows, onChange }: { id: string; design: Design; rows: EntityFieldRow[]; onChange: (rows: EntityFieldRow[]) => void }) {
  const update = (index: number, patch: Partial<EntityFieldRow>) => onChange(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  return (
    <fieldset className={styles.rows}>
      <legend>Fields</legend>
      {rows.map((row, i) => (
        <div key={i} className={styles.row}>
          <label htmlFor={`${id}-${i}-name`} className="visually-hidden">Field {i + 1} name</label>
          <input id={`${id}-${i}-name`} placeholder="name" value={row.name} onChange={(e) => update(i, { name: e.target.value })} />
          <label htmlFor={`${id}-${i}-type`} className="visually-hidden">Field {i + 1} type</label>
          <input id={`${id}-${i}-type`} placeholder="type" value={row.type} onChange={(e) => update(i, { type: e.target.value })} />
          <label htmlFor={`${id}-${i}-key`} className="visually-hidden">Field {i + 1} key</label>
          <select id={`${id}-${i}-key`} value={row.key} onChange={(e) => update(i, { key: e.target.value })}>
            <option value="none">none</option>
            <option value="pk">PK</option>
            <option value="fk">FK</option>
          </select>
          {row.key === "fk" && (
            <>
              <label htmlFor={`${id}-${i}-ref`} className="visually-hidden">Field {i + 1} references</label>
              <select id={`${id}-${i}-ref`} value={row.references} onChange={(e) => update(i, { references: e.target.value })}>
                <option value="">references…</option>
                {refOptions(design, "entities").map((o) => (
                  <option key={o.id} value={o.id}>{o.label}</option>
                ))}
              </select>
            </>
          )}
          <button type="button" aria-label={`Remove field ${i + 1}`} onClick={() => onChange(rows.filter((_, j) => j !== i))}>
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...rows, { name: "", type: "", key: "none", references: "" }])}>
        Add field
      </button>
    </fieldset>
  );
}

function FlowSteps({ id, design, rows, onChange }: { id: string; design: Design; rows: FlowStepRow[]; onChange: (rows: FlowStepRow[]) => void }) {
  const update = (index: number, patch: Partial<FlowStepRow>) => onChange(rows.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  const components = refOptions(design, "components");
  const select = (key: "from_component" | "to_component", i: number, row: FlowStepRow, text: string) => (
    <>
      <label htmlFor={`${id}-${i}-${key}`} className="visually-hidden">Step {i + 1} {text}</label>
      <select id={`${id}-${i}-${key}`} value={row[key]} onChange={(e) => update(i, { [key]: e.target.value })}>
        <option value="">{text}…</option>
        {components.map((o) => (
          <option key={o.id} value={o.id}>{o.label}</option>
        ))}
      </select>
    </>
  );
  return (
    <fieldset className={styles.rows}>
      <legend>Steps</legend>
      {rows.map((row, i) => (
        <div key={i} className={styles.row}>
          {select("from_component", i, row, "from")}
          {select("to_component", i, row, "to")}
          <label htmlFor={`${id}-${i}-label`} className="visually-hidden">Step {i + 1} label</label>
          <input id={`${id}-${i}-label`} placeholder="label" value={row.label} onChange={(e) => update(i, { label: e.target.value })} />
          <button type="button" aria-label={`Remove step ${i + 1}`} onClick={() => onChange(rows.filter((_, j) => j !== i))}>
            Remove
          </button>
        </div>
      ))}
      <button type="button" onClick={() => onChange([...rows, { from_component: "", to_component: "", label: "" }])}>
        Add step
      </button>
    </fieldset>
  );
}

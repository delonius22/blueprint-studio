"use client";

// Choosing files to attach (SPEC-document-import §5): a button and a drop zone stage the files,
// and the user says what each one is (a PRD, a spec or a supporting document) before any is
// uploaded. Used in the interview chat and on the new-session form.
import { type DragEvent, useRef, useState } from "react";
import { DOCUMENT_ROLES, type DocumentRole } from "../../lib/document-roles";
import styles from "./Attachments.module.css";

export type StagedFile = { key: string; file: File; role: DocumentRole | null };

/** True when there is something to upload and every file has a role. */
export function allLabelled(files: StagedFile[]): boolean {
  return files.length > 0 && files.every((f) => f.role !== null);
}

const fileKey = (file: File) => `${file.name}:${file.size}:${file.lastModified}`;

function size(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

type Props = {
  accepts: string[];
  disabled: boolean;
  files: StagedFile[];
  onChange: (files: StagedFile[]) => void;
};

export function FilePicker({ accepts, disabled, files, onChange }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);

  function stage(chosen: File[]) {
    if (disabled) return;
    const known = new Set(files.map((f) => f.key));
    const added = chosen.filter((file) => !known.has(fileKey(file))).map((file) => ({ key: fileKey(file), file, role: null }));
    if (added.length) onChange([...files, ...added]);
  }

  function drop(event: DragEvent) {
    event.preventDefault();
    setOver(false);
    stage(Array.from(event.dataTransfer.files));
  }

  return (
    <div className={styles.picker}>
      <div
        className={`${styles.drop} ${over && !disabled ? styles.over : ""}`}
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={drop}
      >
        <button type="button" disabled={disabled} onClick={() => input.current?.click()}>
          <svg className={styles.icon} width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <path fill="currentColor" d="M4 0h2v10H4zM0 4h10v2H0z" />
          </svg>
          Choose files
        </button>
        <span className={styles.hint}>An existing PRD, spec or supporting work; or drop files here</span>
        <input
          ref={input}
          type="file"
          multiple
          hidden
          accept={accepts.join(",")}
          aria-label="Files to attach"
          onChange={(event) => {
            stage(Array.from(event.target.files ?? []));
            event.target.value = "";
          }}
        />
      </div>
      {files.length > 0 && (
        <>
          <p className={styles.hint}>
            Say what each file is, so the interviewer knows how to read it. PRD: product requirements. Spec: a
            technical design. Supporting: diagrams, notes or research.
          </p>
          <ul className={styles.staged} aria-label="Chosen files">
            {files.map((staged) => (
              <li key={staged.key}>
                <fieldset className={styles.roles} disabled={disabled}>
                  <legend>
                    {staged.file.name} <span className={styles.hint}>{size(staged.file.size)}</span>
                  </legend>
                  {DOCUMENT_ROLES.map((role) => (
                    <label key={role.value} className={styles.role} title={role.hint}>
                      <input
                        type="radio"
                        name={`role-${staged.key}`}
                        value={role.value}
                        checked={staged.role === role.value}
                        onChange={() => onChange(files.map((f) => (f.key === staged.key ? { ...f, role: role.value } : f)))}
                      />
                      {role.label}
                    </label>
                  ))}
                  <button
                    type="button"
                    className={styles.remove}
                    aria-label={`Don't attach ${staged.file.name}`}
                    onClick={() => onChange(files.filter((f) => f.key !== staged.key))}
                  >
                    Remove
                  </button>
                </fieldset>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

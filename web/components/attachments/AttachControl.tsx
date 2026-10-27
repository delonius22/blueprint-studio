"use client";

// Attaching files to the interview (SPEC-document-import §5): a button and a drop zone that
// upload each file, then hand the new ones to the workspace so the agent reads them.
import { type DragEvent, useRef, useState } from "react";
import { ApiError, sessionsApi, type UploadedAttachment } from "../../lib/sessions";
import styles from "./Attachments.module.css";

type Props = {
  sessionId: string;
  accepts: string[];
  disabled: boolean;
  onAttached: (files: UploadedAttachment[]) => void;
};

export function AttachControl({ sessionId, accepts, disabled, onAttached }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [over, setOver] = useState(false);
  const off = disabled || busy;

  async function upload(files: File[]) {
    if (off || files.length === 0) return;
    setBusy(true);
    setMessage(`Uploading ${files.length} file${files.length === 1 ? "" : "s"}…`);
    const added: UploadedAttachment[] = [];
    const problems: string[] = [];
    for (const file of files) {
      try {
        const uploaded = await sessionsApi.attach(sessionId, file);
        if (uploaded.duplicate) problems.push(`${file.name} is already attached as ${uploaded.id}`);
        else added.push(uploaded);
      } catch (caught) {
        problems.push(caught instanceof ApiError ? caught.message : `${file.name} could not be uploaded`);
      }
    }
    setBusy(false);
    setMessage(problems.join(". "));
    if (added.length) onAttached(added);
  }

  function drop(event: DragEvent) {
    event.preventDefault();
    setOver(false);
    void upload(Array.from(event.dataTransfer.files));
  }

  return (
    <div
      className={`${styles.drop} ${over && !off ? styles.over : ""}`}
      onDragOver={(event) => {
        event.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={drop}
    >
      <button type="button" disabled={off} onClick={() => input.current?.click()}>
        Attach files
      </button>
      <span className={styles.hint}>PRDs, specs, diagrams or notes; or drop them here</span>
      <input
        ref={input}
        type="file"
        multiple
        hidden
        accept={accepts.join(",")}
        aria-label="Files to attach"
        onChange={(event) => {
          void upload(Array.from(event.target.files ?? []));
          event.target.value = "";
        }}
      />
      <p role="status" className={styles.hint}>
        {message}
      </p>
    </div>
  );
}

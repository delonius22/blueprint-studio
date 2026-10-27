"use client";

// Attaching files to the interview (SPEC-document-import §5): the user chooses files, says what
// each one is, and attaches them; the workspace then hands the new ones to the agent.
import { useState } from "react";
import type { UploadedAttachment } from "../../lib/sessions";
import styles from "./Attachments.module.css";
import { FilePicker, type StagedFile, allLabelled } from "./FilePicker";
import { uploadStaged } from "./upload";

type Props = {
  sessionId: string;
  accepts: string[];
  disabled: boolean;
  onAttached: (files: UploadedAttachment[]) => void;
};

export function AttachControl({ sessionId, accepts, disabled, onAttached }: Props) {
  const [files, setFiles] = useState<StagedFile[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const off = disabled || busy;
  const ready = allLabelled(files);

  async function attach() {
    if (off || !ready) return;
    setBusy(true);
    setMessage(`Uploading ${files.length} file${files.length === 1 ? "" : "s"}…`);
    const { added, failed, problems } = await uploadStaged(sessionId, files);
    setBusy(false);
    setFiles(failed);
    setMessage(problems.join(". "));
    if (added.length) onAttached(added);
  }

  return (
    <div className={styles.attach}>
      <FilePicker accepts={accepts} disabled={off} files={files} onChange={setFiles} />
      {files.length > 0 && (
        <div className={styles.attachActions}>
          <button type="button" className="go" disabled={off || !ready} onClick={() => void attach()}>
            Attach {files.length} file{files.length === 1 ? "" : "s"}
          </button>
          {!ready && <span className={styles.hint}>Choose PRD, Spec or Supporting for each file first.</span>}
        </div>
      )}
      <p role="status" className={styles.hint}>
        {message}
      </p>
    </div>
  );
}

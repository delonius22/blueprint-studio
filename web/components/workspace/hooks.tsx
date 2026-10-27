"use client";

// The workspace's hooks (SPECS S11.2, S11.6, SPEC-document-import §5): thread history, tool
// notes in the chat, the error alert, and attaching files.
import { useAgent, useCopilotKit, useRenderTool } from "@copilotkit/react-core/v2";
import { useCallback, useEffect, useRef, useState } from "react";
import { AGENT_NAME } from "../../lib/constants";
import { roleLabel } from "../../lib/document-roles";
import { clearErrorForNewTurn } from "../../lib/errors";
import { type AttachmentListing, sessionsApi, type UploadedAttachment } from "../../lib/sessions";
import type { SessionState } from "../../lib/state";
import { toolNote } from "../../lib/tool-notes";
import type { ErrorInfo } from "./ErrorAlert";
import styles from "./Workspace.module.css";

// The runtime keeps a thread's events in memory only. After a restart it has nothing to
// replay, so an empty thread is re-synced from the agent's checkpoint with a run that adds
// no message: the graph ends at once and the agent sends its message and state snapshots.
export function useThreadHistory(sessionId: string) {
  const { copilotkit } = useCopilotKit();
  const { agent } = useAgent({ agentId: AGENT_NAME });
  useEffect(() => {
    let cancelled = false;
    agent.threadId = sessionId;
    void (async () => {
      await copilotkit.connectAgent({ agent });
      if (!cancelled && agent.messages.length === 0) await copilotkit.runAgent({ agent });
    })();
    return () => {
      cancelled = true;
    };
  }, [copilotkit, agent, sessionId]);
}

// The interviewer's design tools (every tool without a gate card) show as one line each in the
// chat, so a turn that only records items does not leave an empty message.
export function useToolNotes() {
  useRenderTool(
    {
      name: "*",
      render: ({ args, result }: { args?: unknown; result?: unknown }) => {
        const note = toolNote(args, result);
        return note ? <p className={styles.toolNote}>{note}</p> : null;
      },
    },
    [],
  );
}

// S11.6: last_error as a dismissible alert whose Retry re-sends the last user turn.
export function useLastError(error: ErrorInfo | null) {
  const { copilotkit } = useCopilotKit();
  const { agent } = useAgent({ agentId: AGENT_NAME });
  const failedTurn = useRef<string | null>(null);
  const [dismissed, setDismissed] = useState<ErrorInfo | null>(null);
  const [retrying, setRetrying] = useState(false);

  useEffect(() => {
    if (error && failedTurn.current === null) {
      const lastUser = [...agent.messages].reverse().find((m) => m.role === "user");
      failedTurn.current = lastUser?.id ?? null;
    }
    if (!error) failedTurn.current = null;
  }, [agent, error]);

  useEffect(() => {
    const subscription = agent.subscribe({
      onRunInitialized: ({ state, messages }) => {
        const next = clearErrorForNewTurn(state as Record<string, unknown>, messages, failedTurn.current);
        return next ? { state: next } : undefined;
      },
    });
    return () => subscription.unsubscribe();
  }, [agent]);

  async function retry() {
    setRetrying(true);
    try {
      agent.setState({ ...(agent.state as Record<string, unknown>), last_error: null });
      await copilotkit.runAgent({ agent });
    } finally {
      setRetrying(false);
    }
  }

  const visible = error && error !== dismissed && error.message !== dismissed?.message ? error : null;
  return { visible, retry, dismiss: () => setDismissed(error), retrying };
}

// SPEC-document-import §5: the attachment listing (the server decides what it accepts), and
// attaching: upload, then one chat line naming the new files, which starts the agent's import.
export function useAttachments(sessionId: string, refreshKey: string) {
  const { copilotkit } = useCopilotKit();
  const { agent } = useAgent({ agentId: AGENT_NAME });
  const [listing, setListing] = useState<AttachmentListing>({ accepts: [], attachments: [] });
  const refresh = useCallback(() => {
    sessionsApi.attachments(sessionId).then(setListing, () => undefined);
  }, [sessionId]);
  useEffect(refresh, [refresh, refreshKey]);

  async function attached(files: UploadedAttachment[]) {
    refresh();
    const names = files.map((f) => `${f.name} (${f.id}, ${roleLabel(f.role)})`).join(", ");
    agent.addMessage({ id: crypto.randomUUID(), role: "user", content: `Attached ${names}.` });
    await copilotkit.runAgent({ agent });
  }

  async function remove(attachmentId: string) {
    await sessionsApi.detach(sessionId, attachmentId).catch(() => undefined);
    refresh();
  }

  return { listing, attached, remove, running: agent.isRunning };
}

/** "brief.md · p.3" for every design item recorded from an attached file. */
export function itemSources(state: SessionState): Record<string, string> {
  const names = new Map((state.attachments ?? []).map((a) => [a.id, a.name]));
  return Object.fromEntries(
    Object.entries(state.provenance ?? {}).map(([itemId, ref]) => [
      itemId,
      `${names.get(ref.attachment_id) ?? ref.attachment_id} · ${ref.locator}`,
    ]),
  );
}

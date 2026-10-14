"use client";

// The session workspace (SPECS S11.1, S11.2): CopilotKit wired to this session's thread (S4.4).
import { CopilotChat, CopilotKit, useAgent, useCopilotKit } from "@copilotkit/react-core/v2";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AGENT_NAME, RUNTIME_PATH } from "../lib/constants";
import { ApiError, type SessionDetail, sessionsApi } from "../lib/sessions";
import { liveState } from "../lib/state";
import { Canvas } from "./canvas/Canvas";
import styles from "./Workspace.module.css";

// The runtime keeps a thread's events in memory only. After a restart it has nothing to
// replay, so an empty thread is re-synced from the agent's checkpoint with a run that adds
// no message: the graph ends at once and the agent sends its message and state snapshots.
function useThreadHistory(sessionId: string) {
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

function WorkspaceBody({ session }: { session: SessionDetail }) {
  useThreadHistory(session.id);
  const { agent } = useAgent({ agentId: AGENT_NAME });
  const state = liveState(agent.state, session.state);
  return (
    <div className={styles.body}>
      <main className={styles.main}>
        <Canvas design={state.design} />
      </main>
      <aside className={styles.chat} aria-label="Interview chat">
        <CopilotChat agentId={AGENT_NAME} threadId={session.id} />
      </aside>
    </div>
  );
}

export function Workspace({ sessionId }: { sessionId: string }) {
  const [session, setSession] = useState<SessionDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    sessionsApi
      .get(sessionId)
      .then(setSession)
      .catch((caught: unknown) =>
        setError(
          caught instanceof ApiError && caught.status === 404
            ? "This session does not exist. It may have been deleted."
            : "The session could not be loaded.",
        ),
      );
  }, [sessionId]);

  if (error) {
    return (
      <main className={styles.message}>
        <p role="alert">{error}</p>
        <Link href="/">Back to sessions</Link>
      </main>
    );
  }
  if (!session) {
    return (
      <main className={styles.message} aria-busy="true">
        <p>Loading session…</p>
      </main>
    );
  }

  return (
    <CopilotKit runtimeUrl={RUNTIME_PATH} agentId={AGENT_NAME}>
      <div className={styles.shell}>
        <header className={styles.header}>
          <Link href="/">Sessions</Link>
          <h1>{session.name}</h1>
        </header>
        <WorkspaceBody session={session} />
      </div>
    </CopilotKit>
  );
}

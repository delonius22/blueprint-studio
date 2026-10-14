"use client";

// The session workspace (SPECS S11.1, S11.2): CopilotKit wired to this session's thread (S4.4).
import {
  CopilotChat,
  CopilotKit,
  useAgent,
  useCopilotKit,
  useHumanInTheLoop,
} from "@copilotkit/react-core/v2";
import Link from "next/link";
import { useEffect, useState } from "react";
import { z } from "zod";
import { AGENT_NAME, RUNTIME_PATH } from "../lib/constants";
import { ApiError, type SessionDetail, sessionsApi } from "../lib/sessions";
import { liveState } from "../lib/state";
import { Canvas } from "./canvas/Canvas";
import { ConfirmStepCard, type ConfirmStepArgs } from "./gates/ConfirmStepCard";
import { StageTracker } from "./StageTracker";
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

// Approval gates are frontend tools rendered as cards (PRD D5, SPECS S11.4).
function useGates() {
  useHumanInTheLoop<ConfirmStepArgs>({
    name: "confirm_step",
    description:
      "Ask the user to confirm that the current framework step is complete before moving to " +
      "the next one. Call it only when the step's questions are answered and recorded. " +
      "step: the current step number. summary: a short summary of what the step established. " +
      'The answer is {"approved": true} or {"approved": false, "missing": "<what the user says is missing>"}.',
    parameters: z.object({ step: z.number().int().min(1).max(5), summary: z.string() }),
    render: ({ args, status, respond, result }) => (
      <ConfirmStepCard
        args={args}
        status={String(status) as "inProgress" | "executing" | "complete"}
        respond={respond ? (answer) => void respond(answer) : undefined}
        result={result}
      />
    ),
  });
}

function WorkspaceShell({ session }: { session: SessionDetail }) {
  useThreadHistory(session.id);
  useGates();
  const { agent } = useAgent({ agentId: AGENT_NAME });
  const state = liveState(agent.state, session.state);
  return (
    <div className={styles.shell}>
      <header className={styles.header}>
        <Link href="/">Sessions</Link>
        <h1>{session.name}</h1>
        <StageTracker
          stage={state.stage}
          currentStep={state.current_step}
          confirmedSteps={state.confirmed_steps}
        />
      </header>
      <div className={styles.body}>
        <main className={styles.main}>
          <Canvas design={state.design} />
        </main>
        <aside className={styles.chat} aria-label="Interview chat">
          <CopilotChat agentId={AGENT_NAME} threadId={session.id} />
        </aside>
      </div>
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
      <WorkspaceShell session={session} />
    </CopilotKit>
  );
}

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
import { useEffect, useRef, useState } from "react";
import { z } from "zod";
import { AGENT_NAME, RUNTIME_PATH } from "../lib/constants";
import { clearErrorForNewTurn } from "../lib/errors";
import { ApiError, type SessionDetail, sessionsApi } from "../lib/sessions";
import { liveState, type PrdDoc } from "../lib/state";
import { Canvas } from "./canvas/Canvas";
import { ConfirmStepCard, type ConfirmStepArgs } from "./gates/ConfirmStepCard";
import { type CardGap, DecideGapsCard } from "./gates/DecideGapsCard";
import { TicketView } from "./TicketView";
import { CompletionView } from "./CompletionView";
import { SignOffCard } from "./gates/SignOffCard";
import { DownloadsMenu } from "./DownloadsMenu";
import { PrdViewer } from "./PrdViewer";
import { ErrorAlert, type ErrorInfo } from "./ErrorAlert";
import { GapRegister } from "./GapRegister";
import { ScorecardPanel } from "./ScorecardPanel";
import { ReviewModelWarning } from "./ReviewModelWarning";
import { StageTracker } from "./StageTracker";
import { TokenMeter } from "./TokenMeter";
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

// Approval gates are frontend tools rendered as cards (PRD D5, SPECS S11.4). Since the build only
// the step confirmations, the gap decisions and the PRD sign-off stop for the user.
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
  useHumanInTheLoop<{ gaps: CardGap[] }>({
    name: "decide_gaps",
    description:
      "The app asks the user to answer or accept each open gap from the design review. " +
      "Never call this yourself.",
    parameters: z.object({
      gaps: z.array(
        z.object({
          id: z.string(),
          lens: z.string(),
          severity: z.string(),
          item_ids: z.array(z.string()),
          risk: z.string(),
          decision_needed: z.string(),
        }),
      ),
    }),
    render: ({ args, status, respond, result }) => (
      <DecideGapsCard
        args={args}
        status={String(status) as "inProgress" | "executing" | "complete"}
        respond={respond ? (decisions) => void respond(decisions) : undefined}
        result={result}
      />
    ),
  });
  useHumanInTheLoop<{ prd: PrdDoc }>({
    name: "sign_off_prd",
    description: "The app asks the user to sign off PRD v1.0 or reject it with a reason. Never call this yourself.",
    parameters: z.object({ prd: z.any() }),
    render: ({ args, status, respond, result }) => (
      <SignOffCard
        args={args as Partial<{ prd: PrdDoc }>}
        status={String(status) as "inProgress" | "executing" | "complete"}
        respond={respond ? (answer) => void respond(answer) : undefined}
        result={result}
      />
    ),
  });
}

// S11.6: last_error as a dismissible alert whose Retry re-sends the last user turn.
function useLastError(error: ErrorInfo | null) {
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

function NoAddMenu() {
  return null;
}

const OPENING_PLACEHOLDER = "What would you like to build?";
const ANSWER_PLACEHOLDER = "Type your answer...";
const WELCOME =
  "Tell me what you'd like to build, in as much or as little detail as you have. " +
  "I'll turn it into requirements and walk you through the five design steps with questions.";

function WorkspaceShell({ session }: { session: SessionDetail }) {
  useThreadHistory(session.id);
  useGates();
  const { agent } = useAgent({ agentId: AGENT_NAME });
  const state = liveState(agent.state, session.state);
  const lastError = useLastError((state.last_error as ErrorInfo | null) ?? null);
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
        <TokenMeter used={state.tokens_used} budget={state.token_budget} />
        <DownloadsMenu
          sessionId={session.id}
          sessionName={session.name}
          refreshKey={`${state.stage}-${state.prd_versions.length}`}
        />
      </header>
      <ReviewModelWarning distinct={state.review_model_distinct} />
      {lastError.visible && (
        <ErrorAlert
          error={lastError.visible}
          busy={lastError.retrying}
          onRetry={() => void lastError.retry()}
          onDismiss={lastError.dismiss}
        />
      )}
      <div className={styles.body}>
        {/* Focusable so keyboard users can scroll the panel even where it holds no control. */}
        <main className={styles.main} tabIndex={0} aria-label="Session workspace">
          {state.scorecard && ["interview", "design_review", "gap_resolution"].includes(state.stage) && (
            <ScorecardPanel scorecard={state.scorecard} />
          )}
          {state.stage === "interview" ? (
            // Read-only: the interviewer records the design; the user answers in the chat.
            <Canvas design={state.design} />
          ) : state.stage === "design_review" || state.stage === "gap_resolution" ? (
            <GapRegister gaps={state.gaps} design={state.design} stage={state.stage} />
          ) : state.stage === "complete" ? (
            <>
              <CompletionView sessionId={session.id} sessionName={session.name} />
              <TicketView tickets={state.tickets} stage={state.stage} />
            </>
          ) : ["ticket_breakdown", "ticket_gate"].includes(state.stage) ? (
            <TicketView tickets={state.tickets} stage={state.stage} />
          ) : (
            <PrdViewer draft={state.prd_draft ?? null} versions={state.prd_versions} stage={state.stage} />
          )}
        </main>
        <aside className={styles.chat} aria-label="Interview chat">
          <CopilotChat
            agentId={AGENT_NAME}
            threadId={session.id}
            // A new session opens on one question; the user's answer is the brief the
            // interviewer records first, and from then on the interviewer leads.
            labels={{
              chatInputPlaceholder: agent.messages.length === 0 ? OPENING_PLACEHOLDER : ANSWER_PLACEHOLDER,
              welcomeMessageText: WELCOME,
            }}
            // S11.7: the send and scroll-to-bottom buttons get accessible names; the attachments
            // menu has nothing to offer in this app (no attachments, no tools menu), so it is
            // not rendered.
            input={{ sendButton: { "aria-label": "Send message" }, addMenuButton: NoAddMenu }}
            scrollView={{ scrollToBottomButton: { "aria-label": "Scroll to the latest message" } }}
          />
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

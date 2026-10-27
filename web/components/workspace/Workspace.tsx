"use client";

// The session workspace (SPECS S11.1, S11.2): CopilotKit wired to this session's thread (S4.4).
import { CopilotChat, CopilotKit, useAgent } from "@copilotkit/react-core/v2";
import Link from "next/link";
import { useEffect, useState } from "react";
import { AGENT_NAME, RUNTIME_PATH } from "../../lib/constants";
import { ApiError, type SessionDetail, sessionsApi } from "../../lib/sessions";
import { liveState } from "../../lib/state";
import { AttachControl } from "../attachments/AttachControl";
import { SourcesPanel } from "../attachments/SourcesPanel";
import { Canvas } from "../canvas/Canvas";
import { AllDiagrams } from "../canvas/Diagrams";
import { CompletionView } from "../delivery/CompletionView";
import { PrdViewer } from "../delivery/PrdViewer";
import { TicketView } from "../delivery/TicketView";
import { useGates } from "../gates/useGates";
import { GapRegister } from "../review/GapRegister";
import { ScorecardPanel } from "../review/ScorecardPanel";
import { DownloadsMenu } from "./DownloadsMenu";
import { ErrorAlert, type ErrorInfo } from "./ErrorAlert";
import { itemSources, useAttachments, useLastError, useThreadHistory, useToolNotes } from "./hooks";
import { ReviewModelWarning } from "./ReviewModelWarning";
import { StageTracker } from "./StageTracker";
import { TokenMeter } from "./TokenMeter";
import styles from "./Workspace.module.css";

function NoAddMenu() {
  return null;
}

const OPENING_PLACEHOLDER = "What would you like to build?";
const ANSWER_PLACEHOLDER = "Type your answer...";

function WorkspaceShell({ session }: { session: SessionDetail }) {
  useThreadHistory(session.id);
  useGates();
  useToolNotes();
  const { agent } = useAgent({ agentId: AGENT_NAME });
  const state = liveState(agent.state, session.state);
  const lastError = useLastError((state.last_error as ErrorInfo | null) ?? null);
  const interviewing = state.stage === "interview";
  const files = useAttachments(session.id, `${state.stage}-${state.attachments?.length ?? 0}`);
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
            <>
              <SourcesPanel
                sessionId={session.id}
                listing={files.listing.attachments}
                state={state}
                canRemove={!files.running}
                onRemove={(id) => void files.remove(id)}
              />
              <Canvas design={state.design} sources={itemSources(state)} />
            </>
          ) : state.stage === "design_review" || state.stage === "gap_resolution" ? (
            <GapRegister gaps={state.gaps} design={state.design} stage={state.stage} />
          ) : state.stage === "complete" ? (
            <>
              <CompletionView sessionId={session.id} sessionName={session.name} />
              <AllDiagrams design={state.design} />
              <TicketView tickets={state.tickets} stage={state.stage} />
            </>
          ) : ["ticket_breakdown", "ticket_gate"].includes(state.stage) ? (
            <TicketView tickets={state.tickets} stage={state.stage} />
          ) : (
            <PrdViewer draft={state.prd_draft ?? null} versions={state.prd_versions} stage={state.stage} />
          )}
        </main>
        <aside className={styles.chat} aria-label="Interview chat">
          {interviewing && (
            <AttachControl
              sessionId={session.id}
              accepts={files.listing.accepts}
              disabled={files.running}
              onAttached={(added) => void files.attached(added)}
            />
          )}
          <CopilotChat
            agentId={AGENT_NAME}
            threadId={session.id}
            // A new session opens on one question; the user's answer is the brief the
            // interviewer records first, and from then on the interviewer leads. (CopilotKit
            // shows no welcome screen on a chat bound to a saved thread, so the input asks.)
            labels={{
              chatInputPlaceholder: agent.messages.length === 0 ? OPENING_PLACEHOLDER : ANSWER_PLACEHOLDER,
            }}
            // S11.7: the send and scroll-to-bottom buttons get accessible names. CopilotKit's own
            // attachments menu is not rendered: files are attached above the chat instead, so
            // they reach the agent's import (SPEC-document-import §5).
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

// Keeps last_error from blocking the user's next turn (SPECS S5.1, S11.6).
//
// The graph ends any run that starts while last_error is set, so a page-load re-sync never
// retries a failed call by itself. The workspace clears last_error at the start of a run the
// user starts: Retry, or a new message (the newest message is not the turn that failed).
type Message = { id: string; role: string };
type State = Record<string, unknown> & { last_error?: unknown };

export function clearErrorForNewTurn(
  state: State,
  messages: readonly Message[],
  failedTurnId: string | null,
): State | undefined {
  if (!state.last_error) return undefined;
  const newest = messages.at(-1);
  if (newest && newest.role === "user" && newest.id !== failedTurnId) return { ...state, last_error: null };
  return undefined;
}

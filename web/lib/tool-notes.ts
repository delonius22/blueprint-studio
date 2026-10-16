// What the interviewer's design tools did, as one chat line each (SPECS S5.3): the canvas
// shows the item, the chat says it was recorded. Gate tools have their own cards.

// The field that best names an item, by design list.
const SUMMARY_FIELDS = ["statement", "text", "name", "scenario", "risk", "data", "quantity", "decision", "signal"];

const MAX_SUMMARY = 90;

function summary(args: unknown): string | null {
  if (!args || typeof args !== "object") return null;
  for (const field of SUMMARY_FIELDS) {
    const value = (args as Record<string, unknown>)[field];
    if (typeof value === "string" && value.trim()) {
      const text = value.trim().replace(/\s+/g, " ");
      return text.length > MAX_SUMMARY ? `${text.slice(0, MAX_SUMMARY - 1)}…` : text;
    }
  }
  return null;
}

// The line for a finished design tool call, or null to show nothing: while it runs, and when
// it failed (the interviewer reads the error and corrects itself).
export function toolNote(args: unknown, result: unknown): string | null {
  if (typeof result !== "string") return null;
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(result) as Record<string, unknown>;
  } catch {
    return null;
  }
  if (!parsed || typeof parsed !== "object" || "error" in parsed) return null;
  if (parsed.recorded === "cap_stance") return "✓ Recorded the CAP stance";
  const verbs: [string, string][] = [
    ["recorded", "Recorded"],
    ["decided", "Decided"],
    ["resolved", "Resolved"],
    ["deleted", "Deleted"],
  ];
  for (const [key, verb] of verbs) {
    const id = parsed[key];
    if (typeof id === "string") {
      const about = key === "recorded" ? summary(args) : null;
      return `✓ ${verb} ${id}${about ? `: ${about}` : ""}`;
    }
  }
  return null;
}

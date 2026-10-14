// Server-side only: where the agent service lives (SPECS S1.3 AGENT_URL).
export function agentUrl(): string {
  const url = process.env.AGENT_URL;
  if (!url) throw new Error("AGENT_URL is required but is not set");
  return url.replace(/\/+$/, "");
}

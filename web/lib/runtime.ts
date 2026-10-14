// The CopilotKit runtime that proxies the browser to the agent service (SPECS S4.3).
// The browser only ever talks to RUNTIME_PATH on this app; AGENT_URL is server-side only.
import { HttpAgent } from "@ag-ui/client";
import { CopilotRuntime, createCopilotRuntimeHandler } from "@copilotkit/runtime/v2";
import { AGENT_NAME, RUNTIME_PATH } from "./constants";

export type RuntimeHandler = (request: Request) => Promise<Response>;

export function createRuntimeHandler(agentUrl: string): RuntimeHandler {
  const runtime = new CopilotRuntime({
    agents: { [AGENT_NAME]: new HttpAgent({ url: `${agentUrl.replace(/\/+$/, "")}/agent` }) },
  });
  return createCopilotRuntimeHandler({ runtime, basePath: RUNTIME_PATH });
}

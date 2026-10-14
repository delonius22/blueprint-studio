import { createRuntimeHandler, type RuntimeHandler } from "../../../../lib/runtime";

export const dynamic = "force-dynamic";

let handler: RuntimeHandler | undefined;

// Read AGENT_URL per process at request time, never at build time.
function runtimeHandler(): RuntimeHandler {
  if (!handler) {
    const agentUrl = process.env.AGENT_URL;
    if (!agentUrl) throw new Error("AGENT_URL is required but is not set");
    handler = createRuntimeHandler(agentUrl);
  }
  return handler;
}

export function GET(request: Request): Promise<Response> {
  return runtimeHandler()(request);
}

export function POST(request: Request): Promise<Response> {
  return runtimeHandler()(request);
}

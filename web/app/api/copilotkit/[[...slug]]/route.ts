import { agentUrl } from "../../../../lib/agent-url";
import { createRuntimeHandler, type RuntimeHandler } from "../../../../lib/runtime";

export const dynamic = "force-dynamic";

let handler: RuntimeHandler | undefined;

// Read AGENT_URL per process at request time, never at build time.
function runtimeHandler(): RuntimeHandler {
  handler ??= createRuntimeHandler(agentUrl());
  return handler;
}

export function GET(request: Request): Promise<Response> {
  return runtimeHandler()(request);
}

export function POST(request: Request): Promise<Response> {
  return runtimeHandler()(request);
}

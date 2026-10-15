// Proxies the session REST API (SPECS S3) to the agent service, which the browser never calls.
import { agentUrl } from "../../../../lib/agent-url";

export const dynamic = "force-dynamic";

async function forward(request: Request): Promise<Response> {
  const incoming = new URL(request.url);
  const target = `${agentUrl()}${incoming.pathname}${incoming.search}`;
  const body = ["GET", "HEAD", "DELETE"].includes(request.method) ? undefined : await request.text();
  const response = await fetch(target, {
    method: request.method,
    headers: { "content-type": request.headers.get("content-type") ?? "application/json" },
    body,
    cache: "no-store",
  });
  const headers = new Headers();
  for (const name of ["content-type", "content-disposition"]) {
    const value = response.headers.get(name);
    if (value) headers.set(name, value);
  }
  return new Response(response.status === 204 ? null : await response.arrayBuffer(), {
    status: response.status,
    headers,
  });
}

export { forward as DELETE, forward as GET, forward as PATCH, forward as POST };

import { compose } from "./stack";

export default function globalSetup(): void {
  if (process.env.E2E_REUSE_STACK) return;
  compose("up", "--build", "--wait", "--detach");
}

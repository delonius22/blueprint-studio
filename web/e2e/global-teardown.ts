import { compose } from "./stack";

export default function globalTeardown(): void {
  if (process.env.E2E_REUSE_STACK) return;
  compose("down", "--volumes");
}

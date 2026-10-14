// T-19: no provider key reaches the web build (SPECS S1.5, NFR-6). The app is built with
// sentinel key values in the environment, and every built file is searched for them.
import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";

const root = join(__dirname, "..");
const KEYS = ["sk-interview-sentinel-7f3a91", "sk-review-sentinel-2c84d0"];

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? (name === "cache" ? [] : files(path)) : [path];
  });
}

it("the web bundle contains neither configured key value", { timeout: 240_000 }, () => {
  execFileSync(join(root, "node_modules", ".bin", "next"), ["build"], {
    cwd: root,
    env: { ...process.env, MODEL_API_KEY: KEYS[0], REVIEW_MODEL_API_KEY: KEYS[1], NEXT_TELEMETRY_DISABLED: "1" },
    stdio: "pipe",
  });
  const built = files(join(root, ".next"));
  expect(built.length).toBeGreaterThan(20);
  for (const file of built) {
    const text = readFileSync(file, "latin1");
    for (const key of KEYS) expect(text.includes(key), `${key} found in ${file}`).toBe(false);
  }
});

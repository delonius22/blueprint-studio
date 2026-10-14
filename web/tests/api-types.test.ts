// T-02: the frontend's REST types are generated from the agent's OpenAPI document (SPECS S3.7).
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { expect, it } from "vitest";

const root = join(__dirname, "..");

it("lib/api-schema.d.ts is exactly what openapi-typescript generates from openapi.json", () => {
  const cli = join(root, "tools", "openapi", "node_modules", ".bin", "openapi-typescript");
  const generated = execFileSync(cli, [join(root, "openapi.json")], { encoding: "utf8" });
  const checkedIn = readFileSync(join(root, "lib", "api-schema.d.ts"), "utf8");
  expect(checkedIn, "run: npm run gen:api").toBe(generated);
});

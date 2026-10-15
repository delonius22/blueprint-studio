// Brings the e2e stack (docker-compose.yml + docker-compose.e2e.yml) up and down.
import { execFileSync } from "node:child_process";
import { join } from "node:path";

const root = join(__dirname, "..", "..");
const files = ["-f", "docker-compose.yml", "-f", "docker-compose.e2e.yml", "-p", "blueprint-e2e"];

export function compose(...args: string[]): void {
  execFileSync("docker", ["compose", ...files, ...args], { cwd: root, stdio: "inherit" });
}

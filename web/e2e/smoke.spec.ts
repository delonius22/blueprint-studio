// T-20: one session through the full stack with scripted fake models — from creating a session
// to downloading the zip (SPECS S10.8) — run as five sessions at once (NFR-12). The first one
// also scans every screen, panel and gate card for WCAG 2.1 AA violations in both themes and
// drives the session list and a gate card by keyboard (S11.7).
import AxeBuilder from "@axe-core/playwright";
import { expect, type Page, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { strFromU8, unzipSync } from "fflate";

type Violations = { scope: string; theme: string; rule: string; impact: string | null | undefined; nodes: string[] }[];

async function scan(page: Page, scope: string, found: Violations): Promise<void> {
  for (const theme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme: theme });
    const result = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]).analyze();
    for (const v of result.violations) {
      found.push({ scope, theme, rule: v.id, impact: v.impact, nodes: v.nodes.map((n) => n.target.join(" ")).slice(0, 5) });
    }
  }
  await page.emulateMedia({ colorScheme: "light" });
}

// The chat input asks "What would you like to build?" until the first message, then for answers.
const CHAT_INPUT = /^(What would you like to build\?|Type your answer\.\.\.)$/;

async function send(page: Page, text: string): Promise<void> {
  // The chat ignores Enter while a run is still in progress (for example the re-sync run on
  // page load), so keep pressing until the message has gone.
  const input = page.getByPlaceholder(CHAT_INPUT);
  await expect(input).toBeEditable();
  await input.fill(text);
  await expect(async () => {
    if ((await input.inputValue()) !== "") await input.press("Enter");
    await expect(input).toHaveValue("", { timeout: 1_000 });
  }).toPass({ timeout: 30_000 });
}

async function confirmStep(page: Page, step: number, keyboard = false): Promise<void> {
  await send(page, `CONFIRM ${step}`);
  const approve = page.getByRole("button", { name: `Approve step ${step}` });
  await expect(approve).toBeVisible();
  if (keyboard) {
    // Reach the button with Tab alone, then press it with Enter.
    await page.getByPlaceholder(CHAT_INPUT).focus();
    for (let i = 0; i < 60 && !(await approve.evaluate((el) => el === document.activeElement)); i++) {
      await page.keyboard.press("Shift+Tab");
    }
    await expect(approve).toBeFocused();
    await page.keyboard.press("Enter");
  } else {
    await approve.click();
  }
  await expect(page.getByText(`Step ${step} critique`)).toBeVisible();
}

for (let n = 1; n <= 5; n++) {
  test(`session ${n}: interview to zip`, async ({ page }) => {
    const tag = `s${n}-${Date.now().toString(36)}`;
    const audit = n === 1;
    const violations: Violations = [];
    const unrendered: string[] = [];
    page.on("console", (message) => {
      if (message.text().includes("no renderer is registered")) unrendered.push(message.text());
    });

    // Session list: create the session (by keyboard in the audited run).
    await page.goto("/");
    if (audit) await scan(page, "session list", violations);
    const name = page.getByLabel("Session name");
    if (audit) {
      await name.focus();
      await page.keyboard.type(`Smoke ${tag}`);
      await page.keyboard.press("Tab");
      await expect(page.getByRole("button", { name: "New session" })).toBeFocused();
      await page.keyboard.press("Enter");
    } else {
      await name.fill(`Smoke ${tag}`);
      await page.getByRole("button", { name: "New session" }).click();
    }
    await page.waitForURL(/\/s\//);
    const sessionId = page.url().split("/s/")[1];

    // Step 1: the chat opens on one question; the answer is recorded live on the canvas.
    await expect(page.getByPlaceholder("What would you like to build?")).toBeVisible();
    await send(page, `FR: Users shorten URLs for ${tag}\nFR: Visitors are redirected for ${tag}`);
    await expect(page.getByRole("region", { name: /^Functional requirements/ }).getByText("FR-2")).toBeVisible();
    await expect(page.getByPlaceholder("Type your answer...")).toBeVisible();
    // Each recorded item is a line in the chat too.
    const chat = page.getByRole("complementary", { name: "Interview chat" });
    await expect(chat.getByText(`✓ Recorded FR-2: Visitors are redirected for ${tag}`)).toBeVisible();
    if (audit) await scan(page, "workspace: canvas (interview)", violations);
    await send(page, "CONFIRM 1");
    await expect(page.getByRole("group", { name: /Confirm Step 1/ })).toBeVisible();
    if (audit) await scan(page, "gate card: confirm_step", violations);
    await page.getByRole("button", { name: "Not yet" }).click(); // reject with a reason first
    await page.getByLabel("What is missing from step 1?").fill("Nothing really; approve next time");
    await page.getByRole("button", { name: "Send back" }).click();
    await expect(page.getByText(/Step 1 sent back/)).toBeVisible();
    await page.waitForTimeout(500);
    await confirmStep(page, 1, audit);

    await confirmStep(page, 2);
    await send(page, "CMP: API\nFM: Database is down");
    await expect(page.getByRole("region", { name: /^Failure modes/ }).getByText("FM-1")).toBeVisible();
    await confirmStep(page, 3);
    await send(page, "SPOF: CMP-1 | One API node | Two replicas");
    await expect(page.getByRole("region", { name: /^Single points of failure/ }).getByText("SPOF-1")).toBeVisible();
    await confirmStep(page, 4);
    await confirmStep(page, 5);
    await expect(page.getByText("Final scorecard")).toBeVisible();

    // Design review on the review model: one gap, accepted as an open risk.
    const gapCard = page.getByRole("form", { name: "Decide the open gaps" });
    await expect(gapCard).toBeVisible();
    await expect(page.getByRole("table")).toContainText("GAP-1");
    if (audit) await scan(page, "gate card: decide_gaps + gap register", violations);
    await gapCard.getByRole("radio", { name: "Accept as open risk" }).check();
    await gapCard.getByLabel("Note for GAP-1 (optional)").fill(`Accepted for ${tag}`);
    await gapCard.getByRole("button", { name: "Submit decisions" }).click();

    // PRD v1.0 sign-off is the last approval: seams (v1.1), proposed changes (v1.2) and the
    // tickets follow by themselves.
    const signOff = page.getByRole("button", { name: "Sign off v1.0" });
    await expect(signOff).toBeVisible();
    if (audit) await scan(page, "gate card: sign_off_prd + PRD viewer", violations);
    await signOff.click();

    // Completion: download everything as one zip.
    const all = page.getByRole("link", { name: "Download all (.zip)" });
    await expect(all).toBeVisible();
    // The diagrams are drawn in the browser, not just listed as source.
    await expect(page.getByRole("img", { name: /^Architecture diagram/ }).locator("svg")).toBeVisible();
    if (audit) await scan(page, "completion view", violations);
    const [download] = await Promise.all([page.waitForEvent("download"), all.click()]);
    expect(download.suggestedFilename()).toBe(`Smoke ${tag} - Blueprint.zip`);
    const files = unzipSync(new Uint8Array(readFileSync(await download.path())));
    expect(Object.keys(files)).toEqual([
      "PRD v1.0.docx", "PRD v1.1.docx", "PRD v1.2.docx", "Requirements.docx", "UserStories.docx", "context.md",
      "Diagrams.md",
    ]); // prettier-ignore

    // Independence: this session's documents hold this session's design and no other's.
    const diagramsMd = strFromU8(files["Diagrams.md"]);
    expect(diagramsMd).toContain("## Architecture");
    expect(diagramsMd).toContain("```mermaid\nflowchart LR");
    const context = strFromU8(files["context.md"]);
    expect(context).toContain(`FR-1: Users shorten URLs for ${tag}`);
    expect(context).toContain(`Note: Accepted for ${tag}`);
    const tags = new Set(Array.from(context.matchAll(/for (s\d-[a-z0-9]+)/g), (m) => m[1]));
    expect([...tags]).toEqual([tag]); // no other session's design leaked in
    const detail = await (await page.request.get(`/api/sessions/${sessionId}`)).json();
    expect(detail.state.stage).toBe("complete");
    expect(detail.state.design.functional_requirements.map((r: { statement: string }) => r.statement)).toEqual([
      `Users shorten URLs for ${tag}`,
      `Visitors are redirected for ${tag}`,
    ]);
    expect(detail.state.prd_versions.map((v: { version: string }) => v.version)).toEqual(["1.0", "1.1", "1.2"]);

    expect(violations, JSON.stringify(violations, null, 2)).toEqual([]);
    expect(unrendered).toEqual([]); // every tool call the agent makes has a renderer
  });
}

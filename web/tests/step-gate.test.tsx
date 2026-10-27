// @vitest-environment jsdom
// T-04: the confirm_step card (SPECS S5.7, S11.4) and the header's stage tracker (S11.2).
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConfirmStepCard } from "../components/gates/ConfirmStepCard";
import { StageTracker } from "../components/workspace/StageTracker";

afterEach(cleanup);

describe("ConfirmStepCard", () => {
  const args = { step: 1, summary: "Users shorten URLs; p95 redirect under 50 ms." };

  it("shows what is being decided and approves", async () => {
    const respond = vi.fn();
    render(<ConfirmStepCard args={args} status="executing" respond={respond} />);
    const card = screen.getByRole("group", { name: "Confirm Step 1: Clarify requirements" });
    expect(within(card).getByText(args.summary)).toBeTruthy();

    await userEvent.click(screen.getByRole("button", { name: "Approve step 1" }));
    expect(respond).toHaveBeenCalledWith({ approved: true });
  });

  it("requires text to send a step back", async () => {
    const respond = vi.fn();
    render(<ConfirmStepCard args={args} status="executing" respond={respond} />);
    await userEvent.click(screen.getByRole("button", { name: "Not yet" }));

    const send = screen.getByRole("button", { name: "Send back" }) as HTMLButtonElement;
    expect(send.disabled).toBe(true);
    await userEvent.type(screen.getByLabelText("What is missing from step 1?"), "   ");
    expect(send.disabled).toBe(true);
    await userEvent.type(screen.getByLabelText("What is missing from step 1?"), "No availability target");
    expect(send.disabled).toBe(false);
    await userEvent.click(send);
    expect(respond).toHaveBeenCalledWith({ approved: false, missing: "No availability target" });
  });

  it("shows the outcome once answered", () => {
    render(<ConfirmStepCard args={args} status="complete" result='{"approved": false, "missing": "SLOs"}' />);
    expect(screen.getByText("Step 1 sent back: SLOs")).toBeTruthy();
    expect(screen.queryByRole("button")).toBeNull();
  });
});

describe("StageTracker", () => {
  it("marks confirmed steps and the current step", () => {
    render(<StageTracker stage="interview" currentStep={3} confirmedSteps={[1, 2]} />);
    const items = within(screen.getByRole("navigation", { name: "Progress" })).getAllByRole("listitem");
    expect(items.map((item) => item.textContent)).toEqual([
      expect.stringContaining("Step 1: Clarify requirements, confirmed"),
      expect.stringContaining("Step 2: Data & API layer, confirmed"),
      expect.stringContaining("Step 3: High-level architecture, current"),
      expect.stringContaining("Step 4: Scale, bottlenecks & reliability, not started"),
      expect.stringContaining("Step 5: Trade-offs & extensions, not started"),
    ]);
    expect(items[2].getAttribute("aria-current")).toBe("step");
  });

  it("shows the stage after the interview", () => {
    render(<StageTracker stage="design_review" currentStep={5} confirmedSteps={[1, 2, 3, 4, 5]} />);
    expect(screen.getByText("Stage: Design review")).toBeTruthy();
    expect(document.querySelector("[aria-current]")).toBeNull();
  });
});

describe("blocked confirmation", () => {
  it("renders no card when the graph answered the call with blockers (S5.6)", () => {
    const result = JSON.stringify({ error: "Step 3 cannot be confirmed yet.", blockers: ["needs a failure mode"] });
    const { container } = render(
      <ConfirmStepCard args={{ step: 3, summary: "done" }} status="complete" result={result} />,
    );
    expect(container.innerHTML).toBe("");
  });
});

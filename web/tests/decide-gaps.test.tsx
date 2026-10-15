// @vitest-environment jsdom
// T-11: decide_gaps decides item by item and offers accept all; answers require text and
// acceptance notes are optional (SPECS S6.5, S11.4).
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { type CardGap, DecideGapsCard } from "../components/gates/DecideGapsCard";

afterEach(cleanup);

const gaps: CardGap[] = [
  { id: "GAP-1", lens: "security", severity: "high", item_ids: ["EP-1"], risk: "Open endpoint", decision_needed: "Who may call it?" },
  { id: "GAP-2", lens: "efficiency", severity: "low", item_ids: ["FR-1"], risk: "No cache", decision_needed: "Cache hot codes?" },
];

describe("DecideGapsCard", () => {
  it("shows each gap and submits per-gap decisions once every answer has text", async () => {
    const respond = vi.fn();
    render(<DecideGapsCard args={{ gaps }} status="executing" respond={respond} />);
    expect(screen.getByText(/Open endpoint/)).toBeTruthy();
    const submit = screen.getByRole("button", { name: "Submit decisions" }) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);

    const [answer1] = screen.getAllByRole("radio", { name: "Answer" });
    await userEvent.click(answer1);
    const [, accept2] = screen.getAllByRole("radio", { name: "Accept as open risk" });
    await userEvent.click(accept2);
    expect(submit.disabled).toBe(true); // GAP-1's answer has no text yet
    await userEvent.type(screen.getByLabelText("Your answer to GAP-1"), "Signed-in users only");
    expect(submit.disabled).toBe(false); // GAP-2's note is optional

    await userEvent.click(submit);
    expect(respond).toHaveBeenCalledWith([
      { gap_id: "GAP-1", decision: "answer", text: "Signed-in users only" },
      { gap_id: "GAP-2", decision: "accept", text: "" },
    ]);
  });

  it("accepts all at once", async () => {
    const respond = vi.fn();
    render(<DecideGapsCard args={{ gaps }} status="executing" respond={respond} />);
    await userEvent.click(screen.getByRole("button", { name: "Accept all as open risks" }));
    expect(respond).toHaveBeenCalledWith([
      { gap_id: "GAP-1", decision: "accept", text: "" },
      { gap_id: "GAP-2", decision: "accept", text: "" },
    ]);
  });

  it("shows the decisions once answered", () => {
    const result = JSON.stringify([{ gap_id: "GAP-1", decision: "accept", text: "v2" }]);
    render(<DecideGapsCard args={{ gaps }} status="complete" result={result} />);
    expect(screen.getByText("GAP-1: accepted as an open risk — v2")).toBeTruthy();
  });
});

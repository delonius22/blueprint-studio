// @vitest-environment jsdom
// T-14: review_changes decides each change (a rejection needs a reason) or accepts all.
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { type CardChange, ReviewChangesCard } from "../components/gates/ReviewChangesCard";

afterEach(cleanup);

const changes: CardChange[] = [
  { id: "CHG-1", section: "goals", kind: "add", proposed_text: "Links expire", reason: "Needed by US-4" },
  { id: "CHG-2", section: "functional_requirements", target_id: "FR-2", kind: "modify", current_text: "Redirect", proposed_text: "Redirect with 301", reason: "Precision" },
];

it("decides change by change, requiring a reason to reject", async () => {
  const respond = vi.fn();
  render(<ReviewChangesCard args={{ changes }} status="executing" respond={respond} />);
  expect(screen.getByText(/Redirect with 301/)).toBeTruthy();
  const submit = screen.getByRole("button", { name: "Submit decisions" }) as HTMLButtonElement;
  const [approve1] = screen.getAllByRole("radio", { name: "Approve" });
  const [, reject2] = screen.getAllByRole("radio", { name: "Reject" });
  await userEvent.click(approve1);
  await userEvent.click(reject2);
  expect(submit.disabled).toBe(true);
  await userEvent.type(screen.getByLabelText("Why reject CHG-2?"), "Keep it simple");
  await userEvent.click(submit);
  expect(respond).toHaveBeenCalledWith([
    { change_id: "CHG-1", decision: "approved" },
    { change_id: "CHG-2", decision: "rejected", reason: "Keep it simple" },
  ]);
});

it("accepts all", async () => {
  const respond = vi.fn();
  render(<ReviewChangesCard args={{ changes }} status="executing" respond={respond} />);
  await userEvent.click(screen.getByRole("button", { name: "Accept all changes" }));
  expect(respond).toHaveBeenCalledWith([
    { change_id: "CHG-1", decision: "approved" },
    { change_id: "CHG-2", decision: "approved" },
  ]);
});

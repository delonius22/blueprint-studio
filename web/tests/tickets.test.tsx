// @vitest-environment jsdom
// T-15: the ticket view shows the breakdown with blocking edges (SPECS S11.2); review_tickets
// approves or asks for a revision in plain words (S9.4).
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { ReviewTicketsCard } from "../components/gates/ReviewTicketsCard";
import { TicketView } from "../components/TicketView";
import { buildWaves, type Ticket } from "../lib/state";

afterEach(cleanup);

const tickets: Ticket[] = [
  { id: "T-01", title: "Walking skeleton", what_to_build: "End to end", blocked_by: [], acceptance_criteria: ["Runs"], story_ids: ["US-1"], kind: "slice" },
  { id: "T-02", title: "Redirect", what_to_build: "Resolve codes", blocked_by: ["T-01"], acceptance_criteria: ["301"], story_ids: ["US-2"], kind: "slice" },
  { id: "T-03", title: "Owners", what_to_build: "List links", blocked_by: ["T-01"], acceptance_criteria: ["Lists"], story_ids: ["US-3"], kind: "slice" },
];

it("shows every ticket with its blocking edges, stories, criteria and waves", () => {
  render(<TicketView tickets={tickets} stage="ticket_gate" />);
  expect(screen.getByText(/3 tickets in 2 build waves: wave 1: T-01; wave 2: T-02, T-03\./)).toBeTruthy();
  expect(screen.getByRole("heading", { name: /T-02: Redirect/ })).toBeTruthy();
  expect(screen.getAllByText(/Blocked by: T-01 · Delivers: US-2/)).toHaveLength(1);
  expect(within(screen.getByRole("list", { name: "Acceptance criteria for T-02" })).getByText("301")).toBeTruthy();
});

it("computes build waves from the blocking edges", () => {
  expect(buildWaves(tickets).map((w) => w.map((t) => t.id))).toEqual([["T-01"], ["T-02", "T-03"]]);
});

it("approves, or requires instructions to revise", async () => {
  const respond = vi.fn();
  render(<ReviewTicketsCard args={{ tickets }} status="executing" respond={respond} />);
  await userEvent.click(screen.getByRole("button", { name: "Ask for a revision" }));
  const send = screen.getByRole("button", { name: "Send revision" }) as HTMLButtonElement;
  expect(send.disabled).toBe(true);
  await userEvent.type(screen.getByLabelText(/What should change/), "Merge T-02 and T-03");
  await userEvent.click(send);
  expect(respond).toHaveBeenLastCalledWith({ decision: "revise", instructions: "Merge T-02 and T-03" });
  cleanup();
  render(<ReviewTicketsCard args={{ tickets }} status="executing" respond={respond} />);
  await userEvent.click(screen.getByRole("button", { name: "Approve the tickets" }));
  expect(respond).toHaveBeenLastCalledWith({ decision: "approve" });
});

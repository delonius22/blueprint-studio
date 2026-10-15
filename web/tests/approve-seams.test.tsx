// @vitest-environment jsdom
// T-13: approve_seams approves (possibly edited) seams, or asks again with required feedback.
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import { ApproveSeamsCard } from "../components/gates/ApproveSeamsCard";

afterEach(cleanup);

const seams = [{ id: "SEAM-1", name: "HTTP API", description: "End to end", covers: ["US-1"] }];

it("approves the seams as edited", async () => {
  const respond = vi.fn();
  render(<ApproveSeamsCard args={{ seams }} status="executing" respond={respond} />);
  const name = screen.getByLabelText("Name");
  await userEvent.clear(name);
  await userEvent.type(name, "Public HTTP API");
  await userEvent.click(screen.getByRole("button", { name: "Add a seam" }));
  await userEvent.type(screen.getAllByLabelText("Name")[1], "Redirect path");
  await userEvent.click(screen.getByRole("button", { name: "Approve seams" }));
  expect(respond).toHaveBeenCalledWith({
    approved: true,
    seams: [
      { id: "SEAM-1", name: "Public HTTP API", description: "End to end", covers: ["US-1"] },
      { name: "Redirect path", description: "", covers: [] },
    ],
  });
});

it("needs feedback to ask for different seams", async () => {
  const respond = vi.fn();
  render(<ApproveSeamsCard args={{ seams }} status="executing" respond={respond} />);
  await userEvent.click(screen.getByRole("button", { name: "Ask for different seams" }));
  const send = screen.getByRole("button", { name: "Send feedback" }) as HTMLButtonElement;
  expect(send.disabled).toBe(true);
  await userEvent.type(screen.getByLabelText("What should change?"), "Test at the graph");
  await userEvent.click(send);
  expect(respond).toHaveBeenCalledWith({ approved: false, feedback: "Test at the graph" });
});

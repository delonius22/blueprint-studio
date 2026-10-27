// @vitest-environment jsdom
// T-10: the persistent same-model warning (SPECS S6.6, S11.6).
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { ReviewModelWarning } from "../components/workspace/ReviewModelWarning";

afterEach(cleanup);

it("warns while the review model is not distinct, and only then", () => {
  render(<ReviewModelWarning distinct={false} />);
  expect(screen.getByRole("note").textContent).toContain("cross-model design check is not active");
  cleanup();
  const { container } = render(<ReviewModelWarning distinct />);
  expect(container.innerHTML).toBe("");
});

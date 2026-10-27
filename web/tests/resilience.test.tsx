// @vitest-environment jsdom
// T-19: the error alert with Retry, the per-role token meter (SPECS S11.6), and clearing
// last_error only for a turn the user starts.
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorAlert } from "../components/workspace/ErrorAlert";
import { TokenMeter } from "../components/workspace/TokenMeter";
import { clearErrorForNewTurn } from "../lib/errors";

afterEach(cleanup);

describe("ErrorAlert", () => {
  it("shows the error with Retry and Dismiss", async () => {
    const onRetry = vi.fn();
    const onDismiss = vi.fn();
    render(
      <ErrorAlert
        error={{ code: "provider_error", message: "The interview model is not responding.", retryable: true }}
        onRetry={onRetry}
        onDismiss={onDismiss}
      />,
    );
    expect(screen.getByRole("alert").textContent).toContain("The interview model is not responding.");
    await userEvent.click(screen.getByRole("button", { name: "Retry" }));
    await userEvent.click(screen.getByRole("button", { name: "Dismiss this message" }));
    expect(onRetry).toHaveBeenCalledOnce();
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("offers no Retry for an error that retrying cannot fix", () => {
    render(
      <ErrorAlert error={{ code: "budget_exhausted", message: "Budget used.", retryable: false }} onRetry={() => {}} onDismiss={() => {}} />,
    );
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });
});

describe("TokenMeter", () => {
  it("shows use per role against the budget", () => {
    render(<TokenMeter used={{ interview: 120_000, review: 30_000 }} budget={2_000_000} />);
    expect(screen.getByText(/Interview 120K · Review 30K of 2M \(8%\)/)).toBeTruthy();
    expect(screen.queryByRole("status")).toBeNull();
    expect((screen.getByRole("meter") as HTMLMeterElement).value).toBe(150_000);
  });

  it("warns at 80 % of the combined total and says when the budget is used up", () => {
    render(<TokenMeter used={{ interview: 1_000_000, review: 600_000 }} budget={2_000_000} />);
    expect(screen.getByRole("status").textContent).toBe("Over 80% of the token budget used");
    cleanup();
    render(<TokenMeter used={{ interview: 1_500_000, review: 500_000 }} budget={2_000_000} />);
    expect(screen.getByRole("status").textContent).toBe("Token budget used up");
  });
});

describe("clearErrorForNewTurn", () => {
  const error = { code: "provider_error", message: "x", retryable: true };

  it("clears last_error when the user sends a new message", () => {
    const messages = [{ id: "u1", role: "user" }, { id: "u2", role: "user" }];
    expect(clearErrorForNewTurn({ last_error: error, stage: "interview" }, messages, "u1")).toEqual({
      last_error: null,
      stage: "interview",
    });
  });

  it("keeps last_error on a re-sync that adds nothing, so no model call is made", () => {
    expect(clearErrorForNewTurn({ last_error: error }, [{ id: "u1", role: "user" }], "u1")).toBeUndefined();
    expect(clearErrorForNewTurn({ last_error: null }, [{ id: "u2", role: "user" }], "u1")).toBeUndefined();
  });
});

// @vitest-environment jsdom
// The three themes (DESIGN.md): auto follows the device, a chosen theme is kept per browser,
// and the chat turns dark with Night and Contrast.
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ThemeSwitcher } from "../components/theme/ThemeSwitcher";
import { resolveTheme, THEME_SCRIPT } from "../lib/theme";

function prefersDark(dark: boolean) {
  vi.stubGlobal("matchMedia", (query: string) => ({ matches: dark, media: query, addEventListener: () => {} }));
}

beforeEach(() => {
  window.localStorage.clear();
  delete document.documentElement.dataset.theme;
  document.documentElement.classList.remove("dark");
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("themes", () => {
  it("resolves auto from the device and keeps a chosen theme", () => {
    expect(resolveTheme("auto", false)).toBe("day");
    expect(resolveTheme("auto", true)).toBe("night");
    expect(resolveTheme("contrast", false)).toBe("contrast");
  });

  it("applies the saved theme before the first paint", () => {
    prefersDark(false);
    window.localStorage.setItem("blueprint-theme", "night");
    new Function(THEME_SCRIPT)();
    expect(document.documentElement.dataset.theme).toBe("night");
    expect(document.documentElement.classList.contains("dark")).toBe(true);

    window.localStorage.setItem("blueprint-theme", "nonsense");
    new Function(THEME_SCRIPT)();
    expect(document.documentElement.dataset.theme).toBe("day");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });

  it("switches theme from the header and remembers the choice", async () => {
    prefersDark(true);
    render(<ThemeSwitcher />);
    const group = screen.getByRole("group", { name: "Theme" });
    expect(group.querySelector("[aria-pressed=true]")?.textContent).toBe("Auto");
    expect(document.documentElement.dataset.theme).toBe("night");

    await userEvent.click(screen.getByRole("button", { name: "Contrast" }));
    expect(screen.getByRole("button", { name: "Contrast" }).getAttribute("aria-pressed")).toBe("true");
    expect(document.documentElement.dataset.theme).toBe("contrast");
    expect(window.localStorage.getItem("blueprint-theme")).toBe("contrast");

    await userEvent.click(screen.getByRole("button", { name: "Day" }));
    expect(document.documentElement.dataset.theme).toBe("day");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});

// The three themes (DESIGN.md): 8-bit Day, 8-bit Night and High-Contrast Terminal. "auto"
// follows the device, light to Day and dark to Night. The choice is kept per browser until
// accounts exist; the page reads it before the first paint so no theme flashes.
export const THEME_CHOICES = ["auto", "day", "night", "contrast"] as const;
export type ThemeChoice = (typeof THEME_CHOICES)[number];
export type Theme = Exclude<ThemeChoice, "auto">;

export const THEME_LABELS: Record<ThemeChoice, string> = {
  auto: "Auto",
  day: "Day",
  night: "Night",
  contrast: "Contrast",
};

const STORAGE_KEY = "blueprint-theme";
const DARK_QUERY = "(prefers-color-scheme: dark)";

export function isThemeChoice(value: unknown): value is ThemeChoice {
  return THEME_CHOICES.includes(value as ThemeChoice);
}

export function resolveTheme(choice: ThemeChoice, prefersDark: boolean): Theme {
  if (choice !== "auto") return choice;
  return prefersDark ? "night" : "day";
}

export function savedChoice(): ThemeChoice {
  try {
    const saved = window.localStorage.getItem(STORAGE_KEY);
    return isThemeChoice(saved) ? saved : "auto";
  } catch {
    return "auto";
  }
}

/** Puts the theme on <html>; CopilotKit's chat turns dark only under a `dark` class. */
export function applyTheme(choice: ThemeChoice): void {
  const theme = resolveTheme(choice, window.matchMedia(DARK_QUERY).matches);
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.classList.toggle("dark", theme !== "day");
}

export function chooseTheme(choice: ThemeChoice): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, choice);
  } catch {
    // Storage may be blocked; the choice still applies to this page.
  }
  applyTheme(choice);
}

/** Runs in <head> before the first paint, and follows the device while the choice is auto. */
export const THEME_SCRIPT = `(() => {
  const key = ${JSON.stringify(STORAGE_KEY)};
  const choices = ${JSON.stringify(THEME_CHOICES)};
  const dark = window.matchMedia(${JSON.stringify(DARK_QUERY)});
  const apply = () => {
    let choice = "auto";
    try { choice = localStorage.getItem(key) || "auto"; } catch {}
    if (!choices.includes(choice)) choice = "auto";
    const theme = choice === "auto" ? (dark.matches ? "night" : "day") : choice;
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle("dark", theme !== "day");
  };
  apply();
  dark.addEventListener("change", apply);
})();`;

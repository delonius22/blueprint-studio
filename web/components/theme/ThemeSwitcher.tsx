"use client";

// The theme switcher in every header (DESIGN.md, Chips): Auto · Day · Night · Contrast, each a
// pixel icon and a label; the current choice is pressed.
import { useEffect, useState } from "react";
import { THEME_CHOICES, THEME_LABELS, type ThemeChoice, applyTheme, chooseTheme, savedChoice } from "../../lib/theme";
import styles from "./ThemeSwitcher.module.css";

const ICONS: Record<ThemeChoice, string> = {
  auto: "M2 2h12v12H2zM4 4v8h4V4z",
  day: "M7 0h2v3H7zM7 13h2v3H7zM0 7h3v2H0zM13 7h3v2h-3zM4 4h8v8H4z",
  night: "M6 1h5v2H8v2H7v6h1v2h3v2H6v-2H4v-2H3V5h1V3h2z",
  contrast: "M2 2h12v2H2zM2 12h12v2H2zM2 4h2v8H2zM12 4h2v8h-2zM4 4h4v8H4z",
};

export function ThemeSwitcher() {
  // The server renders "auto"; the saved choice is read once the page is in the browser.
  const [choice, setChoice] = useState<ThemeChoice>("auto");
  useEffect(() => {
    const saved = savedChoice();
    setChoice(saved);
    applyTheme(saved);
  }, []);

  return (
    <div role="group" aria-label="Theme" className={styles.switcher}>
      {THEME_CHOICES.map((option) => (
        <button
          key={option}
          type="button"
          className={styles.option}
          aria-pressed={choice === option}
          onClick={() => {
            setChoice(option);
            chooseTheme(option);
          }}
        >
          <svg className={styles.icon} width="12" height="12" viewBox="0 0 16 16" aria-hidden="true">
            <path fill="currentColor" fillRule="evenodd" d={ICONS[option]} />
          </svg>
          {THEME_LABELS[option]}
        </button>
      ))}
    </div>
  );
}

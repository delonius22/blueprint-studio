import type { Metadata } from "next";
import type { ReactNode } from "react";
import "@copilotkit/react-core/v2/styles.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blueprint Studio",
  description: "Design a system with an AI interviewer, then take away a signed-off PRD and tickets.",
};

// The app follows the system colour scheme with a media query; CopilotKit's chat switches to
// dark only under a `dark` class. This sets that class from the same setting before the first
// paint, and keeps it in step when the setting changes, so the chat is never a white panel in
// a dark page.
const THEME_SCRIPT = `(() => {
  const dark = window.matchMedia("(prefers-color-scheme: dark)");
  const apply = () => document.documentElement.classList.toggle("dark", dark.matches);
  apply();
  dark.addEventListener("change", apply);
})();`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // The class is set by the script above, so the server's markup cannot know it.
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>{children}</body>
    </html>
  );
}

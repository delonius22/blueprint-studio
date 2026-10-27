import type { Metadata } from "next";
import { JetBrains_Mono, Pixelify_Sans, Silkscreen, Space_Grotesk } from "next/font/google";
import type { ReactNode } from "react";
import "@copilotkit/react-core/v2/styles.css";
import { Sky } from "../components/theme/Sky";
import { THEME_SCRIPT } from "../lib/theme";
import "./globals.css";

export const metadata: Metadata = {
  title: "Blueprint Studio",
  description: "Design a system with an AI interviewer, then take away a signed-off PRD and tickets.",
};

// The faces of the three themes (DESIGN.md, Typography), self-hosted by next/font.
const pixel = Pixelify_Sans({ subsets: ["latin"], variable: "--font-pixel" });
const silk = Silkscreen({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-silk" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-jb" });
const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk" });

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    // data-theme and the `dark` class are set by THEME_SCRIPT, so the server cannot know them.
    <html
      lang="en"
      className={[pixel.variable, silk.variable, mono.variable, grotesk.variable].join(" ")}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <Sky />
        <div className="app">{children}</div>
      </body>
    </html>
  );
}

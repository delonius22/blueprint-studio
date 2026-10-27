---
name: Blueprint Studio
description: A system design partner dressed as a well-made 8-bit game, with three user-selectable themes.
colors:
  accent-go: "#00FF87"
  accent-go-hover: "#5CFFB0"
  accent-go-ink: "#007A41"
  accent-go-mark: "#00A85A"
  accent-go-shade: "#00804A"
  accent-go-glow: "#B3FFD9"
  status-warning: "#FFB020"
  status-critical: "#FF5470"
  day-sky-top: "#5BB8F5"
  day-sky-bottom: "#C9EAFF"
  day-panel: "#FFFFFF"
  day-well: "#F3FAFF"
  day-hover: "#E8F6FF"
  day-ink: "#0B0D10"
  day-ink-soft: "#1F2A38"
  day-muted: "#3B4A5E"
  day-faint: "#56677D"
  day-drop: "#1E5E99"
  night-sky-top: "#060918"
  night-sky-bottom: "#141F48"
  night-ground: "#070B1C"
  night-panel: "#111833"
  night-well: "#0B1124"
  night-hover: "#18224A"
  night-frame: "#C9D6F0"
  night-frame-soft: "#6F82A8"
  night-ink: "#EAF2FF"
  night-muted: "#A9B9D9"
  night-faint: "#8193B5"
  night-drop: "#03050D"
  night-rock: "#04050B"
  night-rock-rim: "#1B2448"
  night-star-warm: "#FFF4C9"
  night-constellation: "#8DA2D6"
  terminal-ground: "#0B0D10"
  terminal-ink: "#F4F6F8"
  terminal-muted: "#C7CED8"
  terminal-placeholder: "#AEB6C2"
  terminal-rule-soft: "#5A6270"
typography:
  display:
    fontFamily: "Pixelify Sans, sans-serif"
    fontSize: "44px"
    fontWeight: 700
    lineHeight: 1
  metric:
    fontFamily: "Pixelify Sans, sans-serif"
    fontSize: "48px"
    fontWeight: 700
    lineHeight: 1
  headline:
    fontFamily: "Pixelify Sans, sans-serif"
    fontSize: "30px"
    fontWeight: 700
    lineHeight: 1.1
  title:
    fontFamily: "Pixelify Sans, sans-serif"
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.2
  body:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Silkscreen, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    letterSpacing: "0.02em"
  terminal-display:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "36px"
    fontWeight: 700
    lineHeight: 1
  terminal-title:
    fontFamily: "Space Grotesk, sans-serif"
    fontSize: "16px"
    fontWeight: 700
  terminal-body:
    fontFamily: "JetBrains Mono, ui-monospace, monospace"
    fontSize: "12.5px"
    fontWeight: 400
    lineHeight: 1.55
rounded:
  none: "0px"
spacing:
  hair: "2px"
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "22px"
  xl: "34px"
components:
  button-primary:
    backgroundColor: "{colors.accent-go}"
    textColor: "{colors.day-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 16px"
    height: "38px"
  button-primary-hover:
    backgroundColor: "{colors.accent-go-hover}"
    textColor: "{colors.day-ink}"
  button-ghost-day:
    backgroundColor: "{colors.day-panel}"
    textColor: "{colors.day-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 14px"
    height: "38px"
  button-ghost-day-hover:
    backgroundColor: "{colors.day-hover}"
  button-ghost-night:
    backgroundColor: "{colors.night-well}"
    textColor: "{colors.night-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 14px"
    height: "38px"
  button-ghost-night-hover:
    backgroundColor: "{colors.night-hover}"
  button-terminal:
    backgroundColor: "{colors.accent-go}"
    textColor: "{colors.terminal-ground}"
    typography: "{typography.terminal-body}"
    rounded: "{rounded.none}"
    padding: "0 12px"
    height: "32px"
  panel-day:
    backgroundColor: "{colors.day-panel}"
    textColor: "{colors.day-ink}"
    rounded: "{rounded.none}"
    padding: "22px 24px"
  panel-night:
    backgroundColor: "{colors.night-panel}"
    textColor: "{colors.night-ink}"
    rounded: "{rounded.none}"
    padding: "22px 24px"
  input-day:
    backgroundColor: "{colors.day-well}"
    textColor: "{colors.day-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0 12px"
    height: "38px"
  input-night:
    backgroundColor: "{colors.night-well}"
    textColor: "{colors.night-ink}"
    typography: "{typography.body}"
    rounded: "{rounded.none}"
    padding: "0 12px"
    height: "38px"
  chip-theme:
    typography: "{typography.label}"
    rounded: "{rounded.none}"
    padding: "0 10px"
    height: "30px"
  chip-theme-active:
    backgroundColor: "{colors.accent-go}"
    textColor: "{colors.day-ink}"
  chip-status-warning:
    backgroundColor: "{colors.status-warning}"
    textColor: "{colors.day-ink}"
    typography: "{typography.label}"
    padding: "1px 6px"
  chip-status-critical:
    backgroundColor: "{colors.status-critical}"
    textColor: "{colors.day-ink}"
    typography: "{typography.label}"
    padding: "1px 6px"
---

<!-- Source of truth: the chosen boards (columns 5–7) on the Blueprint Studio Directions canvas, https://claude.ai/artifact/BVTFZUxoPCfwJaTbRWhVnU. The web app (web/app/globals.css) still carries neutral placeholder styles; re-run /impeccable document after the themes are implemented there so tokens are extracted from the shipped code. -->

# Design System: Blueprint Studio

## Overview

**Creative North Star: "The Blueprint Arcade"**

Blueprint Studio is a rigorous planning tool built like a well-made 8-bit game. Every panel is a chunky pixel frame, headings are set in pixel type, and one green "go" colour marks the action that moves the session forward. The game language serves the work: it makes a long, structured interview feel like progress through levels, while the data itself (item IDs, quotes, tokens, tickets) stays in a calm monospace that reads like a spec.

The system ships as three themes the user picks in Settings, each a full peer:

- **8-bit Day**, the light theme: white pixel panels with black notched frames on a banded sky, an offset blue drop and slow-drifting pixel clouds.
- **8-bit Night**, the dark theme: navy panels seen from inside a cave mouth, with the rock framing the screen and a sky behind it where stars twinkle, constellations shaped like system diagrams fade in and out, and the odd shooting star crosses.
- **High-Contrast Terminal**, the CLI theme: bright ink on near-black, hairline rules, lowercase command-style labels and a blinking cursor.

"System" follows the device: light gets Day, dark gets Night. A Day · Night · Contrast switcher sits in every screen's header.

Density is Operate-grade. The dashboard, workspace and forms are scannable first; the arcade lives in frames, type and the sky, never in the content.

**Key Characteristics:**
- Square corners everywhere; depth comes from stepped, hard-edged pixel shadows, never blur.
- One accent (`accent-go`) shared by all three themes, used as a fill for the primary action, the current selection and "healthy" marks.
- Three type voices: pixel display (Pixelify Sans), pixel labels (Silkscreen) and monospace data (JetBrains Mono).
- Pixel icons drawn on a 16-unit grid with crisp edges.
- Motion is stepped, like sprite frames, and stops entirely under reduced motion.

## Colors

The palette is one electric green on top of three grounds: a cool sky (Day), a deep cave navy (Night) and near-black (Terminal).

### Primary
- **Go Green** (`accent-go`): the one accent. In all three themes it fills the primary button, the selected tab or theme chip, the active stage, and the slider thumb. It is a fill only; text on it is always the theme's darkest ink.
- **Go Green, hover** (`accent-go-hover`): the primary button's hover fill.
- **Go Green Ink** (`accent-go-ink`): link hover and green text on Day's white panels, where the bright fill would fail contrast.
- **Go Green Mark** (`accent-go-mark`): small "healthy" icons and marks on white. It is for icons only: at 3.1:1 it passes the non-text bar but not the text bar.
- **Go Green Shade** (`accent-go-shade`): the pressed-depth lip under Night's primary button.
- **Go Green Glow** (`accent-go-glow`): link hover on the dark themes.

### Status
- **Amber Alert** (`status-warning`): warnings, gaps awaiting an answer and the "shared with you" chip.
- **Coral Fault** (`status-critical`): critical gaps, failed runs and a budget that has run out.

Both always appear as chips with black text, a pixel icon and a label.

### Neutral: 8-bit Day
- **Sky bands** (`day-sky-top` to `day-sky-bottom`): six flat horizontal bands of a hard-stepped gradient (`#5BB8F5`, `#6FC2FA`, `#84CCFC`, `#9AD6FE`, `#B2E0FF`, `#C9EAFF`), never a smooth blend.
- **Paper White** (`day-panel`): panel surface.
- **Ice Well** (`day-well`): input and inset surfaces.
- **Frost Hover** (`day-hover`): hover fill for ghost controls.
- **Pixel Black** (`day-ink`): body text, every frame and every outline.
- **Slate**, **Steel** and **Pewter** (`day-ink-soft`, `day-muted`, `day-faint`): secondary text, labels and placeholders, in falling emphasis.
- **Harbour Blue** (`day-drop`): the offset pixel drop under panels.

### Neutral: 8-bit Night
- **Night bands** (`night-sky-top` to `night-sky-bottom`): six stepped navy bands, `#060918` to `#141F48`.
- **Cave Ground** (`night-ground`): the page ground behind the sky.
- **Midnight Panel** (`night-panel`): panel surface.
- **Deep Well** (`night-well`): inputs and ghost buttons.
- **Moonlit Frame** and **Dusk Frame** (`night-frame`, `night-frame-soft`): outer panel frames and inner control frames.
- **Starlight**, **Haze** and **Mist** (`night-ink`, `night-muted`, `night-faint`): text, in falling emphasis.
- **Cave Rock** and **Rock Rim** (`night-rock`, `night-rock-rim`): the pixel stalactites, walls and floor that frame the viewport.
- **Warm Star** and **Constellation Line** (`night-star-warm`, `night-constellation`): highlight stars and dashed constellation strokes.

### Neutral: High-Contrast Terminal
- **Terminal Black** (`terminal-ground`): ground and all surfaces; there is no panel tint.
- **Phosphor White** (`terminal-ink`): text, hairline borders and the inverted selected state.
- **Ash** (`terminal-muted`): comments, secondary text and descriptions.
- **Cinder** (`terminal-rule-soft`): unselected option borders only, never text.

### Named Rules
**The One Go Rule.** Go Green appears once per decision: the primary action, the current selection, or a healthy mark. If two green fills compete on one panel, one of them is wrong.

**The Fill-Not-Ink Rule.** Bright Go Green is never text on a light surface. On Day, green text uses Go Green Ink; on the dark themes, text sitting on a green fill uses the darkest ink.

**The Stepped Gradient Rule.** Skies are banded in hard stops, like a palette-limited sprite. Smooth gradients don't exist in this system.

## Typography

**Display Font:** Pixelify Sans (with sans-serif)
**Label Font:** Silkscreen (with sans-serif)
**Body/Data Font:** JetBrains Mono (with ui-monospace, monospace)
**Terminal headings:** Space Grotesk (with sans-serif)

**Character:** The pixel faces give every heading and number the arcade's voice; the monospace keeps IDs, quotes and requirements legible and spec-like. Terminal swaps the pixel faces for a sharp grotesk and lets the monospace carry the voice.

### Hierarchy
- **Display** (700, 44px, line-height 1): page titles such as "Start a design session".
- **Metric** (700, 48px, line-height 1): headline numbers in the dashboard's stat tiles.
- **Headline** (700, 30px): section and stage headings.
- **Title** (700, 20px): panel titles ("Your sessions", "How a session runs").
- **Body** (400, 13px, line-height 1.6): all data, prose and form values, with a 60–72ch measure on paragraphs.
- **Label** (400, 11px, 0.02em tracking): Silkscreen for buttons, chips, field labels, timestamps and navigation.
- **Terminal display / title / body** (Space Grotesk 700 at 36px and 16px; JetBrains Mono 12.5px, line-height 1.55): Terminal's set. Labels stay lowercase and command-like (`blueprint new`, `~/overview`, `--theme`).

### Named Rules
**The Data Stays Mono Rule.** Anything the user wrote, approved or will export (item IDs, quotes, requirements, ticket text) is set in JetBrains Mono. Pixel faces never carry content.

**The Label Ceiling Rule.** Silkscreen is for labels of a few words. Never set a sentence in it.

## Layout

The screens are a left rail (Day and Night: 44px square icon buttons; Terminal: 40px) beside a main column. The main column has a header row (back link or title, the theme switcher, the primary action) and then panels on a flexible wrap grid. Panels use `flex: 3 1 520px` and `2 1 360px` pairs, so the layout falls to one column without breakpoints.

The 8-bit themes are airy: gaps between panels are 34px (`xl`), inside panels 22–26px, and between fields 18–22px (`lg`). Night adds root padding of 92–104px vertically and 64–72px horizontally to clear the cave rock. Terminal is denser, at 10–16px padding with 14–18px gaps.

Pixel frames sit outside the box (box-shadow), so every framed element keeps a 2–3px margin to stop frames colliding.

## Elevation & Depth

Depth is hard-edged and stepped, like a sprite drop. Nothing blurs.

### Shadow Vocabulary
- **Pixel frame, outer** (`box-shadow: 0 -3px 0 0 F, 0 3px 0 0 F, -3px 0 0 0 F, 3px 0 0 0 F`): a 3px notched frame with clipped corners, the signature silhouette. F is `day-ink` or `night-frame`.
- **Pixel drop** (`6px 6px 0 0 D, 3px 9px 0 0 D, 9px 3px 0 0 D`, appended to the outer frame): a stepped offset drop under panels. D is `day-drop` or `night-drop`.
- **Pixel frame, inner** (the same four offsets at 2px): inputs, ghost buttons, theme chips and inset wells.
- **Press lip** (`0 7px 0 0 L, -3px 4px 0 0 L, 3px 4px 0 0 L`): the 4px lip under the primary button. On `:active` the button moves down 4px and the lip disappears. L is `day-ink` on Day and `accent-go-shade` on Night.

Terminal has no shadows. Depth there is a 1px border, and selection is inversion.

### Named Rules
**The No-Blur Rule.** Every shadow has zero blur and zero spread. A soft shadow breaks the world.

**The Notched Corner Rule.** Frames are drawn with four single-axis offsets so the corners stay notched. Never use a plain `border` on an 8-bit surface.

## Shapes

Every corner is square (`rounded.none`). The 8-bit themes get their silhouette from the notched corners of the pixel frame. Icons are SVG paths on a 16-unit grid with `shape-rendering: crispEdges`, built only from horizontal and vertical runs. Focus is a 3px dashed outline offset 4px (Day: `day-ink`; Night: `accent-go`). On Terminal it is a 2px solid `terminal-ink` outline offset 2px.

## Components

### Buttons
Chunky and pressable, like a cabinet button.
- **Primary:** a Go Green fill with a dark label in Silkscreen, a 38–40px height, the outer frame plus the press lip, and a 120ms two-step press transition.
- **Hover / Active:** hover lightens to `accent-go-hover`. Active drops the button 4px and removes the lip.
- **Ghost:** the panel or well fill with the inner frame, and a `*-hover` fill on hover.
- **Terminal:** a flat Go Green block, 32px high, in bold mono, with no frame. Secondary actions are 1px-bordered text buttons.

### Chips
- **Theme switcher:** three chips, Day · Night · Contrast, each with a pixel icon (sun, moon, contrast square). They are 30px high with the inner frame. The current theme is filled with Go Green and marked `aria-current`. On Terminal the chips are 1px-bordered lowercase links, and the current one is inverted.
- **Status:** Amber Alert or Coral Fault fills with a 2px `day-ink` ring, black Silkscreen text and an 8px pixel icon.
- **Visibility:** Go Green for "Shared · n", Starlight or white for "Private", Amber for "Shared with you".

### Cards / Containers
- **Corner Style:** square, with the notched outer frame.
- **Background:** `day-panel` or `night-panel`.
- **Shadow Strategy:** the outer frame plus the pixel drop (see Elevation & Depth).
- **Internal Padding:** 22–28px.
- **Terminal:** a 1px `terminal-ink` border on the ground colour, with no fill.

### Inputs / Fields
- **Style:** a `*-well` fill with the inner frame, a 38px height and 12px padding. A Silkscreen label sits above in `*-muted`, with helper text below at 12px.
- **Caret / Placeholder:** the caret is Go Green on Night and Terminal and Pixel Black on Day; placeholders use the theme's faint tone.
- **Focus:** the theme's dashed focus outline.
- **Drop zone:** a 3px dashed outline inset on the well, holding an "Attach files" ghost button and the accepted types in mono.

### Navigation
- **Left rail:** square icon buttons with pixel icons. The active button takes the Go Green fill (Day, Night) or the inverted fill (Terminal) and is marked `aria-current`.
- **Segmented tabs** (Mine / Shared / All pending): a row of ghost chips; the pressed one is filled and marked `aria-pressed`.

### The Night Sky (signature)
These are decoration-only layers (`aria-hidden`, `pointer-events: none`) behind the content:
- two tiled star patterns twinkling in two steps at 3.4s and 5.1s;
- constellations drawn as small system diagrams (a load balancer, a ticket), each fading in and out on its own 27–31s cycle with a staggered delay;
- shooting stars that streak once every 13–17s;
- the cave: tiled stalactites, walls and floor in Cave Rock with a Rock Rim edge.

Under reduced motion every animation stops, and one constellation stays visible as a still.

### Day Clouds (signature)
These are pixel clouds made of white blocks with a `day-drop` underside. They drift 12px in four steps over 6s and are still under reduced motion.

## Do's and Don'ts

### Do:
- **Do** frame every 8-bit surface with the four-offset pixel frame and keep a 2–3px margin outside it.
- **Do** keep Go Green a fill. Use `accent-go-ink` for green text on Day.
- **Do** set every ID, quote and requirement in JetBrains Mono, and keep labels in Silkscreen to a few words.
- **Do** step every animation (`steps()` timing) and stop all of it under `prefers-reduced-motion`.
- **Do** keep the Night sky quiet and behind content: no star, constellation or comet may cross text or controls.
- **Do** give every status chip an icon and a label as well as its colour.
- **Do** put the Day · Night · Contrast switcher in the header of every screen, linking to the same screen in each theme.
- **Do** meet WCAG 2.1 AA in all three themes; check Day's faint text (`day-faint` on white) and Night's faint text (`night-faint` on `night-panel`) whenever a surface changes.

### Don't:
- **Don't** round a corner, blur a shadow or use a smooth gradient.
- **Don't** add a second accent hue. Status colours are reserved for status and never decorate.
- **Don't** set a sentence or user content in a pixel face.
- **Don't** treat Terminal as a fallback: it is an equal theme and gets the same polish and the same screens.
- **Don't** bring back the rejected directions (Dark IDE, Dither Mono, Tactical HUD, Minimalist Ledger) or the brief's banned faces (Inter, Arial).
- **Don't** use purple-to-blue gradients, glossy blobs or rounded SaaS card shadows.

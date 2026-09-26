# BlueprintBob UI Revamp — Implementation Plan

## Status: PENDING IMPLEMENTATION

---

## Color Palette

| Token         | Hex       | Role                                      |
|---------------|-----------|-------------------------------------------|
| `--navy`      | `#1B2631` | Primary background, deepest surface       |
| `--slate`     | `#4A4E69` | Panels, drawers, modal surfaces           |
| `--blush`     | `#F9AFAF` | Primary accent — active states, labels, borders on focus |
| `--off-white` | `#F6F6F6` | Body text, primary readable content       |
| `--sand`      | `#F8C291` | Secondary accent — warnings, file paths, secondary actions |

---

## What Is Being Changed (Frontend Only)

The entire UI lives in one method: `_getHtmlForWebview()` inside
`extensions/blueprintbob/src/diagramPanel.ts` (lines 179–1853).

The backend (`backend/routers/blueprintbob/`) and all TypeScript logic outside
`_getHtmlForWebview` are **untouched**. Only CSS variables, element classes,
and inline HTML inside the returned template string change.

---

## Problems in the Current UI

| Problem | Where it appears |
|---------|-----------------|
| Purple gradient on `.brand-badge` (`linear-gradient(135deg, #1f6feb, #8957e5)`) | Header bar |
| Purple gradient on `.toggle-btn.active` and `.btn-primary` | Toolbar toggles, modal save button |
| Pill-shaped toolbar with `border-radius: 30px` | `.control-pill` / `.floating-toolbar` |
| Pill-shaped toggle buttons with `border-radius: 18-20px` | `.toggle-btn`, `.pill-btn` |
| Emojis throughout: ⚡ ✨ 🏢 🔍 🔑 ✕ 📋 ℹ ❌ ✓ 🔒 📂 👁️ 🙈 ⚠️ | Toolbar buttons, modal text, banners |
| GitHub dark blue `#238636` on `.btn-action` | Node drawer "Open in Editor" button |
| GitHub blue `#58a6ff` on `.md-h3`, `.type-badge` | Insights panel typography |
| GitHub purple `#bc8cff` on `.md-h4` | Insights panel typography |
| Black-on-dark background (`#0d1117`) instead of navy | Root `body` background |
| `box-shadow: 0 0 12px rgba(88,166,255,...)` glow on hover | Multiple buttons |
| `filter: drop-shadow(0 0 8px rgba(88, 166, 255, 0.6))` on node hover | Mermaid SVG nodes |

---

## Design Rules for the Revamp

1. **No gradients** — except a single `backdrop-filter: blur()` glassmorphic surface (permitted on panels/drawers/toolbar).
2. **No pills** — toolbar and toggle containers use `border-radius: 4px`. Buttons use `border-radius: 3px`.
3. **No emojis** — replace with minimal SVG inline icons or plain text symbols (`+`, `−`, `×`).
4. **Palette only** — all colour values must come from the 5-token palette above. No GitHub blues, no purples outside `--slate`.
5. **Flat active state** — active/selected buttons use `background: #F9AFAF; color: #1B2631` (blush fill, dark text). No glow.
6. **Glassmorphic panels only** — `background: rgba(27,38,49,0.82); backdrop-filter: blur(14px)` for header, toolbar, drawers, modals.

---

## Sub-Tasks

---

### Sub-Task 1 — CSS Variables & Root Reset

**Status:** [ ] pending

**Intent:**
Replace the current GitHub dark palette CSS variables with the ByteSized palette.
This is the foundation; every other sub-task builds on top of it.

**Expected Outcomes:**
- `:root` block uses only the 5 new tokens.
- `body` background is `#1B2631` (navy).
- No `#0d1117`, no `#58a6ff`, no `#bc8cff`, no `#8957e5` remain anywhere in the CSS.

**Changes:**
```css
/* BEFORE */
--bg-color: #0d1117;
--panel-bg: rgba(22, 27, 34, 0.85);
--pill-bg: rgba(30, 36, 46, 0.85);
--border-color: rgba(255, 255, 255, 0.12);
--accent-blue: #58a6ff;
--accent-purple: #bc8cff;
--accent-green: #3fb950;
--text-main: #e6edf3;
--text-muted: #8b949e;

/* AFTER */
--navy: #1B2631;
--slate: #4A4E69;
--blush: #F9AFAF;
--off-white: #F6F6F6;
--sand: #F8C291;
--bg-color: var(--navy);
--panel-bg: rgba(27, 38, 49, 0.82);
--border-color: rgba(246, 246, 246, 0.12);
--text-main: var(--off-white);
--text-muted: rgba(246, 246, 246, 0.5);
```

**Files:** `extensions/blueprintbob/src/diagramPanel.ts` — CSS inside `_getHtmlForWebview`, lines ~206-217.

---

### Sub-Task 2 — Header Bar

**Status:** [ ] pending

**Intent:**
Remove the gradient brand badge. Replace with a flat, bordered label using the new palette.
Remove emoji from the warning badge. Replace with a plain text `[!]` prefix.

**Expected Outcomes:**
- `.brand-badge`: flat `background: var(--slate)`, `color: var(--blush)`, no gradient, `border-radius: 3px`.
- `.badge`: uses `--slate` border and muted off-white text.
- `.badge.badge-warning`: uses `--sand` border and text, no emoji in HTML template.
- `isAiFallback` badge text: `[!] Offline AST Fallback (AI Failed)` — no ⚠️.

**Files:** CSS lines ~254-291 + HTML line ~1081.

---

### Sub-Task 3 — Floating Toolbar (biggest visual change)

**Status:** [ ] pending

**Intent:**
The pill-shaped floating toolbar is the most prominent AI-generated UI element.
Replace with a compact rectangular floating bar. Convert all pill/toggle buttons to
flat rectangular buttons. Remove all emojis from button labels.

**Expected Outcomes:**
- `.floating-toolbar` / `.control-pill`: `border-radius: 4px` (was 30px), same glassmorphic background.
- `.mode-toggle-pill`, `.granularity-toggle-pill`: `border-radius: 4px` (was 20px), no `box-shadow: inset`.
- `.toggle-btn`: `border-radius: 3px`, no `border-radius: 18px`.
- `.toggle-btn.active`: `background: var(--blush)`, `color: var(--navy)` — no gradient, no glow.
- `.pill-btn`: `border-radius: 3px`, `padding: 5px 10px`.
- Button label text replacements (no emojis):

| Before | After |
|--------|-------|
| `⚡ Offline` | `Offline` |
| `✨ AI Mode` | `AI Mode` |
| `🏢 Overview` | `Overview` |
| `🔍 Deep Map` | `Deep Map` |
| `🔑 Key` | `Key` |
| `＋ Zoom` | `+` |
| `－ Zoom` | `−` |
| `⛶ Fit` | `Fit` |
| `↺ Reset` | `Reset` |
| `ℹ Insights` | `Insights` |
| `📋 Copy Code` | `Copy` |

- `.key-indicator-dot`: change glow color from green `#3fb950` to `var(--blush)`.

**Files:** CSS lines ~326-748 + HTML lines ~1105-1126.

---

### Sub-Task 4 — AI Error Banner

**Status:** [ ] pending

**Intent:**
Remove emoji icons from the error banner. Replace red GitHub tones with sand/blush.

**Expected Outcomes:**
- `.ai-error-banner`: `background: rgba(27, 38, 49, 0.96)`, `border-bottom: 1px solid var(--sand)`.
- `.ai-error-content`: color `var(--sand)` (was `#ff7b72`).
- `.btn-banner-key`: `border: 1px solid var(--sand)`, `background: rgba(248, 194, 145, 0.15)`.
- HTML: `ai-error-icon` span replaced with plain `[!]` text, no ❌.
- HTML: `btn-banner-check-key` label: `Check API Key` (no 🔑).
- HTML: `btn-banner-dismiss` label: `×` (plain multiplication sign, no ✕).

**Files:** CSS lines ~751-817 + HTML lines ~1084-1096.

---

### Sub-Task 5 — API Key Modal

**Status:** [ ] pending

**Intent:**
Remove gradient from the primary save button. Remove emoji from modal text.
Apply new palette to inputs and action buttons.

**Expected Outcomes:**
- `.btn-primary`: `background: var(--blush)`, `color: var(--navy)`, no gradient, no glow on hover.
- `.btn-secondary` (Clear Key): `color: var(--sand)`, `border-color: rgba(248,194,145,0.4)`.
- `.form-input:focus`: `border-color: var(--blush)`, focus ring `rgba(249,175,175,0.2)`.
- `.provider-radio input`: `accent-color: var(--blush)`.
- HTML modal title/subtitle: no emoji.
- `modal-mode-banner` active color: `var(--blush)` for AI mode, `var(--sand)` for offline (was blue/purple).
- Modal error box: `var(--sand)` tones (was red `#f85149`).
- Security note: remove 🔒 emoji, plain text.
- `btn-close-key-modal` label: `×` (no ✕).
- `btn-save-key` label: `Save & Generate with AI` (unchanged, but button style updated).
- Key status text: replace ✓ check with `[ok]` and remove inline color override using blue.

**Files:** CSS lines ~844-1072 + HTML lines ~1128-1194.

---

### Sub-Task 6 — Insights (Explanation) Modal

**Status:** [ ] pending

**Intent:**
Remove emoji from the modal title. Update markdown typography tokens to use the new palette.

**Expected Outcomes:**
- `.md-h3` color: `var(--blush)` (was `var(--accent-blue)` = `#58a6ff`).
- `.md-h4` color: `var(--sand)` (was `var(--accent-purple)` = `#bc8cff`).
- `.md-item::before` bullet color: `var(--blush)`.
- `.md-subitem::before` bullet color: `var(--sand)`.
- `.md-code` text color: `var(--sand)` (was `#79c0ff`).
- `.md-arrow` color: `var(--sand)`.
- HTML explanation modal title: `System Architecture Insights` (no ℹ).
- `.explanation-close` / `btn-close-explanation` label: `×`.

**Files:** CSS lines ~577-657 + HTML lines ~1197-1203.

---

### Sub-Task 7 — Slide-over Info Drawer (Node Details)

**Status:** [ ] pending

**Intent:**
Remove emoji from the "Open in Editor" button. Update the type badge and action button colors.

**Expected Outcomes:**
- `.type-badge`: `background: rgba(249,175,175,0.12)`, `color: var(--blush)`, `border: 1px solid rgba(249,175,175,0.3)` (was blue).
- `.btn-action` (Open in Editor): `background: var(--blush)`, `color: var(--navy)`, `border-radius: 3px` (was GitHub green `#238636`).
- `.btn-action:hover`: `background: var(--sand)` (slightly warmer hover).
- HTML `btn-open-file` label: `Open in Editor` (no 📂).
- Drawer close button label: `×`.

**Files:** CSS lines ~453-484 + HTML lines ~1205-1233.

---

### Sub-Task 8 — Fallback Card View

**Status:** [ ] pending

**Intent:**
Update the fallback component card grid (shown when Mermaid CDN fails) to use the new palette.

**Expected Outcomes:**
- Card hover accent color changes from `var(--accent-blue)` to `var(--blush)`.
- Node label color in `renderFallback()` JS: replace `var(--accent-blue)` string with `var(--blush)`.

**Files:** JS lines ~1829-1848 inside `_getHtmlForWebview`.

---

### Sub-Task 9 — Mermaid Theme Overrides

**Status:** [ ] pending

**Intent:**
The mermaid `.node:hover` currently has a blue glow. Replace with a blush-tinted shadow.
Update mermaid initialization theme config to align with the dark navy background.

**Expected Outcomes:**
- `.node:hover`: `filter: drop-shadow(0 0 6px rgba(249,175,175,0.5))` (was blue glow).
- `mermaid.initialize` theme remains `'dark'` (correct for navy background).

**Files:** CSS lines ~664-671 + JS `renderDiagram()` function lines ~1779-1788.

---

### Sub-Task 10 — Compile & Verify

**Status:** [ ] pending

**Intent:**
Confirm zero TypeScript errors after all CSS/HTML string changes, and run a visual spot-check.

**Todo List:**
1. Run `npm run compile` inside `extensions/blueprintbob/` — confirm zero errors.
2. Launch extension with F5, run `BlueprintBob: Visualize Workspace Architecture` on any folder.
3. Verify: no emojis visible, no pill shapes, no blue/purple accents, all interactive states use blush/sand/navy.

---

## Implementation Order

Sub-tasks must be done sequentially inside `_getHtmlForWebview` to avoid conflicts.
Recommended order: **1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10**.

Sub-task 1 (CSS variables) unblocks everything downstream since most colours reference `var()` tokens.

---

## What Is NOT Changing

- All TypeScript logic: `extension.ts`, `workspaceScanner.ts`, the `DiagramPanel` class methods.
- The backend: `backend/routers/blueprintbob/` — completely untouched.
- Pan/zoom JS, message handlers, Mermaid rendering, markdown formatter — all JS logic is preserved.
- The floating toolbar position (bottom-centre) and drawer position (right slide-over) — layout unchanged.
- Glassmorphic `backdrop-filter: blur()` on panels/drawers — this is explicitly permitted and kept.

# ByteSized Suite — Project Completion Plan

## Status: IN PROGRESS

---

## Top-Level Overview

**Goal:** Complete the ByteSized Suite from its current hackathon-demo state to a
fully working, demo-ready product. Every feature described in the README must actually
work. Every stub must be wired. Every visual inconsistency must be resolved.

**What is already done (do not touch):**
- Multi-extension monorepo structure (`extensions/`, `backend/routers/`)
- Backend FastAPI router layout with `rtl` and `blueprintbob` routers mounted
- Universal 8-language lint engine (`engine.py`)
- BlueprintBob backend (generator, compiler, AST engine, analyzer)
- BlueprintBob extension UI (diagramPanel, workspaceScanner, dual-engine, granularity toggle)
- Shared npm package (`@bytesized/shared` — `postJson`, `createStatusBar`)
- Load testing suite (`tests/load_testing.py`)
- Deploy config (`deploy/docker-compose.yml`, `deploy/Dockerfile`, `deploy/k8s/`)
- README Extension 1 and Extension 2 descriptions

**What is NOT done (this plan):**
Six focused sub-tasks covering the four real functional gaps plus two polish tasks.

---

## Sub-Task 1 — Wire the WebSocket Collaboration (connectWorkspace)

**Status:** [ ] pending

**Intent:**
`connectWorkspace.ts` currently just prints a notification message — it never opens
a real WebSocket connection. The backend `ConnectionManager` at
`backend/routers/rtl/engine.py:464` is complete. This task wires the extension
side so engineers can actually join a room, see live code updates, and see the active
user count update in the status bar.

**Expected Outcomes:**
- Calling `siliconbob.connectWorkspace` creates a real `WebSocket` connection to
  `ws://<backendUrl>/ws/<roomId>`.
- On `INIT_STATE` message: status bar shows `$(broadcast) SiliconBob: Room #<id> (N users)`.
- On `CODE_UPDATE` message from another user: opens the updated code in a read-only
  preview beside the current editor so the collaborating engineer can see what changed.
- Disconnecting (closing the editor or calling the command again) closes the socket
  cleanly.
- If the WebSocket fails to connect, a clear error message is shown.

**Todo List:**
1. In `connectWorkspace.ts`, after the `roomId` input box, open a `new WebSocket(wsUrl)`.
2. On `socket.onopen`: update status bar to `$(broadcast) SiliconBob: Room #<id>`.
3. On `socket.onmessage`: parse JSON; handle `INIT_STATE` (show user count) and
   `CODE_UPDATE` (open virtual document with new content in `ViewColumn.Beside`).
4. On `socket.onerror` / `socket.onclose`: reset status bar to `$(chip) SiliconBob: Ready`
   and show an error message.
5. Store the active socket in a module-level variable so a second command invocation
   closes the old socket before opening a new one.
6. Add a `siliconbob.leaveWorkspace` command that closes the socket and resets the
   status bar — register it in `extension.ts` and add it to `package.json` contributes.

**Relevant Context:**
- Current stub: `extensions/siliconbob-rtl/src/commands/connectWorkspace.ts` lines 18–23
- Backend WS handler: `backend/routers/rtl/engine.py:464` — `ConnectionManager`
- WS message types: `INIT_STATE` (has `document`, `active_users`), `CODE_UPDATE` (has `code`)
- Node.js `WebSocket` is available via `ws` npm package or via the VS Code runtime's
  built-in `WebSocket` (available since VS Code 1.85 which is the declared engine minimum)

---

## Sub-Task 2 — Per-Issue Lightbulb Code Actions (Apply Fix / Preview Fix)

**Status:** [ ] pending

**Intent:**
Squiggles appear on detected issues but clicking them does nothing. This task adds
a `CodeActionProvider` so every squiggle shows a 💡 lightbulb with two options:
**Apply Fix** (one-click `WorkspaceEdit`) and **Preview Fix** (`vscode.diff` of
just that single line change). The backend must first expose `fixed_line` on each
issue so the extension knows what to replace.

**Expected Outcomes:**
- `RTLIssue` Pydantic model has `fixed_line: Optional[str] = None`.
- Every rule in `engine.py` that has a deterministic fix populates `fixed_line`
  with the exact replacement text for that line.
- Hovering a SiliconBob squiggle shows a lightbulb.
- Lightbulb menu has two items: `SiliconBob: Apply Fix — <rule_id>` and
  `SiliconBob: Preview Fix — <rule_id>`.
- Apply Fix replaces only the flagged line using `WorkspaceEdit` without touching
  the rest of the file.
- Preview Fix opens `vscode.diff` between the original file and a temp doc with
  only that one fix applied.
- Rules without a safe deterministic fix (`fixed_line = None`) show no lightbulb.

**Todo List:**
1. Add `fixed_line: Optional[str] = None` to `RTLIssue` in
   `backend/shared/models.py`.
2. In `backend/routers/rtl/engine.py`, for each rule that already writes to
   `optimized_lines[idx]`, store that same value on the issue object as `fixed_line`.
   - RTL-001: `fixed_line = re.sub(...)` (replace `=` with `<=`)
   - RTL-002: `fixed_line = default_fix + line` (default branch insertion)
   - RTL-003: `fixed_line = re.sub(r"#\s*\d+\s*;?", "", line)` (strip delay)
   - RTL-004 pipeline: `fixed_line = pipelined_code` (pipelined replacement)
   - PY-001 through GO-002: same pattern — store the already-computed `optimized[idx]`
     on the issue's `fixed_line` field.
3. In `extensions/siliconbob-rtl/src/commands/optimizeRTL.ts`:
   - Define `interface SiliconBobDiagData { rule_id: string; fixed_line: string | null; line: number }`.
   - Create a `WeakMap<vscode.Diagnostic, SiliconBobDiagData>` at module level (`diagDataMap`).
   - After building each `vscode.Diagnostic`, call `diagDataMap.set(diag, { ... })`.
4. Create `extensions/siliconbob-rtl/src/codeActions.ts`:
   - Implement `SiliconBobCodeActionProvider implements vscode.CodeActionProvider`.
   - `provideCodeActions`: for each `SiliconBob` diagnostic with non-null `fixed_line`,
     return two `CodeAction` objects — `QuickFix` (with `WorkspaceEdit`) and `Empty`
     (with `command: siliconbob.previewFix`).
5. Register `siliconbob.previewFix` command in `extension.ts`:
   - Args: `(originalUri, lineIdx, fixedLine)`.
   - Build patched document by splicing `fixedLine` at `lineIdx`, open with `vscode.diff`.
6. Register the `SiliconBobCodeActionProvider` via
   `vscode.languages.registerCodeActionsProvider` in `extension.ts` for
   `verilog`, `systemverilog`, `python`, `cpp`, `c`, `javascript`, `typescript`,
   `java`, `go`, `rust`.
7. Add `siliconbob.previewFix` to `package.json` commands contribution (no menu entry).
8. Run `npm run compile` — confirm zero errors.

**Relevant Context:**
- `backend/shared/models.py:5` — `RTLIssue` model
- `backend/routers/rtl/engine.py:47–119` — all fix computations already exist;
  just store them on the issue object
- `@types/vscode@1.138.0` is installed — `Diagnostic.data` does NOT exist in this
  version; use a `WeakMap` pattern instead (confirmed from previous session)
- `extensions/siliconbob-rtl/src/commands/optimizeRTL.ts:81` — where diagnostics
  are built

---

## Sub-Task 3 — On-Save Linting Trigger

**Status:** [ ] pending

**Intent:**
Currently linting only fires when the user manually invokes the command. Real linters
(ESLint, Pylance) run automatically on save. This task adds a
`vscode.workspace.onDidSaveTextDocument` listener that automatically re-runs the
analysis whenever a supported file is saved, keeping squiggles always current.

**Expected Outcomes:**
- Saving any file with a supported language ID (`python`, `javascript`, `typescript`,
  `cpp`, `c`, `java`, `go`, `rust`, `verilog`, `systemverilog`) automatically
  triggers the optimize-code call in the background.
- The status bar shows the spinning indicator during the background analysis.
- No notification/progress dialog appears for auto-triggered runs (silent mode) —
  only the squiggles update.
- The diff view is NOT auto-opened on save — only on explicit command invocation.
- A VS Code setting `siliconbob.lintOnSave` (boolean, default `true`) lets users
  disable the auto-trigger.

**Todo List:**
1. In `optimizeRTL.ts`, extract the fetch+diagnostics logic into a reusable
   `runAnalysis(document, backendUrl, diagnosticCollection, statusBarItem, opts: { silent: boolean })`.
   - When `silent: true`: skip `withProgress` and the `showInformationMessage` / diff open.
   - When `silent: false`: existing full UX (progress, message, diff view, apply prompt).
2. In `extension.ts`, register a `vscode.workspace.onDidSaveTextDocument` listener.
3. In the listener, check `siliconbob.lintOnSave` config. If false, return early.
4. Check that `document.languageId` is in the supported set. If not, return early.
5. Call `runAnalysis(document, backendUrl, diagnosticCollection, statusBarItem, { silent: true })`.
6. Add `siliconbob.lintOnSave` boolean config to `package.json` `contributes.configuration`.

**Relevant Context:**
- `extensions/siliconbob-rtl/src/commands/optimizeRTL.ts:46` — `handleOptimize` function
  to refactor into `runAnalysis`.
- Supported language IDs are already listed in `package.json` `activationEvents`.
- Do not trigger on save for generic/unknown languages — only the explicitly
  supported set.

---

## Sub-Task 4 — BlueprintBob UI Revamp (ByteSized Palette)

**Status:** [ ] pending

**Intent:**
The BlueprintBob Webview UI was built with a GitHub dark blue / purple palette and
contains emojis and pill-shaped buttons throughout. This task applies the ByteSized
brand palette and design rules. All changes are CSS/HTML string edits inside
`_getHtmlForWebview()` in `diagramPanel.ts`. No logic changes.

Full specification is already written in `blueprintbob-ui-revamp-plan.md`.

**Expected Outcomes:**
- CSS variables use only the 5 ByteSized tokens: `--navy #1B2631`, `--slate #4A4E69`,
  `--blush #F9AFAF`, `--off-white #F6F6F6`, `--sand #F8C291`.
- No gradients, no pill shapes (`border-radius` max `4px` on containers, `3px` on buttons).
- No emojis anywhere — replaced with plain text or `×` / `+` / `−` symbols.
- Active/selected states use `background: var(--blush); color: var(--navy)`.
- Node hover glow uses `rgba(249,175,175,0.5)` (blush) not blue.
- `npm run compile` inside `extensions/blueprintbob/` produces zero errors.

**Todo List:**
Implement each of the 10 sub-tasks from `blueprintbob-ui-revamp-plan.md` in order:
1. CSS Variables & Root Reset (Sub-Task 1 of revamp plan)
2. Header Bar (Sub-Task 2)
3. Floating Toolbar — pill → rectangle, remove emojis (Sub-Task 3)
4. AI Error Banner (Sub-Task 4)
5. API Key Modal (Sub-Task 5)
6. Insights Modal (Sub-Task 6)
7. Slide-over Node Drawer (Sub-Task 7)
8. Fallback Card View (Sub-Task 8)
9. Mermaid Theme Overrides (Sub-Task 9)
10. Compile & Visual Verify (Sub-Task 10)

**Relevant Context:**
- All changes are inside `_getHtmlForWebview()`:
  `extensions/blueprintbob/src/diagramPanel.ts` lines 179–2104.
- Full colour-by-colour and element-by-element spec: `blueprintbob-ui-revamp-plan.md`.
- TypeScript compiles the HTML/CSS as template strings — syntax errors inside
  the template string won't be caught until runtime, so compile + F5 test is
  essential after each sub-task.

---

## Sub-Task 5 — Expose the Cycle Simulator via REST API

**Status:** [ ] pending

**Intent:**
`backend/simulators/cycle_sim.py` contains a complete 4-value logic gate and
flip-flop simulation engine with VCD export — but it has no API endpoint and no
extension command. This task adds a minimal REST endpoint so the engine is
reachable, and a basic extension command that lets users run a quick gate-level
simulation on a selected Verilog module.

**Expected Outcomes:**
- `POST /api/simulate` accepts a simple JSON simulation spec (list of gates/flip-flops,
  clock period, stimulus events) and returns signal waveform data and a VCD string.
- `GET /api/simulate/health` returns `{"status": "online", "service": "CycleSim Engine"}`.
- A new VS Code command `siliconbob.runSimulation` opens a quick-pick letting the
  user choose a predefined example (`ripple_counter`, `dff_chain`) and displays the
  VCD output in a new editor tab.
- The backend router is mounted in `backend/main.py` alongside the existing routers.

**Todo List:**
1. Create `backend/routers/simulator/__init__.py` (empty).
2. Create `backend/routers/simulator/models.py`:
   - `GateSpec(BaseModel)` — `name`, `gate_type`, `inputs`, `output`
   - `FlipFlopSpec(BaseModel)` — `name`, `ff_type` (`dff`/`jkff`), signal names, reset config
   - `StimulusEvent(BaseModel)` — `signal`, `value` (0/1/X/Z), `at_time_ps`
   - `SimulateRequest(BaseModel)` — `gates`, `flip_flops`, `stimuli`, `clock_period_ps`,
     `run_until_ps`, `example` (optional string shortcut)
   - `SimulateResponse(BaseModel)` — `status`, `vcd`, `signal_summary` (final values),
     `event_count`, `cycle_count`
3. Create `backend/routers/simulator/router.py`:
   - `GET /api/simulate/health`
   - `POST /api/simulate` — build a `SimulationEngine`, apply gates/FFs/stimuli from
     request, call `engine.run(until_time_ps)`, return `SimulateResponse`.
   - Support `example="ripple_counter"` and `example="dff_chain"` shortcuts that call
     the existing `run_ripple_counter_example()` and `run_dff_chain_example()` functions
     from `cycle_sim.py`.
4. Mount the new router in `backend/main.py`:
   `from backend.routers.simulator.router import router as sim_router`
   `app.include_router(sim_router)`
5. In `extensions/siliconbob-rtl/src/commands/`, create `runSimulation.ts`:
   - `vscode.window.showQuickPick(["Ripple Counter", "D Flip-Flop Chain"])` prompt.
   - POST to `/api/simulate` with `{ example: "ripple_counter" | "dff_chain" }`.
   - Open response `.vcd` string in a new untitled editor tab (language `plaintext`).
6. Register `siliconbob.runSimulation` in `extension.ts` and `package.json`.

**Relevant Context:**
- `backend/simulators/cycle_sim.py` — `SimulationEngine`, `run_ripple_counter_example()`,
  `run_dff_chain_example()`, `VCDExporter.export()`
- Pattern to follow: `backend/routers/blueprintbob/router.py` (single-file router)
- No changes needed to `cycle_sim.py` itself — just wrap it.

---

## Sub-Task 6 — Add Unit Tests for the 8 Language Engines

**Status:** [ ] pending

**Intent:**
There are zero unit tests for the language lint engines. A bad regex change goes
undetected. This task adds a pytest test file that validates every rule in every
language engine fires correctly and produces the expected `rule_id` and `fixed_line`
output.

**Expected Outcomes:**
- `backend/tests/test_engine.py` exists and all tests pass with `pytest`.
- Every rule ID (`RTL-001` through `RTL-004`, `PY-001` through `PY-004`,
  `CPP-001` through `CPP-003`, `JS-001` through `JS-003`, `JAVA-001` through
  `JAVA-003`, `GO-001`, `GO-002`, `RUST-001`, `SEC-001`, `DEBT-001`) has at
  least one positive-case test and one negative-case test.
- Tests use the existing `test_samples/` files for Verilog cases.
- Tests use inline code strings for all other language cases (no extra files needed).
- `pytest backend/tests/test_engine.py` passes with zero failures.

**Todo List:**
1. Create `backend/tests/__init__.py` (empty).
2. Create `backend/tests/test_engine.py`:
   - Import `analyze_and_optimize_code` from `backend.routers.rtl.engine`.
   - For each rule: write a `test_<rule_id>_detects()` function with a minimal
     code snippet that triggers exactly that rule.
   - Assert: `len(issues) >= 1`, `issues[0].rule_id == "<RULE_ID>"`,
     `issues[0].fixed_line is not None` (for fixable rules).
   - Write a corresponding `test_<rule_id>_clean()` function with correct code
     that should produce zero issues for that rule.
3. For Verilog rules, read the existing `test_samples/*.v` files as inputs.
4. Run `pytest backend/tests/test_engine.py -v` and fix any failures.

**Relevant Context:**
- `backend/routers/rtl/engine.py` — `analyze_and_optimize_code` dispatcher
- `backend/test_blueprintbob.py` — example of existing test structure to follow
- `test_samples/alu_with_latch.v`, `race_condition.v`, `unpipelined_mult.v`

---

## Implementation Order & Dependencies

```
Sub-Task 2 (fixed_line backend) must come before Sub-Task 2 (CodeActionProvider)
Sub-Task 3 (on-save) depends on the refactor inside Sub-Task 2 (runAnalysis extraction)
Sub-Task 5 (simulator router) is fully independent
Sub-Task 4 (UI revamp) is fully independent
Sub-Task 6 (tests) depends on Sub-Task 2 (fixed_line) being done first
```

Recommended execution order: **2 → 3 → 1 → 5 → 4 → 6**

| Order | Sub-Task | Why this position |
|---|---|---|
| 1st | Sub-Task 2 — fixed_line + CodeActions | Core UX; also unblocks test writing |
| 2nd | Sub-Task 3 — on-save trigger | Builds on the refactor done in Sub-Task 2 |
| 3rd | Sub-Task 1 — WebSocket wiring | Self-contained; biggest functional gap |
| 4th | Sub-Task 5 — Simulator API | Self-contained; adds new route + command |
| 5th | Sub-Task 4 — BlueprintBob UI | Pure CSS/HTML; no logic dependencies |
| 6th | Sub-Task 6 — Unit tests | Validates all of the above when complete |

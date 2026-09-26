# Multi-Extension Monorepo Refactor Plan
## SiliconBob / ByteSized — IBM Bob IDE Extensions Platform

### Status: ✅ COMPLETE

---

## Top-Level Overview

**Goal:** Transform the current single-extension, single-backend project into a monorepo
that can host multiple VS Code / IBM Bob extensions — each owned by a different team member —
without breaking the existing SiliconBob RTL extension.

**Scope:**
- Restructure the `extension/` folder into an `extensions/` monorepo with one sub-folder per extension.
- Restructure `backend/main.py` into a modular FastAPI router layout where each extension owns its own router module.
- Create a proper `extensions/shared/` local npm package (with its own `package.json` + `tsconfig.json`) so extensions import it as `@bytesized/shared` — no fragile relative `../../` chains.
- Scaffold a placeholder `extensions/2nd-ext/` and `backend/routers/2nd-ext/` so the next team member has a starting point.
- Move the existing SiliconBob RTL work into the new structure without changing any behaviour.
- Leave packaging decisions (separate `.vsix` vs combined) for a later stage.

**Non-goals:**
- No new extension logic or features are added in this plan.
- No CI/CD, publish pipeline, or bundler (webpack/esbuild) changes.
- Packaging strategy (mono-extension vs independent extensions) explicitly deferred.

---

## Proposed Directory Layout (Target State)

```
ByteSized/
├── extensions/
│   ├── shared/                          # Local npm package — @bytesized/shared
│   │   ├── package.json                 # name: "@bytesized/shared", version: "1.0.0"
│   │   ├── tsconfig.json                # compiles src/ -> out/, declarationDir: out/
│   │   ├── src/
│   │   │   ├── index.ts                 # barrel re-export
│   │   │   ├── apiClient.ts             # postJson<T>(url, body): Promise<T>
│   │   │   └── statusBar.ts             # createStatusBar(text, command): StatusBarItem
│   │   └── out/                         # compiled JS + .d.ts (git-ignored)
│   │
│   ├── siliconbob-rtl/                  # Extension 1 — existing RTL work, relocated
│   │   ├── package.json                 # depends on "@bytesized/shared": "file:../shared"
│   │   ├── tsconfig.json                # references ../../shared
│   │   ├── README.md
│   │   ├── src/
│   │   │   ├── extension.ts             # thin activate/deactivate only
│   │   │   └── commands/
│   │   │       ├── optimizeRTL.ts       # siliconbob.optimizeRTL handler
│   │   │       └── connectWorkspace.ts  # siliconbob.connectWorkspace handler
│   │   └── out/                         # compiled JS (git-ignored)
│   │
│   └── 2nd-ext/                         # Extension 2 — placeholder scaffold
│       ├── package.json                 # depends on "@bytesized/shared": "file:../shared"
│       ├── tsconfig.json
│       ├── README.md
│       └── src/
│           └── extension.ts             # stub activate/deactivate
│
├── backend/
│   ├── main.py                          # App factory only — creates app, mounts routers
│   ├── requirements.txt                 # unchanged
│   ├── shared/
│   │   ├── __init__.py
│   │   └── models.py                    # RTLIssue, OptimizeRequest, OptimizeResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── rtl/
│   │   │   ├── __init__.py
│   │   │   ├── router.py                # APIRouter: /health, /api/optimize-rtl, /ws/{room_id}
│   │   │   └── engine.py                # analyze_and_optimize_rtl + ConnectionManager
│   │   └── 2nd-ext/                     # Placeholder for 2nd extension's backend
│   │       ├── __init__.py
│   │       └── router.py                # stub APIRouter (GET /2nd-ext/health)
│   └── test_api.py                      # unchanged — same URLs still work
│
├── test_samples/                        # unchanged
├── bob_sessions/                        # unchanged
├── README.md
└── SECURITY.MD
```

---

## Sub-Tasks

---

### Sub-Task 1 — Restructure the Backend into Routers

**Status:** [x] done

**Intent:**
`backend/main.py` is one flat file with models, logic, and routes all inline.
Adding a second extension's routes would mean editing the same file and creating merge conflicts.
Introduce FastAPI's `APIRouter` pattern: `main.py` becomes a thin app factory,
shared Pydantic models live in `backend/shared/models.py`, and each extension owns
a `backend/routers/<name>/` sub-package with its own `router.py` and logic file.

**Expected Outcomes:**
- `backend/main.py` contains only: app instantiation, CORS middleware, and `app.include_router()` calls.
- `backend/shared/models.py` holds `RTLIssue`, `OptimizeRequest`, `OptimizeResponse`.
- `backend/routers/rtl/engine.py` holds `analyze_and_optimize_rtl` and `ConnectionManager`.
- `backend/routers/rtl/router.py` holds the three route handlers on an `APIRouter`.
- `backend/routers/2nd-ext/router.py` holds a stub `APIRouter` with one `GET /2nd-ext/health` route.
- All existing API paths (`GET /health`, `POST /api/optimize-rtl`, `WS /ws/{room_id}`) are preserved exactly.
- `backend/test_api.py` runs without any changes.
- A new team member only needs to create `backend/routers/<their-ext>/router.py` and add one `include_router` line in `main.py`.

**Todo List:**
1. Create `backend/shared/__init__.py` (empty) and `backend/shared/models.py` — move `RTLIssue`, `OptimizeRequest`, `OptimizeResponse` pydantic classes here from `main.py`.
2. Create `backend/routers/__init__.py` (empty).
3. Create `backend/routers/rtl/__init__.py` (empty).
4. Create `backend/routers/rtl/engine.py` — move `analyze_and_optimize_rtl` function and `ConnectionManager` class + `manager` instance here; import from `backend.shared.models`.
5. Create `backend/routers/rtl/router.py` — instantiate `APIRouter()`, move the three route handler functions, import `engine` and `models`.
6. Create `backend/routers/2nd-ext/__init__.py` (empty).
7. Create `backend/routers/2nd-ext/router.py` — stub `APIRouter` with a single `GET /2nd-ext/health` returning `{"status": "online", "service": "2nd-ext"}`.
8. Rewrite `backend/main.py` — app creation, CORS, then `app.include_router(rtl_router)` and `app.include_router(second_ext_router)`.
9. Smoke-test: `uvicorn main:app --reload` from `backend/` — confirm `/health`, `/api/optimize-rtl`, `/ws/test-room`, and `/2nd-ext/health` all respond.

**Relevant Context:**
- `backend/main.py` lines 26–42 (models to move), 47–138 (engine to move), 143–210 (routes to move).
- FastAPI `APIRouter` pattern: `router = APIRouter()` in router.py, then `app.include_router(router)` in main.py.
- `backend/test_api.py` hits `http://127.0.0.1:8000/health` and `/api/optimize-rtl` — do not change those paths.

---

### Sub-Task 2 — Create the Shared Extension Package

**Status:** [x] done

**Intent:**
Create `extensions/shared/` as a proper local npm package (`@bytesized/shared`).
Extensions declare it as a `file:` dependency in their `package.json`, TypeScript resolves
types via its compiled `.d.ts` files, and there are no fragile relative import paths.
When a utility needs updating, only `shared/` changes — all consumers recompile automatically.

**Expected Outcomes:**
- `extensions/shared/package.json` exists with `"name": "@bytesized/shared"`.
- `extensions/shared/tsconfig.json` compiles `src/` to `out/` and emits declaration files.
- `extensions/shared/src/apiClient.ts` exports `postJson<T>(url: string, body: unknown): Promise<T>`.
- `extensions/shared/src/statusBar.ts` exports `createStatusBar(text: string, command: string): vscode.StatusBarItem`.
- `extensions/shared/src/index.ts` barrel-exports both utilities.
- Running `npm install && npm run compile` inside `shared/` produces `out/` with `.js` and `.d.ts` files.

**Todo List:**
1. Create `extensions/shared/package.json` — name `@bytesized/shared`, version `1.0.0`, `"main": "./out/index.js"`, `"types": "./out/index.d.ts"`, scripts `compile` and `watch` using `tsc`.
2. Create `extensions/shared/tsconfig.json` — target ES2020, module CommonJS, `declaration: true`, `outDir: ./out`, `rootDir: ./src`.
3. Create `extensions/shared/src/apiClient.ts` — `postJson<T>` generic fetch wrapper.
4. Create `extensions/shared/src/statusBar.ts` — `createStatusBar` factory using `vscode.window.createStatusBarItem`.
5. Create `extensions/shared/src/index.ts` — re-export everything from `apiClient` and `statusBar`.
6. Run `npm install && npm run compile` inside `extensions/shared/` to confirm zero errors and `out/` is generated.

**Relevant Context:**
- `extension/src/extension.ts` lines 35–50 (fetch call to extract into `postJson`) and lines 15–20 (StatusBarItem setup to extract into `createStatusBar`).
- The `@types/vscode` devDependency is needed in `shared/package.json` since `statusBar.ts` imports from `vscode`.
- `"main"` and `"types"` fields in `shared/package.json` tell TypeScript and Node where to find the compiled output when other packages use `file:../shared`.

---

### Sub-Task 3 — Migrate siliconbob-rtl Extension into Monorepo

**Status:** [x] done

**Intent:**
Move the existing `extension/` folder to `extensions/siliconbob-rtl/`, wire it to the
shared package, and split the monolithic `extension.ts` into per-command files.
This is a structural move only — the compiled output and runtime behaviour stay identical.

**Expected Outcomes:**
- `extension/` folder no longer exists at root; contents live under `extensions/siliconbob-rtl/`.
- `extensions/siliconbob-rtl/package.json` has `"@bytesized/shared": "file:../shared"` in `dependencies`.
- `extensions/siliconbob-rtl/src/commands/optimizeRTL.ts` contains the `siliconbob.optimizeRTL` handler, importing `postJson` from `@bytesized/shared`.
- `extensions/siliconbob-rtl/src/commands/connectWorkspace.ts` contains the `siliconbob.connectWorkspace` handler, importing `createStatusBar` from `@bytesized/shared`.
- `extensions/siliconbob-rtl/src/extension.ts` is a thin shell that only calls the command registrations.
- `npm run compile` inside `extensions/siliconbob-rtl/` produces zero TypeScript errors.

**Todo List:**
1. Create `extensions/siliconbob-rtl/` directory tree — copy `package.json`, `tsconfig.json`, `README.md` from `extension/`.
2. Add `"@bytesized/shared": "file:../shared"` to `dependencies` in `extensions/siliconbob-rtl/package.json`.
3. Run `npm install` inside `extensions/siliconbob-rtl/` so the symlink to `shared/` is created in `node_modules/@bytesized/`.
4. Create `extensions/siliconbob-rtl/src/commands/optimizeRTL.ts` — extract the `siliconbob.optimizeRTL` handler from old `extension.ts`; replace the inline `fetch` call with `postJson` from `@bytesized/shared`.
5. Create `extensions/siliconbob-rtl/src/commands/connectWorkspace.ts` — extract the `siliconbob.connectWorkspace` handler; use `createStatusBar` where appropriate.
6. Rewrite `extensions/siliconbob-rtl/src/extension.ts` to import both command handlers and register them in `activate`; keep `deactivate` cleaning up the `DiagnosticCollection`.
7. Update `extensions/siliconbob-rtl/tsconfig.json` — ensure `moduleResolution` is `node` so `@bytesized/shared` resolves through `node_modules`.
8. Delete the old `extension/` folder at repo root.
9. Run `npm run compile` from `extensions/siliconbob-rtl/` — fix any TypeScript errors.
10. Press F5 in Bob/VS Code from `extensions/siliconbob-rtl/` — confirm both commands work end-to-end with the backend running.

**Relevant Context:**
- `extension/src/extension.ts` lines 23–104 (`optimizeRTL` to move) and 107–125 (`connectWorkspace` to move).
- `extension/package.json` `"main": "./out/extension.js"` — stays relative to the package root, so no change needed.
- The compiled output path stays `./out/extension.js` — VS Code resolves this relative to each extension's own folder.

---

### Sub-Task 4 — Scaffold the 2nd-ext Placeholder

**Status:** [x] done

**Intent:**
Give the second team member a working, runnable starting point so they can immediately
start writing their extension logic without having to figure out boilerplate. The scaffold
mirrors the `siliconbob-rtl` layout but with stub content only.

**Expected Outcomes:**
- `extensions/2nd-ext/` exists with `package.json`, `tsconfig.json`, `README.md`, and a stub `src/extension.ts`.
- `extensions/2nd-ext/package.json` depends on `@bytesized/shared` via `file:../shared`.
- The stub `extension.ts` activates and logs a console message — compiles and launches with F5.
- `backend/routers/2nd-ext/router.py` provides a `GET /2nd-ext/health` route already mounted in `main.py`.

**Todo List:**
1. Create `extensions/2nd-ext/package.json` — copy structure from `siliconbob-rtl/package.json`, update `name`, `displayName`, `description`, activation events.
2. Create `extensions/2nd-ext/tsconfig.json` — copy from `siliconbob-rtl/tsconfig.json`.
3. Create `extensions/2nd-ext/README.md` — placeholder with the extension name.
4. Create `extensions/2nd-ext/src/extension.ts` — stub with `activate` logging `[2nd-ext] activated` and empty `deactivate`.
5. Run `npm install && npm run compile` inside `extensions/2nd-ext/` — confirm clean compile.

**Relevant Context:**
- `backend/routers/2nd-ext/` is already created in Sub-Task 1 (step 6–7).
- Keep command names, contribution points, and settings prefixed `2nd-ext.*` to avoid collision with `siliconbob.*`.

---

### Sub-Task 5 — Update Root-Level Files

**Status:** [x] done

**Intent:**
The root `README.md` and `.gitignore` still refer to the old `extension/` path.
Update them to reflect the monorepo structure and add an "Adding a New Extension" guide
so future team members know exactly what to create.

**Expected Outcomes:**
- `.gitignore` ignores `extensions/*/out/` and `extensions/*/node_modules/` instead of the old flat patterns.
- `README.md` Quick Start references `extensions/siliconbob-rtl/` not `extension/`.
- `README.md` has a "Repo Structure" section and a brief "Adding a New Extension" guide.
- `SECURITY.MD` has no stale `extension/` path references.

**Todo List:**
1. Add `extensions/*/out/` and `extensions/*/node_modules/` to `.gitignore`; remove any explicit `extension/out/` or `extension/node_modules/` entries if present.
2. Update `README.md` Quick Start — `cd extensions/siliconbob-rtl` instead of `cd extension`.
3. Add a "Repo Structure" section in `README.md` showing the new `extensions/` tree.
4. Add an "Adding a New Extension" section in `README.md` with the four steps: create folder, copy scaffold, add shared dep, add backend router.
5. Check `SECURITY.MD` for stale paths and update if any exist.

**Relevant Context:**
- `README.md` lines 80–90 (Quick Start compile instructions).
- `.gitignore` line 74 (`node_modules/`) already covers the global pattern but explicit folder entries may exist.

---

## Decisions Made

| Question | Decision |
|---|---|
| Shared package structure | Proper local npm package (`@bytesized/shared`) with own `package.json` + `tsconfig.json` |
| Import style | `@bytesized/shared` via `file:` dependency — no fragile relative paths |
| npm workspaces | Not used yet — each extension runs its own `npm install`; workspaces can be layered on later |
| Packaging strategy | Deferred — folder structure supports both single `.vsix` and independent packages |
| 2nd extension name | `2nd-ext` (placeholder) |

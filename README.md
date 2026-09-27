# ByteSized: Developer & Hardware Engineering Suite
### A 2-Extension Collaborative Platform for IBM Bob IDE

> **IBM Bob 2.0 48-Hour Hackathon Submission**
> *Track: Developer Workflow Optimization (Software & Silicon Engineering)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![IBM Bob 2.0](https://img.shields.io/badge/Built%20With-IBM%20Bob%202.0-blue)](https://lablab.ai)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)](https://fastapi.tiangolo.com/)
[![CI](https://img.shields.io/badge/CI-GitHub%20Actions-blue)](https://github.com/GAGAN7350/ByteSized/actions)

---

## Submission Deliverables

- **Public Repository:** [https://github.com/GAGAN7350/ByteSized](https://github.com/GAGAN7350/ByteSized)
- **Demo Video:** `[LINK_TO_DEMO_VIDEO]`
- **IBM Bob Session Summaries:** See [`bob_sessions/`](./bob_sessions/) for session summaries.

---

## Suite Overview

```
ByteSized Suite (IBM Bob IDE / VS Code)
├── SiliconBob RTL   ──> Multi-language AST Linter & Auto-Rewriter
│                        (Verilog, Python, C/C++, JS/TS, Java, Go, Rust)
├── BlueprintBob     ──> Interactive Architecture & Codebase Visualizer
│                        (Offline AST engine + AI mode via Gemini/OpenAI)
├── PCB & Chip Studio──> Interactive Microchip Block Layout & Circuit Designer
│                        (Draggable IC blocks, pinouts, and hardware netlist exporter)
└── Backend          ──> Unified FastAPI server with WebSocket co-working hub
```

---

## Extensions

### Extension 1 — SiliconBob RTL (`extensions/siliconbob-rtl/`)

**Command:** `SiliconBob: Analyze & Optimize Code (All Languages)`  
Right-click any open file → context menu, or open the Command Palette (`Ctrl+Shift+P`) and search `SiliconBob`.

**Also available:** `SiliconBob: Join Multi-Engineer Room` — connects to the WebSocket co-working hub.

**What it detects and fixes:**

| Language | Rule | Fix |
|---|---|---|
| Verilog/RTL | Blocking `=` in `posedge` block (race condition) | Auto-replaces with `<=` |
| Verilog/RTL | `case` without `default:` (latch inference) | Inserts `default: begin … end` |
| Verilog/RTL | Non-synthesizable `#delay` | Strips delay |
| Verilog/RTL | Unpipelined multiply-accumulate on critical path | 2-stage pipeline rewrite |
| Python | Mutable default argument (`=[]`) | Replaces with `=None` |
| Python | Bare `except:` | Rewrites to `except Exception:` |
| Python | `range(len(x))` | Converts to `enumerate(x)` |
| Python | `type(x) == T` | Converts to `isinstance(x, T)` |
| C/C++ | `strcpy(` → buffer overflow (CWE-120) | Rewrites to `strncpy(` |
| C/C++ | `gets(` → insecure (CWE-242) | Rewrites to `fgets(` |
| C/C++ | `sprintf(` → bounds hazard (CWE-134) | Rewrites to `snprintf(` |
| JavaScript/TS | `var` declaration | Upgrades to `const` |
| JavaScript/TS | Loose `==` / `!=` | Upgrades to `===` / `!==` |
| Java | String `==` comparison | Converts to `.equals()` |
| Go | Ignored error (`_, _ =`) | Flags for manual fix |
| Go | `panic(` in production code | Flags for manual fix |
| Rust | `.unwrap()` | Flags for manual fix |
| Generic | Hardcoded credentials (CWE-798) | Flags for manual fix |
| Generic | `TODO` / `FIXME` markers | Flags for manual fix |

---

### Extension 2 — BlueprintBob (`extensions/blueprintbob/`)

**Command:** `BlueprintBob: Visualize Workspace Architecture`  
Open the Command Palette (`Ctrl+Shift+P`) and search `BlueprintBob`, or click the status bar item.

**What it produces:**
- An interactive pan/zoom Mermaid flowchart of your entire repository architecture
- A structured node/edge graph with group layers (backend, frontend, extensions, shared, tests, config)
- An AI-written or AST-extracted explanation of architectural relationships

**Two engine modes** (toggled in the toolbar):
- `Offline` — deterministic AST analysis; no API key required; works fully air-gapped
- `AI Mode` — sends file tree + key file contents to Gemini or OpenAI for richer explanations

**Two granularity levels:**
- `Overview` — 10–14 macro-component nodes
- `Deep Map` — 22–36 individual file nodes with import edges

---

### Extension 3 — Microchip & PCB Visual Designer (`extensions/02-chip-pcb-designer/`)

**Command:** `ByteSized: Open Microchip & PCB Visual Designer`  
Open the Command Palette (`Ctrl+Shift+P`) and search `ByteSized: Open Microchip & PCB Visual Designer`.

**What it provides:**
- **Interactive Component Palette:** 32-bit ALU Core, ARM / RISC-V MCU, 64KB SRAM Cache, PLL Clock Generator, and AXI4 Bus Arbiter.
- **Visual Dot-Grid Canvas:** Drag, drop, and position integrated circuit logic blocks and pinout terminals in real time.
- **Hardware Netlist Exporter:** 1-click serialization to export the complete schematic netlist directly back to the editor.
- **Air-Gapped Operation:** Operates 100% locally with zero external cloud dependencies.

---

## Repo Structure

```
ByteSized/
├── .github/
│   └── workflows/ci.yml        ← CI pipeline (lint → test → build → security audit)
├── backend/
│   ├── config.py               ← Typed environment config (pydantic-settings)
│   ├── main.py                 ← App factory: CORS, logging, rate-limiting, /health
│   ├── requirements.txt        ← Runtime dependencies
│   ├── requirements-dev.txt    ← Dev/test dependencies (pytest, ruff, pip-audit)
│   ├── shared/
│   │   └── models.py           ← Shared Pydantic request/response models
│   ├── routers/
│   │   ├── rtl/
│   │   │   ├── engine.py       ← All language AST rule implementations
│   │   │   └── router.py       ← /api/optimize-code, /api/optimize-rtl, /ws/{room_id}
│   │   └── blueprintbob/
│   │       ├── analyzer.py     ← File tree classifier & path normalizer
│   │       ├── ast_engine.py   ← Offline AST + JSDoc docstring extractor
│   │       ├── compiler.py     ← Mermaid diagram compiler
│   │       ├── generator.py    ← Orchestrator: offline/AI engine, caching, Gemini/OpenAI
│   │       └── router.py       ← /api/blueprintbob/generate, /api/blueprintbob/health
│   └── tests/
│       ├── test_engine.py      ← 24 unit tests for all RTL/language rules
│       └── test_blueprintbob.py ← 16 integration tests for BlueprintBob
├── extensions/
│   ├── shared/                 ← @bytesized/shared — npm utilities for all extensions
│   ├── siliconbob-rtl/         ← Extension 1: Universal code optimizer
│   │   └── src/
│   │       ├── extension.ts    ← Activation entry point
│   │       └── commands/
│   │           ├── optimizeRTL.ts       ← Core analysis + diff command
│   │           ├── connectWorkspace.ts  ← WebSocket room join
│   │           ├── codeActions.ts       ← In-gutter quick-fix actions
│   │           └── runSimulation.ts     ← RTL simulation runner
│   ├── blueprintbob/
│   │   └── src/
│   │       ├── extension.ts         ← Activation + command handler
│   │       ├── workspaceScanner.ts  ← Scans workspace file tree + key files
│   │       └── diagramPanel.ts      ← Webview panel: Mermaid canvas, drawers, modals
│   └── 02-chip-pcb-designer/   ← Extension 3: Microchip & PCB visual studio
│       ├── package.json         ← Extension manifest & commands
│       └── src/
│           └── extension.ts     ← Webview panel: draggable IC blocks, pinouts, netlist export
├── deploy/
│   ├── Dockerfile              ← Multi-stage production image (non-root, slim)
│   ├── docker-compose.yml      ← Redis + backend (4 workers) + nginx (TLS)
│   ├── k8s/                    ← Kubernetes manifests (deployment, HPA, ingress)
│   └── terraform/              ← Infrastructure-as-code
├── test_samples/               ← Sample .v Verilog files for manual testing
├── ruff.toml                   ← Python linter configuration
├── CONTRIBUTING.md             ← How to add rules, routers, and extensions
└── bob_sessions/               ← IBM Bob session screenshots (hackathon deliverable)
```

---

## Prerequisites

| Tool | Minimum version | Used for |
|---|---|---|
| Python | 3.11 | Backend |
| Node.js | 20 LTS | Extensions |
| npm | 10 | Extensions |
| IBM Bob IDE or VS Code | latest | Running extensions |
| Docker (optional) | 24 | Containerised deployment |

---

## Running Everything — Step by Step

### Step 1 — Clone and enter the repo

```bash
git clone https://github.com/GAGAN7350/ByteSized.git
cd ByteSized
```

---

### Step 2 — Configure the backend environment

```bash
# Copy the example env file and fill in values
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
```

Open `.env` and set at minimum:

```env
# Required for BlueprintBob AI mode (optional — offline mode works without it)
GEMINI_API_KEY=your_gemini_key_here

# Allowed frontend origins (keep default for local dev)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,vscode-webview://*

# Environment (development | staging | production)
ENVIRONMENT=development
```

All other values have sensible defaults. See `.env.example` for the full list.

---

### Step 3 — Install backend dependencies and start the server

```bash
cd backend

# Install runtime dependencies
pip install -r requirements.txt

# Start the development server (auto-reloads on file changes)
cd ..
uvicorn backend.main:app --reload --port 8000
```

The server starts at **`http://localhost:8000`**.

| URL | What it is |
|---|---|
| `http://localhost:8000/docs` | Swagger interactive API docs |
| `http://localhost:8000/redoc` | ReDoc API reference |
| `http://localhost:8000/health` | Liveness probe (`{"status":"online"}`) |
| `http://localhost:8000/api/optimize-code` | RTL/code analysis endpoint (POST) |
| `http://localhost:8000/api/blueprintbob/generate` | Architecture diagram endpoint (POST) |
| `ws://localhost:8000/ws/{room_id}` | WebSocket co-working room |

---

### Step 4 — Build the shared npm package (first time only)

```bash
cd extensions/shared
npm install
npm run compile
cd ../..
```

---

### Step 5 — Build and launch the SiliconBob extension

```bash
cd extensions/siliconbob-rtl
npm install
npm run compile
```

- Press **`F5`** in IBM Bob IDE / VS Code to launch the **Extension Development Host**.
- In the host window, open any file from `test_samples/`:
  - `test_samples/alu_with_latch.v` — tests latch inference detection
  - `test_samples/race_condition.v` — tests blocking assignment race condition
  - `test_samples/unpipelined_mult.v` — tests PPA pipelining suggestion
- Right-click inside the editor → **"SiliconBob: Analyze & Optimize Code (All Languages)"**

---

### Step 6 — Build and launch the BlueprintBob extension

```bash
cd extensions/blueprintbob
npm install
npm run compile
```

- Press **`F5`** to launch the Extension Development Host (or reuse the one from Step 5).
- Open the Command Palette (`Ctrl+Shift+P`) → **"BlueprintBob: Visualize Workspace Architecture"**.
- The panel opens with an interactive architecture diagram of your current workspace.
- Use the toolbar to switch between **Offline** / **AI Mode** and **Overview** / **Deep Map**.

---

### Step 7 — Build and launch the Microchip & PCB Designer extension

```bash
cd extensions/02-chip-pcb-designer
npm install
npm run compile
```

- In the Extension Development Host (or IBM Bob IDE), press `Ctrl+Shift+P` → **"ByteSized: Open Microchip & PCB Visual Designer"**.
- The interactive **Microchip & PCB Studio** canvas opens.
- Click components (ALU Core, ARM/RISC-V MCU, SRAM Cache, PLL Clock, AXI4 Bus) to drop them onto the canvas and drag to position.
- Click **"Export Netlist"** to export the integrated circuit netlist directly back to the editor.

---

### Step 8 — Optional: Package & Install all 3 Extensions permanently as .VSIX

If you prefer installing the extensions permanently into **IBM Bob IDE** or **VS Code** rather than running via F5:

```bash
# 1. Package and install Extension 1 (SiliconBob)
cd extensions/siliconbob-rtl
npm run package
bobide --install-extension siliconbob-hardware-ide-1.0.0.vsix --force

# 2. Package and install Extension 2 (BlueprintBob)
cd ../blueprintbob
npm run package
bobide --install-extension blueprintbob-0.1.0.vsix --force

# 3. Package and install Extension 3 (Microchip & PCB Designer)
cd ../02-chip-pcb-designer
npx @vscode/vsce package --no-dependencies
bobide --install-extension bytesized-pcb-chip-designer-1.0.0.vsix --force
```

---

## Using the Extensions

The extensions can be run either from an **Extension Development Host (F5)** or permanently installed via **.vsix** using the commands above. Start the backend first on port 8000:

### Complete end-to-end startup

Use three terminals on Windows so the backend and extension development tools
can remain running at the same time. From the repository root, create a Python
3.13 virtual environment, activate it, and install the backend dependencies:

```powershell
cd C:\Users\keert\ByteSized
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r backend\requirements-dev.txt
Copy-Item .env.example .env
```

Python 3.13 is recommended for the backend. Python 3.14 alpha releases may
cause FastAPI/Pydantic compatibility errors. For basic local use, the default
`.env` values are sufficient. Add `GEMINI_API_KEY` to `.env` only if you want
BlueprintBob AI mode. Never commit `.env` or place API keys in source code.

In the first terminal, start the FastAPI backend from the repository root:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --port 8000
```

Confirm that `http://localhost:8000/health` returns an online response before
opening an extension. The backend also provides interactive API documentation
at `http://localhost:8000/docs`. In a second terminal, build SiliconBob:

```powershell
cd C:\Users\keert\ByteSized\extensions\siliconbob-rtl
npm install
npm run compile
code .
```

Press **F5** in VS Code or IBM Bob to open the Extension Development Host. In
that host, open a sample or project source file and run the SiliconBob command
from the Command Palette. In a third terminal, build BlueprintBob if it is
not already compiled:

```powershell
cd C:\Users\keert\ByteSized\extensions\blueprintbob
npm install
npm run compile
```

Open the repository you want to inspect as the active workspace in the
Extension Development Host, then run the BlueprintBob command. If both
extensions are being developed together, compile both folders first and use
the corresponding launch configuration or press **F5** from the extension
project being tested.

### SiliconBob: Analyze and optimize code

1. Make sure the backend is running at `http://localhost:8000`.
2. Open a supported source file in the Extension Development Host.
3. Run **SiliconBob: Analyze & Optimize Code (All Languages)** from the
   Command Palette (`Ctrl+Shift+P`) or the editor context menu.
4. SiliconBob sends the current file to `/api/optimize-code`.
5. Detected issues appear as diagnostics in the editor and the optimized result
   opens in a side-by-side diff.
6. Choose **Apply to Current File** to replace the current file with the
   optimized result, or **Open in New Tab** to keep the result separate.

Supported language IDs are:
`verilog`, `systemverilog`, `python`, `c`, `cpp`, `javascript`,
`typescript`, `java`, `go`, and `rust`.

### SiliconBob: Apply or preview an individual fix

When an issue has a safe deterministic replacement, hover over its diagnostic
and select the lightbulb action:

- **SiliconBob: Apply Fix** replaces only the affected line.
- **SiliconBob: Preview Fix** opens a diff containing only that proposed change.

Some findings, such as ignored Go errors, Rust `unwrap()` calls, hardcoded
credentials, and TODO markers, are advisory only and do not provide an
automatic fix.

### SiliconBob: Run CycleSim

With the backend running and the SiliconBob extension loaded in the Extension
Development Host:

1. Press `Ctrl+Shift+P`.
2. Run **SiliconBob: Run CycleSim Simulation**.
3. Choose **Ripple Counter** or **D Flip-Flop Chain**.
4. SiliconBob calls `/api/simulate/` and opens the final signal states and VCD
   waveform output in a new editor tab.

The CycleSim backend also exposes `GET /api/simulate/health` and accepts custom
gate, flip-flop, stimulus, and clock definitions through `POST /api/simulate/`.

### SiliconBob: Lint on save

Lint-on-save is enabled by default. Saving a supported source file silently
refreshes its SiliconBob diagnostics without opening a diff or notification.
To disable it, open VS Code settings and turn off:

```text
SiliconBob › Lint On Save
```

The setting can also be placed in `.vscode/settings.json`:

```json
{
  "siliconbob.lintOnSave": true,
  "siliconbob.backendUrl": "http://localhost:8000"
}
```

If the backend is running on another host or port, change
`siliconbob.backendUrl`. Reload the Extension Development Host after changing
extension settings if the status bar still shows the old URL.

### SiliconBob: Collaboration rooms

Run **SiliconBob: Join Multi-Engineer Room**, enter a shared room ID such as
`soc-core-alu`, and wait for the status bar to show the room and active-user
count. The extension connects to:

```text
ws://localhost:8000/ws/<room-id>
```

Incoming `CODE_UPDATE` messages are opened as a read-only preview beside the
current editor. Run **SiliconBob: Leave Collaboration Room** to close the
connection. Collaboration state is held by the backend process and is intended
for development/demo use; use a shared Redis-backed deployment for a
multi-process production setup.

### BlueprintBob: Visualize a workspace

Dev2 owns the BlueprintBob architecture visualizer. It is a VS Code/IBM Bob
extension that scans the active workspace, sends a filtered file tree plus
important files to the BlueprintBob backend, and renders the returned graph in
an interactive webview. To use Dev2, first start the backend and then launch
the BlueprintBob extension through the Extension Development Host. Open the
repository that you want to understand, press `Ctrl+Shift+P`, and select
**BlueprintBob: Visualize Workspace Architecture**. BlueprintBob reads the
workspace README, manifests such as `package.json` or `requirements.txt`,
entrypoints, routers, models, services, and shared modules. It excludes
generated folders and binary/noise files such as `node_modules`, `.git`,
`dist`, `out`, virtual environments, and compiled artifacts. After scanning,
the panel displays a Mermaid architecture diagram, grouped components,
relationships, an explanation, and file metadata. Click a file node or its
file reference to open the source file in the editor; use the copy action to
copy Mermaid output when you need to include the diagram elsewhere.

Use **Overview** when you need a concise system-level map with macro
components, and use **Deep Map** when you need individual backend routers,
engines, extension files, tests, and configuration nodes. Use **Offline** mode
for deterministic AST/file-tree analysis with no API key or external AI
request. Use **AI Mode** for a richer generated explanation: open the API key
dialog from the BlueprintBob panel, choose the provider, enter the key, and
save it. The key is stored through VS Code Secret Storage and is sent only as
part of the generation request; it is not written into the repository. The
backend must have the matching provider configuration and network access. The
panel toolbar can switch modes and regenerate the diagram, change granularity,
save or clear the key, and refresh the visualization. If the active workspace
has no readable files, BlueprintBob reports that there is nothing to visualize.

Offline mode does not require an API key. AI mode uses the backend's configured
provider and key; do not place private credentials in source files or commit
them to the repository.

The Dev2 data flow is:

```text
Active workspace
    -> workspaceScanner.ts
    -> POST /api/blueprintbob/generate
    -> analyzer.py / ast_engine.py / generator.py
    -> graph + Mermaid response
    -> diagramPanel.ts webview
```

If BlueprintBob fails, check the backend terminal first, then verify
`blueprintbob.backendUrl` points to the running server. Offline mode is the
recommended first test because it does not depend on an AI key or provider.
The BlueprintBob backend health endpoint is
`http://localhost:8000/api/blueprintbob/health`.

### Extension settings and command reference

The important settings are:

| Setting | Default | Purpose |
|---|---|---|
| `siliconbob.backendUrl` | `http://localhost:8000` | Backend used by SiliconBob |
| `siliconbob.lintOnSave` | `true` | Re-analyze supported files after saving |
| `blueprintbob.backendUrl` | `http://localhost:8000` | Backend used by BlueprintBob |

The primary commands are:

| Command | Extension | Purpose |
|---|---|---|
| `SiliconBob: Analyze & Optimize Code (All Languages)` | SiliconBob | Analyze the active file and show an optimized diff |
| `SiliconBob: Preview Fix` | SiliconBob | Preview one deterministic issue fix |
| `SiliconBob: Run CycleSim Simulation` | SiliconBob | Run a built-in ripple counter or DFF-chain simulation |
| `SiliconBob: Join Multi-Engineer Room` | SiliconBob | Join a WebSocket collaboration room |
| `SiliconBob: Leave Collaboration Room` | SiliconBob | Close the active collaboration socket |
| `BlueprintBob: Visualize Workspace Architecture` | BlueprintBob | Scan and render the active workspace architecture |

### Troubleshooting

| Symptom | Fix |
|---|---|
| `Backend Offline` in the status bar | Start `uvicorn backend.main:app --reload --port 8000` from the repository root and check `http://localhost:8000/health`. |
| No SiliconBob diagnostics | Confirm the file uses one of the supported language IDs and run the command manually once. |
| Lightbulb does not appear | Only deterministic rules expose quick fixes; advisory findings intentionally do not. |
| Collaboration cannot connect | Check the backend URL, room ID, and that WebSocket connections are allowed by the proxy. |
| BlueprintBob AI mode fails | Use Offline mode or configure `GEMINI_API_KEY` in the backend environment. |
| Changes are not visible after editing extension code | Stop the Extension Development Host, run `npm run compile`, and press `F5` again. |

---

### Step 7 — Run the tests

```bash
# Install dev dependencies (includes pytest, ruff, pip-audit)
pip install -r backend/requirements-dev.txt

# Run all backend tests
python -m pytest backend/tests/test_engine.py backend/test_blueprintbob.py -v

# Run with coverage report
python -m pytest backend/ --cov=backend --cov-report=term-missing
```

Expected result: **59 tests, 0 failures.**

---

## Running with Docker (Production Stack)

The Docker Compose stack runs the full production configuration: Redis pub/sub + backend + nginx reverse proxy with WebSocket upgrade.

```bash
# Copy and configure environment
copy .env.example .env

# Build and start all services
docker compose -f deploy/docker-compose.yml up --build

# Backend only + Redis (no nginx)
docker compose -f deploy/docker-compose.yml up backend redis

# Stop and remove volumes
docker compose -f deploy/docker-compose.yml down -v
```

Services started:

| Service | Port | Description |
|---|---|---|
| `redis` | 6379 | WebSocket pub/sub backbone |
| `backend` | 8000 | FastAPI app (4 Uvicorn workers) |
| `backend_ws` | 8001 | Second replica for WS fan-out demo |
| `nginx` | 80 / 443 | Reverse proxy with TLS termination |

> **Note:** nginx requires SSL certificates at `deploy/nginx/ssl/`. For local testing, start without nginx: `docker compose -f deploy/docker-compose.yml up backend redis`.

---

## CI Pipeline

Every push to `main` or `dev/**` and every pull request runs the full CI pipeline automatically via [`.github/workflows/ci.yml`](.github/workflows/ci.yml):

| Job | Steps |
|---|---|
| `backend-ci` | Ruff lint → pytest (with coverage threshold) → pip-audit security scan |
| `extension-ci (siliconbob-rtl)` | npm install → TypeScript compile → npm audit |
| `extension-ci (blueprintbob)` | npm install → TypeScript compile → npm audit |

To run the linter locally:

```bash
pip install ruff
ruff check backend/
```

---

## Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` |
| `LOG_LEVEL` | `info` | `debug` / `info` / `warning` / `error` |
| `CORS_ORIGINS` | `http://localhost:3000,...` | Comma-separated allowed origins |
| `RATE_LIMIT_PER_MINUTE` | `60` | Max analysis requests per IP per minute |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini key for BlueprintBob AI mode |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `REDIS_PASSWORD` | *(empty)* | Redis AUTH password |
| `UVICORN_WORKERS` | `1` | Worker processes (use 1 with `--reload`) |

---

## Adding a New Extension

1. **Create the extension folder**
   ```bash
   # Windows
   xcopy /E /I extensions\blueprintbob extensions\<your-ext-name>
   # macOS / Linux
   cp -r extensions/blueprintbob extensions/<your-ext-name>
   ```
   Update `name`, `displayName`, and command prefixes in `extensions/<your-ext-name>/package.json`.

2. **Install the shared package**
   ```bash
   cd extensions/<your-ext-name>
   npm install        # resolves @bytesized/shared from file:../shared
   npm run compile
   ```

3. **Add a backend router** — copy `backend/routers/blueprintbob/` as a template, then mount it in `backend/main.py`:
   ```python
   from backend.routers.<your_ext>.router import router as your_ext_router
   app.include_router(your_ext_router)
   ```

4. **Write your feature** — add command handlers in `src/commands/`, import utilities from `@bytesized/shared`.

See [CONTRIBUTING.md](./CONTRIBUTING.md) for the full guide including how to add AST rules and write tests.

---

## How IBM Bob 2.0 Was Used

- **Plan Mode:** Structured the extension division of labour and backend REST contracts.
- **Agent Mode:** Built AST rules, Webview canvas rendering, WebSocket room managers, CI pipeline, security hardening, and typed config.
- **Screenshots:** Session evidence stored in [`bob_sessions/`](./bob_sessions/).

---

## The ByteSized Team (Team of 6)

| Member | Role |
|---|---|
| Gagan (Dev 1) | SiliconBob RTL & Universal Code Optimizer Lead |
| Technical Member 2 (Dev 2) | Microchip & PCB Visual Designer Lead |
| Technical Member 3 (Dev 3) | Git Architecture & Flow Diagram Lead |
| Non-Technical Member 1 | Video & Presentation Lead |
| Non-Technical Member 2 | Semiconductor & Software Market Research Lead |
| Non-Technical Member 3 | Documentation & IBM Bob Compliance Lead |

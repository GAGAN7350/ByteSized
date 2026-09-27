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
│   └── blueprintbob/
│       └── src/
│           ├── extension.ts         ← Activation + command handler
│           ├── workspaceScanner.ts  ← Scans workspace file tree + key files
│           └── diagramPanel.ts      ← Webview panel: Mermaid canvas, drawers, modals
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

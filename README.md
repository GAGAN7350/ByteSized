# ByteSized: Developer & Hardware Engineering Suite ⚡
### A 3-Extension Collaborative Platform for IBM Bob IDE

> **IBM Bob 2.0 48-Hour Hackathon Submission**  
> *Track: Developer Workflow Optimization (Software & Silicon Engineering)*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![IBM Bob 2.0](https://img.shields.io/badge/Built%20With-IBM%20Bob%202.0-blue)](https://lablab.ai)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-green)](https://fastapi.tiangolo.com/)
[![VS Code](https://img.shields.io/badge/Extensions-3%20Installed-purple)](https://code.visualstudio.com/)

---

## 📽️ Submission Deliverables
* **Public Repository:** [https://github.com/GAGAN7350/ByteSized](https://github.com/GAGAN7350/ByteSized)
* **Demo Video:** `[LINK_TO_DEMO_VIDEO]`
* **IBM Bob Session Summaries:** See [`bob_sessions/`](./bob_sessions/) for session summaries across all team members.

---

## 🧩 The 3 Developer Extensions Overview

Our team of 3 technical developers engineered **3 dedicated extensions** that run natively inside **IBM Bob IDE**, supported by a unified real-time backend and co-working platform:

```
ByteSized Suite (IBM Bob IDE)
├── 01. Universal Code Optimizer (Dev 1)   ──> Multi-language AST Linter & Auto-Rewriter
├── 02. Microchip & PCB Designer (Dev 2)   ──> Interactive Visual Circuit & Pinout Canvas
├── 03. Git Flow & Architecture (Dev 3)    ──> Visual Commit Topology & System Flow Graph
└── Shared Co-Working Platform             ──> Multi-People WebSocket Collaboration Hub
```

---

### 1️⃣ Extension 1: Universal Code Checker & Optimizer (`extensions/01-code-optimizer/`)
* **Developer:** Dev 1 (Gagan)
* **Scope:** All programming languages (Verilog, Python, C/C++, JavaScript/TypeScript).
* **Key Features:**
  * **Verilog/RTL:** Catches catastrophic hardware latches, race conditions in shift registers, and unpipelined critical paths.
  * **Python:** Eliminates mutable default arguments, bare `except:`, and slow `range(len())` loops.
  * **C/C++:** Hardens against buffer overflow hazards (`strcpy` $\rightarrow$ `strncpy`) and RAII memory leaks.
  * **JavaScript:** Upgrades legacy `var` scoping and loose equality (`==` $\rightarrow$ `===`).
  * **UX:** Renders in-gutter squiggles (`DiagnosticCollection`), side-by-side diff (`vscode.diff`), and performance gain metrics.
* **Command:** `ByteSized: Check & Optimize Code`

---

## 🗂️ Repo Structure

```
ByteSized/
├── extensions/
│   ├── shared/            ← @bytesized/shared — local npm package, utilities for all extensions
│   ├── siliconbob-rtl/    ← Extension 1: RTL hardware copilot (IBM Bob / VS Code)
│   └── 2nd-ext/           ← Extension 2: placeholder scaffold for next team member
├── backend/
│   ├── main.py            ← App factory — mounts all routers
│   ├── shared/            ← Shared Pydantic models
│   └── routers/
│       ├── rtl/           ← SiliconBob RTL routes + engine
│       └── second_ext/    ← 2nd-ext stub routes
├── test_samples/          ← Sample .v files for testing
└── bob_sessions/          ← IBM Bob session screenshots (hackathon deliverable)
```

---

## 🚀 Quick Start Guide

---

### 3️⃣ Extension 3: Git Architecture & Flow Diagram (`extensions/03-git-diagram-generator/`)
* **Developer:** Dev 3
* **Scope:** Repository visualization and team architecture flow.
* **Key Features:**
  * **Git Commit DAG:** Interactive visualization of branch branches (`main`, `dev1/code-optimizer`, `dev2/pcb-designer`, `dev3/git-diagram`) and merge topologies.
  * **System Flow Diagram:** Visual flowchart showing how extensions interact with backend services.
  * **Live Repository Health:** Tracks modules, contributor commits, and sync status.
* **Command:** `ByteSized: View Git Flow & Architecture Diagram`

---

### 4️⃣ Multi-People Co-Working Platform (`shared_coworking_hub/`)
* **Scope:** Real-time collaboration.
* **Key Features:**
  * WebSocket Room Manager (`/ws/{room_id}`) connecting engineers in shared sessions.
  * Synchronized code inspection, shared hardware floorplanning, and collaborative reviews.

---

## 🚀 How to Run the ByteSized Suite

### 1. Launch the Unified Backend Server
```bash
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```
*API Swagger Documentation: `http://localhost:8000/docs`*

### 2. Build the Shared Package (first time only)
```bash
cd extensions/shared
npm install
npm run compile
```

### 3. Launch the SiliconBob RTL Extension in IBM Bob IDE / VS Code
```bash
cd extensions/siliconbob-rtl
npm install
npm run compile
```
* Press **`F5`** inside IBM Bob IDE / VS Code to launch the **Extension Development Host**.
* In the host window, open any file from `test_samples/`:
  * `test_samples/alu_with_latch.v` (Tests latch inference bug)
  * `test_samples/race_condition.v` (Tests blocking race condition)
  * `test_samples/unpipelined_mult.v` (Tests PPA optimization)
* Right-click anywhere in the editor → click **"SiliconBob: Analyze & Optimize RTL"**!

---

## ➕ Adding a New Extension

Each new extension follows the same four-step pattern:

1. **Create the extension folder**
   ```bash
   cp -r extensions/2nd-ext extensions/<your-ext-name>
   ```
   Update `name`, `displayName`, and command prefixes in `extensions/<your-ext-name>/package.json`.

2. **Install the shared package**
   ```bash
   cd extensions/<your-ext-name>
   npm install        # resolves @bytesized/shared from file:../shared
   npm run compile
   ```

3. **Add your backend router**
   ```bash
   # Create backend/routers/<your_ext>/
   # Copy backend/routers/second_ext/ as a template
   ```
   Then add one line in `backend/main.py`:
   ```python
   from backend.routers.<your_ext>.router import router as your_ext_router
   app.include_router(your_ext_router)
   ```

4. **Write your feature** — add command handlers in `src/commands/`, import from `@bytesized/shared`.

---

## 🤖 How IBM Bob 2.0 Was Used
IBM Bob 2.0 was used to plan, implement, and document the 3 extensions:
* **Plan Mode:** Structured the 3-extension division of labor and backend REST contracts.
* **Agent Mode:** Assisted each developer in building AST rules, Webview canvas rendering, and WebSocket room managers.
* **Screenshots:** Detailed session evidence from each developer is stored in [`bob_sessions/`](./bob_sessions/).

---

## 👥 The ByteSized Team (Team of 6)
* **Gagan (Dev 1)** - Universal Code Checker & Optimizer Lead
* **Technical Member 2 (Dev 2)** - Microchip & PCB Visual Designer Lead
* **Technical Member 3 (Dev 3)** - Git Architecture & Flow Diagram Lead
* **Non-Technical Member 1** - Video & Presentation Lead
* **Non-Technical Member 2** - Semiconductor & Software Market Research Lead
* **Non-Technical Member 3** - Documentation & IBM Bob Compliance Lead

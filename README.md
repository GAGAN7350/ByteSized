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

### 2️⃣ Extension 2: Microchip & PCB Visual Designer (`extensions/02-chip-pcb-designer/`)
* **Developer:** Dev 2
* **Scope:** Electronic chip floorplanning, microchip block diagramming, and PCB schematics.
* **Key Features:**
  * **Component Palette:** Drag-and-drop RISC-V/ARM MCUs, 32-bit ALU cores, 64KB SRAM cache, PLL clock generators, and AXI4 bus arbiters.
  * **Interactive Canvas:** Visual block placement, pinout inspection, and interconnect routing.
  * **Hardware Netlist Exporter:** Generates netlists and pinout mappings for EDA tools with one click.
* **Command:** `ByteSized: Open Microchip & PCB Visual Designer`

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
uvicorn main:app --reload --port 8000
```
*API Swagger Documentation: `http://localhost:8000/docs`*

### 2. Testing the Extensions in IBM Bob IDE
All 3 extensions are packaged as `.vsix` files and can be installed with:
```bash
bobide --install-extension extensions/01-code-optimizer/bytesized-code-optimizer-1.0.0.vsix
bobide --install-extension extensions/02-chip-pcb-designer/bytesized-pcb-chip-designer-1.0.0.vsix
bobide --install-extension extensions/03-git-diagram-generator/bytesized-git-diagram-1.0.0.vsix
```

In **IBM Bob IDE**:
* **Extension 1:** Open any file (`.v`, `.py`, `.cpp`, `.js`) $\rightarrow$ Right-click $\rightarrow$ **"ByteSized: Check & Optimize Code"**!
* **Extension 2:** Press `Ctrl+Shift+P` $\rightarrow$ type **"ByteSized: Open Microchip & PCB Visual Designer"**!
* **Extension 3:** Press `Ctrl+Shift+P` $\rightarrow$ type **"ByteSized: View Git Flow & Architecture Diagram"**!

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

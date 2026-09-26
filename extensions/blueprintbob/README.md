# BlueprintBob: Architecture & Codebase Visualizer

> **ByteSized — Architecture Topology & Component Visualizer for IBM Bob IDE / VS Code**

BlueprintBob generates interactive, zoomable, and clickable architecture diagrams and component topologies directly from your workspace.

## Getting Started

```bash
cd extensions/blueprintbob
npm install
npm run compile
```

Press **`F5`** in IBM Bob IDE / VS Code to launch the Extension Development Host.

## Backend

BlueprintBob connects to the unified FastAPI backend at `backend/routers/blueprintbob/router.py`.  
- Health check: `GET http://localhost:8000/api/blueprintbob/health`
- Generate architecture: `POST http://localhost:8000/api/blueprintbob/generate`

## Commands

- `blueprintbob.visualizeWorkspace`: Scans the active workspace and opens the interactive BlueprintBob architecture canvas.

"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
function activate(context) {
    console.log('[ByteSized] Git Architecture & Flow Diagram Extension activated!');
    let disposable = vscode.commands.registerCommand('bytesized.generateGitDiagram', () => {
        const panel = vscode.window.createWebviewPanel('bytesizedGitDiagram', 'ByteSized: Git Architecture & Flow Studio', vscode.ViewColumn.One, {
            enableScripts: true,
            retainContextWhenHidden: true
        });
        panel.webview.html = getGitDiagramHtml();
    });
    context.subscriptions.push(disposable);
}
function getGitDiagramHtml() {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ByteSized: Git Architecture & Flow</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 24px;
            background-color: #11111b;
            color: #cdd6f4;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #313244;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }
        h1 { margin: 0; font-size: 20px; color: #89b4fa; }
        .tag { background: #313244; padding: 4px 10px; border-radius: 12px; font-size: 12px; color: #a6e3a1; }
        .section-title { font-size: 15px; color: #cba6f7; margin-bottom: 12px; font-weight: 600; }
        .card {
            background-color: #181825;
            border: 1px solid #313244;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 24px;
            overflow-x: auto;
        }
        .mermaid { display: flex; justify-content: center; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }
        .stat-box {
            background-color: #1e1e2e;
            border: 1px solid #313244;
            border-radius: 6px;
            padding: 12px 16px;
        }
        .stat-value { font-size: 22px; font-weight: bold; color: #f9e2af; }
        .stat-label { font-size: 12px; color: #a6adc8; }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>🌳 ByteSized: Git Architecture & Topology Flow</h1>
            <span style="font-size: 12px; color: #6c7086;">Repository: GAGAN7350/ByteSized (IBM Bob 2.0 Hackathon)</span>
        </div>
        <span class="tag">● Active Branch: main</span>
    </div>

    <div class="stats-grid">
        <div class="stat-box">
            <div class="stat-value">3 Extensions</div>
            <div class="stat-label">Architectural Modules Tracked</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">6 Engineers</div>
            <div class="stat-label">Active Co-working Collaborators</div>
        </div>
        <div class="stat-box">
            <div class="stat-value">100% Synced</div>
            <div class="stat-label">Git Commit Topology Health</div>
        </div>
    </div>

    <div class="section-title">📌 Git Branching & Commit Topology Graph</div>
    <div class="card">
        <div class="mermaid">
        gitGraph
            commit id: "Init Template"
            branch "dev1/code-optimizer"
            checkout "dev1/code-optimizer"
            commit id: "feat: AST Lint & Squiggles"
            commit id: "feat: Multi-lang Diff Viewer"
            checkout main
            branch "dev2/pcb-designer"
            checkout "dev2/pcb-designer"
            commit id: "feat: Chip Block Canvas"
            commit id: "feat: Netlist Exporter"
            checkout main
            branch "dev3/git-diagram"
            checkout "dev3/git-diagram"
            commit id: "feat: Git Topology Parser"
            checkout main
            merge "dev1/code-optimizer" id: "merge: Extension 1"
            merge "dev2/pcb-designer" id: "merge: Extension 2"
            merge "dev3/git-diagram" id: "merge: Extension 3"
            commit id: "ByteSized Suite v1.0"
        </div>
    </div>

    <div class="section-title">🏗️ Multi-Extension Architecture & System Flow</div>
    <div class="card">
        <div class="mermaid">
        flowchart LR
            User([Developer / Hardware Engineer]) --> BobIDE[IBM Bob IDE Workspace]
            
            subgraph "ByteSized Extension Suite"
                Ext1["Ext 1: Code Optimizer<br/>(Dev 1)"]
                Ext2["Ext 2: Microchip & PCB Designer<br/>(Dev 2)"]
                Ext3["Ext 3: Git Architecture Flow<br/>(Dev 3)"]
            end

            BobIDE --> Ext1
            BobIDE --> Ext2
            BobIDE --> Ext3

            subgraph "Backend Services"
                API["FastAPI Engine (:8000)"]
                AST["AST Linter & Optimizer"]
                WS["Multiplayer Co-Working Hub"]
            end

            Ext1 -->|POST /api/optimize-code| API
            API --> AST
            Ext2 -->|Export Netlist / SVG| API
            Ext3 -->|Git Topology Metrics| API
            Ext1 -.->|WebSocket /ws/room| WS
            Ext2 -.->|WebSocket /ws/room| WS
        </div>
    </div>

    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'dark',
            gitGraph: { mainBranchName: 'main' }
        });
    </script>
</body>
</html>`;
}
function deactivate() { }
//# sourceMappingURL=extension.js.map
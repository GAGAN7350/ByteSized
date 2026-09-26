import * as vscode from 'vscode';
import * as path from 'path';

export interface DiagramNodeData {
    id: string;
    label: string;
    type?: string;
    description?: string;
    path?: string;
    shape?: string;
    group_id?: string;
}

export interface DiagramGraphData {
    groups?: Array<{ id: string; label: string; description?: string }>;
    nodes?: DiagramNodeData[];
    edges?: Array<{ source: string; target: string; label?: string; style?: string }>;
}

export class DiagramPanel {
    public static currentPanel: DiagramPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    public static createOrShow(
        extensionUri: vscode.Uri,
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>
    ) {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (DiagramPanel.currentPanel) {
            DiagramPanel.currentPanel._panel.reveal(column);
            DiagramPanel.currentPanel.update(mermaidCode, explanation, graph, metrics);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'blueprintbobDiagram',
            'BlueprintBob: Architecture Visualizer',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
                localResourceRoots: [extensionUri]
            }
        );

        DiagramPanel.currentPanel = new DiagramPanel(panel, mermaidCode, explanation, graph, metrics);
    }

    private constructor(
        panel: vscode.WebviewPanel,
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>
    ) {
        this._panel = panel;
        this.update(mermaidCode, explanation, graph, metrics);

        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);

        this._panel.webview.onDidReceiveMessage(
            async (message) => {
                switch (message.command) {
                    case 'openFile':
                        if (message.filePath) {
                            await this._openFileInEditor(message.filePath);
                        }
                        break;
                    case 'copyMermaid':
                        if (message.text) {
                            await vscode.env.clipboard.writeText(message.text);
                            vscode.window.showInformationMessage('Mermaid diagram code copied to clipboard!');
                        }
                        break;
                    case 'showNotification':
                        vscode.window.showInformationMessage(message.text);
                        break;
                }
            },
            null,
            this._disposables
        );
    }

    private async _openFileInEditor(filePath: string) {
        try {
            let targetUri: vscode.Uri;
            if (path.isAbsolute(filePath)) {
                targetUri = vscode.Uri.file(filePath);
            } else {
                const workspaceFolders = vscode.workspace.workspaceFolders;
                if (workspaceFolders && workspaceFolders.length > 0) {
                    targetUri = vscode.Uri.joinPath(workspaceFolders[0].uri, filePath);
                } else {
                    targetUri = vscode.Uri.file(filePath);
                }
            }

            const doc = await vscode.workspace.openTextDocument(targetUri);
            await vscode.window.showTextDocument(doc, { preview: false });
        } catch (err: any) {
            vscode.window.showErrorMessage(`BlueprintBob: Unable to open file "${filePath}". ${err?.message || ''}`);
        }
    }

    public update(
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>
    ) {
        this._panel.webview.html = this._getHtmlForWebview(mermaidCode, explanation, graph, metrics);
    }

    private _getHtmlForWebview(
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>
    ): string {
        const nodesJson = JSON.stringify(graph?.nodes || []);
        const metricsJson = JSON.stringify(metrics || {});
        const safeMermaid = mermaidCode.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');
        const safeExplanation = explanation.replace(/\\/g, '\\\\').replace(/`/g, '\\`').replace(/\$/g, '\\$');

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BlueprintBob Architecture Visualizer</title>
    <style>
        :root {
            --bg-color: #0d1117;
            --panel-bg: rgba(22, 27, 34, 0.85);
            --pill-bg: rgba(30, 36, 46, 0.85);
            --border-color: rgba(255, 255, 255, 0.12);
            --accent-blue: #58a6ff;
            --accent-purple: #bc8cff;
            --accent-green: #3fb950;
            --text-main: #e6edf3;
            --text-muted: #8b949e;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            overflow: hidden;
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        /* Top Header Bar */
        .header-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 18px;
            background: var(--panel-bg);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            z-index: 10;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .brand-badge {
            font-size: 13px;
            font-weight: 700;
            letter-spacing: 0.5px;
            padding: 4px 10px;
            border-radius: 6px;
            background: linear-gradient(135deg, #1f6feb 0%, #8957e5 100%);
            color: #fff;
            text-transform: uppercase;
        }

        .header-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
        }

        .metrics-badges {
            display: flex;
            gap: 8px;
        }

        .badge {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 12px;
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
        }

        /* Canvas Area */
        #viewport {
            flex: 1;
            position: relative;
            overflow: hidden;
            cursor: grab;
            user-select: none;
            background-image: 
                radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.05) 1px, transparent 0);
            background-size: 24px 24px;
        }

        #viewport:active {
            cursor: grabbing;
        }

        #diagram-canvas {
            transform-origin: 0 0;
            position: absolute;
            top: 40px;
            left: 40px;
            transition: transform 0.05s ease-out;
        }

        /* Floating Glassmorphic Control Pill */
        .control-pill {
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            background: var(--pill-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
            z-index: 20;
        }

        .pill-btn {
            background: transparent;
            border: none;
            color: var(--text-main);
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: all 0.15s ease;
        }

        .pill-btn:hover {
            background: rgba(255, 255, 255, 0.12);
            color: #fff;
        }

        .pill-btn:active {
            transform: scale(0.96);
        }

        .pill-divider {
            width: 1px;
            height: 18px;
            background: var(--border-color);
        }

        /* Slide-over Info Drawer */
        #info-drawer {
            position: absolute;
            top: 0;
            right: 0;
            width: 360px;
            height: 100%;
            background: var(--panel-bg);
            backdrop-filter: blur(20px);
            border-left: 1px solid var(--border-color);
            transform: translateX(100%);
            transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            z-index: 30;
            display: flex;
            flex-direction: column;
            box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
        }

        #info-drawer.open {
            transform: translateX(0);
        }

        .drawer-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px;
            border-bottom: 1px solid var(--border-color);
        }

        .drawer-title {
            font-size: 15px;
            font-weight: 600;
        }

        .drawer-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 18px;
            padding: 4px 8px;
            border-radius: 4px;
        }

        .drawer-close:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.1);
        }

        .drawer-content {
            flex: 1;
            overflow-y: auto;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .field-group {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .field-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }

        .field-value {
            font-size: 13px;
            color: var(--text-main);
            word-break: break-all;
        }

        .type-badge {
            align-self: flex-start;
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 6px;
            background: rgba(88, 166, 255, 0.15);
            color: var(--accent-blue);
            border: 1px solid rgba(88, 166, 255, 0.3);
            text-transform: uppercase;
            font-weight: 600;
        }

        .btn-action {
            background: #238636;
            color: #fff;
            border: none;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            transition: background 0.15s ease;
            margin-top: 8px;
        }

        .btn-action:hover {
            background: #2ea043;
        }

        /* Explanation Drawer */
        #explanation-modal {
            position: absolute;
            top: 60px;
            left: 20px;
            max-width: 440px;
            background: var(--panel-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 18px;
            display: none;
            z-index: 25;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            font-size: 13px;
            line-height: 1.5;
        }

        #explanation-modal.open {
            display: block;
        }

        /* Mermaid Graph Styles */
        svg {
            max-width: none !important;
        }

        .node {
            cursor: pointer !important;
            transition: opacity 0.15s;
        }

        .node:hover {
            opacity: 0.85;
            filter: drop-shadow(0 0 8px rgba(88, 166, 255, 0.6));
        }

        /* Fallback Box */
        .fallback-box {
            padding: 24px;
            background: rgba(22, 27, 34, 0.95);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            max-width: 700px;
            margin: 40px auto;
        }
    </style>
</head>
<body>
    <div class="header-bar">
        <div class="header-left">
            <span class="brand-badge">BlueprintBob</span>
            <span class="header-title">Architecture Topology & Component Map</span>
        </div>
        <div class="metrics-badges" id="metrics-container"></div>
    </div>

    <div id="viewport">
        <div id="diagram-canvas">
            <div id="mermaid-target"></div>
        </div>
    </div>

    <!-- Floating Glassmorphic Control Pill -->
    <div class="control-pill">
        <button class="pill-btn" id="btn-zoom-in" title="Zoom In">＋ Zoom</button>
        <button class="pill-btn" id="btn-zoom-out" title="Zoom Out">－ Zoom</button>
        <div class="pill-divider"></div>
        <button class="pill-btn" id="btn-fit" title="Fit Screen">⛶ Fit</button>
        <button class="pill-btn" id="btn-reset" title="Reset View">↺ Reset</button>
        <div class="pill-divider"></div>
        <button class="pill-btn" id="btn-explanation" title="Architecture Overview">ℹ Insights</button>
        <button class="pill-btn" id="btn-copy" title="Copy Mermaid Code">📋 Copy Code</button>
    </div>

    <!-- Explanation Box -->
    <div id="explanation-modal">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <h4 style="font-size:14px; font-weight:600;">System Architecture Insights</h4>
            <button id="btn-close-explanation" style="background:none; border:none; color:var(--text-muted); cursor:pointer;">✕</button>
        </div>
        <div id="explanation-text" style="color:var(--text-muted);"></div>
    </div>

    <!-- Slide-over Info Drawer -->
    <div id="info-drawer">
        <div class="drawer-header">
            <span class="drawer-title" id="drawer-node-label">Component Details</span>
            <button class="drawer-close" id="btn-close-drawer">✕</button>
        </div>
        <div class="drawer-content">
            <span class="type-badge" id="drawer-node-type">Module</span>

            <div class="field-group">
                <span class="field-label">Component ID</span>
                <span class="field-value" id="drawer-node-id">-</span>
            </div>

            <div class="field-group">
                <span class="field-label">File / Target Path</span>
                <span class="field-value" id="drawer-node-path" style="font-family:monospace; font-size:12px;">-</span>
            </div>

            <div class="field-group">
                <span class="field-label">Description</span>
                <span class="field-value" id="drawer-node-desc">-</span>
            </div>

            <button class="btn-action" id="btn-open-file">
                📂 Open in Editor
            </button>
        </div>
    </div>

    <!-- Dual Loading: Mermaid CDN with Inline Fallback -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
    <script>
        const vscode = acquireVsCodeApi();
        const rawMermaid = \`${safeMermaid}\`;
        const explanationMarkdown = \`${safeExplanation}\`;
        const graphNodes = ${nodesJson};
        const metrics = ${metricsJson};

        // Render metrics badges
        const metricsContainer = document.getElementById('metrics-container');
        if (metrics.nodes_count) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.nodes_count} Nodes</span>\`;
        }
        if (metrics.edges_count) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.edges_count} Edges</span>\`;
        }
        if (metrics.scanned_files) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.scanned_files} Files Scanned</span>\`;
        }

        // Setup Explanation Modal
        document.getElementById('explanation-text').innerHTML = explanationMarkdown.replace(/\\n/g, '<br/>');
        document.getElementById('btn-explanation').addEventListener('click', () => {
            document.getElementById('explanation-modal').classList.toggle('open');
        });
        document.getElementById('btn-close-explanation').addEventListener('click', () => {
            document.getElementById('explanation-modal').classList.remove('open');
        });

        // Copy Mermaid
        document.getElementById('btn-copy').addEventListener('click', () => {
            vscode.postMessage({ command: 'copyMermaid', text: rawMermaid });
        });

        // Pan & Zoom Implementation
        let scale = 1.0;
        let panX = 40;
        let panY = 40;
        let isDragging = false;
        let startX = 0;
        let startY = 0;

        const viewport = document.getElementById('viewport');
        const canvas = document.getElementById('diagram-canvas');

        function updateTransform() {
            canvas.style.transform = \`translate(\${panX}px, \${panY}px) scale(\${scale})\`;
        }

        viewport.addEventListener('mousedown', (e) => {
            if (e.target.closest('.control-pill') || e.target.closest('#info-drawer') || e.target.closest('#explanation-modal')) {
                return;
            }
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            panX = e.clientX - startX;
            panY = e.clientY - startY;
            updateTransform();
        });

        window.addEventListener('mouseup', () => {
            isDragging = false;
        });

        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = e.deltaY < 0 ? 1.12 : 0.88;
            const newScale = Math.min(Math.max(scale * zoomFactor, 0.2), 4.0);

            // Zoom toward cursor
            const rect = viewport.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            panX = mouseX - (mouseX - panX) * (newScale / scale);
            panY = mouseY - (mouseY - panY) * (newScale / scale);
            scale = newScale;

            updateTransform();
        }, { passive: false });

        document.getElementById('btn-zoom-in').addEventListener('click', () => {
            scale = Math.min(scale * 1.2, 4.0);
            updateTransform();
        });

        document.getElementById('btn-zoom-out').addEventListener('click', () => {
            scale = Math.max(scale / 1.2, 0.2);
            updateTransform();
        });

        document.getElementById('btn-reset').addEventListener('click', () => {
            scale = 1.0;
            panX = 40;
            panY = 40;
            updateTransform();
        });

        document.getElementById('btn-fit').addEventListener('click', () => {
            const svg = document.querySelector('#mermaid-target svg');
            if (!svg) return;
            const bbox = svg.getBoundingClientRect();
            const vpRect = viewport.getBoundingClientRect();

            const widthRatio = (vpRect.width - 80) / bbox.width;
            const heightRatio = (vpRect.height - 80) / bbox.height;
            scale = Math.min(widthRatio, heightRatio, 1.5);
            panX = (vpRect.width - bbox.width * scale) / 2;
            panY = (vpRect.height - bbox.height * scale) / 2;
            updateTransform();
        });

        // Slide-over Info Drawer Logic
        const drawer = document.getElementById('info-drawer');
        const drawerLabel = document.getElementById('drawer-node-label');
        const drawerType = document.getElementById('drawer-node-type');
        const drawerId = document.getElementById('drawer-node-id');
        const drawerPath = document.getElementById('drawer-node-path');
        const drawerDesc = document.getElementById('drawer-node-desc');
        const btnOpenFile = document.getElementById('btn-open-file');

        let selectedNodePath = '';

        function showNodeDetails(nodeId) {
            // Find node in graphNodes
            const cleanId = nodeId.toLowerCase().replace(/[^a-z0-9_]/g, '_');
            const node = graphNodes.find(n => 
                n.id === nodeId || 
                n.id.toLowerCase().replace(/[^a-z0-9_]/g, '_') === cleanId
            ) || {
                id: nodeId,
                label: nodeId,
                type: 'Component',
                description: 'Component details detected from workspace structure',
                path: nodeId
            };

            drawerLabel.textContent = node.label || node.id;
            drawerType.textContent = node.type || 'module';
            drawerId.textContent = node.id;
            drawerPath.textContent = node.path || 'Workspace Component';
            drawerDesc.textContent = node.description || 'No detailed documentation provided.';

            selectedNodePath = node.path || '';
            btnOpenFile.style.display = selectedNodePath ? 'flex' : 'none';

            drawer.classList.add('open');
        }

        document.getElementById('btn-close-drawer').addEventListener('click', () => {
            drawer.classList.remove('open');
        });

        btnOpenFile.addEventListener('click', () => {
            if (selectedNodePath) {
                vscode.postMessage({ command: 'openFile', filePath: selectedNodePath });
            }
        });

        // Bridge for Mermaid click handler
        window.onNodeClick = function(nodeId) {
            showNodeDetails(nodeId);
        };

        // Render Mermaid
        function renderDiagram() {
            if (typeof mermaid !== 'undefined') {
                try {
                    mermaid.initialize({
                        startOnLoad: false,
                        theme: 'dark',
                        securityLevel: 'loose',
                        flowchart: {
                            useMaxWidth: false,
                            htmlLabels: true,
                            curve: 'basis'
                        }
                    });

                    mermaid.render('mermaid-svg-id', rawMermaid).then(({ svg }) => {
                        const target = document.getElementById('mermaid-target');
                        target.innerHTML = svg;

                        // Attach delegated click listener on rendered SVG nodes as extra bridge
                        target.addEventListener('click', (e) => {
                            const nodeElem = e.target.closest('.node');
                            if (nodeElem) {
                                const idAttr = nodeElem.id || '';
                                // Clean up id (e.g. flowchart-backend_main-123 -> backend_main)
                                const match = idAttr.match(/flowchart-([^-]+)/);
                                const foundId = match ? match[1] : idAttr;
                                if (foundId) {
                                    showNodeDetails(foundId);
                                }
                            }
                        });
                    }).catch(err => {
                        console.error('Mermaid render error:', err);
                        renderFallback();
                    });
                } catch (e) {
                    console.error('Mermaid init error:', e);
                    renderFallback();
                }
            } else {
                renderFallback();
            }
        }

        function renderFallback() {
            const target = document.getElementById('mermaid-target');
            let cardsHtml = '';
            for (const n of graphNodes) {
                cardsHtml += \`
                    <div style="background:rgba(255,255,255,0.04); border:1px solid var(--border-color); border-radius:8px; padding:12px; margin-bottom:8px; cursor:pointer;" onclick="showNodeDetails('\${n.id}')">
                        <div style="font-weight:600; color:var(--accent-blue);">\${n.label}</div>
                        <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">\${n.path || n.id}</div>
                    </div>
                \`;
            }

            target.innerHTML = \`
                <div class="fallback-box">
                    <h3 style="margin-bottom:8px; color:var(--accent-blue);">BlueprintBob Architecture Map</h3>
                    <p style="color:var(--text-muted); font-size:12px; margin-bottom:16px;">
                        Interactive topology rendered via component schema. Click any component below to view details or open in editor:
                    </p>
                    <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:12px;">
                        \${cardsHtml}
                    </div>
                </div>
            \`;
        }

        renderDiagram();
    </script>
</body>
</html>`;
    }

    public dispose() {
        DiagramPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const x = this._disposables.pop();
            if (x) {
                x.dispose();
            }
        }
    }
}

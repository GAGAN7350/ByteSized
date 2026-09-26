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

export interface KeyInfo {
    hasKey: boolean;
    provider: string;
    maskedKey: string;
    currentMode?: 'ai' | 'offline';
}

export interface DiagramMessageHandlers {
    onSaveApiKey?: (apiKey: string, provider: string) => Promise<void>;
    onClearApiKey?: () => Promise<void>;
    onSwitchEngineMode?: (mode: 'ai' | 'offline') => Promise<void>;
    onSwitchGranularity?: (granularity: 'overview' | 'detailed') => Promise<void>;
}

export class DiagramPanel {
    public static currentPanel: DiagramPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];
    private _handlers?: DiagramMessageHandlers;

    public static createOrShow(
        extensionUri: vscode.Uri,
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>,
        keyInfo?: KeyInfo,
        granularityOrHandlers?: string | DiagramMessageHandlers,
        handlers?: DiagramMessageHandlers
    ) {
        let granularity = 'detailed';
        let actualHandlers = handlers;
        if (typeof granularityOrHandlers === 'string') {
            granularity = granularityOrHandlers;
        } else if (granularityOrHandlers) {
            actualHandlers = granularityOrHandlers;
        }

        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (DiagramPanel.currentPanel) {
            DiagramPanel.currentPanel._handlers = actualHandlers;
            DiagramPanel.currentPanel._panel.reveal(column);
            DiagramPanel.currentPanel.update(mermaidCode, explanation, graph, metrics, keyInfo, granularity);
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

        DiagramPanel.currentPanel = new DiagramPanel(panel, mermaidCode, explanation, graph, metrics, keyInfo, granularity, actualHandlers);
    }

    private constructor(
        panel: vscode.WebviewPanel,
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>,
        keyInfo?: KeyInfo,
        granularity: string = 'detailed',
        handlers?: DiagramMessageHandlers
    ) {
        this._panel = panel;
        this._handlers = handlers;
        this.update(mermaidCode, explanation, graph, metrics, keyInfo, granularity);

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
                    case 'saveApiKey':
                        if (this._handlers?.onSaveApiKey) {
                            await this._handlers.onSaveApiKey(message.apiKey, message.provider);
                        }
                        break;
                    case 'clearApiKey':
                        if (this._handlers?.onClearApiKey) {
                            await this._handlers.onClearApiKey();
                        }
                        break;
                    case 'switchEngineMode':
                        if (this._handlers?.onSwitchEngineMode && message.mode) {
                            await this._handlers.onSwitchEngineMode(message.mode);
                        }
                        break;
                    case 'switchGranularity':
                        if (this._handlers?.onSwitchGranularity && message.granularity) {
                            await this._handlers.onSwitchGranularity(message.granularity);
                        }
                        break;
                }
            },
            null,
            this._disposables
        );
    }

    public openApiKeyModal() {
        this._panel.webview.postMessage({ command: 'openApiKeyModal' });
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
        metrics?: Record<string, any>,
        keyInfo?: KeyInfo,
        granularity: string = 'detailed'
    ) {
        this._panel.webview.html = this._getHtmlForWebview(mermaidCode, explanation, graph, metrics, keyInfo, granularity);
    }

    private _getHtmlForWebview(
        mermaidCode: string,
        explanation: string,
        graph?: DiagramGraphData,
        metrics?: Record<string, any>,
        keyInfo?: KeyInfo,
        granularity: string = 'detailed'
    ): string {
        const nodesJson = JSON.stringify(graph?.nodes || []);
        const metricsJson = JSON.stringify(metrics || {});
        const keyInfoJson = JSON.stringify(keyInfo || { hasKey: false, provider: 'gemini', maskedKey: '', currentMode: 'offline' });
        const mermaidJson = JSON.stringify(mermaidCode || '');
        const explanationJson = JSON.stringify(explanation || '');
        const granularityJson = JSON.stringify(granularity || 'detailed');

        const currentMode = keyInfo?.currentMode || (metrics?.engine_mode?.startsWith('byok') ? 'ai' : (keyInfo?.hasKey ? 'ai' : 'offline'));
        const isAiFallback = Boolean(
            metrics?.api_error ||
            (metrics?.engine_mode === 'offline_ast' && metrics?.generation_mode !== 'llm_byok' && (currentMode === 'ai' || keyInfo?.currentMode === 'ai' || !keyInfo || metrics?.warning))
        );

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BlueprintBob Architecture Visualizer</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap');

        :root {
            --navy:      #1B2631;
            --slate:     #4A4E69;
            --blush:     #F9AFAF;
            --off-white: #F6F6F6;
            --sand:      #F8C291;

            --bg-color:    var(--navy);
            --panel-bg:    rgba(27, 38, 49, 0.82);
            --border-color: rgba(246, 246, 246, 0.12);
            --text-main:   var(--off-white);
            --text-muted:  rgba(246, 246, 246, 0.48);

            --font-primary: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
            --font-secondary: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;
            --font-quirky: Consolas, 'JetBrains Mono', 'Courier New', monospace;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            background-color: var(--bg-color);
            color: var(--text-main);
            font-family: var(--font-primary), var(--font-secondary);
            overflow: hidden;
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        button, input, select, textarea {
            font-family: var(--font-primary), var(--font-secondary);
        }

        .brand-badge, .badge, .type-badge {
            font-family: var(--font-primary), var(--font-secondary);
        }

        .floating-toolbar, .control-pill {
            font-family: var(--font-primary), var(--font-secondary);
        }

        #info-drawer {
            font-family: var(--font-primary), var(--font-secondary);
        }

        .modal-card, #explanation-modal {
            font-family: var(--font-primary), var(--font-secondary);
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
            border-radius: 3px;
            background: var(--slate);
            color: var(--blush);
            text-transform: uppercase;
            border: 1px solid rgba(249, 175, 175, 0.25);
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
            border-radius: 3px;
            background: rgba(74, 78, 105, 0.4);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
        }

        .badge.badge-warning {
            background: rgba(248, 194, 145, 0.12);
            border: 1px solid rgba(248, 194, 145, 0.4);
            color: var(--sand);
            font-weight: 600;
        }

        /* Canvas Area */
        #viewport,
        #diagram-container,
        .diagram-container {
            flex: 1;
            position: relative;
            overflow: hidden;
            cursor: grab;
            user-select: none;
            background-image: 
                radial-gradient(circle at 1px 1px, rgba(255, 255, 255, 0.05) 1px, transparent 0);
            background-size: 24px 24px;
        }

        #viewport:active,
        #diagram-container:active {
            cursor: grabbing;
        }

        #diagram-canvas,
        #canvas,
        .canvas {
            transform-origin: 0 0;
            position: absolute;
            top: 40px;
            left: 40px;
            padding-bottom: 120px;
            transition: transform 0.05s ease-out;
        }

        #mermaid-target {
            padding-bottom: 120px;
        }

        /* Floating Glassmorphic Control Pill / Floating Toolbar */
        .floating-toolbar,
        .control-pill {
            position: absolute;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 6px 10px;
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
        }

        .pill-btn {
            background: transparent;
            border: none;
            color: var(--text-main);
            padding: 5px 10px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            transition: background 0.15s ease, color 0.15s ease;
        }

        .pill-btn:hover {
            background: rgba(246, 246, 246, 0.1);
            color: var(--off-white);
        }

        .pill-btn:active {
            background: rgba(249, 175, 175, 0.15);
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
            border-radius: 3px;
            background: rgba(249, 175, 175, 0.12);
            color: var(--blush);
            border: 1px solid rgba(249, 175, 175, 0.3);
            text-transform: uppercase;
            font-weight: 600;
        }

        .btn-action {
            background: var(--blush);
            color: var(--navy);
            border: none;
            padding: 10px 14px;
            border-radius: 3px;
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
            background: var(--sand);
        }

        /* Explanation Modal / Drawer */
        #explanation-modal {
            position: absolute;
            top: 60px;
            left: 20px;
            width: 480px;
            max-width: calc(100vw - 40px);
            max-height: calc(100vh - 140px);
            background: var(--panel-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 25;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            font-size: 13px;
            line-height: 1.5;
        }

        #explanation-modal.open {
            display: flex;
        }

        .explanation-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border-color);
            flex-shrink: 0;
            background: rgba(255, 255, 255, 0.02);
        }

        .explanation-title {
            font-size: 14px;
            font-weight: 600;
            color: var(--text-main);
            margin: 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .explanation-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 16px;
            padding: 2px 6px;
            border-radius: 4px;
            transition: all 0.15s ease;
        }

        .explanation-close:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.1);
        }

        .explanation-body,
        #explanation-text {
            flex: 1;
            overflow-y: auto;
            padding: 16px 18px 24px 18px;
            color: var(--text-main);
        }

        .explanation-body::-webkit-scrollbar,
        #explanation-text::-webkit-scrollbar {
            width: 6px;
        }

        .explanation-body::-webkit-scrollbar-track,
        #explanation-text::-webkit-scrollbar-track {
            background: transparent;
        }

        .explanation-body::-webkit-scrollbar-thumb,
        #explanation-text::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.18);
            border-radius: 4px;
        }

        .explanation-body::-webkit-scrollbar-thumb:hover,
        #explanation-text::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.32);
        }

        /* Markdown Formatted Typography & Elements */
        .md-h3 {
            font-size: 14px;
            font-weight: 600;
            color: var(--blush);
            margin: 14px 0 6px 0;
        }

        .md-h3:first-child {
            margin-top: 0;
        }

        .md-h4 {
            font-size: 13px;
            font-weight: 600;
            color: var(--sand);
            margin: 12px 0 6px 0;
        }

        .md-p {
            margin: 0 0 10px 0;
            line-height: 1.55;
            color: var(--text-main);
        }

        .md-list {
            margin: 6px 0 12px 0;
            padding-left: 0;
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .md-item {
            position: relative;
            padding-left: 14px;
            font-size: 12.5px;
            line-height: 1.5;
            color: var(--text-main);
        }

        .md-item::before {
            content: "•";
            position: absolute;
            left: 2px;
            color: var(--blush);
            font-weight: bold;
        }

        .md-subitem {
            position: relative;
            padding-left: 28px;
            font-size: 12px;
            line-height: 1.45;
            color: var(--text-muted);
        }

        .md-subitem::before {
            content: "◦";
            position: absolute;
            left: 16px;
            color: var(--sand);
            font-weight: bold;
        }

        .md-code {
            font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
            font-size: 11.5px;
            background: rgba(74, 78, 105, 0.35);
            border: 1px solid var(--border-color);
            border-radius: 3px;
            padding: 1px 5px;
            color: var(--sand);
        }

        .md-arrow {
            color: var(--sand);
            font-weight: 600;
            margin: 0 4px;
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
            filter: drop-shadow(0 0 6px rgba(249, 175, 175, 0.5));
        }

        /* Fallback Box */
        .fallback-box {
            padding: 24px;
            background: rgba(27, 38, 49, 0.95);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            max-width: 700px;
            margin: 40px auto;
        }

        /* Dual-Segment Mode Toggle & Granularity Toggle */
        .mode-toggle-pill, .granularity-toggle-pill {
            display: inline-flex;
            align-items: center;
            height: 34px;
            box-sizing: border-box;
            background: rgba(27, 38, 49, 0.6);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            padding: 2px;
            gap: 2px;
            transition: all 0.2s ease;
        }

        .granularity-toggle-pill {
            background: rgba(27, 38, 49, 0.5);
        }

        .toggle-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 4px 14px;
            height: 28px;
            box-sizing: border-box;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            white-space: nowrap !important;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
            gap: 4px;
            cursor: pointer;
            transition: background 0.15s ease, color 0.15s ease;
            user-select: none;
        }

        .toggle-btn:hover {
            color: var(--text-main);
            background: rgba(246, 246, 246, 0.08);
        }

        .toggle-btn.active {
            background: var(--blush);
            color: var(--navy);
        }

        .toggle-btn.failed {
            color: var(--sand);
            opacity: 0.85;
            border: 1px dashed rgba(248, 194, 145, 0.4);
        }

        .toggle-btn.failed:hover {
            opacity: 1;
            background: rgba(248, 194, 145, 0.12);
            color: var(--off-white);
        }

        .key-indicator-dot {
            width: 6px;
            height: 6px;
            background-color: var(--blush);
            border-radius: 50%;
            display: inline-block;
            margin-left: 3px;
        }

        /* Prominent AI Error Toast / Banner Docked Directly Beneath Header Bar */
        .ai-error-banner {
            position: relative;
            width: 100%;
            flex-shrink: 0;
            z-index: 28;
            background: rgba(27, 38, 49, 0.96);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid var(--sand);
            padding: 10px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            animation: errorSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1);
        }

        @keyframes errorSlideIn {
            from {
                opacity: 0;
                transform: translateY(-100%);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .ai-error-content {
            display: flex;
            align-items: center;
            gap: 10px;
            color: var(--sand);
            font-size: 12px;
            line-height: 1.4;
        }

        .ai-error-icon {
            font-size: 13px;
            flex-shrink: 0;
            color: var(--sand);
        }

        .btn-banner-key {
            background: rgba(248, 194, 145, 0.15);
            border: 1px solid var(--sand);
            color: var(--off-white);
            padding: 5px 12px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            white-space: nowrap;
            transition: background 0.15s ease;
        }

        .btn-banner-key:hover {
            background: rgba(248, 194, 145, 0.28);
        }

        .btn-banner-dismiss {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 14px;
            padding: 2px 6px;
        }

        .btn-banner-dismiss:hover {
            color: var(--off-white);
        }

        .modal-mode-banner {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 12px;
            border-radius: 3px;
            background: rgba(74, 78, 105, 0.3);
            border: 1px solid var(--border-color);
            font-size: 12px;
        }

        .modal-error-box {
            background: rgba(248, 194, 145, 0.1);
            border: 1px solid rgba(248, 194, 145, 0.4);
            border-radius: 3px;
            padding: 10px 14px;
            color: var(--sand);
            font-size: 12px;
            line-height: 1.45;
        }

        /* Minimal, Beautiful Modal Styles */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(0, 0, 0, 0.65);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            z-index: 2500 !important;
            overflow-y: auto;
            padding: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-card {
            background: var(--panel-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            max-height: calc(100vh - 80px);
            overflow-y: auto;
            width: 520px;
            max-width: 90vw;
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.6);
            display: flex;
            flex-direction: column;
            animation: modalFadeIn 0.18s ease-out;
        }

        @keyframes modalFadeIn {
            from { opacity: 0; transform: scale(0.96) translateY(-8px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            padding: 20px 24px 14px 24px;
            border-bottom: 1px solid var(--border-color);
        }

        .modal-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-main);
            margin-bottom: 4px;
        }

        .modal-subtitle {
            font-size: 12px;
            color: var(--text-muted);
            line-height: 1.4;
        }

        .modal-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 18px;
            padding: 4px 8px;
            border-radius: 4px;
            transition: all 0.15s;
        }

        .modal-close:hover {
            color: var(--off-white);
            background: rgba(246, 246, 246, 0.08);
        }

        .modal-body {
            padding: 20px 24px;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .form-label {
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
        }

        .provider-options {
            display: flex;
            gap: 18px;
        }

        .provider-radio {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            cursor: pointer;
            color: var(--text-main);
        }

        .provider-radio input {
            cursor: pointer;
            accent-color: var(--blush);
        }

        .input-password-wrapper {
            position: relative;
            display: flex;
            align-items: center;
        }

        .form-input {
            width: 100%;
            padding: 10px 40px 10px 12px;
            background: rgba(27, 38, 49, 0.9);
            border: 1px solid var(--border-color);
            border-radius: 3px;
            color: var(--text-main);
            font-size: 13px;
            outline: none;
            transition: border-color 0.15s;
            font-family: inherit;
        }

        .form-input:focus {
            border-color: var(--blush);
            box-shadow: 0 0 0 3px rgba(249, 175, 175, 0.18);
        }

        .btn-toggle-vis {
            position: absolute;
            right: 8px;
            background: none;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            font-size: 14px;
            padding: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn-toggle-vis:hover {
            color: var(--text-main);
        }

        .key-status-hint {
            font-size: 11px;
            margin-top: 2px;
            line-height: 1.4;
        }

        .modal-security-note {
            font-size: 12px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px 12px;
            line-height: 1.4;
        }

        .modal-actions {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 16px 24px 20px 24px;
            border-top: 1px solid var(--border-color);
            background: rgba(27, 38, 49, 0.5);
        }

        .btn-primary {
            background: var(--blush);
            color: var(--navy);
            border: none;
            padding: 9px 16px;
            border-radius: 3px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.15s ease;
        }

        .btn-primary:hover {
            background: var(--sand);
        }

        .btn-secondary {
            background: transparent;
            color: var(--sand);
            border: 1px solid rgba(248, 194, 145, 0.4);
            padding: 8px 14px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 500;
            cursor: pointer;
            transition: background 0.15s ease;
        }

        .btn-secondary:hover {
            background: rgba(248, 194, 145, 0.12);
        }

        .btn-cancel {
            background: transparent;
            color: var(--text-muted);
            border: 1px solid var(--border-color);
            padding: 8px 14px;
            border-radius: 3px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.15s ease, color 0.15s ease;
        }

        .btn-cancel:hover {
            color: var(--text-main);
            background: rgba(246, 246, 246, 0.07);
        }

        /* Loading Overlay & Pure Geometric Spinner */
        .loading-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: rgba(27, 38, 49, 0.78);
            backdrop-filter: blur(14px);
            -webkit-backdrop-filter: blur(14px);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: opacity 0.2s ease;
        }

        .loading-card {
            background: rgba(27, 38, 49, 0.88);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 28px 36px;
            display: flex;
            flex-direction: column;
            align-items: center;
            text-align: center;
            max-width: 440px;
            width: 90%;
            box-shadow: 0 16px 40px rgba(0, 0, 0, 0.5);
        }

        .blueprint-spinner {
            position: relative;
            width: 52px;
            height: 52px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .spinner-ring {
            position: absolute;
            width: 100%;
            height: 100%;
            border: 3px solid rgba(246, 246, 246, 0.08);
            border-top-color: var(--blush);
            border-right-color: var(--sand);
            border-radius: 50%;
            animation: blueprintSpin 1s cubic-bezier(0.6, 0.2, 0.4, 0.9) infinite;
        }

        .spinner-pulse {
            position: absolute;
            width: 14px;
            height: 14px;
            background: var(--blush);
            transform: rotate(45deg);
            animation: diamondPulse 1.6s ease-in-out infinite;
            border-radius: 2px;
        }

        @keyframes blueprintSpin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        @keyframes diamondPulse {
            0%, 100% {
                transform: rotate(45deg) scale(0.75);
                opacity: 0.6;
            }
            50% {
                transform: rotate(225deg) scale(1.1);
                opacity: 1;
                background: var(--sand);
            }
        }

        .loading-quirky-message {
            font-family: var(--font-quirky);
            font-size: 13px;
            font-weight: 600;
            color: var(--blush);
            margin-bottom: 6px;
            min-height: 20px;
            line-height: 1.4;
            letter-spacing: 0.2px;
            transition: opacity 0.15s ease;
        }

        .loading-subtext {
            font-size: 11px;
            color: var(--text-muted);
            letter-spacing: 0.5px;
            text-transform: uppercase;
            margin-bottom: 18px;
        }

        .loading-progress-bar {
            width: 100%;
            height: 4px;
            background: rgba(246, 246, 246, 0.08);
            border-radius: 2px;
            overflow: hidden;
            position: relative;
        }

        .progress-bar-fill {
            height: 100%;
            width: 45%;
            position: absolute;
            background: linear-gradient(90deg, var(--blush), var(--sand));
            border-radius: 2px;
            animation: progressShimmer 1.8s ease-in-out infinite;
        }

        @keyframes progressShimmer {
            0% {
                left: -45%;
            }
            50% {
                left: 40%;
                width: 60%;
            }
            100% {
                left: 100%;
                width: 45%;
            }
        }
    </style>
</head>
<body>
    <div id="loading-overlay" class="loading-overlay">
        <div class="loading-card">
            <div class="blueprint-spinner">
                <div class="spinner-ring"></div>
                <div class="spinner-pulse"></div>
            </div>
            <div id="loading-message" class="loading-quirky-message">Initializing BlueprintBob architecture engine...</div>
            <div class="loading-subtext">AST & AI Topology Synthesis</div>
            <div class="loading-progress-bar"><div class="progress-bar-fill"></div></div>
        </div>
    </div>

    <div class="header-bar" id="header-bar">
        <div class="header-left">
            <span class="brand-badge">BlueprintBob</span>
            <span class="header-title">Architecture Topology & Component Map</span>
        </div>
        <div class="metrics-badges" id="metrics-container">${isAiFallback ? `<span class="badge badge-warning">[!] Offline AST Fallback (AI Failed)</span>` : ''}</div>
    </div>

    ${metrics?.api_error ? `
    <!-- AI Error Banner -->
    <div id="ai-error-banner" class="ai-error-banner">
        <div class="ai-error-content">
            <span class="ai-error-icon">[!]</span>
            <span class="ai-error-text"><strong>AI Generation Failed:</strong> ${metrics.api_error.replace(/</g, '&lt;').replace(/>/g, '&gt;')}. Displaying Offline AST analysis.</span>
        </div>
        <div style="display:flex; align-items:center; gap:8px;">
            <button class="btn-banner-key" id="btn-banner-check-key">Check API Key</button>
            <button class="btn-banner-dismiss" id="btn-banner-dismiss" title="Dismiss">×</button>
        </div>
    </div>
    ` : ''}

    <div id="viewport" class="diagram-container" data-testid="diagram-container">
        <div id="diagram-canvas" class="canvas" data-testid="canvas">
            <div id="mermaid-target"></div>
        </div>
    </div>

    <!-- Floating Toolbar -->
    <div class="control-pill floating-toolbar" id="floating-toolbar">
        <div class="mode-toggle-pill">
            <button id="toggleOfflineBtn" class="toggle-btn ${(!isAiFallback && currentMode === 'ai') ? '' : 'active'}" title="Instant offline AST analysis (0 tokens)">Offline</button>
            <button id="toggleAiBtn" class="toggle-btn ${(!isAiFallback && currentMode === 'ai') ? 'active' : ''} ${isAiFallback ? 'failed' : ''}" title="${isAiFallback ? 'AI Generation Failed — click to configure key or retry' : 'Deep AI architectural reasoning'}">AI Mode${isAiFallback ? ' (Failed)' : ''}</button>
        </div>
        <div class="granularity-toggle-pill" title="Switch architectural granularity">
            <button id="toggleOverviewBtn" class="toggle-btn ${granularity === 'overview' ? 'active' : ''}">Overview</button>
            <button id="toggleDetailedBtn" class="toggle-btn ${granularity === 'detailed' ? 'active' : ''}">Deep Map</button>
        </div>
        <button class="pill-btn" id="btn-api-key" title="AI Engine & API Key Configuration">
            Key${keyInfo?.hasKey ? '<span class="key-indicator-dot"></span>' : ''}
        </button>
        <div class="pill-divider"></div>
        <button class="pill-btn" id="btn-zoom-in" title="Zoom In">+</button>
        <button class="pill-btn" id="btn-zoom-out" title="Zoom Out">−</button>
        <div class="pill-divider"></div>
        <button class="pill-btn" id="btn-fit" title="Fit to screen">Fit</button>
        <button class="pill-btn" id="btn-reset" title="Reset view">Reset</button>
        <div class="pill-divider"></div>
        <button class="pill-btn" id="btn-explanation" title="Architecture insights">Insights</button>
        <button class="pill-btn" id="btn-copy" title="Copy Mermaid code">Copy</button>
    </div>

    <!-- Minimal, Beautiful Modal: AI Engine & API Key -->
    <div id="apiKeyModal" class="modal-overlay" style="display: none;">
        <div class="modal-card">
            <div class="modal-header">
                <div>
                    <h3 class="modal-title">AI Engine & API Key</h3>
                    <p class="modal-subtitle">Run fully offline or bring your Gemini / OpenAI key for deep AI synthesis</p>
                </div>
                <button class="modal-close" id="btn-close-key-modal" title="Close modal">×</button>
            </div>
            <div class="modal-body">
                <div class="modal-mode-banner">
                    <span style="color:var(--text-muted);">Current Mode:</span>
                    <strong style="color:${currentMode === 'ai' ? 'var(--blush)' : 'var(--sand)'};">
                        ${currentMode === 'ai' ? 'AI Mode' : 'Offline AST Mode'}
                    </strong>
                </div>

                ${metrics?.api_error ? `
                <div class="modal-error-box">
                    <strong>Last AI Attempt Failed:</strong><br/>
                    ${metrics.api_error.replace(/</g, '&lt;').replace(/>/g, '&gt;')}
                </div>
                ` : ''}

                <div class="form-group">
                    <label class="form-label">AI Provider</label>
                    <div class="provider-options">
                        <label class="provider-radio">
                            <input type="radio" name="apiProvider" value="gemini" id="provider-gemini" checked />
                            <span class="radio-label">Google Gemini (Recommended)</span>
                        </label>
                        <label class="provider-radio">
                            <input type="radio" name="apiProvider" value="openai" id="provider-openai" />
                            <span class="radio-label">OpenAI</span>
                        </label>
                    </div>
                </div>

                <div class="form-group">
                    <label class="form-label" for="apiKeyInput">API Key</label>
                    <div class="input-password-wrapper">
                        <input
                            type="password"
                            id="apiKeyInput"
                            class="form-input"
                            placeholder="Enter API Key (e.g. AIza... or sk-...)"
                            autocomplete="off"
                            spellcheck="false"
                        />
                        <button type="button" id="btn-toggle-key-vis" class="btn-toggle-vis" title="Show/Hide API Key">[show]</button>
                    </div>
                    <div id="key-status-text" class="key-status-hint"></div>
                </div>

                <div class="modal-security-note">
                    Stored securely in your IDE's SecretStorage. Switch between AI Mode and Offline Mode anytime via the toolbar toggle without having to clear your key.
                </div>
            </div>
            <div class="modal-actions">
                <button type="button" class="btn-secondary" id="btn-clear-key">Clear Key (Use Offline Mode)</button>
                <div style="flex:1;"></div>
                <button type="button" class="btn-cancel" id="btn-cancel-key">Cancel</button>
                <button type="button" class="btn-primary" id="btn-save-key">Save & Generate with AI</button>
            </div>
        </div>
    </div>

    <!-- Explanation Modal / Drawer -->
    <div id="explanation-modal">
        <div class="explanation-header">
            <h4 class="explanation-title">System Architecture Insights</h4>
            <button id="btn-close-explanation" class="explanation-close" title="Close insights">×</button>
        </div>
        <div id="explanation-text" class="explanation-body"></div>
    </div>

    <!-- Slide-over Info Drawer -->
    <div id="info-drawer">
        <div class="drawer-header">
            <span class="drawer-title" id="drawer-node-label">Component Details</span>
            <button class="drawer-close" id="btn-close-drawer">×</button>
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
                Open in Editor
            </button>
        </div>
    </div>

    <!-- Dual Loading: Mermaid CDN with Inline Fallback -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
    <script>
        const vscode = acquireVsCodeApi();
        const rawMermaid = ${mermaidJson};
        const explanationMarkdown = ${explanationJson};
        const graphNodes = ${nodesJson};
        const metrics = ${metricsJson};
        const keyInfo = ${keyInfoJson};
        const currentGranularity = ${granularityJson};

        // Loading Overlay System
        const LOADING_MESSAGES = [
            "Initializing BlueprintBob architecture engine...",
            "Brewing fresh coffee for the AST parser...",
            "Decompiling abstract syntax trees...",
            "Consulting Gemini for high-level architectural reasoning...",
            "Untangling spaghetti code into clean subsystems...",
            "Resolving cross-module imports and dependency graphs...",
            "Loading shapes, bezier curves, and subgraph boundaries...",
            "Topological sorting in progress...",
            "Polishing nodes & applying glassmorphic styling...",
            "Almost ready! Assembling final architecture blueprint..."
        ];

        let loadingInterval = null;
        let currentMessageIndex = 0;

        function showLoading(initialText) {
            const overlay = document.getElementById('loading-overlay');
            const messageEl = document.getElementById('loading-message');
            if (!overlay || !messageEl) return;

            if (initialText) {
                messageEl.textContent = initialText;
            } else {
                messageEl.textContent = LOADING_MESSAGES[0];
            }

            overlay.style.display = 'flex';

            if (loadingInterval) {
                clearInterval(loadingInterval);
            }

            currentMessageIndex = 1;
            loadingInterval = setInterval(() => {
                if (currentMessageIndex >= LOADING_MESSAGES.length) {
                    currentMessageIndex = 0;
                }
                messageEl.style.opacity = '0';
                setTimeout(() => {
                    messageEl.textContent = LOADING_MESSAGES[currentMessageIndex];
                    messageEl.style.opacity = '1';
                    currentMessageIndex++;
                }, 150);
            }, 2200);
        }

        function hideLoading() {
            const overlay = document.getElementById('loading-overlay');
            if (loadingInterval) {
                clearInterval(loadingInterval);
                loadingInterval = null;
            }
            if (overlay) {
                overlay.style.display = 'none';
            }
        }

        // Setup API Key Modal Logic
        const apiKeyModal = document.getElementById('apiKeyModal');
        const btnApiKey = document.getElementById('btn-api-key');
        const btnCloseKeyModal = document.getElementById('btn-close-key-modal');
        const btnCancelKey = document.getElementById('btn-cancel-key');
        const btnSaveKey = document.getElementById('btn-save-key');
        const btnClearKey = document.getElementById('btn-clear-key');
        const apiKeyInput = document.getElementById('apiKeyInput');
        const btnToggleKeyVis = document.getElementById('btn-toggle-key-vis');
        const keyStatusText = document.getElementById('key-status-text');

        // Mode Toggle Buttons
        const toggleOfflineBtn = document.getElementById('toggleOfflineBtn');
        const toggleAiBtn = document.getElementById('toggleAiBtn');

        if (toggleOfflineBtn) {
            toggleOfflineBtn.addEventListener('click', () => {
                if (keyInfo.currentMode === 'offline') return;
                showLoading("Switching to Offline AST Mode...");
                vscode.postMessage({ command: 'switchEngineMode', mode: 'offline' });
            });
        }

        if (toggleAiBtn) {
            toggleAiBtn.addEventListener('click', () => {
                if (keyInfo.currentMode === 'ai' && !metrics.api_error) return;
                if (!keyInfo.hasKey) {
                    openKeyModal();
                    return;
                }
                showLoading("Consulting Gemini for high-level architectural reasoning...");
                vscode.postMessage({ command: 'switchEngineMode', mode: 'ai' });
            });
        }

        // Granularity Toggle Buttons
        const toggleOverviewBtn = document.getElementById('toggleOverviewBtn');
        const toggleDetailedBtn = document.getElementById('toggleDetailedBtn');

        if (toggleOverviewBtn) {
            toggleOverviewBtn.addEventListener('click', () => {
                if (currentGranularity === 'overview') return;
                showLoading("Synthesizing high-level architectural overview...");
                vscode.postMessage({ command: 'switchGranularity', granularity: 'overview' });
            });
        }

        if (toggleDetailedBtn) {
            toggleDetailedBtn.addEventListener('click', () => {
                if (currentGranularity === 'detailed') return;
                showLoading("Assembling deep architectural component map...");
                vscode.postMessage({ command: 'switchGranularity', granularity: 'detailed' });
            });
        }

        // Error Banner Listeners
        const btnBannerCheckKey = document.getElementById('btn-banner-check-key');
        if (btnBannerCheckKey) {
            btnBannerCheckKey.addEventListener('click', openKeyModal);
        }

        const btnBannerDismiss = document.getElementById('btn-banner-dismiss');
        if (btnBannerDismiss) {
            btnBannerDismiss.addEventListener('click', () => {
                const banner = document.getElementById('ai-error-banner');
                if (banner) banner.style.display = 'none';
            });
        }

        // Webview message listener for commands sent from extension host
        window.addEventListener('message', (event) => {
            const msg = event.data;
            if (msg && msg.command === 'openApiKeyModal') {
                openKeyModal();
            }
        });

        function updateModalState() {
            if (keyInfo.provider === 'openai') {
                document.getElementById('provider-openai').checked = true;
            } else {
                document.getElementById('provider-gemini').checked = true;
            }

            if (keyInfo.hasKey) {
                keyStatusText.innerHTML = '<span style="color: var(--blush); font-weight: 500;">[ok] Stored Key Active: <code>' + keyInfo.maskedKey + '</code></span>';
                apiKeyInput.placeholder = 'Key configured (' + keyInfo.maskedKey + ') - enter new key to replace';
                btnClearKey.style.display = 'inline-block';
            } else {
                keyStatusText.innerHTML = '<span style="color: var(--text-muted);">No custom API key configured. BlueprintBob is running with offline AST analysis.</span>';
                apiKeyInput.placeholder = 'Enter API Key (e.g. AIza... or sk-...)';
                btnClearKey.style.display = 'none';
            }
        }

        function openKeyModal() {
            updateModalState();
            apiKeyInput.value = '';
            apiKeyInput.type = 'password';
            btnToggleKeyVis.textContent = '[show]';
            apiKeyModal.style.display = 'flex';
            apiKeyInput.focus();
        }

        function closeKeyModal() {
            apiKeyModal.style.display = 'none';
        }

        btnApiKey.addEventListener('click', openKeyModal);
        btnCloseKeyModal.addEventListener('click', closeKeyModal);
        btnCancelKey.addEventListener('click', closeKeyModal);

        apiKeyModal.addEventListener('click', (e) => {
            if (e.target === apiKeyModal) {
                closeKeyModal();
            }
        });

        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && apiKeyModal.style.display === 'flex') {
                closeKeyModal();
            }
        });

        btnToggleKeyVis.addEventListener('click', () => {
            if (apiKeyInput.type === 'password') {
                apiKeyInput.type = 'text';
                btnToggleKeyVis.textContent = '[hide]';
            } else {
                apiKeyInput.type = 'password';
                btnToggleKeyVis.textContent = '[show]';
            }
        });

        apiKeyInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                btnSaveKey.click();
            }
        });

        btnSaveKey.addEventListener('click', () => {
            const enteredKey = apiKeyInput.value.trim();
            const selectedProvider = document.querySelector('input[name="apiProvider"]:checked')?.value || 'gemini';

            if (!enteredKey && !keyInfo.hasKey) {
                alert('Please enter an API Key to enable AI synthesis, or use Offline AST Mode.');
                return;
            }

            closeKeyModal();
            showLoading("Validating API key and synthesizing architecture...");
            vscode.postMessage({
                command: 'saveApiKey',
                apiKey: enteredKey,
                provider: selectedProvider
            });
        });

        btnClearKey.addEventListener('click', () => {
            closeKeyModal();
            showLoading("Switching to Offline AST Mode...");
            vscode.postMessage({
                command: 'clearApiKey'
            });
        });

        // Render metrics badges
        const metricsContainer = document.getElementById('metrics-container');
        if (${isAiFallback} && !metricsContainer.querySelector('.badge-warning')) {
            metricsContainer.innerHTML += '<span class="badge badge-warning">[!] Offline AST Fallback (AI Failed)</span>';
        }
        if (metrics.nodes_count) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.nodes_count} Nodes</span>\`;
        }
        if (metrics.edges_count) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.edges_count} Edges</span>\`;
        }
        if (metrics.scanned_files) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.scanned_files} Files Scanned</span>\`;
        }
        if (metrics.granularity) {
            metricsContainer.innerHTML += \`<span class="badge">\${metrics.granularity === 'detailed' ? 'Deep Map' : 'Overview'}</span>\`;
        }

        function escapeHtml(str) {
            return str
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        }

        function formatInline(text) {
            // Split by backtick (ASCII 96) for code spans
            var codeParts = text.split(String.fromCharCode(96));
            for (var p = 0; p < codeParts.length; p++) {
                if (p % 2 === 1) {
                    codeParts[p] = '<code class="md-code">' + escapeHtml(codeParts[p]) + '</code>';
                } else {
                    var s = escapeHtml(codeParts[p]);
                    // Bold **text**
                    var boldParts = s.split('**');
                    if (boldParts.length > 2) {
                        for (var b = 1; b < boldParts.length; b += 2) {
                            boldParts[b] = '<strong>' + boldParts[b] + '</strong>';
                        }
                        s = boldParts.join('');
                    }
                    // Arrows
                    s = s.replace(/\u2794/g, '<span class="md-arrow">&rarr;</span>');
                    s = s.replace(/->/g, '<span class="md-arrow">&rarr;</span>');
                    s = s.replace(/-&gt;/g, '<span class="md-arrow">&rarr;</span>');
                    codeParts[p] = s;
                }
            }
            return codeParts.join('');
        }

        function formatMarkdown(md) {
            if (!md || typeof md !== 'string') return '';

            var lines = md.replace(/\\r/g, '').split(String.fromCharCode(10));
            var html = [];
            var inList = false;
            var paragraphLines = [];

            function flushParagraph() {
                if (paragraphLines.length > 0) {
                    html.push('<p class="md-p">' + formatInline(paragraphLines.join(' ')) + '</p>');
                    paragraphLines = [];
                }
            }

            function flushList() {
                if (inList) {
                    html.push('</ul>');
                    inList = false;
                }
            }

            for (var i = 0; i < lines.length; i++) {
                var rawLine = lines[i];
                var trimmed = rawLine.trim();

                if (!trimmed) {
                    flushParagraph();
                    flushList();
                    continue;
                }

                // Headers
                if (trimmed.startsWith('### ')) {
                    flushParagraph();
                    flushList();
                    html.push('<h3 class="md-h3">' + formatInline(trimmed.slice(4)) + '</h3>');
                    continue;
                }
                if (trimmed.startsWith('#### ')) {
                    flushParagraph();
                    flushList();
                    html.push('<h4 class="md-h4">' + formatInline(trimmed.slice(5)) + '</h4>');
                    continue;
                }
                if (trimmed.startsWith('## ')) {
                    flushParagraph();
                    flushList();
                    html.push('<h3 class="md-h3">' + formatInline(trimmed.slice(3)) + '</h3>');
                    continue;
                }

                // Bullet lists
                var isSubItem = rawLine.startsWith('  - ') || rawLine.startsWith('    - ') || rawLine.startsWith('\\t- ') || rawLine.startsWith('  * ') || rawLine.startsWith('    * ');
                var isTopItem = !isSubItem && (trimmed.startsWith('- ') || trimmed.startsWith('* '));

                if (isSubItem) {
                    flushParagraph();
                    if (!inList) {
                        html.push('<ul class="md-list">');
                        inList = true;
                    }
                    var text = trimmed.slice(2).trim();
                    html.push('<li class="md-subitem">' + formatInline(text) + '</li>');
                    continue;
                }

                if (isTopItem) {
                    flushParagraph();
                    if (!inList) {
                        html.push('<ul class="md-list">');
                        inList = true;
                    }
                    var text = trimmed.slice(2).trim();
                    html.push('<li class="md-item">' + formatInline(text) + '</li>');
                    continue;
                }

                // Regular paragraph
                flushList();
                paragraphLines.push(trimmed);
            }

            flushParagraph();
            flushList();

            return html.join(String.fromCharCode(10));
        }

        // Setup Explanation Modal
        document.getElementById('explanation-text').innerHTML = formatMarkdown(explanationMarkdown);
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

        // Pan & Zoom Implementation with Boundary Clamping
        let scale = 1.0;
        let panX = 40;
        let panY = 40;
        let isDragging = false;
        let startX = 0;
        let startY = 0;

        const viewport = document.getElementById('viewport');
        const canvas = document.getElementById('diagram-canvas');

        function updateTransform() {
            canvas.style.transform = 'translate(' + panX + 'px, ' + panY + 'px) scale(' + scale + ')';
        }

        function clampPan(x, y, currentScale) {
            const svg = document.querySelector('#mermaid-target svg');
            let contentW = 800;
            let contentH = 600;

            if (svg) {
                try {
                    const bbox = svg.getBBox();
                    if (bbox && bbox.width > 0 && bbox.height > 0) {
                        contentW = bbox.width;
                        contentH = bbox.height;
                    } else if (svg.clientWidth && svg.clientHeight) {
                        contentW = svg.clientWidth;
                        contentH = svg.clientHeight;
                    }
                } catch (e) {
                    if (svg.clientWidth && svg.clientHeight) {
                        contentW = svg.clientWidth;
                        contentH = svg.clientHeight;
                    }
                }
            }

            const vpW = viewport ? (viewport.clientWidth || window.innerWidth) : window.innerWidth;
            const vpH = viewport ? (viewport.clientHeight || window.innerHeight) : window.innerHeight;

            const scaledW = contentW * currentScale;
            const scaledH = contentH * currentScale;

            const bufferX = Math.max(140, vpW * 0.25);
            const bufferY = Math.max(100, vpH * 0.2);

            const minX = Math.min(40, vpW - scaledW - 40) - bufferX;
            const maxX = Math.max(40, vpW - scaledW - 40) + bufferX;
            const minY = Math.min(40, vpH - scaledH - 120) - bufferY;
            const maxY = Math.max(40, vpH - scaledH - 120) + bufferY;

            return {
                x: Math.min(Math.max(x, minX), maxX),
                y: Math.min(Math.max(y, minY), maxY)
            };
        }

        viewport.addEventListener('mousedown', (e) => {
            if (e.target.closest('.control-pill') || e.target.closest('.floating-toolbar') || e.target.closest('#info-drawer') || e.target.closest('#explanation-modal')) {
                return;
            }
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
        });

        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            const clamped = clampPan(e.clientX - startX, e.clientY - startY, scale);
            panX = clamped.x;
            panY = clamped.y;
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

            const rawX = mouseX - (mouseX - panX) * (newScale / scale);
            const rawY = mouseY - (mouseY - panY) * (newScale / scale);
            const clamped = clampPan(rawX, rawY, newScale);
            panX = clamped.x;
            panY = clamped.y;
            scale = newScale;

            updateTransform();
        }, { passive: false });

        document.getElementById('btn-zoom-in').addEventListener('click', () => {
            const newScale = Math.min(scale * 1.2, 4.0);
            const clamped = clampPan(panX, panY, newScale);
            panX = clamped.x;
            panY = clamped.y;
            scale = newScale;
            updateTransform();
        });

        document.getElementById('btn-zoom-out').addEventListener('click', () => {
            const newScale = Math.max(scale / 1.2, 0.2);
            const clamped = clampPan(panX, panY, newScale);
            panX = clamped.x;
            panY = clamped.y;
            scale = newScale;
            updateTransform();
        });

        document.getElementById('btn-reset').addEventListener('click', () => {
            const newScale = 1.0;
            const clamped = clampPan(40, 40, newScale);
            panX = clamped.x;
            panY = clamped.y;
            scale = newScale;
            updateTransform();
        });

        document.getElementById('btn-fit').addEventListener('click', () => {
            const svg = document.querySelector('#mermaid-target svg');
            if (!svg) return;
            let bboxW = 800;
            let bboxH = 600;
            try {
                const bbox = svg.getBBox();
                if (bbox && bbox.width > 0 && bbox.height > 0) {
                    bboxW = bbox.width;
                    bboxH = bbox.height;
                } else {
                    const r = svg.getBoundingClientRect();
                    bboxW = r.width || 800;
                    bboxH = r.height || 600;
                }
            } catch (e) {
                const r = svg.getBoundingClientRect();
                bboxW = r.width || 800;
                bboxH = r.height || 600;
            }

            const vpRect = viewport.getBoundingClientRect();

            // Include 100px bottom margin for the floating toolbar so nodes are never hidden
            const toolbarMargin = 100;
            const effectiveBboxHeight = bboxH + toolbarMargin;
            const widthRatio = (vpRect.width - 80) / bboxW;
            const heightRatio = (vpRect.height - 80) / effectiveBboxHeight;
            const newScale = Math.min(widthRatio, heightRatio, 1.5);
            const rawX = (vpRect.width - bboxW * newScale) / 2;
            const rawY = (vpRect.height - toolbarMargin - bboxH * newScale) / 2;
            const clamped = clampPan(rawX, rawY, newScale);
            panX = clamped.x;
            panY = clamped.y;
            scale = newScale;
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
            showLoading();
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

                        const clamped = clampPan(panX, panY, scale);
                        panX = clamped.x;
                        panY = clamped.y;
                        updateTransform();

                        hideLoading();

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
            hideLoading();
            const target = document.getElementById('mermaid-target');
            let cardsHtml = '';
            for (const n of graphNodes) {
                cardsHtml += \`
                    <div style="background:rgba(255,255,255,0.04); border:1px solid var(--border-color); border-radius:8px; padding:12px; margin-bottom:8px; cursor:pointer;" onclick="showNodeDetails('\${n.id}')">
                        <div style="font-weight:600; color:var(--blush);">\${n.label}</div>
                        <div style="font-size:11px; color:var(--text-muted); margin-top:4px;">\${n.path || n.id}</div>
                    </div>
                \`;
            }

            target.innerHTML = \`
                <div class="fallback-box">
                    <h3 style="margin-bottom:8px; color:var(--blush);">BlueprintBob Architecture Map</h3>
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

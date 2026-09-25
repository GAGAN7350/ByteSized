"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = require("vscode");
let diagnosticCollection;
let activeSocket = null;
let statusBarItem;
function activate(context) {
    console.log('[SiliconBob] Hardware Engineering Extension activated in IBM Bob IDE!');
    // 1. Initialize Diagnostic Collection for squiggles in the editor gutter
    diagnosticCollection = vscode.languages.createDiagnosticCollection('siliconbob');
    context.subscriptions.push(diagnosticCollection);
    // 2. Initialize Status Bar Item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = "$(chip) SiliconBob: Ready";
    statusBarItem.tooltip = "Click to Analyze and Optimize RTL";
    statusBarItem.command = "siliconbob.optimizeRTL";
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);
    // 3. Register Command: siliconbob.optimizeRTL
    const optimizeCmd = vscode.commands.registerCommand('siliconbob.optimizeRTL', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('SiliconBob: Open a Verilog (.v / .sv) file first.');
            return;
        }
        const document = editor.document;
        const code = document.getText();
        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get('backendUrl', 'http://localhost:8000');
        statusBarItem.text = "$(sync~spin) SiliconBob: Analyzing RTL...";
        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "SiliconBob: Running AST Linting & RTL Optimization...",
            cancellable: false
        }, async () => {
            try {
                const response = await fetch(`${backendUrl}/api/optimize-rtl`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        verilog_code: code,
                        file_path: document.fileName,
                        target: "ppa"
                    })
                });
                if (!response.ok) {
                    throw new Error(`Server returned HTTP ${response.status}`);
                }
                const data = await response.json();
                // Clear previous diagnostics for this document
                diagnosticCollection.delete(document.uri);
                // Add squiggles to the editor
                const diagnostics = [];
                for (const issue of data.issues) {
                    const lineIdx = Math.max(0, issue.line - 1);
                    const range = new vscode.Range(lineIdx, 0, lineIdx, 100);
                    const severity = issue.severity === 'error'
                        ? vscode.DiagnosticSeverity.Error
                        : vscode.DiagnosticSeverity.Warning;
                    const diag = new vscode.Diagnostic(range, `[${issue.rule_id}] ${issue.message}`, severity);
                    diag.source = 'SiliconBob';
                    diagnostics.push(diag);
                }
                diagnosticCollection.set(document.uri, diagnostics);
                // Open Side-by-Side Diff View
                const originalUri = document.uri;
                const optimizedDoc = await vscode.workspace.openTextDocument({
                    content: data.optimized_code,
                    language: 'verilog'
                });
                await vscode.commands.executeCommand('vscode.diff', originalUri, optimizedDoc.uri, `SiliconBob: ${document.fileName.split(/[\\/]/).pop()} (Original ↔ Optimized)`);
                statusBarItem.text = `$(check) SiliconBob: ${data.issues.length} Resolved`;
                vscode.window.showInformationMessage(`SiliconBob: Resolved ${data.issues.length} hardware issue(s)! Power: ${data.metrics.power_efficiency} | Timing: ${data.metrics.timing_slack}`);
            }
            catch (err) {
                statusBarItem.text = "$(alert) SiliconBob: Backend Offline";
                vscode.window.showErrorMessage(`SiliconBob Connection Error: Could not connect to backend at ${backendUrl}. Ensure 'uvicorn main:app' is running on port 8000.`);
            }
        });
    });
    context.subscriptions.push(optimizeCmd);
    // 4. Register Command: siliconbob.connectWorkspace (Multi-Engineer Room)
    const connectCmd = vscode.commands.registerCommand('siliconbob.connectWorkspace', async () => {
        const roomId = await vscode.window.showInputBox({
            prompt: "Enter Hardware Collaboration Room ID",
            placeHolder: "soc-core-alu",
            value: "soc-core-alu"
        });
        if (!roomId)
            return;
        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get('backendUrl', 'http://localhost:8000');
        const wsUrl = backendUrl.replace(/^http/, 'ws') + `/ws/${roomId}`;
        statusBarItem.text = `$(broadcast) SiliconBob: Connected (#${roomId})`;
        vscode.window.showInformationMessage(`SiliconBob: Connected to collaborative hardware room #${roomId} on ${wsUrl}`);
    });
    context.subscriptions.push(connectCmd);
}
function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}
//# sourceMappingURL=extension.js.map
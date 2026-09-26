import * as vscode from 'vscode';

let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('[ByteSized] Universal Code Checker & Optimizer activated in IBM Bob IDE!');

    // 1. Diagnostic Collection for in-editor squiggles across all languages
    diagnosticCollection = vscode.languages.createDiagnosticCollection('bytesized-optimizer');
    context.subscriptions.push(diagnosticCollection);

    // 2. Status Bar Item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.text = "$(zap) ByteSized: Optimizer Ready";
    statusBarItem.tooltip = "Click to Check & Optimize Code in any language";
    statusBarItem.command = "bytesized.optimizeCode";
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // 3. Command: bytesized.optimizeCode
    const optimizeCmd = vscode.commands.registerCommand('bytesized.optimizeCode', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('ByteSized: Open any source code file first.');
            return;
        }

        const document = editor.document;
        const code = document.getText();
        const languageId = document.languageId;
        const config = vscode.workspace.getConfiguration('bytesized');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');

        statusBarItem.text = `$(sync~spin) ByteSized: Optimizing ${languageId}...`;

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `ByteSized: Analyzing & Optimizing ${languageId.toUpperCase()} Code...`,
            cancellable: false
        }, async () => {
            try {
                const response = await fetch(`${backendUrl}/api/optimize-code`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        code: code,
                        language: languageId,
                        file_path: document.fileName
                    })
                });

                if (!response.ok) {
                    throw new Error(`Server returned HTTP ${response.status}`);
                }

                const data: any = await response.json();

                // Clear previous squiggles for this document
                diagnosticCollection.delete(document.uri);

                // Add squiggles to the editor
                const diagnostics: vscode.Diagnostic[] = [];
                for (const issue of data.issues) {
                    const lineIdx = Math.max(0, issue.line - 1);
                    const range = new vscode.Range(lineIdx, 0, lineIdx, 100);
                    const severity = issue.severity === 'error'
                        ? vscode.DiagnosticSeverity.Error
                        : vscode.DiagnosticSeverity.Warning;

                    const diag = new vscode.Diagnostic(range, `[${issue.rule_id}] ${issue.message}`, severity);
                    diag.source = 'ByteSized Optimizer';
                    diagnostics.push(diag);
                }
                diagnosticCollection.set(document.uri, diagnostics);

                // Open Side-by-Side Diff View
                const originalUri = document.uri;
                const optimizedDoc = await vscode.workspace.openTextDocument({
                    content: data.optimized_code,
                    language: languageId
                });

                await vscode.commands.executeCommand(
                    'vscode.diff',
                    originalUri,
                    optimizedDoc.uri,
                    `ByteSized: ${document.fileName.split(/[\\/]/).pop()} (${languageId} Original ↔ Optimized)`
                );

                statusBarItem.text = `$(check) ByteSized: ${data.issues.length} Resolved`;
                vscode.window.showInformationMessage(
                    `ByteSized: Resolved ${data.issues.length} issue(s)! ${data.summary || ''}`
                );

            } catch (err: any) {
                statusBarItem.text = "$(alert) ByteSized: Backend Offline";
                vscode.window.showErrorMessage(
                    `ByteSized Error: Could not connect to backend at ${backendUrl}. Ensure uvicorn is running.`
                );
            }
        });
    });
    context.subscriptions.push(optimizeCmd);

    // 4. Command: bytesized.joinRoom (Multi-engineer co-working)
    const joinCmd = vscode.commands.registerCommand('bytesized.joinRoom', async () => {
        const roomId = await vscode.window.showInputBox({
            prompt: "Enter Team Co-Working Room ID",
            placeHolder: "sprint-alpha",
            value: "sprint-alpha"
        });

        if (!roomId) return;
        statusBarItem.text = `$(broadcast) ByteSized: Connected (#${roomId})`;
        vscode.window.showInformationMessage(`ByteSized: Joined collaborative room #${roomId}`);
    });
    context.subscriptions.push(joinCmd);
}

export function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

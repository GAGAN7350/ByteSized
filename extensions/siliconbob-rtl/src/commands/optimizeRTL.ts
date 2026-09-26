import * as vscode from 'vscode';
import { postJson } from '@bytesized/shared';

interface RTLIssue {
    line: number;
    column: number;
    severity: string;
    message: string;
    rule_id: string;
}

interface OptimizeResponse {
    status: string;
    issues: RTLIssue[];
    optimized_code: string;
    metrics: { power_efficiency: string; timing_slack: string; [key: string]: string };
}

export function registerOptimizeRTL(
    context: vscode.ExtensionContext,
    diagnosticCollection: vscode.DiagnosticCollection,
    statusBarItem: vscode.StatusBarItem
): void {
    const cmd = vscode.commands.registerCommand('siliconbob.optimizeRTL', async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('SiliconBob: Open a Verilog (.v / .sv) file first.');
            return;
        }

        const document = editor.document;
        const code = document.getText();
        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');

        statusBarItem.text = "$(sync~spin) SiliconBob: Analyzing RTL...";

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: "SiliconBob: Running AST Linting & RTL Optimization...",
            cancellable: false
        }, async () => {
            try {
                const data = await postJson<OptimizeResponse>(
                    `${backendUrl}/api/optimize-rtl`,
                    { verilog_code: code, file_path: document.fileName, target: "ppa" }
                );

                // Clear previous diagnostics and add squiggles
                diagnosticCollection.delete(document.uri);
                const diagnostics: vscode.Diagnostic[] = data.issues.map(issue => {
                    const lineIdx = Math.max(0, issue.line - 1);
                    const range = new vscode.Range(lineIdx, 0, lineIdx, 100);
                    const severity = issue.severity === 'error'
                        ? vscode.DiagnosticSeverity.Error
                        : vscode.DiagnosticSeverity.Warning;
                    const diag = new vscode.Diagnostic(range, `[${issue.rule_id}] ${issue.message}`, severity);
                    diag.source = 'SiliconBob';
                    return diag;
                });
                diagnosticCollection.set(document.uri, diagnostics);

                // Open Side-by-Side Diff View
                const optimizedDoc = await vscode.workspace.openTextDocument({
                    content: data.optimized_code,
                    language: 'verilog'
                });
                await vscode.commands.executeCommand(
                    'vscode.diff',
                    document.uri,
                    optimizedDoc.uri,
                    `SiliconBob: ${document.fileName.split(/[\\/]/).pop()} (Original ↔ Optimized)`
                );

                statusBarItem.text = `$(check) SiliconBob: ${data.issues.length} Resolved`;
                vscode.window.showInformationMessage(
                    `SiliconBob: Resolved ${data.issues.length} hardware issue(s)! Power: ${data.metrics.power_efficiency} | Timing: ${data.metrics.timing_slack}`
                );

            } catch (err: any) {
                statusBarItem.text = "$(alert) SiliconBob: Backend Offline";
                vscode.window.showErrorMessage(
                    `SiliconBob Connection Error: Could not connect to backend at ${backendUrl}. Ensure 'uvicorn backend.main:app' is running on port 8000.`
                );
            }
        });
    });

    context.subscriptions.push(cmd);
}

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
    const handleOptimize = async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('SiliconBob: Open any code file first.');
            return;
        }

        const document = editor.document;
        const code = document.getText();
        const languageId = document.languageId;
        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');

        statusBarItem.text = `$(sync~spin) SiliconBob: Analyzing ${languageId}...`;

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `SiliconBob: Analyzing & Optimizing ${languageId.toUpperCase()} Code...`,
            cancellable: false
        }, async () => {
            try {
                const data = await postJson<OptimizeResponse>(
                    `${backendUrl}/api/optimize-rtl`,
                    {
                        code: code,
                        verilog_code: code,
                        language: languageId,
                        file_path: document.fileName,
                        target: "ppa"
                    }
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

                // Open Side-by-Side Diff View in the document's language
                const optimizedDoc = await vscode.workspace.openTextDocument({
                    content: data.optimized_code,
                    language: languageId
                });
                await vscode.commands.executeCommand(
                    'vscode.diff',
                    document.uri,
                    optimizedDoc.uri,
                    `SiliconBob: ${document.fileName.split(/[\\/]/).pop()} (${languageId} Original ↔ Optimized)`
                );

                statusBarItem.text = `$(check) SiliconBob: ${data.issues.length} Resolved`;
                const metricDetails = Object.entries(data.metrics || {})
                    .filter(([k]) => k !== 'violations_fixed')
                    .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
                    .join(' | ');

                vscode.window.showInformationMessage(
                    `SiliconBob: Resolved ${data.issues.length} ${languageId} issue(s)! ${metricDetails}`
                );

            } catch (err: any) {
                statusBarItem.text = "$(alert) SiliconBob: Backend Offline";
                vscode.window.showErrorMessage(
                    `SiliconBob Connection Error: Could not connect to backend at ${backendUrl}. Ensure 'uvicorn backend.main:app' is running on port 8000.`
                );
            }
        });
    };

    const cmd1 = vscode.commands.registerCommand('siliconbob.optimizeCode', handleOptimize);
    const cmd2 = vscode.commands.registerCommand('siliconbob.optimizeRTL', handleOptimize);

    context.subscriptions.push(cmd1, cmd2);
}

import * as vscode from 'vscode';
import { postJson } from '../shared';

export interface RTLIssue {
    line: number;
    column: number;
    severity: string;
    message: string;
    rule_id: string;
    fixed_line?: string | null;
}

export interface SiliconBobDiagData {
    rule_id: string;
    fixed_line: string | null;
    line: number;
}

export const diagDataMap = new WeakMap<vscode.Diagnostic, SiliconBobDiagData>();

interface OptimizeResponse {
    status: string;
    issues: RTLIssue[];
    optimized_code: string;
    metrics: { power_efficiency: string; timing_slack: string; [key: string]: string };
}

/**
 * TextDocumentContentProvider for displaying virtual read-only optimized files in diff views.
 */
class SiliconBobContentProvider implements vscode.TextDocumentContentProvider {
    private contentMap = new Map<string, string>();
    private onDidChangeEmitter = new vscode.EventEmitter<vscode.Uri>();
    public onDidChange = this.onDidChangeEmitter.event;

    public update(uri: vscode.Uri, content: string): void {
        this.contentMap.set(uri.toString(), content);
        this.onDidChangeEmitter.fire(uri);
    }

    public provideTextDocumentContent(uri: vscode.Uri): string {
        return this.contentMap.get(uri.toString()) || '';
    }
}

export function registerOptimizeRTL(
    context: vscode.ExtensionContext,
    diagnosticCollection: vscode.DiagnosticCollection,
    statusBarItem: vscode.StatusBarItem
): void {
    const provider = new SiliconBobContentProvider();
    const providerRegistration = vscode.workspace.registerTextDocumentContentProvider('siliconbob-optimized', provider);
    context.subscriptions.push(providerRegistration);

    async function runAnalysis(
        document: vscode.TextDocument,
        options: { silent?: boolean } = {}
    ): Promise<void> {
        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        const languageId = document.languageId;
        const fileName = document.fileName.split(/[\\/]/).pop() || 'code';

        statusBarItem.text = `$(sync~spin) SiliconBob: Analyzing ${languageId}...`;

        const run = async () => {
            const code = document.getText();
            const data = await postJson<OptimizeResponse>(
                `${backendUrl}/api/optimize-code`,
                {
                    code,
                    verilog_code: code,
                    language: languageId,
                    file_path: document.fileName,
                    target: 'ppa'
                }
            );

            diagnosticCollection.delete(document.uri);
            const diagnostics: vscode.Diagnostic[] = data.issues.map(issue => {
                const lineIdx = Math.max(0, issue.line - 1);
                const range = new vscode.Range(lineIdx, 0, lineIdx, 100);
                const severity = issue.severity === 'error'
                    ? vscode.DiagnosticSeverity.Error
                    : vscode.DiagnosticSeverity.Warning;
                const diag = new vscode.Diagnostic(range, `[${issue.rule_id}] ${issue.message}`, severity);
                diag.source = 'SiliconBob';
                diagDataMap.set(diag, {
                    rule_id: issue.rule_id,
                    fixed_line: issue.fixed_line ?? null,
                    line: issue.line
                });
                return diag;
            });
            diagnosticCollection.set(document.uri, diagnostics);

            const optimizedUri = vscode.Uri.parse(`siliconbob-optimized://siliconbob/${fileName}`);
            provider.update(optimizedUri, data.optimized_code);

            if (!options.silent) {
                try {
                    await vscode.commands.executeCommand(
                        'vscode.diff',
                        document.uri,
                        optimizedUri,
                        `${fileName} (Original ↔ SiliconBob Optimized)`,
                        { viewColumn: vscode.ViewColumn.Beside, preview: false }
                    );
                } catch (diffErr) {
                    console.error('[SiliconBob] vscode.diff error:', diffErr);
                    const doc = await vscode.workspace.openTextDocument(optimizedUri);
                    await vscode.window.showTextDocument(doc, { viewColumn: vscode.ViewColumn.Beside, preview: false });
                }
            }

            statusBarItem.text = `$(check) SiliconBob: ${data.issues.length} Resolved`;

            if (options.silent) {
                return;
            }

            const metricDetails = Object.entries(data.metrics || {})
                .filter(([k]) => k !== 'violations_fixed')
                .map(([k, v]) => `${k.replace(/_/g, ' ')}: ${v}`)
                .join(' | ');

            const choice = await vscode.window.showInformationMessage(
                `SiliconBob: Resolved ${data.issues.length} ${languageId} issue(s)! ${metricDetails}`,
                'Apply to Current File',
                'Open in New Tab'
            );

            if (choice === 'Apply to Current File') {
                const edit = new vscode.WorkspaceEdit();
                const fullRange = new vscode.Range(
                    document.positionAt(0),
                    document.positionAt(document.getText().length)
                );
                edit.replace(document.uri, fullRange, data.optimized_code);
                await vscode.workspace.applyEdit(edit);
                vscode.window.showInformationMessage(`SiliconBob: Optimized code applied to ${fileName}! (Undo with Ctrl+Z)`);
            } else if (choice === 'Open in New Tab') {
                const untitledDoc = await vscode.workspace.openTextDocument({
                    content: data.optimized_code,
                    language: languageId
                });
                await vscode.window.showTextDocument(untitledDoc, { viewColumn: vscode.ViewColumn.Beside, preview: false });
            }
        };

        try {
            await (async () => {
                if (options.silent) {
                    return await run();
                }
                return await vscode.window.withProgress({
                    location: vscode.ProgressLocation.Notification,
                    title: `SiliconBob: Analyzing & Optimizing ${languageId.toUpperCase()} Code...`,
                    cancellable: false
                }, async () => run());
            })();
        } catch (err: any) {
            statusBarItem.text = '$(alert) SiliconBob: Backend Offline';
            vscode.window.showErrorMessage(
                `SiliconBob Connection Error: Could not connect to backend at ${backendUrl}. Ensure 'uvicorn backend.main:app' is running on port 8000.`
            );
            console.error('[SiliconBob] Backend request failed', err);
        }
    }

    const handleOptimize = async () => {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('SiliconBob: Open any code file first.');
            return;
        }

        await runAnalysis(editor.document, { silent: false });
    };

    const supportedLanguageIds = new Set([
        'python', 'javascript', 'typescript', 'cpp', 'c', 'java', 'go', 'rust', 'verilog', 'systemverilog'
    ]);

    const onDidSave = vscode.workspace.onDidSaveTextDocument(async (document) => {
        const config = vscode.workspace.getConfiguration('siliconbob');
        if (!config.get<boolean>('lintOnSave', true)) {
            return;
        }
        if (!supportedLanguageIds.has(document.languageId)) {
            return;
        }

        await runAnalysis(document, { silent: true });
    });
    context.subscriptions.push(onDidSave);

    const cmd1 = vscode.commands.registerCommand('siliconbob.optimizeCode', handleOptimize);
    const cmd2 = vscode.commands.registerCommand('siliconbob.optimizeRTL', handleOptimize);

    context.subscriptions.push(cmd1, cmd2);
}

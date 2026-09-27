import * as vscode from 'vscode';
import { diagDataMap } from './optimizeRTL';

/**
 * SiliconBobCodeActionProvider
 *
 * Adds a 💡 lightbulb to every SiliconBob squiggle that has a deterministic fix.
 * Two code actions are offered per issue:
 *   1. Apply Fix   — WorkspaceEdit replaces the flagged line immediately.
 *   2. Preview Fix — vscode.diff showing only that single-line change.
 */
export class SiliconBobCodeActionProvider implements vscode.CodeActionProvider {
    provideCodeActions(
        document: vscode.TextDocument,
        _range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        for (const diag of context.diagnostics) {
            if (diag.source !== 'SiliconBob') { continue; }

            const data = diagDataMap.get(diag);
            if (!data || data.fixed_line === null) { continue; }

            const { rule_id, fixed_line, line } = data;
            const lineIdx = Math.max(0, line - 1);

            // ── Action 1: Apply Fix immediately ──────────────────────────
            const applyAction = new vscode.CodeAction(
                `SiliconBob: Apply Fix — ${rule_id}`,
                vscode.CodeActionKind.QuickFix
            );
            applyAction.diagnostics = [diag];
            applyAction.isPreferred = true;

            const edit = new vscode.WorkspaceEdit();
            const lineRange = document.lineAt(lineIdx).rangeIncludingLineBreak;
            // Normalise trailing newline — fixed_line may be multi-line (e.g. RTL-002)
            const fixText = fixed_line.endsWith('\n') ? fixed_line : fixed_line + '\n';
            edit.replace(document.uri, lineRange, fixText);
            applyAction.edit = edit;
            actions.push(applyAction);

            // ── Action 2: Preview Fix in diff view ───────────────────────
            const previewAction = new vscode.CodeAction(
                `SiliconBob: Preview Fix — ${rule_id}`,
                vscode.CodeActionKind.Empty
            );
            previewAction.diagnostics = [diag];
            previewAction.command = {
                command: 'siliconbob.previewFix',
                title: 'Preview Fix',
                arguments: [document.uri, lineIdx, fixed_line]
            };
            actions.push(previewAction);
        }

        return actions;
    }
}

/**
 * Register the CodeActionProvider and the siliconbob.previewFix command.
 */
export function registerCodeActions(
    context: vscode.ExtensionContext
): void {
    // Supported language selectors (mirrors activationEvents in package.json)
    const SUPPORTED_LANGS = [
        'verilog', 'systemverilog',
        'python',
        'c', 'cpp',
        'javascript', 'typescript',
        'java',
        'go',
        'rust'
    ];

    context.subscriptions.push(
        vscode.languages.registerCodeActionsProvider(
            SUPPORTED_LANGS.map(language => ({ language })),
            new SiliconBobCodeActionProvider(),
            { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix, vscode.CodeActionKind.Empty] }
        )
    );

    // siliconbob.previewFix — opens a single-fix diff view
    context.subscriptions.push(
        vscode.commands.registerCommand(
            'siliconbob.previewFix',
            async (originalUri: vscode.Uri, lineIdx: number, fixedLine: string) => {
                const originalDoc = await vscode.workspace.openTextDocument(originalUri);
                const originalLines = originalDoc.getText().split('\n');

                // Splice only the fixed line(s); everything else stays as-is
                const patchedLines = [...originalLines];
                const fixLines = fixedLine.split('\n');
                patchedLines.splice(lineIdx, 1, ...fixLines);

                const patchedDoc = await vscode.workspace.openTextDocument({
                    content: patchedLines.join('\n'),
                    language: originalDoc.languageId
                });

                const fileName = originalUri.path.split('/').pop() ?? 'file';
                await vscode.commands.executeCommand(
                    'vscode.diff',
                    originalUri,
                    patchedDoc.uri,
                    `SiliconBob Fix Preview: ${fileName} (Original ↔ Fixed)`
                );
            }
        )
    );
}

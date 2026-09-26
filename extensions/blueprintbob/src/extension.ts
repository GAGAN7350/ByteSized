import * as vscode from 'vscode';
import { createStatusBar, postJson } from './shared';
import { scanWorkspace } from './workspaceScanner';
import { DiagramPanel, DiagramGraphData } from './diagramPanel';

let statusBarItem: vscode.StatusBarItem;

interface BlueprintBobResponse {
    status: string;
    mermaid_code: string;
    explanation: string;
    graph?: DiagramGraphData;
    metrics?: Record<string, any>;
}

export function activate(context: vscode.ExtensionContext) {
    console.log('[BlueprintBob] Extension activated in IBM Bob IDE / VS Code!');

    // Status Bar Item
    statusBarItem = createStatusBar("$(project) BlueprintBob: Ready", "blueprintbob.visualizeWorkspace", 90);
    statusBarItem.tooltip = "Click to visualize workspace architecture (BlueprintBob)";
    context.subscriptions.push(statusBarItem);

    const visualizeHandler = async () => {
        try {
            await vscode.window.withProgress(
                {
                    location: vscode.ProgressLocation.Notification,
                    title: "BlueprintBob: Generating Architecture Diagram...",
                    cancellable: false
                },
                async (progress) => {
                    progress.report({ increment: 20, message: "Scanning workspace files and manifests..." });
                    const scanned = await scanWorkspace();

                    if (!scanned.fileTree || scanned.fileTree.length === 0) {
                        vscode.window.showWarningMessage("BlueprintBob: No workspace files found to visualize.");
                        return;
                    }

                    progress.report({ increment: 40, message: `Analyzing ${scanned.fileTree.length} files...` });

                    const config = vscode.workspace.getConfiguration('blueprintbob');
                    const backendUrl = (config.get<string>('backendUrl') || 'http://localhost:8000').replace(/\/+$/, '');

                    const payload = {
                        file_tree: scanned.fileTree,
                        readme: scanned.readme,
                        manifest: scanned.manifest,
                        key_files: scanned.keyFiles,
                        custom_prompt: null
                    };

                    progress.report({ increment: 30, message: "Synthesizing architecture graph..." });

                    // Call BlueprintBob backend engine
                    const endpoint = `${backendUrl}/api/blueprintbob/generate`;
                    const response = await postJson<BlueprintBobResponse>(endpoint, payload);

                    if (response.status !== 'success') {
                        throw new Error(`Backend returned status: ${response.status}`);
                    }

                    progress.report({ increment: 10, message: "Rendering interactive canvas..." });

                    DiagramPanel.createOrShow(
                        context.extensionUri,
                        response.mermaid_code,
                        response.explanation,
                        response.graph,
                        response.metrics
                    );
                }
            );
        } catch (error: any) {
            console.error('[BlueprintBob] Visualization failed:', error);
            vscode.window.showErrorMessage(
                `BlueprintBob failed: ${error?.message || error}. Is the backend running on http://localhost:8000?`
            );
        }
    };

    // Register command
    context.subscriptions.push(
        vscode.commands.registerCommand('blueprintbob.visualizeWorkspace', visualizeHandler)
    );
}

export function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

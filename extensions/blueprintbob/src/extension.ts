import * as vscode from 'vscode';
import { createStatusBar, postJson } from '@bytesized/shared';
import { scanWorkspace } from './workspaceScanner';
import { DiagramPanel, DiagramGraphData, KeyInfo } from './diagramPanel';

let statusBarItem: vscode.StatusBarItem;

interface BlueprintBobResponse {
    status: string;
    mermaid_code: string;
    explanation: string;
    graph?: DiagramGraphData;
    metrics?: Record<string, any>;
}

export async function activate(context: vscode.ExtensionContext) {
    console.log('[BlueprintBob] Extension activated in IBM Bob IDE / VS Code!');

    // When activating, retrieve stored key & provider
    const initialApiKey = await context.secrets.get('blueprintbob.apiKey');
    const initialApiProvider = context.globalState.get<string>('blueprintbob.apiProvider') || 'gemini';
    const initialGranularity = context.globalState.get<string>('blueprintbob.granularity') || 'detailed';
    console.log(`[BlueprintBob] Initial config - Has Key: ${!!initialApiKey}, Provider: ${initialApiProvider}, Granularity: ${initialGranularity}`);

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
                    progress.report({ increment: 15, message: "Scanning workspace files and manifests..." });
                    const scanned = await scanWorkspace();

                    if (!scanned.fileTree || scanned.fileTree.length === 0) {
                        vscode.window.showWarningMessage("BlueprintBob: No workspace files found to visualize.");
                        return;
                    }

                    progress.report({ increment: 35, message: `Analyzing ${scanned.fileTree.length} files...` });

                    const config = vscode.workspace.getConfiguration('blueprintbob');
                    const backendUrl = (config.get<string>('backendUrl') || 'http://localhost:8000').replace(/\/+$/, '');

                    const apiKey = await context.secrets.get('blueprintbob.apiKey');
                    const apiProvider = context.globalState.get<string>('blueprintbob.apiProvider') || 'gemini';
                    const storedEngineMode = context.globalState.get<string>('blueprintbob.engineMode');
                    const currentEngineMode = storedEngineMode || (apiKey ? 'ai' : 'offline');
                    const currentGranularity = context.globalState.get<string>('blueprintbob.granularity') || 'detailed';

                    const payload = {
                        file_tree: scanned.fileTree,
                        readme: scanned.readme,
                        manifest: scanned.manifest,
                        key_files: scanned.keyFiles,
                        custom_prompt: null,
                        api_key: apiKey || undefined,
                        api_provider: apiProvider,
                        engine_mode: currentEngineMode,
                        granularity: currentGranularity
                    };

                    progress.report({ increment: 30, message: "Synthesizing architecture graph..." });

                    // Call BlueprintBob backend engine
                    const endpoint = `${backendUrl}/api/blueprintbob/generate`;
                    const response = await postJson<BlueprintBobResponse>(endpoint, payload);

                    if (response.status !== 'success') {
                        throw new Error(`Backend returned status: ${response.status}`);
                    }

                    if (currentEngineMode === 'ai' && response.metrics?.api_error) {
                        vscode.window.showErrorMessage(`BlueprintBob AI Error: ${response.metrics.api_error}`);
                    }

                    progress.report({ increment: 10, message: "Rendering interactive canvas..." });

                    const keyInfo: KeyInfo = {
                        hasKey: !!apiKey,
                        provider: apiProvider,
                        maskedKey: apiKey
                            ? (apiKey.length > 10
                                ? `${apiKey.substring(0, 6)}...${apiKey.substring(apiKey.length - 4)}`
                                : apiKey)
                            : '',
                        currentMode: (currentEngineMode as 'ai' | 'offline')
                    };

                    DiagramPanel.createOrShow(
                        context.extensionUri,
                        response.mermaid_code,
                        response.explanation,
                        response.graph,
                        response.metrics,
                        keyInfo,
                        currentGranularity,
                        {
                            onSwitchEngineMode: async (mode: 'ai' | 'offline') => {
                                if (mode === 'offline') {
                                    await context.globalState.update('blueprintbob.engineMode', 'offline');
                                    vscode.window.showInformationMessage('BlueprintBob: Switched to Offline AST Mode.');
                                    await visualizeHandler();
                                } else if (mode === 'ai') {
                                    const key = await context.secrets.get('blueprintbob.apiKey');
                                    if (!key) {
                                        vscode.window.showWarningMessage('Please enter your Gemini / OpenAI API key to enable AI Mode.');
                                        DiagramPanel.currentPanel?.openApiKeyModal();
                                    } else {
                                        await context.globalState.update('blueprintbob.engineMode', 'ai');
                                        vscode.window.showInformationMessage('BlueprintBob: Switched to AI Mode. Generating with AI...');
                                        await visualizeHandler();
                                    }
                                }
                            },
                            onSwitchGranularity: async (granularity: 'overview' | 'detailed') => {
                                await context.globalState.update('blueprintbob.granularity', granularity);
                                vscode.window.showInformationMessage(
                                    `BlueprintBob: Switched to ${granularity === 'detailed' ? 'Deep File Map' : 'System Overview'}.`
                                );
                                await visualizeHandler();
                            },
                            onSaveApiKey: async (newApiKey: string, provider: string) => {
                                const trimmed = (newApiKey || '').trim();
                                if (trimmed) {
                                    await context.secrets.store('blueprintbob.apiKey', trimmed);
                                }
                                await context.globalState.update('blueprintbob.apiProvider', provider || 'gemini');
                                await context.globalState.update('blueprintbob.engineMode', 'ai');
                                vscode.window.showInformationMessage('BlueprintBob: API Key saved! Regenerating architecture diagram with AI...');
                                await visualizeHandler();
                            },
                            onClearApiKey: async () => {
                                await context.secrets.delete('blueprintbob.apiKey');
                                await context.globalState.update('blueprintbob.apiProvider', 'gemini');
                                await context.globalState.update('blueprintbob.engineMode', 'offline');
                                vscode.window.showInformationMessage('BlueprintBob: API Key removed. Switched to Offline AST Mode.');
                                await visualizeHandler();
                            }
                        }
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

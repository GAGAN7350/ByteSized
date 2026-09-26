import * as vscode from 'vscode';
import { createStatusBar } from './shared';
import { registerOptimizeRTL } from './commands/optimizeRTL';
import { registerConnectWorkspace } from './commands/connectWorkspace';

let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('[SiliconBob] Universal Code Optimizer Extension activated in IBM Bob IDE!');

    diagnosticCollection = vscode.languages.createDiagnosticCollection('siliconbob');
    context.subscriptions.push(diagnosticCollection);

    statusBarItem = createStatusBar("$(check-all) SiliconBob: Optimize", "siliconbob.optimizeCode");
    statusBarItem.tooltip = "SiliconBob: Analyze & Optimize Code (All Languages)";
    context.subscriptions.push(statusBarItem);

    registerOptimizeRTL(context, diagnosticCollection, statusBarItem);
    registerConnectWorkspace(context, statusBarItem);
}

export function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.clear();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

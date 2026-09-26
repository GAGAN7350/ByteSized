import * as vscode from 'vscode';
import { createStatusBar } from '@bytesized/shared';
import { registerOptimizeRTL } from './commands/optimizeRTL';
import { registerConnectWorkspace } from './commands/connectWorkspace';

let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('[SiliconBob] Hardware Engineering Extension activated in IBM Bob IDE!');

    diagnosticCollection = vscode.languages.createDiagnosticCollection('siliconbob');
    context.subscriptions.push(diagnosticCollection);

    statusBarItem = createStatusBar("$(chip) SiliconBob: Ready", "siliconbob.optimizeRTL");
    statusBarItem.tooltip = "Click to Analyze and Optimize RTL";
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

import * as vscode from 'vscode';
import { createStatusBar } from '@bytesized/shared';

let statusBarItem: vscode.StatusBarItem;

export function activate(context: vscode.ExtensionContext) {
    console.log('[2nd-ext] Extension activated in IBM Bob IDE!');

    statusBarItem = createStatusBar("$(extensions) 2nd-ext: Ready", "2nd-ext.helloWorld");
    statusBarItem.tooltip = "2nd-ext is active";
    context.subscriptions.push(statusBarItem);

    const cmd = vscode.commands.registerCommand('2nd-ext.helloWorld', () => {
        vscode.window.showInformationMessage('Hello from 2nd-ext! Replace this with your feature.');
    });
    context.subscriptions.push(cmd);
}

export function deactivate() {
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}

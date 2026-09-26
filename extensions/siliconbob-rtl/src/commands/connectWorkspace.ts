import * as vscode from 'vscode';

export function registerConnectWorkspace(
    context: vscode.ExtensionContext,
    statusBarItem: vscode.StatusBarItem
): void {
    const cmd = vscode.commands.registerCommand('siliconbob.connectWorkspace', async () => {
        const roomId = await vscode.window.showInputBox({
            prompt: "Enter Hardware Collaboration Room ID",
            placeHolder: "soc-core-alu",
            value: "soc-core-alu"
        });

        if (!roomId) { return; }

        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        const wsUrl = backendUrl.replace(/^http/, 'ws') + `/ws/${roomId}`;

        statusBarItem.text = `$(broadcast) SiliconBob: Connected (#${roomId})`;
        vscode.window.showInformationMessage(
            `SiliconBob: Connected to collaborative hardware room #${roomId} on ${wsUrl}`
        );
    });

    context.subscriptions.push(cmd);
}

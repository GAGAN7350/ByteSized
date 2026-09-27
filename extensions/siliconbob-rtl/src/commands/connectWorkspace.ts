import * as vscode from 'vscode';

const wsGlobal = globalThis as typeof globalThis & { WebSocket?: new (url: string) => any };
let activeSocket: any | undefined;

export function registerConnectWorkspace(
    context: vscode.ExtensionContext,
    statusBarItem: vscode.StatusBarItem
): void {
    const closeCurrentSocket = () => {
        if (activeSocket) {
            activeSocket.close();
            activeSocket = undefined;
        }
    };

    const cmd = vscode.commands.registerCommand('siliconbob.connectWorkspace', async () => {
        const roomId = await vscode.window.showInputBox({
            prompt: "Enter Hardware Collaboration Room ID",
            placeHolder: "soc-core-alu",
            value: "soc-core-alu"
        });

        if (!roomId) { return; }

        closeCurrentSocket();

        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');
        const wsUrl = backendUrl.replace(/^http/, 'ws') + `/ws/${roomId}`;

        try {
            const WebSocketCtor = wsGlobal.WebSocket ?? globalThis.WebSocket;
            if (!WebSocketCtor) {
                throw new Error('WebSocket API is unavailable in this environment');
            }
            const socket = new WebSocketCtor(wsUrl);
            activeSocket = socket;

            socket.onopen = () => {
                statusBarItem.text = `$(broadcast) SiliconBob: Room #${roomId}`;
                vscode.window.showInformationMessage(
                    `SiliconBob: Connected to collaborative hardware room #${roomId}`
                );
            };

            socket.onmessage = (event: MessageEvent) => {
                try {
                    const payload = JSON.parse(String(event.data));
                    if (payload.type === 'INIT_STATE') {
                        statusBarItem.text = `$(broadcast) SiliconBob: Room #${roomId} (${payload.active_users ?? 1} users)`;
                    } else if (payload.type === 'CODE_UPDATE' && payload.code) {
                        const doc = vscode.workspace.openTextDocument({
                            content: payload.code,
                            language: vscode.window.activeTextEditor?.document.languageId ?? 'plaintext'
                        });
                        doc.then((textDoc) => vscode.window.showTextDocument(textDoc, {
                            viewColumn: vscode.ViewColumn.Beside,
                            preview: true
                        }));
                    }
                } catch (error) {
                    console.error('[SiliconBob] Failed to parse collaboration payload', error);
                }
            };

            socket.onerror = () => {
                statusBarItem.text = '$(chip) SiliconBob: Ready';
                vscode.window.showErrorMessage(
                    `SiliconBob: Failed to connect to collaborative room #${roomId} at ${wsUrl}`
                );
            };

            socket.onclose = () => {
                if (activeSocket === socket) {
                    activeSocket = undefined;
                }
                statusBarItem.text = '$(chip) SiliconBob: Ready';
            };
        } catch (error) {
            statusBarItem.text = '$(chip) SiliconBob: Ready';
            vscode.window.showErrorMessage(`SiliconBob: WebSocket setup failed for room #${roomId}`);
            console.error('[SiliconBob] WebSocket setup failed', error);
        }
    });

    const closeCmd = vscode.commands.registerCommand('siliconbob.leaveWorkspace', () => {
        closeCurrentSocket();
        statusBarItem.text = '$(chip) SiliconBob: Ready';
    });

    context.subscriptions.push(cmd, closeCmd);
}

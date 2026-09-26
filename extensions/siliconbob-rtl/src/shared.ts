import * as vscode from 'vscode';

/**
 * Typed fetch helper for SiliconBob.
 * Sends a POST request with a JSON body and returns the parsed response.
 */
export async function postJson<T>(url: string, body: unknown): Promise<T> {
    const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });

    if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json() as Promise<T>;
}

/**
 * Creates and shows a status bar item for SiliconBob.
 */
export function createStatusBar(
    text: string,
    command: string,
    priority: number = 100
): vscode.StatusBarItem {
    const item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, priority);
    item.text = text;
    item.command = command;
    item.show();
    return item;
}

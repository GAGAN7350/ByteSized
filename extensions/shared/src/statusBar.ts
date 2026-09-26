import * as vscode from 'vscode';

/**
 * Creates and shows a status bar item — shared across all ByteSized extensions.
 *
 * @param text    - Initial text (supports ThemeIcon syntax, e.g. "$(chip) Ready")
 * @param command - Command ID to execute on click
 * @param priority - Right-alignment priority (higher = further right). Default 100.
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

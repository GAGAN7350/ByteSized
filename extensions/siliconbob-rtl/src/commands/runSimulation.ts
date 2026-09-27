import * as vscode from 'vscode';
import { postJson } from '../shared';

interface SignalState {
    name: string;
    final_value: string;
}

interface SimulateResponse {
    status: string;
    vcd: string;
    signals: SignalState[];
    event_count: number;
    cycle_count: number;
    sim_time_ps: number;
}

const EXAMPLES: vscode.QuickPickItem[] = [
    {
        label: '$(circuit-board) Ripple Counter',
        description: '4-stage asynchronous ripple counter — posedge triggered D flip-flops',
        detail: 'example: ripple_counter'
    },
    {
        label: '$(symbol-event) D Flip-Flop Chain',
        description: '3-stage DFF shift register — data propagation across clock edges',
        detail: 'example: dff_chain'
    }
];

export function registerRunSimulation(
    context: vscode.ExtensionContext,
    statusBarItem: vscode.StatusBarItem
): void {
    const cmd = vscode.commands.registerCommand('siliconbob.runSimulation', async () => {
        const pick = await vscode.window.showQuickPick(EXAMPLES, {
            title: 'SiliconBob: CycleSim — Choose a Simulation Example',
            placeHolder: 'Select a circuit to simulate',
            ignoreFocusOut: false
        });
        if (!pick) { return; }

        const exampleKey = pick.detail?.replace('example: ', '') as 'ripple_counter' | 'dff_chain';
        const config = vscode.workspace.getConfiguration('siliconbob');
        const backendUrl = config.get<string>('backendUrl', 'http://localhost:8000');

        statusBarItem.text = '$(sync~spin) SiliconBob: Simulating circuit...';

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: `SiliconBob CycleSim: Running ${pick.label.replace(/\$\([^)]+\)\s*/, '')}...`,
            cancellable: false
        }, async () => {
            try {
                const data = await postJson<SimulateResponse>(
                    `${backendUrl}/api/simulate/`,
                    { example: exampleKey }
                );

                statusBarItem.text = `$(check) SiliconBob: Sim done (${data.cycle_count} cycles)`;

                // Build a summary header
                const signalSummary = data.signals
                    .map(s => `// ${s.name.padEnd(16)} = ${s.final_value}`)
                    .join('\n');

                const output =
                    `// SiliconBob CycleSim — ${exampleKey}\n` +
                    `// Sim time: ${data.sim_time_ps} ps  |  Cycles: ${data.cycle_count}  |  Events: ${data.event_count}\n` +
                    `//\n` +
                    `// Final signal states:\n` +
                    `${signalSummary}\n\n` +
                    data.vcd;

                // Open VCD output in a new editor tab
                const doc = await vscode.workspace.openTextDocument({
                    content: output,
                    language: 'plaintext'
                });
                await vscode.window.showTextDocument(doc, {
                    viewColumn: vscode.ViewColumn.Beside,
                    preview: false
                });

                vscode.window.showInformationMessage(
                    `SiliconBob CycleSim: Simulation complete — ${data.cycle_count} cycles, ${data.event_count} events, ${data.sim_time_ps} ps.`
                );

            } catch {
                statusBarItem.text = '$(alert) SiliconBob: Sim Failed';
                vscode.window.showErrorMessage(
                    `SiliconBob CycleSim: Could not connect to backend at ${backendUrl}. Ensure 'uvicorn backend.main:app' is running on port 8000.`
                );
            }
        });
    });

    context.subscriptions.push(cmd);
}

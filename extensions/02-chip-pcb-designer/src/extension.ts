import * as vscode from 'vscode';

export function activate(context: vscode.ExtensionContext) {
    console.log('[ByteSized] Microchip & PCB Visual Designer Extension activated!');

    let disposable = vscode.commands.registerCommand('bytesized.openCircuitDesigner', () => {
        const panel = vscode.window.createWebviewPanel(
            'bytesizedCircuitDesigner',
            'ByteSized: Microchip & PCB Studio',
            vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        panel.webview.html = getCircuitDesignerHtml();

        panel.webview.onDidReceiveMessage(message => {
            if (message.command === 'exportNetlist') {
                vscode.window.showInformationMessage(`ByteSized: Exported hardware netlist with ${message.count} components!`);
            } else if (message.command === 'alert') {
                vscode.window.showInformationMessage(message.text);
            }
        }, undefined, context.subscriptions);
    });

    context.subscriptions.push(disposable);
}

function getCircuitDesignerHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ByteSized: Microchip & PCB Designer</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #1e1e2e;
            color: #cdd6f4;
            display: flex;
            height: 100vh;
            overflow: hidden;
        }
        #sidebar {
            width: 260px;
            background-color: #181825;
            border-right: 1px solid #313244;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        h2 { margin: 0 0 8px 0; font-size: 16px; color: #89b4fa; }
        .component-btn {
            background-color: #313244;
            border: 1px solid #45475a;
            color: #cdd6f4;
            padding: 10px 14px;
            border-radius: 6px;
            cursor: pointer;
            text-align: left;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: all 0.2s;
        }
        .component-btn:hover {
            background-color: #45475a;
            border-color: #89b4fa;
        }
        #canvas-container {
            flex: 1;
            position: relative;
            background: radial-gradient(#313244 1px, transparent 1px);
            background-size: 20px 20px;
            background-color: #11111b;
            overflow: auto;
            padding: 20px;
        }
        #topbar {
            position: absolute;
            top: 16px;
            right: 20px;
            display: flex;
            gap: 10px;
            z-index: 10;
        }
        .action-btn {
            background-color: #a6e3a1;
            color: #11111b;
            font-weight: 600;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
        }
        .action-btn:hover { background-color: #94e2d5; }
        .clear-btn { background-color: #f38ba8; color: #11111b; font-weight: 600; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; }
        .chip-block {
            position: absolute;
            background-color: #181825;
            border: 2px solid #89b4fa;
            border-radius: 8px;
            padding: 12px;
            width: 140px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.5);
            cursor: move;
            user-select: none;
        }
        .chip-title { font-weight: bold; font-size: 13px; color: #cba6f7; border-bottom: 1px solid #313244; padding-bottom: 4px; margin-bottom: 8px; }
        .pin { font-size: 11px; color: #a6adc8; display: flex; justify-content: space-between; }
        .pin-dot { width: 8px; height: 8px; border-radius: 50%; background-color: #f9e2af; display: inline-block; }
    </style>
</head>
<body>
    <div id="sidebar">
        <h2>⚡ Component Palette</h2>
        <button class="component-btn" onclick="addComponent('ALU Core', ['A[3:0]', 'B[3:0]', 'Op[1:0]', 'Res[3:0]'], '#89b4fa')">➕ 32-bit ALU Block</button>
        <button class="component-btn" onclick="addComponent('Microcontroller (MCU)', ['VCC', 'GND', 'GPIO_0', 'CLK'], '#a6e3a1')">➕ ARM / RISC-V MCU</button>
        <button class="component-btn" onclick="addComponent('SRAM Cache', ['Addr[9:0]', 'Data_In', 'Data_Out', 'WE'], '#f9e2af')">➕ 64KB SRAM Cache</button>
        <button class="component-btn" onclick="addComponent('Clock Generator', ['OSC_IN', 'PLL_OUT', 'RST_N'], '#f38ba8')">➕ PLL Clock Generator</button>
        <button class="component-btn" onclick="addComponent('AXI4 Bus Arbiter', ['M_VALID', 'M_READY', 'S_VALID', 'S_READY'], '#cba6f7')">➕ AXI4 Bus Interconnect</button>
    </div>

    <div id="canvas-container" id="canvas">
        <div id="topbar">
            <button class="action-btn" onclick="exportNetlist()">💾 Export Netlist</button>
            <button class="clear-btn" onclick="clearCanvas()">🗑️ Clear</button>
        </div>
        <div id="workspace" style="position: relative; width: 100%; height: 100%;"></div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        let componentCount = 0;

        function addComponent(name, pins, color) {
            componentCount++;
            const workspace = document.getElementById('workspace');
            const block = document.createElement('div');
            block.className = 'chip-block';
            block.style.borderColor = color;
            block.style.left = (40 + (componentCount * 30) % 400) + 'px';
            block.style.top = (40 + (componentCount * 30) % 300) + 'px';

            let pinsHtml = pins.map(p => '<div class="pin"><span>' + p + '</span><span class="pin-dot"></span></div>').join('');
            block.innerHTML = '<div class="chip-title">' + name + ' #' + componentCount + '</div>' + pinsHtml;

            // Make draggable
            let isDragging = false, startX, startY;
            block.addEventListener('mousedown', (e) => {
                isDragging = true;
                startX = e.clientX - block.offsetLeft;
                startY = e.clientY - block.offsetTop;
            });
            window.addEventListener('mousemove', (e) => {
                if (isDragging) {
                    block.style.left = (e.clientX - startX) + 'px';
                    block.style.top = (e.clientY - startY) + 'px';
                }
            });
            window.addEventListener('mouseup', () => { isDragging = false; });

            workspace.appendChild(block);
        }

        function exportNetlist() {
            vscode.postMessage({ command: 'exportNetlist', count: componentCount });
        }

        function clearCanvas() {
            document.getElementById('workspace').innerHTML = '';
            componentCount = 0;
        }

        // Add 2 default blocks on start
        addComponent('RISC-V Core', ['CLK', 'RST_N', 'INSTR[31:0]', 'PC[31:0]'], '#89b4fa');
        addComponent('SRAM Cache', ['Addr[9:0]', 'Data_In', 'Data_Out', 'WE'], '#f9e2af');
    </script>
</body>
</html>`;
}

export function deactivate() {}

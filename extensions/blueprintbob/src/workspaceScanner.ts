import * as vscode from 'vscode';

export interface ScannedWorkspace {
    fileTree: string[];
    readme?: string;
    manifest?: string;
    keyFiles: Record<string, string>;
}

export async function scanWorkspace(): Promise<ScannedWorkspace> {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        return {
            fileTree: [],
            keyFiles: {}
        };
    }

    const excludeGlob = '{**/node_modules/**,**/.git/**,**/__pycache__/**,**/out/**,**/dist/**,**/.venv/**,**/venv/**,**/.vscode/**}';
    
    // Find all files in the workspace matching non-excluded pattern
    const fileUris = await vscode.workspace.findFiles('**/*', excludeGlob, 1000);
    const fileTree: string[] = fileUris.map(uri => vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/'));

    let readme: string | undefined;
    let manifest: string | undefined;
    const keyFiles: Record<string, string> = {};

    const decoder = new TextDecoder('utf-8');

    for (const uri of fileUris) {
        const relPath = vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/');
        const filename = relPath.split('/').pop()?.toLowerCase();

        // Read README if found
        if (!readme && (filename === 'readme.md' || filename === 'readme')) {
            try {
                const bytes = await vscode.workspace.fs.readFile(uri);
                readme = decoder.decode(bytes).slice(0, 8000);
            } catch (err) {
                console.warn('[BlueprintBob] Could not read README:', err);
            }
        }

        // Read package manifest
        if (!manifest && (filename === 'package.json' || filename === 'requirements.txt' || filename === 'cargo.toml')) {
            try {
                const bytes = await vscode.workspace.fs.readFile(uri);
                manifest = decoder.decode(bytes).slice(0, 4000);
                keyFiles[relPath] = manifest;
            } catch (err) {
                console.warn('[BlueprintBob] Could not read manifest:', err);
            }
        }
    }

    return {
        fileTree,
        readme,
        manifest,
        keyFiles
    };
}

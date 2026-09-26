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

    const excludeGlob = '{**/node_modules/**,**/.git/**,**/__pycache__/**,**/out/**,**/dist/**,**/.venv/**,**/venv/**,**/.vscode/**,**/.idea/**,**/target/**,**/bin/**,**/obj/**}';

    // Find all files in the workspace matching non-excluded pattern
    const fileUris = await vscode.workspace.findFiles('**/*', excludeGlob, 1500);
    const fileTree: string[] = fileUris.map(uri => vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/'));

    let readme: string | undefined;
    let manifest: string | undefined;
    const keyFiles: Record<string, string> = {};

    const decoder = new TextDecoder('utf-8');

    // Score and identify top key files to read (manifests, configs, entrypoints, routers, models)
    interface CandidateFile {
        uri: vscode.Uri;
        relPath: string;
        score: number;
    }

    const candidates: CandidateFile[] = [];
    let readmeUri: vscode.Uri | undefined;
    let shallowestReadmeDepth = 999;

    for (const uri of fileUris) {
        const relPath = vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/');
        const depth = relPath.split('/').length;
        const filename = relPath.split('/').pop()?.toLowerCase() || '';

        // Identify README (prefer shallowest/root)
        if (filename === 'readme.md' || filename === 'readme') {
            if (depth < shallowestReadmeDepth) {
                shallowestReadmeDepth = depth;
                readmeUri = uri;
            }
        }

        let score = 0;

        // 1. Root & primary manifests
        if (['package.json', 'pyproject.toml', 'cargo.toml', 'go.mod'].includes(filename)) {
            score = 100 - depth * 2;
        } else if (['requirements.txt', 'tsconfig.json', 'dockerfile', 'docker-compose.yml', 'docker-compose.yaml'].includes(filename)) {
            score = 85 - depth * 2;
        }
        // 2. Main Entrypoints
        else if ([
            'main.py', 'app.py', 'server.py', 'server.ts', 'server.js',
            'index.ts', 'index.js', 'extension.ts', 'main.go', 'main.rs', 'lib.rs',
            'app.tsx', 'app.jsx', 'page.tsx', 'page.jsx'
        ].includes(filename)) {
            score = 90 - depth * 2;
        }
        // 3. Routers and controllers
        else if (filename.includes('router') || filename.includes('route') || filename.includes('controller') || filename.includes('endpoint')) {
            score = 75 - depth * 2;
        }
        // 4. Models and schemas
        else if (filename.includes('model') || filename.includes('schema') || filename.includes('types.ts') || filename.includes('types.py')) {
            score = 70 - depth * 2;
        }
        // 5. Core services / shared modules
        else if (filename.includes('service') || filename.includes('client') || relPath.includes('/shared/')) {
            score = 60 - depth * 2;
        }

        if (score > 0) {
            candidates.push({ uri, relPath, score });
        }
    }

    // Read README if found (max 10KB)
    if (readmeUri) {
        try {
            const bytes = await vscode.workspace.fs.readFile(readmeUri);
            readme = decoder.decode(bytes).slice(0, 10240);
        } catch (err) {
            console.warn('[BlueprintBob] Could not read README:', err);
        }
    }

    // Sort candidate files by score descending and select up to 15
    candidates.sort((a, b) => b.score - a.score);
    const topCandidates = candidates.slice(0, 15);

    // Read top 15 key files (max 10KB each)
    for (const candidate of topCandidates) {
        try {
            const bytes = await vscode.workspace.fs.readFile(candidate.uri);
            const content = decoder.decode(bytes).slice(0, 10240);
            keyFiles[candidate.relPath] = content;

            // Set root manifest if not already assigned
            const fname = candidate.relPath.split('/').pop()?.toLowerCase() || '';
            if (!manifest && ['package.json', 'pyproject.toml', 'cargo.toml', 'requirements.txt', 'go.mod'].includes(fname)) {
                manifest = content;
            }
        } catch (err) {
            console.warn(`[BlueprintBob] Could not read key file ${candidate.relPath}:`, err);
        }
    }

    return {
        fileTree,
        readme,
        manifest,
        keyFiles
    };
}

"""File Tree Analyzer and Architectural Layer Classifier for BlueprintBob."""
import os
import re
from typing import Dict, List, Set, Any

IGNORED_DIRS: Set[str] = {
    'node_modules',
    '.git',
    '__pycache__',
    'dist',
    'build',
    '.venv',
    'venv',
    'out',
    '.vscode',
    '.idea',
    '.mypy_cache',
    '.pytest_cache',
    '.turbo',
    '.next',
    'target',
    'bin',
    'obj',
    '.cache'
}

IGNORED_EXTS: Set[str] = {
    '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.webp',
    '.mp4', '.webm', '.mp3', '.wav',
    '.pyc', '.pyo', '.pyd', '.exe', '.dll', '.so', '.dylib', '.class', '.o', '.obj', '.wasm',
    '.zip', '.tar', '.gz', '.tgz', '.7z', '.rar',
    '.map', '.min.js', '.min.css'
}


def normalize_path(path: str) -> str:
    """Normalize file path to use forward slashes and strip leading/trailing slashes."""
    return path.replace('\\', '/').strip().lstrip('/')


def is_ignored(path: str) -> bool:
    """Determine whether a file or directory path should be ignored."""
    normalized = normalize_path(path)
    parts = normalized.split('/')

    # Check directory components
    for part in parts[:-1]:
        if part in IGNORED_DIRS:
            return True
        if part.startswith('.') and part not in {'.env.example', '.github'}:
            return True

    filename = parts[-1]
    # Check filename
    if filename in IGNORED_DIRS or filename == '.DS_Store':
        return True

    _, ext = os.path.splitext(filename)
    if ext.lower() in IGNORED_EXTS:
        return True

    return False


def filter_files(file_tree: List[str]) -> List[str]:
    """Filter out noise, ignored directories, and binary files from workspace file list."""
    filtered = []
    for f in file_tree:
        norm = normalize_path(f)
        if norm and not is_ignored(norm):
            filtered.append(norm)
    return sorted(filtered)


def categorize_file(path: str) -> str:
    """
    Categorize a file into an architectural layer:
    - backend_router
    - backend_service
    - backend_model
    - extension
    - shared_lib
    - test
    - config
    - docs
    - generic
    """
    norm = normalize_path(path).lower()
    filename = os.path.basename(norm)

    # Tests
    if (
        'test' in norm
        or filename.startswith('test_')
        or filename.endswith('_test.py')
        or filename.endswith('.test.ts')
        or filename.endswith('.spec.ts')
        or filename.endswith('.test.js')
        or filename.endswith('.spec.js')
    ):
        return 'test'

    # Backend Routers & Endpoints
    if (
        'backend/routers/' in norm
        or 'routers/' in norm
        or 'routes/' in norm
        or 'controllers/' in norm
        or 'api/' in norm and ('router' in filename or 'endpoint' in filename or 'handler' in filename)
    ):
        return 'backend_router'

    # Backend Shared Models
    if (
        'backend/shared/' in norm
        or 'models/' in norm
        or 'schemas/' in norm
        or filename in {'models.py', 'schemas.py', 'types.py'}
    ):
        return 'backend_model'

    # Backend Main / Services
    if (
        norm.startswith('backend/')
        or filename in {'main.py', 'app.py', 'server.py', 'main.go', 'server.ts'}
        or 'services/' in norm
    ):
        return 'backend_service'

    # Extension Frontend
    if (
        norm.startswith('extensions/') and 'shared' not in norm
        or 'src/extension.ts' in norm
        or 'webview' in norm
        or 'panel' in filename
    ):
        return 'extension'

    # Shared Libraries
    if (
        'extensions/shared/' in norm
        or 'packages/shared/' in norm
        or norm.startswith('shared/')
        or '/shared/' in norm
        or '/common/' in norm
    ):
        return 'shared_lib'

    # Docs
    if norm.endswith('.md') or norm.endswith('.rst') or 'docs/' in norm:
        return 'docs'

    # Config & Manifests
    if (
        filename in {'package.json', 'tsconfig.json', 'requirements.txt', 'dockerfile', 'docker-compose.yml', 'pyproject.toml'}
        or filename.startswith('.env')
        or filename.endswith('.json')
        or filename.endswith('.yaml')
        or filename.endswith('.yml')
        or filename.endswith('.toml')
    ):
        return 'config'

    return 'generic'

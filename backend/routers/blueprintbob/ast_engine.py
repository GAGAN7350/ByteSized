"""Universal Offline AST & Docstring Engine for BlueprintBob.

Analyzes workspace file trees, extracts real module docstrings, symbol exports,
and manifest descriptions, resolves cross-module imports and dependencies,
and generates dynamic, rich architecture graphs with zero hardcoded mocks.
"""
import ast
import json
import os
import re
from typing import Dict, List, Optional, Set, Tuple

from backend.routers.blueprintbob.analyzer import (
    categorize_file,
    filter_files,
    normalize_path,
)
from backend.routers.blueprintbob.compiler import sanitize_id
from backend.shared.models import (
    BlueprintBobRequest,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
)


def get_group_for_path(path: str) -> Tuple[str, str, str]:
    """Derive logical subgraph group ID, human-readable label, and description from file path."""
    norm = normalize_path(path)
    parts = norm.split('/')

    if len(parts) == 1:
        return ("group_root", "Project Root", "Root configuration, entrypoints, and documentation")

    first = parts[0].lower()

    # Monorepo / multi-extension patterns: extensions/<name>, packages/<name>, apps/<name>
    if first in ('extensions', 'packages', 'apps', 'modules', 'services', 'crates') and len(parts) > 2:
        sub = parts[1]
        gid = f"group_{first}_{sanitize_id(sub)}"
        singular = first[:-1].capitalize() if first.endswith('s') else first.capitalize()
        glabel = f"{singular}: {sub}"
        return (gid, glabel, f"Component package and modules within {first}/{sub}")

    # Sub-layers inside backend
    if first == 'backend' and len(parts) > 2:
        second = parts[1].lower()
        if second in ('routers', 'routes', 'controllers', 'api', 'endpoints'):
            return ("group_backend_api", "Backend API & Routers", "Request handlers, REST controllers, and routing engines")
        if second in ('shared', 'models', 'schemas', 'entities', 'db'):
            return ("group_backend_models", "Data Models & Schemas", "Pydantic models, schemas, and persistence layer")

    # Common architectural directories
    dir_label_map = {
        'backend': ('group_backend', 'Backend Services', 'Server-side application core and service layer'),
        'frontend': ('group_frontend', 'Frontend Application', 'Client interface, views, and state management'),
        'src': ('group_src', 'Source Layer (src)', 'Primary application source code and implementation modules'),
        'app': ('group_app', 'Application Layer (app)', 'Application routing, layout, and page components'),
        'components': ('group_components', 'UI Components', 'Reusable user interface and presentation components'),
        'lib': ('group_lib', 'Core Libraries (lib)', 'Core utility functions, database connectors, and clients'),
        'api': ('group_api', 'API Layer', 'REST/GraphQL routing and request endpoints'),
        'shared': ('group_shared', 'Shared Modules', 'Cross-cutting utilities, models, and shared libraries'),
        'tests': ('group_tests', 'Automated Test Suites', 'Unit, integration, and end-to-end test verification'),
        'test': ('group_tests', 'Automated Test Suites', 'Unit, integration, and end-to-end test verification'),
        'config': ('group_config', 'Configuration', 'Environment variables and system configurations'),
        'docs': ('group_docs', 'Documentation', 'Technical documentation and project guides'),
        'scripts': ('group_scripts', 'Automation Scripts', 'Build, migration, and automation tooling'),
        'internal': ('group_internal', 'Internal Packages', 'Private internal implementation packages'),
        'pkg': ('group_pkg', 'Packages (pkg)', 'Modular library packages')
    }

    if first in dir_label_map:
        return dir_label_map[first]

    clean_name = parts[0].replace('_', ' ').replace('-', ' ').title()
    return (f"group_{sanitize_id(parts[0])}", clean_name, f"Modules in {parts[0]}")


def score_file_significance(path: str, in_key_files: bool = False) -> int:
    """Score file architectural importance to select 10 to 25 top representative nodes."""
    norm = normalize_path(path).lower()
    base = os.path.basename(norm)
    score = 10

    if in_key_files:
        score += 35

    # Entrypoints & root anchors
    entry_names = {
        'main.py', 'app.py', 'server.py', 'server.ts', 'server.js',
        'index.ts', 'index.js', 'main.go', 'main.rs', 'lib.rs',
        'extension.ts', 'app.tsx', 'app.jsx', 'app.vue', 'page.tsx', 'page.jsx'
    }
    if base in entry_names:
        score += 55
    elif any(k in base for k in ('entry', 'bootstrap', 'start')):
        score += 30

    # Routers and controllers
    if any(k in base for k in ('router', 'route', 'controller', 'endpoint', 'handler')) or any(k in norm for k in ('/routers/', '/routes/', '/controllers/', '/api/')):
        score += 45

    # Models and schemas
    if any(k in base for k in ('model', 'schema', 'entity', 'database', 'entities')) or any(k in norm for k in ('/models/', '/schemas/')):
        score += 40

    # Core services, managers, providers
    if any(k in base for k in ('service', 'provider', 'store', 'client', 'engine', 'manager')) or any(k in norm for k in ('/services/', '/lib/')):
        score += 30

    # Top manifests & configs
    if base in ('package.json', 'pyproject.toml', 'cargo.toml', 'go.mod', 'dockerfile', 'docker-compose.yml'):
        score += 25
    elif base in ('tsconfig.json', 'requirements.txt'):
        score += 15

    # Tests (include representative tests)
    if 'test' in base or 'spec' in base:
        score += 20

    # Penalty for excessive depth
    depth = norm.count('/')
    score -= min(depth * 3, 15)

    return score


def select_top_nodes(
    filtered_files: List[str],
    key_files: Dict[str, str],
    max_nodes: Optional[int] = None,
    granularity: str = "detailed"
) -> List[str]:
    """Select a clean, balanced, readable set of top architectural files based on granularity."""
    if max_nodes is None:
        if granularity == "overview":
            max_nodes = 12  # Pick 10-12 nodes for overview
        else:
            max_nodes = 28  # Pick 24-32 nodes for detailed map

    if len(filtered_files) <= max_nodes:
        return sorted(filtered_files)

    # Score all files
    scored = []
    norm_key_files = {normalize_path(k): v for k, v in key_files.items()}
    for f in filtered_files:
        norm = normalize_path(f)
        s = score_file_significance(norm, in_key_files=(norm in norm_key_files))
        scored.append((s, norm))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Group by directory cluster to ensure balanced representation
    grouped: Dict[str, List[Tuple[int, str]]] = {}
    for s, path in scored:
        gid, _, _ = get_group_for_path(path)
        grouped.setdefault(gid, []).append((s, path))

    selected: Set[str] = set()

    # Step 1: Pick top files from each group (2 for overview, 3 for detailed)
    group_sample_limit = 2 if granularity == "overview" else 3
    for gid, files in grouped.items():
        for s, path in files[:group_sample_limit]:
            selected.add(path)
            if len(selected) >= max_nodes:
                break
        if len(selected) >= max_nodes:
            break

    # Step 2: Fill remaining slots with globally highest scoring files
    if len(selected) < max_nodes:
        for s, path in scored:
            selected.add(path)
            if len(selected) >= max_nodes:
                break

    return sorted(list(selected))


def extract_python_details(content: str) -> Tuple[Optional[str], List[str], List[str], List[str]]:
    """
    Parse Python code using AST to extract docstring, imports, classes, and functions.
    Falls back gracefully to regex on parse failure.
    """
    docstring: Optional[str] = None
    imports: List[str] = []
    classes: List[str] = []
    functions: List[str] = []

    try:
        tree = ast.parse(content)
        doc = ast.get_docstring(tree)
        if doc:
            docstring = doc.strip().split('\n')[0].strip()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
                elif node.level and node.level > 0:
                    for name in node.names:
                        imports.append(f"{'.' * node.level}{name.name}")

        for item in tree.body:
            if isinstance(item, ast.ClassDef):
                classes.append(item.name)
            elif isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                functions.append(item.name)

    except Exception:
        # Regex fallback
        doc_m = re.search(r'^[ \t]*"""([\s\S]*?)"""', content, re.MULTILINE)
        if not doc_m:
            doc_m = re.search(r"^[ \t]*'''([\s\S]*?)'''", content, re.MULTILINE)
        if doc_m:
            docstring = doc_m.group(1).strip().split('\n')[0].strip()

        imports.extend(re.findall(r'from\s+([a-zA-Z0-9_.]+)\s+import', content))
        imports.extend(re.findall(r'import\s+([a-zA-Z0-9_.]+)', content))
        classes.extend(re.findall(r'^class\s+([a-zA-Z0-9_]+)', content, re.MULTILINE))
        functions.extend(re.findall(r'^def\s+([a-zA-Z0-9_]+)', content, re.MULTILINE))

    return docstring, imports, classes, functions


def extract_ts_js_details(content: str) -> Tuple[Optional[str], List[str], List[str]]:
    """Parse TypeScript/JavaScript to extract JSDoc block comments, imports, and exports."""
    docstring: Optional[str] = None
    imports: List[str] = []
    exports: List[str] = []

    # Leading or block JSDoc
    jsdoc_m = re.search(r'/\*\*\s*([\s\S]*?)\s*\*/', content)
    if jsdoc_m:
        raw_lines = [l.strip().lstrip('*').strip() for l in jsdoc_m.group(1).split('\n')]
        clean_lines = [l for l in raw_lines if l and not l.startswith('@')]
        if clean_lines:
            docstring = clean_lines[0]

    # Imports: import ... from '...' or require('...')
    imports.extend(re.findall(r'(?:import|from)\s+[\'"]([^\'"]+)[\'"]', content))
    imports.extend(re.findall(r'require\([\'"]([^\'"]+)[\'"]\)', content))

    # Exports
    exports.extend(re.findall(r'export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|type|interface)\s+([A-Za-z0-9_]+)', content))

    return docstring, imports, exports


def extract_manifest_details(path: str, content: str) -> Optional[str]:
    """Extract descriptive metadata from manifests (package.json, pyproject.toml, Cargo.toml)."""
    norm = normalize_path(path).lower()
    base = os.path.basename(norm)

    if base == 'package.json':
        try:
            data = json.loads(content)
            desc = data.get('description')
            name = data.get('name')
            if desc and name:
                return f"{name}: {desc}"
            if desc:
                return desc
            if name:
                return f"Node.js package manifest for {name}"
        except Exception:
            pass

    if base in ('pyproject.toml', 'cargo.toml'):
        desc_m = re.search(r'description\s*=\s*["\']([^"\']+)["\']', content)
        if desc_m:
            return desc_m.group(1)
        name_m = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
        if name_m:
            return f"Package manifest for {name_m.group(1)}"

    return None


def read_file_content_safely(path: str, key_files: Dict[str, str]) -> Optional[str]:
    """Retrieve content from key_files dictionary or read locally from disk up to 25KB."""
    norm = normalize_path(path)
    for k, v in key_files.items():
        if normalize_path(k) == norm:
            return v

    if os.path.isfile(path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read(25600)
        except Exception:
            pass

    return None


def build_node_description(path: str, content: Optional[str], node_type: str) -> str:
    """Generate accurate node description from real docstring, symbols, or structural role."""
    norm = normalize_path(path)
    base = os.path.basename(norm).lower()

    if content:
        # Check manifests first
        manifest_desc = extract_manifest_details(path, content)
        if manifest_desc:
            return manifest_desc[:120]

        # Check Python
        if norm.endswith('.py'):
            doc, _, classes, funcs = extract_python_details(content)
            if doc:
                return doc[:120]
            if 'FastAPI(' in content:
                return "FastAPI application entrypoint with middleware and routes"
            if 'APIRouter(' in content:
                prefix_m = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', content)
                return f"FastAPI APIRouter mounting {prefix_m.group(1)}" if prefix_m else "FastAPI APIRouter endpoint handler"
            if classes:
                return f"Defines schemas/classes: {', '.join(classes[:3])}"
            if funcs:
                return f"Exports functions: {', '.join(funcs[:3])}"

        # Check TypeScript / JavaScript
        if norm.endswith(('.ts', '.tsx', '.js', '.jsx')):
            doc, _, exports = extract_ts_js_details(content)
            if doc:
                return doc[:120]
            if 'activate(context' in content:
                return "VS Code extension activation entrypoint"
            if 'express()' in content:
                return "Express server application entrypoint"
            if 'express.Router()' in content or 'Router()' in content:
                return "Express router and HTTP route handlers"
            if norm.endswith(('.tsx', '.jsx')) or 'import React' in content or 'className=' in content:
                comp_m = re.search(r'export\s+(?:default\s+)?(?:function|const)\s+([A-Z][a-zA-Z0-9_]*)', content)
                return f"React Component: {comp_m.group(1)}" if comp_m else "React UI presentation component"
            if exports:
                return f"Exports: {', '.join(exports[:3])}"

    # Structural fallback based on node_type (NO hardcoded project names)
    fallback_map = {
        'router': "API router and endpoint request handler",
        'database': "Data schemas, persistence models, and type contracts",
        'backend': "Backend service and core execution runtime",
        'frontend': "User interface component / layout presentation",
        'extension': "Editor client extension controller",
        'shared': "Shared utility and reusable helper module",
        'test': "Automated test suite verifying components",
        'config': "Configuration, manifest, and environment definitions",
        'docs': "Project documentation and reference guides"
    }

    return fallback_map.get(node_type, f"Source component ({base})")


def determine_node_attributes(path: str) -> Tuple[str, str, str]:
    """
    Determine (node_type, shape, clean_label) for a given file path.
    Shapes:
      - hexagon: routers, controllers, API handlers
      - database: models, schemas, entities, DB connections
      - document: configs, manifests, tests, docs
      - box: services, components, entrypoints, libraries
    """
    norm = normalize_path(path)
    base = os.path.basename(norm)
    base_lower = base.lower()
    cat = categorize_file(path)

    # 1. Routers & Endpoints
    if (
        cat == 'backend_router'
        or any(k in base_lower for k in ('router', 'route', 'controller', 'endpoint', 'handler'))
        or '/routers/' in norm
        or '/routes/' in norm
        or '/controllers/' in norm
        or ('/api/' in norm and not base_lower.startswith('test'))
    ):
        return ("router", "hexagon", base)

    # 2. Models & Database
    if (
        cat == 'backend_model'
        or any(k in base_lower for k in ('model', 'schema', 'entity', 'entities', 'types.ts', 'types.py'))
        or '/models/' in norm
        or '/schemas/' in norm
        or base_lower in ('database.py', 'db.ts', 'db.py')
    ):
        return ("database", "database", base)

    # 3. Tests
    if cat == 'test' or 'test' in base_lower or 'spec' in base_lower:
        return ("test", "document", base)

    # 4. Manifests & Configs
    if (
        cat == 'config'
        or base_lower in ('package.json', 'pyproject.toml', 'cargo.toml', 'tsconfig.json', 'requirements.txt', 'dockerfile', 'docker-compose.yml')
        or base_lower.endswith(('.json', '.toml', '.yaml', '.yml', '.env'))
    ):
        return ("config", "document", base)

    # 5. Extensions
    if cat == 'extension' or norm.startswith('extensions/'):
        return ("extension", "box", base)

    # 6. Shared libraries
    if cat == 'shared_lib' or '/shared/' in norm or norm.startswith('shared/') or '/common/' in norm:
        return ("shared", "box", base)

    # 7. Frontend Components
    if '/components/' in norm or base_lower.endswith(('.tsx', '.jsx', '.vue', '.svelte')):
        return ("frontend", "box", base)

    # 8. Backend services / Entrypoints
    if (
        base_lower in ('main.py', 'app.py', 'server.py', 'server.ts', 'server.js', 'main.go', 'main.rs', 'lib.rs')
        or norm.startswith('backend/')
        or '/services/' in norm
    ):
        return ("backend", "box", base)

    return ("backend" if 'backend' in norm else "shared", "box", base)


def resolve_import_to_node(
    source_path: str,
    import_target: str,
    nodes_by_path: Dict[str, DiagramNode],
    nodes_by_stem: Dict[str, DiagramNode]
) -> Optional[DiagramNode]:
    """Resolve an import statement string to a known DiagramNode."""
    source_dir = os.path.dirname(source_path)

    # Case 1: Relative import (starts with .)
    if import_target.startswith('.'):
        dot_count = len(import_target) - len(import_target.lstrip('.'))
        rel_mod = import_target[dot_count:].replace('.', '/')

        up_levels = dot_count - 1
        target_dir = source_dir
        for _ in range(up_levels):
            target_dir = os.path.dirname(target_dir)

        cand_stem = os.path.normpath(os.path.join(target_dir, rel_mod)).replace('\\', '/') if rel_mod else target_dir

        # Exact stem match
        if cand_stem in nodes_by_stem:
            return nodes_by_stem[cand_stem]

        # Suffix matching
        for stem, node in nodes_by_stem.items():
            if stem.endswith(cand_stem) or cand_stem.endswith(stem):
                return node

    # Case 2: Direct path / module string
    mod_stem = import_target.replace('.', '/')
    if mod_stem in nodes_by_stem:
        return nodes_by_stem[mod_stem]

    # Package / alias match (e.g. '@bytesized/shared' or 'backend.routers.xyz')
    for stem, node in nodes_by_stem.items():
        if stem.endswith(mod_stem) or mod_stem.endswith(stem):
            return node
        # Match package name component
        pkg_part = import_target.split('/')[-1]
        if pkg_part and len(pkg_part) > 2 and f"/{pkg_part}/" in stem:
            return node

    return None


def resolve_dependencies_and_edges(
    nodes: List[DiagramNode],
    key_files: Dict[str, str]
) -> List[DiagramEdge]:
    """
    Parse actual import/require statements and API calls from key_files to create real directed edges.
    Adds heuristic fallback edges if no imports are found to maintain graph connectivity.
    """
    edges: List[DiagramEdge] = []
    seen_edges: Set[Tuple[str, str]] = set()

    nodes_by_path: Dict[str, DiagramNode] = {n.path: n for n in nodes if n.path}
    nodes_by_stem: Dict[str, DiagramNode] = {
        os.path.splitext(n.path)[0]: n for n in nodes if n.path
    }

    for node in nodes:
        if not node.path:
            continue

        content = read_file_content_safely(node.path, key_files)
        if not content:
            continue

        imports: List[str] = []
        if node.path.endswith('.py'):
            _, py_imps, _, _ = extract_python_details(content)
            imports.extend(py_imps)
        elif node.path.endswith(('.ts', '.tsx', '.js', '.jsx')):
            _, ts_imps, _ = extract_ts_js_details(content)
            imports.extend(ts_imps)

        # Resolve parsed imports
        for imp in imports:
            target_node = resolve_import_to_node(node.path, imp, nodes_by_path, nodes_by_stem)
            if target_node and target_node.id != node.id:
                edge_key = (node.id, target_node.id)
                if edge_key not in seen_edges:
                    # Determine contextual label
                    if ('mount' in content or 'include_router' in content) and target_node.type == 'router':
                        label = "mounts"
                        style = "solid"
                    elif target_node.type == 'database' or 'model' in target_node.id:
                        label = "uses models"
                        style = "dashed"
                    elif node.type == 'test':
                        label = "verifies"
                        style = "dashed"
                    else:
                        label = "imports"
                        style = "dashed"

                    edges.append(DiagramEdge(
                        source=node.id,
                        target=target_node.id,
                        label=label,
                        style=style
                    ))
                    seen_edges.add(edge_key)

        # REST API endpoint calls: search for HTTP paths (e.g. /api/...)
        api_matches = re.findall(r'[\'"`](/api/[a-zA-Z0-9_\-/]+)[\'"`]', content)
        for api_url in api_matches:
            api_slug = api_url.strip('/').split('/')[-1]
            for candidate in nodes:
                if candidate.type == 'router' and candidate.id != node.id:
                    cand_path = candidate.path.lower() if candidate.path else ""
                    if api_slug in cand_path or api_slug in candidate.id.lower() or (candidate.description and api_url in candidate.description):
                        edge_key = (node.id, candidate.id)
                        if edge_key not in seen_edges:
                            method = "POST" if "post" in content.lower() else "calls"
                            edges.append(DiagramEdge(
                                source=node.id,
                                target=candidate.id,
                                label=f"{method} {api_url}",
                                style="solid"
                            ))
                            seen_edges.add(edge_key)
                            break

    # If key_files had limited content, synthesize clean architectural structural connections
    if len(edges) < len(nodes) // 2:
        entrypoints = [n for n in nodes if any(n.path and n.path.lower().endswith(ep) for ep in ('main.py', 'app.py', 'server.ts', 'server.js', 'extension.ts', 'index.ts'))]
        routers = [n for n in nodes if n.type == 'router']
        models = [n for n in nodes if n.type == 'database']
        tests = [n for n in nodes if n.type == 'test']

        # Entrypoints mount routers
        for ep in entrypoints:
            for r in routers:
                edge_key = (ep.id, r.id)
                if edge_key not in seen_edges and ep.id != r.id:
                    edges.append(DiagramEdge(source=ep.id, target=r.id, label="mounts", style="solid"))
                    seen_edges.add(edge_key)

        # Routers use models
        for r in routers:
            for m in models:
                edge_key = (r.id, m.id)
                if edge_key not in seen_edges and r.id != m.id:
                    edges.append(DiagramEdge(source=r.id, target=m.id, label="uses models", style="dashed"))
                    seen_edges.add(edge_key)

        # Tests verify entrypoints or routers
        for t in tests:
            target = routers[0] if routers else (entrypoints[0] if entrypoints else None)
            if target and (t.id, target.id) not in seen_edges:
                edges.append(DiagramEdge(source=t.id, target=target.id, label="verifies", style="dashed"))
                seen_edges.add((t.id, target.id))

    return edges


def build_ast_graph(request: BlueprintBobRequest) -> DiagramGraph:
    """Build a rich, structured architecture graph deterministically from the workspace using AST analysis."""
    filtered = filter_files(request.file_tree)
    granularity = (request.granularity or "detailed").lower().strip()
    selected_files = select_top_nodes(filtered, request.key_files, granularity=granularity)

    groups_map: Dict[str, DiagramGroup] = {}
    nodes: List[DiagramNode] = []

    # Disambiguate duplicate base filenames in labels
    base_counts: Dict[str, int] = {}
    for f in selected_files:
        base = os.path.basename(f)
        base_counts[base] = base_counts.get(base, 0) + 1

    for file_path in selected_files:
        gid, glabel, gdesc = get_group_for_path(file_path)
        if gid not in groups_map:
            groups_map[gid] = DiagramGroup(id=gid, label=glabel, description=gdesc)

        nid = sanitize_id(file_path)
        node_type, shape, base = determine_node_attributes(file_path)

        # Label disambiguation
        if base_counts.get(base, 0) > 1:
            parts = normalize_path(file_path).split('/')
            label = f"{parts[-2]}/{parts[-1]}" if len(parts) > 1 else base
        else:
            label = base

        content = read_file_content_safely(file_path, request.key_files)
        desc = build_node_description(file_path, content, node_type)

        nodes.append(DiagramNode(
            id=nid,
            label=label,
            type=node_type,
            description=desc,
            path=file_path,
            shape=shape,
            group_id=gid
        ))

    # Resolve dependencies and real edges
    edges = resolve_dependencies_and_edges(nodes, request.key_files)

    # Filter out empty groups
    active_group_ids = {n.group_id for n in nodes if n.group_id}
    groups = [g for g in groups_map.values() if g.id in active_group_ids]

    # Custom prompt highlighting
    if request.custom_prompt:
        term = request.custom_prompt.lower()
        for node in nodes:
            if (
                term in node.label.lower()
                or term in (node.path or "").lower()
                or term in node.id.lower()
                or (node.description and term in node.description.lower())
            ):
                node.label = f"⭐ {node.label}"

    return DiagramGraph(groups=groups, nodes=nodes, edges=edges)


def generate_ast_explanation(graph: DiagramGraph, request: BlueprintBobRequest) -> str:
    """Generate dynamic architectural overview in Markdown based on discovered components and relations."""
    lines: List[str] = []

    # Title & Project identity
    proj_title = "Workspace Architecture Overview"
    if request.manifest:
        try:
            m = json.loads(request.manifest)
            if 'name' in m:
                proj_title = f"{m['name']} Architecture Overview"
        except Exception:
            pass

    lines.append(f"### {proj_title}\n")

    # Detect technology stack
    techs: Set[str] = set()
    for node in graph.nodes:
        if node.path:
            p = node.path.lower()
            if p.endswith('.py'):
                techs.add("Python")
            if p.endswith(('.ts', '.tsx')):
                techs.add("TypeScript")
            if p.endswith(('.js', '.jsx')):
                techs.add("JavaScript")
            if p.endswith('.go'):
                techs.add("Go")
            if p.endswith('.rs'):
                techs.add("Rust")
            if 'fastapi' in (node.description or '').lower():
                techs.add("FastAPI")
            if 'react' in (node.description or '').lower() or p.endswith(('.tsx', '.jsx')):
                techs.add("React")
            if 'extension' in (node.description or '').lower() or p.startswith('extensions/'):
                techs.add("VS Code / Bob IDE Extensions")

    tech_str = ", ".join(sorted(techs)) if techs else "Polyglot"
    lines.append(f"This project is composed of **{len(graph.nodes)}** key architectural components organized across **{len(graph.groups)}** functional subsystems using **{tech_str}**.\n")

    # Group breakdown
    lines.append("#### Subsystem Breakdown\n")
    for group in graph.groups:
        group_nodes = [n for n in graph.nodes if n.group_id == group.id]
        lines.append(f"- **{group.label}** ({len(group_nodes)} modules): {group.description}")
        for n in group_nodes[:4]:
            lines.append(f"  - `{n.label}`: {n.description}")
        if len(group_nodes) > 4:
            lines.append(f"  - *(and {len(group_nodes) - 4} other modules)*")

    # Inter-component relationship summary
    if graph.edges:
        lines.append("\n#### Inter-Component Data Flow & Dependencies\n")
        sample_edges = graph.edges[:6]
        id_to_label = {n.id: n.label for n in graph.nodes}
        for edge in sample_edges:
            src = id_to_label.get(edge.source, edge.source)
            tgt = id_to_label.get(edge.target, edge.target)
            label = f" ({edge.label})" if edge.label else ""
            lines.append(f"- `{src}` ➔ `{tgt}`{label}")
        if len(graph.edges) > 6:
            lines.append(f"- *({len(graph.edges) - 6} additional dependency edges mapped in interactive diagram)*")

    return "\n".join(lines)

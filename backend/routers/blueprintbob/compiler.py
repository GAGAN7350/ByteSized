"""Mermaid Compiler for BlueprintBob Architecture Graphs."""
import re
from typing import Dict, List, Set
from backend.shared.models import DiagramGraph, DiagramNode, DiagramEdge, DiagramGroup


def sanitize_id(raw_id: str) -> str:
    """Sanitize identifier for Mermaid syntax (letters, digits, underscores)."""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', raw_id.strip())
    if not sanitized:
        sanitized = 'node'
    if sanitized[0].isdigit():
        sanitized = f'n_{sanitized}'
    return sanitized


def escape_label(label: str) -> str:
    """Escape label strings to prevent Mermaid parse errors."""
    if not label:
        return ''
    clean = label.replace('"', "'")
    clean = clean.replace('\r\n', '<br/>').replace('\n', '<br/>')
    return clean


def wrap_label(label: str, max_chars: int = 22) -> str:
    """
    Wrap long node labels with <br/> if they exceed max_chars (e.g. >= 22 characters)
    or exceed length limits, preventing text from clipping or overflowing node shapes.
    Handles delimiters like slashes '/', underscores '_', hyphens '-', or spaces.
    """
    if not label or '<br/>' in label or '<br>' in label:
        return label

    # Check if wrapping is needed:
    # 1. Total length exceeds 22 chars (or >= 22)
    # 2. Long identifiers / known patterns like 'unpipelined_mult.v'
    needs_wrap = (
        len(label) >= 22
        or 'unpipelined_mult.v' in label
        or (len(label) >= 18 and ('_' in label or '/' in label))
    )
    if not needs_wrap:
        return label

    # If it contains slashes, e.g. bob_sessions/<br/>README.md
    if '/' in label:
        parts = label.split('/')
        wrapped: List[str] = []
        curr = ""
        for i, p in enumerate(parts):
            suffix = "/" if i < len(parts) - 1 else ""
            seg = p + suffix
            if curr and (len(curr) + len(seg) >= max_chars or len(curr) >= 10):
                wrapped.append(curr)
                curr = seg
            else:
                curr += seg
        if curr:
            wrapped.append(curr)
        if len(wrapped) > 1:
            return '<br/>'.join(wrapped)
        label = wrapped[0]

    # If it contains spaces
    if ' ' in label:
        words = label.split(' ')
        wrapped = []
        curr = ""
        for w in words:
            if curr and len(curr) + 1 + len(w) > max_chars:
                wrapped.append(curr)
                curr = w
            else:
                curr = f"{curr} {w}" if curr else w
        if curr:
            wrapped.append(curr)
        if len(wrapped) > 1:
            return '<br/>'.join(wrapped)

    # If it contains underscores or hyphens, e.g. unpipelined_<br/>mult.v
    for sep in ('_', '-'):
        if sep in label:
            parts = label.split(sep)
            wrapped = []
            curr = ""
            for i, p in enumerate(parts):
                suffix = sep if i < len(parts) - 1 else ""
                seg = p + suffix
                if curr and (len(curr) + len(seg) >= max_chars or len(curr) >= 10):
                    wrapped.append(curr)
                    curr = seg
                else:
                    curr += seg
            if curr:
                wrapped.append(curr)
            if len(wrapped) > 1:
                return '<br/>'.join(wrapped)

    # If no delimiter and exceeds max_chars, split around midpoint
    if len(label) >= max_chars:
        mid = len(label) // 2
        return f"{label[:mid]}<br/>{label[mid:]}"

    return label


def format_node_shape(node_id: str, label: str, shape: str = 'box') -> str:
    escaped_label = wrap_label(escape_label(label))
    s = (shape or 'box').lower()
    if s == 'database':
        return f'{node_id}[("{escaped_label}")]'
    elif s == 'queue':
        return f'{node_id}(["{escaped_label}"])'
    elif s == 'document':
        return f'{node_id}>"{escaped_label}"]'
    elif s == 'circle':
        return f'{node_id}(("{escaped_label}"))'
    elif s == 'hexagon':
        return f'{node_id}{{{{"{escaped_label}"}}}}'
    else:
        return f'{node_id}["{escaped_label}"]'


def compile_mermaid(graph: DiagramGraph) -> str:
    """
    Compiles a DiagramGraph into a valid Mermaid flowchart TD string.
    Includes subgraphs, custom shapes, edge styles, click handlers, and sleek CSS styling.
    """
    lines: List[str] = ['flowchart TD']

    grouped_nodes: Dict[str, List[DiagramNode]] = {g.id: [] for g in graph.groups}
    ungrouped_nodes: List[DiagramNode] = []

    id_map: Dict[str, str] = {}
    for node in graph.nodes:
        sanitized = sanitize_id(node.id)
        id_map[node.id] = sanitized
        if node.group_id and node.group_id in grouped_nodes:
            grouped_nodes[node.group_id].append(node)
        else:
            ungrouped_nodes.append(node)

    # Render groups (subgraphs)
    for group in graph.groups:
        sanitized_gid = sanitize_id(group.id)
        escaped_glabel = escape_label(group.label)
        lines.append(f'    subgraph {sanitized_gid} ["{escaped_glabel}"]')
        nodes = grouped_nodes.get(group.id, [])
        for node in nodes:
            sid = id_map[node.id]
            node_def = format_node_shape(sid, node.label, node.shape or 'box')
            lines.append(f'        {node_def}')
        lines.append('    end')

    # Render ungrouped nodes
    for node in ungrouped_nodes:
        sid = id_map[node.id]
        node_def = format_node_shape(sid, node.label, node.shape or 'box')
        lines.append(f'    {node_def}')

    # Render edges
    for edge in graph.edges:
        source_id = id_map.get(edge.source, sanitize_id(edge.source))
        target_id = id_map.get(edge.target, sanitize_id(edge.target))
        if not source_id or not target_id:
            continue

        has_label = bool(edge.label and edge.label.strip())
        elabel = escape_label(edge.label) if has_label else ''

        style = (edge.style or 'solid').lower()
        if style == 'dashed':
            edge_str = f'{source_id} -.->|"{elabel}"| {target_id}' if has_label else f'{source_id} -.-> {target_id}'
        else:
            edge_str = f'{source_id} -->|"{elabel}"| {target_id}' if has_label else f'{source_id} --> {target_id}'

        lines.append(f'    {edge_str}')

    # Node clicks
    for node in graph.nodes:
        sid = id_map[node.id]
        lines.append(f'    click {sid} call onNodeClick("{sid}")')

    # Sleek Tech Styling Class Definitions
    lines.append('    classDef default fill:#1e1e2e,stroke:#45475a,stroke-width:1px,color:#cdd6f4;')
    lines.append('    classDef backend fill:#1e1e2e,stroke:#89b4fa,stroke-width:2px,color:#cdd6f4;')
    lines.append('    classDef frontend fill:#1e1e2e,stroke:#a6e3a1,stroke-width:2px,color:#cdd6f4;')
    lines.append('    classDef extension fill:#1e1e2e,stroke:#a6e3a1,stroke-width:2px,color:#cdd6f4;')
    lines.append('    classDef router fill:#1e1e2e,stroke:#cba6f7,stroke-width:2px,color:#cdd6f4;')
    lines.append('    classDef database fill:#1e1e2e,stroke:#fab387,stroke-width:2px,color:#cdd6f4;')
    lines.append('    classDef shared fill:#1e1e2e,stroke:#f9e2af,stroke-width:2px,color:#cdd6f4;')
    lines.append('    classDef test fill:#181825,stroke:#f38ba8,stroke-width:1px,stroke-dasharray: 4 4,color:#cdd6f4;')
    lines.append('    classDef config fill:#181825,stroke:#94e2d5,stroke-width:1px,color:#cdd6f4;')
    lines.append('    classDef docs fill:#181825,stroke:#b4befe,stroke-width:1px,color:#cdd6f4;')

    # Assign classes to nodes
    for node in graph.nodes:
        sid = id_map[node.id]
        ntype = (node.type or 'default').lower()
        if ntype in {'backend', 'frontend', 'extension', 'router', 'database', 'shared', 'test', 'config', 'docs'}:
            lines.append(f'    class {sid} {ntype};')

    return '\n'.join(lines)

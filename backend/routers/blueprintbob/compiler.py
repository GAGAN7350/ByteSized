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


def format_node_shape(node_id: str, label: str, shape: str = 'box') -> str:
    escaped_label = escape_label(label)
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

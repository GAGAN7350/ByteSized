"""BlueprintBob Architecture Graph & Explanation Generator.

Provides the Universal Dual-Engine Architecture:
1. Bring Your Own Key (BYOK) Mode: calls Gemini or OpenAI with structured JSON schemas
   when API keys are present in environment variables.
2. Universal Offline AST & Docstring Engine: completely offline, universal static analysis
   extracting real docstrings, types, and cross-file import dependencies without hardcoded mocks.
"""
import json
import logging
import os
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from backend.routers.blueprintbob.analyzer import filter_files
from backend.routers.blueprintbob.ast_engine import (
    build_ast_graph,
    generate_ast_explanation,
)
from backend.routers.blueprintbob.compiler import compile_mermaid
from backend.shared.models import (
    BlueprintBobRequest,
    BlueprintBobResponse,
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
)

logger = logging.getLogger(__name__)

# Backwards compatibility alias
build_deterministic_graph = build_ast_graph


def build_byok_prompt(request: BlueprintBobRequest) -> str:
    """Construct structured architectural synthesis prompt for LLM BYOK mode."""
    filtered = filter_files(request.file_tree)
    sample_files = filtered[:80]

    key_files_summary = []
    for path, content in list(request.key_files.items())[:10]:
        preview = content[:800].replace('\r\n', '\n')
        key_files_summary.append(f"--- File: {path} ---\n{preview}\n")

    key_files_text = "\n".join(key_files_summary)
    readme_text = (request.readme or "")[:3000]
    manifest_text = (request.manifest or "")[:1500]

    return f"""You are BlueprintBob, an expert software architecture engine.
Analyze the following workspace components and produce a clean, structured architecture graph and comprehensive markdown explanation.

FILES IN WORKSPACE (sample):
{json.dumps(sample_files, indent=2)}

ROOT MANIFEST:
{manifest_text or "None provided"}

README:
{readme_text or "None provided"}

KEY SOURCE FILES EXCERPTS:
{key_files_text or "None provided"}

REQUIREMENTS:
1. Identify 10 to 20 key architectural nodes grouped into logical subsystems (e.g. Frontend, Backend, Database, Shared, Extensions, Tests).
2. Assign appropriate node types: "backend", "frontend", "extension", "router", "database", "shared", "test", "config".
3. Assign node shapes: "box", "hexagon" (for routers), "database" (for models/db), "document" (for configs/tests).
4. Establish directed dependencies with descriptive labels (e.g., "imports", "mounts", "uses models", "calls API").
5. Return ONLY a valid JSON object matching this schema:
{{
  "explanation": "A rich 2-3 paragraph markdown architectural overview detailing layers, data flow, and subsystems.",
  "graph": {{
    "groups": [
      {{"id": "group_id", "label": "Group Label", "description": "Group Description"}}
    ],
    "nodes": [
      {{"id": "node_id", "label": "Node Label", "type": "backend|frontend|...", "description": "Brief description", "path": "path/to/file", "shape": "box|hexagon|...", "group_id": "group_id"}}
    ],
    "edges": [
      {{"source": "source_node_id", "target": "target_node_id", "label": "relationship", "style": "solid|dashed"}}
    ]
  }}
}}
"""


def call_llm_byok(request: BlueprintBobRequest) -> Optional[Tuple[DiagramGraph, str]]:
    """
    Attempt BYOK LLM analysis using GEMINI_API_KEY or OPENAI_API_KEY.
    Returns (DiagramGraph, explanation) if successful, or None on failure.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if not gemini_key and not openai_key:
        return None

    prompt = build_byok_prompt(request)

    # 1. Try Gemini if configured
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_key}"
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "temperature": 0.2
                }
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                raw_text = resp_data['candidates'][0]['content']['parts'][0]['text']

                # Strip potential markdown formatting if wrapped
                cleaned_text = re.sub(r'^```json\s*', '', raw_text.strip())
                cleaned_text = re.sub(r'```$', '', cleaned_text.strip())
                parsed = json.loads(cleaned_text)

                if "graph" in parsed and "explanation" in parsed:
                    g_data = parsed["graph"]
                    nodes = [DiagramNode(**n) for n in g_data.get("nodes", [])]
                    groups = [DiagramGroup(**g) for g in g_data.get("groups", [])]
                    edges = [DiagramEdge(**e) for e in g_data.get("edges", [])]

                    if nodes:
                        return DiagramGraph(groups=groups, nodes=nodes, edges=edges), parsed["explanation"]

        except Exception as e:
            logger.warning("Gemini BYOK request failed, falling back to offline AST: %s", e)

    # 2. Try OpenAI if configured
    if openai_key:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            payload = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are BlueprintBob, an architecture visualizer returning valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2
            }).encode('utf-8')

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {openai_key}"
                }
            )

            with urllib.request.urlopen(req, timeout=12) as resp:
                resp_data = json.loads(resp.read().decode('utf-8'))
                raw_text = resp_data['choices'][0]['message']['content']
                parsed = json.loads(raw_text)

                if "graph" in parsed and "explanation" in parsed:
                    g_data = parsed["graph"]
                    nodes = [DiagramNode(**n) for n in g_data.get("nodes", [])]
                    groups = [DiagramGroup(**g) for g in g_data.get("groups", [])]
                    edges = [DiagramEdge(**e) for e in g_data.get("edges", [])]

                    if nodes:
                        return DiagramGraph(groups=groups, nodes=nodes, edges=edges), parsed["explanation"]

        except Exception as e:
            logger.warning("OpenAI BYOK request failed, falling back to offline AST: %s", e)

    return None


def generate_diagram(request: BlueprintBobRequest) -> BlueprintBobResponse:
    """
    Main entrypoint for generating architecture diagrams and explanations.
    Uses BYOK mode if API keys are configured and functional; otherwise
    seamlessly uses the Universal Offline AST & Docstring Engine.
    """
    byok_result = call_llm_byok(request)

    if byok_result is not None:
        graph, explanation = byok_result
        generation_mode = "llm_byok"
    else:
        graph = build_ast_graph(request)
        explanation = generate_ast_explanation(graph, request)
        generation_mode = "offline_ast"

    # Compile diagram graph to Mermaid flowchart TD
    mermaid_code = compile_mermaid(graph)

    # Calculate synthesis metrics
    filtered_files = filter_files(request.file_tree)
    metrics = {
        "total_files": len(request.file_tree),
        "scanned_files": len(filtered_files),
        "nodes_count": len(graph.nodes),
        "edges_count": len(graph.edges),
        "groups_count": len(graph.groups),
        "generation_mode": generation_mode
    }

    return BlueprintBobResponse(
        status="success",
        mermaid_code=mermaid_code,
        explanation=explanation,
        graph=graph,
        metrics=metrics
    )

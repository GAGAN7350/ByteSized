"""BlueprintBob Architecture Graph & Explanation Generator.

Provides the Universal Dual-Engine Architecture:
1. Bring Your Own Key (BYOK) Mode: calls Gemini or OpenAI with structured JSON schemas
   when API keys are present in environment variables.
2. Universal Offline AST & Docstring Engine: completely offline, universal static analysis
   extracting real docstrings, types, and cross-file import dependencies without hardcoded mocks.
"""
import hashlib
import json
import logging
import os
import re
import socket
import time
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
    sample_files = filtered[:60]

    key_files_summary = []
    for path, content in list(request.key_files.items())[:6]:
        preview = content[:500].replace('\r\n', '\n')
        key_files_summary.append(f"--- File: {path} ---\n{preview}\n")

    key_files_text = "\n".join(key_files_summary)
    readme_text = (request.readme or "")[:1500]
    manifest_text = (request.manifest or "")[:1000]

    granularity = (request.granularity or "detailed").lower().strip()
    if granularity == "detailed":
        req_text = """REQUIREMENTS FOR DETAILED ARCHITECTURE MAP:
1. Produce a detailed, comprehensive architecture diagram with 22 to 36 specific component and file nodes.
2. Break down the system into specific implementation files rather than single generic boxes:
   - Client extensions: show individual commands (e.g. optimizeRTL.ts, connectWorkspace.ts), views (diagramPanel.ts), and scanners (workspaceScanner.ts).
   - Backend services: show individual routers, engines, analyzers, models, and compilers (e.g. main.py, router.py, engine.py, compiler.py, ast_engine.py).
   - Shared modules and individual test suites.
3. Assign precise file paths to all repository nodes in the `path` field.
4. Connect fine-grained directed edges with descriptive verbs (e.g., 'mounts', 'imports', 'calls REST API', 'parses AST', 'validates schema').
5. Assign appropriate node types: "backend", "frontend", "extension", "router", "database", "shared", "test", "config".
6. Assign node shapes: "box", "hexagon" (for routers), "database" (for models/db), "document" (for configs/tests), "circle" (for external actors)."""
    else:
        req_text = """REQUIREMENTS FOR SYSTEM OVERVIEW MAP:
1. Produce a clean, macro-level 10 to 14 node system overview representing high-level subsystem blocks and architecture layers.
2. Aggregate individual files into macro architectural components (e.g. Core API Service, Frontend UI Layer, Shared Libraries, Database/Models, Test Harness).
3. Assign appropriate node types: "backend", "frontend", "extension", "router", "database", "shared", "test", "config".
4. Assign node shapes: "box", "hexagon" (for routers), "database" (for models/db), "document" (for configs/tests), "circle" (for external actors).
5. Establish clean, high-level directed dependencies with clear relationship labels (e.g., 'mounts', 'imports', 'calls API')."""

    return f"""You are BlueprintBob, an expert software architecture engine modeled after clean GitDiagram visual style.
Analyze the following workspace components and produce a clean, structured architecture graph and concise explanation.

FILES IN WORKSPACE (sample):
{json.dumps(sample_files, indent=2)}

ROOT MANIFEST:
{manifest_text or "None provided"}

README:
{readme_text or "None provided"}

KEY SOURCE FILES EXCERPTS:
{key_files_text or "None provided"}

GITDIAGRAM CLEAN ARCHITECTURAL STYLE GUIDELINES:
- Identify the primary external Actor / User (e.g. "Hardware engineer", "Developer", "Client") as a "circle" shape node (shape: "circle", type: "frontend").
- Identify the Entrypoint UI / Editor (e.g. "VS Code / Bob editor", "Web App UI") invoking commands or initiating actions.
- Group components into clean, logical subsystem subgraphs (e.g. "Extension Client", "Backend Core API", "Analysis Engine", "Data Storage").
- For node labels, include clean file references in brackets where appropriate (e.g. `Extension commands [extension.ts]`, `WebSocket endpoint [main.py]`, `Compiler [compiler.py]`).
- Limit output size: Keep node descriptions under 10 words and the markdown explanation under 120 words so the entire JSON streams in 2-3 seconds.

{req_text}
7. Return ONLY a valid JSON object matching this schema:
{{
  "explanation": "A concise 1-2 paragraph markdown architectural overview detailing layers, data flow, and subsystems (under 120 words).",
  "graph": {{
    "groups": [
      {{"id": "group_id", "label": "Group Label", "description": "Group Description"}}
    ],
    "nodes": [
      {{"id": "node_id", "label": "Node Label [filename]", "type": "backend|frontend|...", "description": "Brief description", "path": "path/to/file", "shape": "box|circle|hexagon|database|...", "group_id": "group_id"}}
    ],
    "edges": [
      {{"source": "source_node_id", "target": "target_node_id", "label": "relationship", "style": "solid|dashed"}}
    ]
  }}
}}
"""


BLACKLIST_MODEL_KEYWORDS = [
    "omni",
    "preview",
    "-tts",
    "tts",
    "audio",
    "embedding",
    "imagen",
    "aqa",
    "robotics",
    "search",
    "whisper",
]

PREFERRED_TEXT_MODELS = [
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash-lite",
    "gemini-1.5-pro-latest",
    "gemini-pro",
]


def _extract_json_payload(raw_text: str) -> dict:
    """Robustly extract and parse JSON object from LLM response text."""
    text = raw_text.strip()

    # Extract JSON fenced in markdown code blocks if present
    fence_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text, re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()
    elif text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    if not text.startswith("{"):
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end+1]

    return json.loads(text)


_gemini_models_cache: Dict[str, Tuple[List[str], float]] = {}
_GEMINI_CACHE_TTL = 300  # 5-minute TTL


def _get_available_gemini_models(api_key: str) -> Tuple[List[str], Optional[str]]:
    """Query Gemini ListModels endpoint to dynamically discover supported generateContent models."""
    api_key = (api_key or "").strip()
    if not api_key:
        return [], "Gemini API Error: Empty API key"

    now = time.time()
    if api_key in _gemini_models_cache:
        cached_models, cached_ts = _gemini_models_cache[api_key]
        if (now - cached_ts) < _GEMINI_CACHE_TTL:
            return list(cached_models), None

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    req = urllib.request.Request(
        url,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            raw_models = resp_data.get("models", [])
            valid_models: List[str] = []
            seen = set()
            for m in raw_models:
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name = m.get("name", "").replace("models/", "").strip()
                    name_lower = name.lower()
                    if any(kw in name_lower for kw in BLACKLIST_MODEL_KEYWORDS):
                        continue
                    if name and name not in seen:
                        seen.add(name)
                        valid_models.append(name)

            # Prioritize pure text generation models:
            # 1. Models explicitly listed in PREFERRED_TEXT_MODELS in strict order
            b1 = [m for m in PREFERRED_TEXT_MODELS if m in valid_models]
            # 2. Any other flash models (e.g. gemini-2.5-flash, gemini-2.0-flash-lite)
            b2 = sorted(
                [m for m in valid_models if "flash" in m.lower() and m not in b1],
                reverse=True
            )
            # 3. Any other pro models (e.g. gemini-2.5-pro)
            b3 = sorted(
                [m for m in valid_models if "pro" in m.lower() and m not in b1 and m not in b2],
                reverse=True
            )
            # 4. Any remaining text generation models
            b4 = sorted(
                [m for m in valid_models if m not in b1 and m not in b2 and m not in b3]
            )

            # Strictly try at most 2 candidate models. Never cycle through 5 models.
            candidate_models = (b1 + b2 + b3 + b4)[:2]
            _gemini_models_cache[api_key] = (candidate_models, now)
            return list(candidate_models), None

    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode('utf-8', errors='ignore')
            parsed_err = json.loads(err_body)
            err_msg = parsed_err.get("error", {}).get("message") or str(e)
        except Exception:
            err_msg = err_body or str(e)
        return [], f"Gemini API Error ({e.code}): {err_msg}"
    except Exception as e:
        return [], f"Gemini API Error: {str(e)}"


def _is_timeout_error(exc: Exception) -> bool:
    """Check if exception was caused by a socket or connection timeout."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    if isinstance(exc, urllib.error.URLError):
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            return True
        if "timed out" in str(exc.reason).lower():
            return True
    if "timed out" in str(exc).lower():
        return True
    return False


def _parse_gemini_http_error(exc: urllib.error.HTTPError) -> str:
    """Extract human-readable error message from Gemini HTTPError."""
    err_body = ""
    try:
        err_body = exc.read().decode('utf-8', errors='ignore')
        parsed_err = json.loads(err_body)
        return parsed_err.get("error", {}).get("message") or err_body or str(exc)
    except Exception:
        return err_body or str(exc)


def _call_gemini(api_key: str, prompt: str) -> Tuple[Optional[DiagramGraph], Optional[str], Optional[str]]:
    """Helper to query Google Gemini generateContent endpoint with retries and JSON fallback."""
    candidate_models, list_err = _get_available_gemini_models(api_key)
    if list_err:
        print(f"[BlueprintBob] ListModels failed: {list_err}", flush=True)
        if any(f"({code})" in list_err for code in (400, 401, 403)):
            return None, None, list_err

    if not candidate_models:
        candidate_models = list(PREFERRED_TEXT_MODELS[:2])
    else:
        candidate_models = candidate_models[:2]

    print(f"[BlueprintBob] Available Gemini models: {candidate_models}", flush=True)

    start_time = time.time()
    MAX_TOTAL_TIME = 15.0

    last_error = list_err
    for model in candidate_models:
        if (time.time() - start_time) >= MAX_TOTAL_TIME:
            print(f"[BlueprintBob] Total Gemini attempt time exceeded {MAX_TOTAL_TIME}s. Falling back to offline engine.", flush=True)
            break

        use_json_mime = True
        retried_503 = False

        while True:
            if (time.time() - start_time) >= MAX_TOTAL_TIME:
                print(f"[BlueprintBob] Total Gemini attempt time exceeded {MAX_TOTAL_TIME}s. Falling back to offline engine.", flush=True)
                break

            try:
                print(f"[BlueprintBob] Calling Gemini API ({model}, json_mime={use_json_mime})...", flush=True)
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                gen_config: Dict[str, Any] = {"temperature": 0.2}
                if use_json_mime:
                    gen_config["responseMimeType"] = "application/json"

                payload = json.dumps({
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": gen_config
                }).encode('utf-8')

                req = urllib.request.Request(
                    url,
                    data=payload,
                    headers={"Content-Type": "application/json"}
                )

                # Set timeout to 12 seconds per model request
                with urllib.request.urlopen(req, timeout=12) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    candidates = resp_data.get('candidates', [])
                    if not candidates:
                        raise ValueError(f"Gemini API returned no candidates from {model}")
                    parts = candidates[0].get('content', {}).get('parts', [])
                    if not parts:
                        raise ValueError(f"Gemini API returned empty content parts from {model}")
                    raw_text = parts[0].get('text', '')

                    parsed = _extract_json_payload(raw_text)

                    if "graph" in parsed and "explanation" in parsed:
                        g_data = parsed["graph"]
                        nodes = [DiagramNode(**n) for n in g_data.get("nodes", [])]
                        groups = [DiagramGroup(**g) for g in g_data.get("groups", [])]
                        edges = [DiagramEdge(**e) for e in g_data.get("edges", [])]
                        if nodes:
                            print(f"[BlueprintBob] Gemini successfully generated architecture graph ({model})!", flush=True)
                            return DiagramGraph(groups=groups, nodes=nodes, edges=edges), parsed["explanation"], None

                    raise ValueError(f"Gemini API returned invalid graph format from {model}")

            except urllib.error.HTTPError as e:
                err_msg = _parse_gemini_http_error(e)
                last_error = f"Gemini API Error ({e.code}): {err_msg}"
                logger.warning("Gemini model %s failed (%s): %s", model, e.code, err_msg)

                # 1. Fallback when JSON Mode is rejected (code 400 with 'JSON mode is not enabled' or referencing JSON mode)
                is_json_mode_error = (e.code == 400) and (
                    "json mode" in err_msg.lower()
                    or "json_mode" in err_msg.lower()
                    or "responsemimetype" in err_msg.lower()
                    or "response_mime_type" in err_msg.lower()
                )
                if is_json_mode_error and use_json_mime:
                    print(f"[BlueprintBob] JSON mode rejected for {model}. Retrying immediately without responseMimeType...", flush=True)
                    use_json_mime = False
                    continue

                # 2. Permanent auth / project errors: stop iterating through all models
                if e.code in (401, 403) or (e.code == 400 and ("api key" in err_msg.lower() or "key not valid" in err_msg.lower())):
                    print(f"[BlueprintBob] Permanent Gemini API Error ({e.code}): {err_msg}", flush=True)
                    return None, None, last_error

                # 3. 429 Quota Exceeded: DO NOT sleep and retry! Quota limit: 0 will never succeed 1.5s later.
                # Immediately move to next candidate model or offline fallback.
                if e.code == 429:
                    print(f"[BlueprintBob] Gemini model {model} returned 429 (quota exceeded). Moving immediately to next candidate or fallback...", flush=True)
                    break

                # 4. 503 High Demand: retry once if within time limit
                if e.code == 503 and not retried_503 and (time.time() - start_time) < (MAX_TOTAL_TIME - 3.0):
                    print(f"[BlueprintBob] Gemini model {model} returned 503. Retrying once after 1.5s...", flush=True)
                    time.sleep(1.5)
                    retried_503 = True
                    continue

                # Otherwise (e.g. 404 Not Found, or second 503 failure), advance to next model
                break

            except Exception as e:
                # Timeouts: Set timeout to 12s per model request, DO NOT sleep and retry.
                # Immediately move to next candidate model or offline fallback.
                if _is_timeout_error(e):
                    last_error = f"Gemini API Error: Request timed out for {model}"
                    print(f"[BlueprintBob] Gemini model {model} timed out. Moving immediately to next candidate or fallback...", flush=True)
                    break

                last_error = f"Gemini API Error: {str(e)}"
                logger.warning("Gemini model %s failed: %s", model, e)
                break

    print(f"[BlueprintBob] Gemini call failed: {last_error}", flush=True)
    return None, None, last_error


def _call_openai(api_key: str, prompt: str) -> Tuple[Optional[DiagramGraph], Optional[str], Optional[str]]:
    """Helper to query OpenAI chat completions endpoint."""
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
                "Authorization": f"Bearer {api_key}"
            }
        )

        with urllib.request.urlopen(req, timeout=12) as resp:
            resp_data = json.loads(resp.read().decode('utf-8'))
            raw_text = resp_data['choices'][0]['message']['content']
            parsed = _extract_json_payload(raw_text)

            if "graph" in parsed and "explanation" in parsed:
                g_data = parsed["graph"]
                nodes = [DiagramNode(**n) for n in g_data.get("nodes", [])]
                groups = [DiagramGroup(**g) for g in g_data.get("groups", [])]
                edges = [DiagramEdge(**e) for e in g_data.get("edges", [])]
                if nodes:
                    return DiagramGraph(groups=groups, nodes=nodes, edges=edges), parsed["explanation"], None
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode('utf-8', errors='ignore')
            parsed_err = json.loads(err_body)
            err_msg = parsed_err.get("error", {}).get("message") or str(e)
        except Exception:
            err_msg = err_body or str(e)
        last_error = f"OpenAI API Error ({e.code}): {err_msg}"
        logger.warning("OpenAI API request failed (%s): %s", e.code, err_msg)
        return None, None, last_error
    except Exception as e:
        last_error = f"OpenAI API Error: {str(e)}"
        logger.warning("OpenAI API request failed: %s", e)
        return None, None, last_error
    return None, None, "OpenAI API did not return valid graph output"


def call_llm_byok(
    request: BlueprintBobRequest
) -> Tuple[Optional[DiagramGraph], Optional[str], str, Optional[str]]:
    """
    Attempt BYOK LLM analysis using request.api_key first, or GEMINI_API_KEY / OPENAI_API_KEY env vars.
    Returns:
        (graph, explanation, engine_mode, error_message)
        where engine_mode is 'byok_gemini', 'byok_openai', or 'offline_ast'.
    """
    api_key = (request.api_key or "").strip()
    provider = (request.api_provider or "gemini").lower().strip()

    # Determine provider and key:
    # 1. Use request.api_key if supplied
    if api_key:
        if api_key.startswith("AIza"):
            provider = "gemini"
        elif api_key.startswith("sk-"):
            provider = "openai"
        elif provider not in ("gemini", "openai"):
            provider = "gemini"
    else:
        # 2. Fallback to environment variables
        if os.getenv("GEMINI_API_KEY"):
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            provider = "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            provider = "openai"

    if not api_key:
        return None, None, "offline_ast", None

    prompt = build_byok_prompt(request)

    if provider == "gemini":
        graph, explanation, err = _call_gemini(api_key, prompt)
        if graph and explanation:
            return graph, explanation, "byok_gemini", None
        return None, None, "offline_ast", err or "Gemini API failed to generate graph"

    elif provider == "openai":
        graph, explanation, err = _call_openai(api_key, prompt)
        if graph and explanation:
            return graph, explanation, "byok_openai", None
        return None, None, "offline_ast", err or "OpenAI API failed to generate graph"

    return None, None, "offline_ast", None


_diagram_cache: Dict[str, BlueprintBobResponse] = {}
_MAX_DIAGRAM_CACHE_SIZE = 128


def compute_diagram_cache_key(request: BlueprintBobRequest) -> str:
    """
    Compute deterministic cache key from (file_tree, readme_len, manifest_len, granularity, mode, provider).
    """
    tree_sorted = sorted(request.file_tree or [])
    readme_len = len(request.readme or "")
    manifest_len = len(request.manifest or "")
    granularity = (request.granularity or "detailed").lower().strip()
    mode = (request.engine_mode or "ai").lower().strip()
    provider = (request.api_provider or "gemini").lower().strip()
    custom_prompt = (request.custom_prompt or "").strip()

    cache_data = {
        "file_tree": tree_sorted,
        "readme_len": readme_len,
        "manifest_len": manifest_len,
        "granularity": granularity,
        "mode": mode,
        "provider": provider,
        "custom_prompt": custom_prompt,
    }
    raw_bytes = json.dumps(cache_data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw_bytes).hexdigest()


def clear_diagram_cache() -> None:
    """Clear all entries in the in-memory diagram cache."""
    _diagram_cache.clear()


def generate_diagram(request: BlueprintBobRequest) -> BlueprintBobResponse:
    """
    Main entrypoint for generating architecture diagrams and explanations.
    Uses in-memory caching to return instant results (0.01s) when inputs are identical.
    Uses BYOK mode if engine_mode is 'ai' and API keys are configured and functional;
    otherwise seamlessly uses the Universal Offline AST & Docstring Engine.
    """
    cache_key = compute_diagram_cache_key(request)
    if cache_key in _diagram_cache:
        cached_resp = _diagram_cache[cache_key]
        resp_copy = cached_resp.model_copy(deep=True)
        resp_copy.metrics["cached"] = True
        return resp_copy

    req_mode = (request.engine_mode or "ai").lower().strip()

    if req_mode == "offline":
        graph = build_ast_graph(request)
        explanation = generate_ast_explanation(graph, request)
        generation_mode = "offline_ast"
        engine_mode = "offline_ast"
        api_error = None
    else:
        graph, explanation, engine_mode, api_error = call_llm_byok(request)
        if graph is not None:
            generation_mode = "llm_byok"
        else:
            graph = build_ast_graph(request)
            ast_explanation = generate_ast_explanation(graph, request)
            if api_error:
                explanation = (
                    f"> ⚠️ **AI Generation Warning:** {api_error}. "
                    f"Fell back to Universal Offline AST Engine.\n\n"
                    f"{ast_explanation}"
                )
            else:
                explanation = ast_explanation
            generation_mode = "offline_ast"
            engine_mode = "offline_ast"

    # Compile diagram graph to Mermaid flowchart TD
    mermaid_code = compile_mermaid(graph)

    # Calculate synthesis metrics
    filtered_files = filter_files(request.file_tree)
    metrics: Dict[str, Any] = {
        "total_files": len(request.file_tree),
        "scanned_files": len(filtered_files),
        "nodes_count": len(graph.nodes),
        "edges_count": len(graph.edges),
        "groups_count": len(graph.groups),
        "granularity": request.granularity or "detailed",
        "generation_mode": generation_mode,
        "engine_mode": engine_mode
    }
    if api_error:
        metrics["api_error"] = api_error
        metrics["warning"] = f"AI API call failed: {api_error}. Fell back to Offline AST engine."

    resp = BlueprintBobResponse(
        status="success",
        mermaid_code=mermaid_code,
        explanation=explanation,
        graph=graph,
        metrics=metrics
    )

    if len(_diagram_cache) >= _MAX_DIAGRAM_CACHE_SIZE:
        oldest_key = next(iter(_diagram_cache))
        _diagram_cache.pop(oldest_key, None)
    _diagram_cache[cache_key] = resp

    return resp


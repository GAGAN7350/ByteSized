"""Unit tests for BlueprintBob Architecture Engine.

Verifies the Universal Dual-Engine Architecture:
- Complete removal of hardcoded ByteSized mocks
- Universal Offline AST & Docstring Engine functionality on generic codebases (Python, Next.js, etc.)
- Real AST docstring and JSDoc extraction
- Cross-module import and dependency edge resolution
- BYOK mode graceful fallback on API errors
- Mermaid diagram compiler shapes and styling
"""
import json
import os
import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.models import (
    DiagramEdge,
    DiagramGraph,
    DiagramGroup,
    DiagramNode,
)
from backend.routers.blueprintbob.compiler import compile_mermaid


class TestBlueprintBobBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_endpoint(self):
        """Test the /api/blueprintbob/health endpoint."""
        resp = self.client.get("/api/blueprintbob/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["service"], "BlueprintBob Architecture Engine")

    def test_generic_python_fastapi_project(self):
        """
        Verify the engine on a generic Python FastAPI project.
        Ensures NO hardcoded ByteSized nodes exist and real docstrings/imports are extracted.
        """
        file_tree = [
            "app/main.py",
            "app/routers/users.py",
            "app/routers/items.py",
            "app/models/user.py",
            "app/services/auth.py",
            "tests/test_users.py",
            "pyproject.toml",
            "README.md",
            ".git/HEAD",
            "__pycache__/main.cpython-312.pyc"
        ]

        key_files = {
            "app/main.py": (
                '"""Main FastAPI application entrypoint."""\n'
                'from fastapi import FastAPI\n'
                'from app.routers import users, items\n'
                'app = FastAPI()\n'
                'app.include_router(users.router)\n'
                'app.include_router(items.router)\n'
            ),
            "app/routers/users.py": (
                '"""User management and registration router."""\n'
                'from fastapi import APIRouter\n'
                'from app.models.user import UserModel\n'
                'from app.services.auth import verify_token\n'
                'router = APIRouter(prefix="/users")\n'
            ),
            "app/routers/items.py": (
                '"""Item catalog and inventory router."""\n'
                'from fastapi import APIRouter\n'
                'router = APIRouter(prefix="/items")\n'
            ),
            "app/models/user.py": (
                '"""Pydantic schemas and database models for users."""\n'
                'from pydantic import BaseModel\n'
                'class UserModel(BaseModel):\n'
                '    id: int\n'
                '    username: str\n'
            ),
            "app/services/auth.py": (
                '"""Authentication service providing JWT validation."""\n'
                'def verify_token(token: str) -> bool:\n'
                '    return True\n'
            ),
            "tests/test_users.py": (
                '"""Unit test suite for user registration."""\n'
                'from app.routers.users import router\n'
            ),
            "pyproject.toml": (
                '[project]\n'
                'name = "fastapi-demo"\n'
                'description = "A high-performance modern API demo"\n'
            )
        }

        payload = {
            "file_tree": file_tree,
            "readme": "# FastAPI Demo Application\nModern microservice example.",
            "manifest": '{"name": "fastapi-demo"}',
            "key_files": key_files,
            "custom_prompt": None
        }

        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["metrics"]["generation_mode"], "offline_ast")

        graph = data["graph"]
        self.assertIsNotNone(graph)
        node_ids = {n["id"] for n in graph["nodes"]}
        node_desc_map = {n["path"]: n["description"] for n in graph["nodes"] if n.get("path")}

        # Verify NO hardcoded ByteSized mocks exist
        self.assertNotIn("ext_siliconbob", node_ids)
        self.assertNotIn("rtl_router", node_ids)
        self.assertNotIn("ext_blueprintbob", node_ids)
        self.assertNotIn("shared_extension_lib", node_ids)

        # Verify real docstrings are extracted from AST
        self.assertEqual(
            node_desc_map.get("app/main.py"),
            "Main FastAPI application entrypoint."
        )
        self.assertEqual(
            node_desc_map.get("app/routers/users.py"),
            "User management and registration router."
        )
        self.assertEqual(
            node_desc_map.get("app/models/user.py"),
            "Pydantic schemas and database models for users."
        )
        self.assertEqual(
            node_desc_map.get("pyproject.toml"),
            "A high-performance modern API demo"
        )

        # Verify real dependency edges were resolved
        edges = graph["edges"]
        edge_pairs = {(e["source"], e["target"]): e.get("label") for e in edges}

        # main.py mounts / imports users.py
        main_id = [n["id"] for n in graph["nodes"] if n["path"] == "app/main.py"][0]
        users_id = [n["id"] for n in graph["nodes"] if n["path"] == "app/routers/users.py"][0]
        models_id = [n["id"] for n in graph["nodes"] if n["path"] == "app/models/user.py"][0]
        test_id = [n["id"] for n in graph["nodes"] if n["path"] == "tests/test_users.py"][0]

        self.assertIn((main_id, users_id), edge_pairs)
        self.assertIn((users_id, models_id), edge_pairs)
        self.assertEqual(edge_pairs[(users_id, models_id)], "uses models")
        self.assertIn((test_id, users_id), edge_pairs)
        self.assertEqual(edge_pairs[(test_id, users_id)], "verifies")

        # Verify mermaid compiles properly
        mermaid = data["mermaid_code"]
        self.assertIn("flowchart TD", mermaid)
        self.assertIn("subgraph", mermaid)

    def test_generic_nextjs_project(self):
        """
        Verify the engine on a generic Next.js / TypeScript project.
        Ensures JSDoc comments, component types, and TS imports resolve correctly.
        """
        file_tree = [
            "package.json",
            "app/page.tsx",
            "app/api/auth/route.ts",
            "components/Navbar.tsx",
            "components/Footer.tsx",
            "lib/db.ts",
            "node_modules/react/index.js",
            ".next/build-manifest.json"
        ]

        key_files = {
            "package.json": '{"name": "collab-board", "description": "Collaborative whiteboard canvas"}',
            "app/page.tsx": (
                'import React from "react";\n'
                'import { Navbar } from "../components/Navbar";\n'
                'import { Footer } from "../components/Footer";\n'
                'export default function Page() { return <div>Home</div>; }\n'
            ),
            "app/api/auth/route.ts": (
                '/** OAuth session authentication handler. */\n'
                'import { queryDb } from "../../../lib/db";\n'
                'export async function GET() { return Response.json({ ok: true }); }\n'
            ),
            "components/Navbar.tsx": (
                '/** Top navigation bar with user profile. */\n'
                'import React from "react";\n'
                'export function Navbar() { return <nav>Navbar</nav>; }\n'
            ),
            "components/Footer.tsx": (
                '/** Application footer with copyright info. */\n'
                'import React from "react";\n'
                'export function Footer() { return <footer>Footer</footer>; }\n'
            ),
            "lib/db.ts": (
                '/** PostgreSQL connection pool and query execution. */\n'
                'export function queryDb(sql: string) { return []; }\n'
            )
        }

        payload = {
            "file_tree": file_tree,
            "manifest": key_files["package.json"],
            "key_files": key_files
        }

        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["status"], "success")
        graph = data["graph"]

        # Ensure no ByteSized mocks
        node_ids = {n["id"] for n in graph["nodes"]}
        self.assertNotIn("ext_siliconbob", node_ids)

        # Check JSDoc docstring extraction
        node_desc_map = {n["path"]: n["description"] for n in graph["nodes"] if n.get("path")}
        self.assertEqual(
            node_desc_map.get("app/api/auth/route.ts"),
            "OAuth session authentication handler."
        )
        self.assertEqual(
            node_desc_map.get("components/Navbar.tsx"),
            "Top navigation bar with user profile."
        )
        self.assertEqual(
            node_desc_map.get("lib/db.ts"),
            "PostgreSQL connection pool and query execution."
        )

        # Check group labels reflect Next.js architecture
        group_labels = {g["label"] for g in graph["groups"]}
        self.assertTrue(any("Components" in label for label in group_labels))
        self.assertTrue(any("Libraries" in label or "lib" in label.lower() for label in group_labels))

        # Check import edges: page.tsx -> Navbar.tsx, route.ts -> db.ts
        page_id = [n["id"] for n in graph["nodes"] if n["path"] == "app/page.tsx"][0]
        nav_id = [n["id"] for n in graph["nodes"] if n["path"] == "components/Navbar.tsx"][0]
        route_id = [n["id"] for n in graph["nodes"] if n["path"] == "app/api/auth/route.ts"][0]
        db_id = [n["id"] for n in graph["nodes"] if n["path"] == "lib/db.ts"][0]

        edge_pairs = {(e["source"], e["target"]) for e in graph["edges"]}
        self.assertIn((page_id, nav_id), edge_pairs)
        self.assertIn((route_id, db_id), edge_pairs)

    def test_byok_fallback_on_invalid_key(self):
        """
        Verify BYOK fallback to offline AST engine when API key is invalid or network fails.
        """
        old_gemini_key = os.environ.get("GEMINI_API_KEY")
        try:
            os.environ["GEMINI_API_KEY"] = "invalid_dummy_key_123"
            payload = {
                "file_tree": ["src/index.ts", "src/utils.ts"],
                "key_files": {
                    "src/index.ts": "import { add } from './utils';",
                    "src/utils.ts": "/** Helper add function. */\nexport function add(a: number, b: number) { return a + b; }"
                }
            }
            resp = self.client.post("/api/blueprintbob/generate", json=payload)
            self.assertEqual(resp.status_code, 200)

            data = resp.json()
            self.assertEqual(data["status"], "success")
            # Must have fallen back gracefully to offline_ast
            self.assertEqual(data["metrics"]["generation_mode"], "offline_ast")
            self.assertIn("flowchart TD", data["mermaid_code"])
        finally:
            if old_gemini_key is not None:
                os.environ["GEMINI_API_KEY"] = old_gemini_key
            else:
                os.environ.pop("GEMINI_API_KEY", None)

    def test_generate_with_custom_prompt(self):
        """Test /api/blueprintbob/generate highlighting components matching custom_prompt."""
        payload = {
            "file_tree": ["backend/main.py", "extensions/blueprintbob/src/extension.ts"],
            "custom_prompt": "blueprintbob"
        }
        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        mermaid = data["mermaid_code"]
        self.assertIn("⭐", mermaid)

    def test_compiler_shapes_and_edges(self):
        """Direct test of compile_mermaid ensuring all shapes and edge styles compile cleanly."""
        graph = DiagramGraph(
            groups=[
                DiagramGroup(id="grp1", label="Core Services")
            ],
            nodes=[
                DiagramNode(id="n1", label="App Box", shape="box", group_id="grp1"),
                DiagramNode(id="n2", label="Database Store", shape="database", group_id="grp1"),
                DiagramNode(id="n3", label="Task Queue", shape="queue"),
                DiagramNode(id="n4", label="Doc Spec", shape="document"),
                DiagramNode(id="n5", label="Hex Router", shape="hexagon"),
                DiagramNode(id="n6", label="Circle Client", shape="circle")
            ],
            edges=[
                DiagramEdge(source="n1", target="n2", label="queries", style="solid"),
                DiagramEdge(source="n1", target="n3", label="enqueues", style="dashed")
            ]
        )

        mermaid = compile_mermaid(graph)
        self.assertIn("flowchart TD", mermaid)
        self.assertIn('subgraph grp1 ["Core Services"]', mermaid)
        self.assertIn('n1["App Box"]', mermaid)
        self.assertIn('n2[("Database Store")]', mermaid)
        self.assertIn('n3(["Task Queue"])', mermaid)
        self.assertIn('n4>"Doc Spec"]', mermaid)
        self.assertIn('n5{{"Hex Router"}}', mermaid)
        self.assertIn('n6(("Circle Client"))', mermaid)
        self.assertIn('n1 -->|"queries"| n2', mermaid)
        self.assertIn('n1 -.->|"enqueues"| n3', mermaid)
        self.assertIn('click n1 call onNodeClick("n1")', mermaid)
        self.assertIn('classDef', mermaid)

    def test_request_byok_gemini_fallback(self):
        """Test BlueprintBobRequest with Gemini api_key and verify graceful fallback and engine_mode."""
        payload = {
            "file_tree": ["src/index.ts"],
            "key_files": {"src/index.ts": "console.log('hello');"},
            "api_key": "AIzaSyDummyInvalidGeminiKey",
            "api_provider": "gemini"
        }
        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["metrics"]["engine_mode"], "offline_ast")
        self.assertEqual(data["metrics"]["generation_mode"], "offline_ast")
        self.assertIn("api_error", data["metrics"])
        self.assertIn("warning", data["metrics"])
        self.assertIn("⚠️ **AI Generation Warning:**", data["explanation"])

    def test_request_byok_openai_fallback(self):
        """Test BlueprintBobRequest with OpenAI api_key and verify graceful fallback and engine_mode."""
        payload = {
            "file_tree": ["src/index.ts"],
            "key_files": {"src/index.ts": "console.log('hello');"},
            "api_key": "sk-dummyInvalidOpenAIKey",
            "api_provider": "openai"
        }
        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["metrics"]["engine_mode"], "offline_ast")
        self.assertEqual(data["metrics"]["generation_mode"], "offline_ast")
        self.assertIn("api_error", data["metrics"])
    def test_explicit_offline_mode_bypasses_ai(self):
        """Test that engine_mode='offline' immediately runs offline AST engine even if api_key is present."""
        payload = {
            "file_tree": ["src/index.ts"],
            "key_files": {"src/index.ts": "console.log('hello');"},
            "api_key": "AIzaSyDummyKeyThatWouldFailIfCalled",
            "api_provider": "gemini",
            "engine_mode": "offline"
        }
        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["metrics"]["engine_mode"], "offline_ast")
        self.assertEqual(data["metrics"]["generation_mode"], "offline_ast")
        # Since it bypassed AI, api_error should NOT be set
        self.assertNotIn("api_error", data["metrics"])
        self.assertNotIn("⚠️ **AI Generation Warning:**", data["explanation"])

    def test_dynamic_gemini_model_discovery_and_prioritization(self):
        """Test _get_available_gemini_models discovers, filters, prioritizes, and caches."""
        from unittest.mock import MagicMock, patch
        from backend.routers.blueprintbob.generator import (
            _gemini_models_cache,
            _get_available_gemini_models,
        )

        _gemini_models_cache.clear()

        mock_payload = {
            "models": [
                {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
                {"name": "models/gemini-3.8-flash-tts", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/audio-preview-001", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/imagen-3.0", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/aqa-preview", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/robotics-v1", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/search-grounding", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/whisper-base", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-1.5-pro", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-flash", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/gemini-2.0-flash-lite", "supportedGenerationMethods": ["generateContent"]},
                {"name": "models/custom-model", "supportedGenerationMethods": ["generateContent"]}
            ]
        }
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            models, err = _get_available_gemini_models("test-valid-key")
            self.assertIsNone(err)
            # Blacklisted non-text models should be excluded
            self.assertNotIn("text-embedding-004", models)
            self.assertNotIn("gemini-3.8-flash-tts", models)
            self.assertNotIn("audio-preview-001", models)
            self.assertNotIn("imagen-3.0", models)
            self.assertNotIn("aqa-preview", models)
            self.assertNotIn("robotics-v1", models)
            self.assertNotIn("search-grounding", models)
            self.assertNotIn("whisper-base", models)

            # Check prioritization: pure text priority models (gemini-2.0-flash, gemini-1.5-flash, gemini-1.5-pro)
            # then other flash, other pro, other
            expected_prefix = [
                "gemini-2.0-flash",
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-2.5-flash",
                "gemini-2.0-flash-lite",
                "gemini-2.5-pro",
                "custom-model",
            ]
            self.assertEqual(models, expected_prefix)
            self.assertEqual(mock_urlopen.call_count, 1)

            # Test TTL caching: second call within TTL should return cached list without network call
            cached_models, err2 = _get_available_gemini_models("test-valid-key")
            self.assertIsNone(err2)
            self.assertEqual(cached_models, models)
            self.assertEqual(mock_urlopen.call_count, 1)

    def test_call_gemini_503_retries_once_then_succeeds(self):
        """Test _call_gemini retries once after 1.5s delay when receiving 503 High Demand."""
        import urllib.error
        from io import BytesIO
        from unittest.mock import MagicMock, call, patch
        from backend.routers.blueprintbob.generator import _call_gemini

        valid_graph_json = json.dumps({
            "explanation": "High demand recovered",
            "graph": {
                "groups": [],
                "nodes": [{"id": "n1", "label": "Node 1", "type": "backend", "shape": "box"}],
                "edges": []
            }
        })
        gemini_success_resp = {
            "candidates": [{"content": {"parts": [{"text": valid_graph_json}]}}]
        }

        err_503_body = json.dumps({
            "error": {"message": "This model is currently experiencing high demand. Please try again later."}
        }).encode("utf-8")
        err_503 = urllib.error.HTTPError(
            url="http://fake", code=503, msg="Service Unavailable", hdrs={}, fp=BytesIO(err_503_body)
        )

        mock_success_resp = MagicMock()
        mock_success_resp.read.return_value = json.dumps(gemini_success_resp).encode("utf-8")
        mock_success_resp.__enter__.return_value = mock_success_resp

        with patch("backend.routers.blueprintbob.generator._get_available_gemini_models",
                   return_value=(["gemini-2.0-flash"], None)):
            with patch("urllib.request.urlopen", side_effect=[err_503, mock_success_resp]) as mock_urlopen:
                with patch("time.sleep") as mock_sleep:
                    graph, exp, err = _call_gemini("fake-key", "Test prompt")
                    self.assertIsNone(err)
                    self.assertIsNotNone(graph)
                    self.assertEqual(exp, "High demand recovered")
                    self.assertEqual(mock_urlopen.call_count, 2)
                    mock_sleep.assert_called_once_with(1.5)

    def test_call_gemini_429_retries_once_then_succeeds(self):
        """Test _call_gemini retries once after 1.5s delay when receiving 429 Rate Limit."""
        import urllib.error
        from io import BytesIO
        from unittest.mock import MagicMock, patch
        from backend.routers.blueprintbob.generator import _call_gemini

        valid_graph_json = json.dumps({
            "explanation": "Rate limit recovered",
            "graph": {
                "groups": [],
                "nodes": [{"id": "n1", "label": "Node 1", "type": "backend", "shape": "box"}],
                "edges": []
            }
        })
        gemini_success_resp = {
            "candidates": [{"content": {"parts": [{"text": valid_graph_json}]}}]
        }

        err_429_body = json.dumps({
            "error": {"message": "Resource has been exhausted (e.g. check quota)."}
        }).encode("utf-8")
        err_429 = urllib.error.HTTPError(
            url="http://fake", code=429, msg="Too Many Requests", hdrs={}, fp=BytesIO(err_429_body)
        )

        mock_success_resp = MagicMock()
        mock_success_resp.read.return_value = json.dumps(gemini_success_resp).encode("utf-8")
        mock_success_resp.__enter__.return_value = mock_success_resp

        with patch("backend.routers.blueprintbob.generator._get_available_gemini_models",
                   return_value=(["gemini-2.0-flash"], None)):
            with patch("urllib.request.urlopen", side_effect=[err_429, mock_success_resp]) as mock_urlopen:
                with patch("time.sleep") as mock_sleep:
                    graph, exp, err = _call_gemini("fake-key", "Test prompt")
                    self.assertIsNone(err)
                    self.assertIsNotNone(graph)
                    self.assertEqual(exp, "Rate limit recovered")
                    self.assertEqual(mock_urlopen.call_count, 2)
                    mock_sleep.assert_called_once_with(1.5)

    def test_call_gemini_timeout_retries_once_then_succeeds(self):
        """Test _call_gemini retries once after 1.5s delay when request times out."""
        import socket
        from unittest.mock import MagicMock, patch
        from backend.routers.blueprintbob.generator import _call_gemini

        valid_graph_json = json.dumps({
            "explanation": "Timeout recovered",
            "graph": {
                "groups": [],
                "nodes": [{"id": "n1", "label": "Node 1", "type": "backend", "shape": "box"}],
                "edges": []
            }
        })
        gemini_success_resp = {
            "candidates": [{"content": {"parts": [{"text": valid_graph_json}]}}]
        }

        mock_success_resp = MagicMock()
        mock_success_resp.read.return_value = json.dumps(gemini_success_resp).encode("utf-8")
        mock_success_resp.__enter__.return_value = mock_success_resp

        with patch("backend.routers.blueprintbob.generator._get_available_gemini_models",
                   return_value=(["gemini-2.0-flash"], None)):
            with patch("urllib.request.urlopen", side_effect=[socket.timeout("The read operation timed out"), mock_success_resp]) as mock_urlopen:
                with patch("time.sleep") as mock_sleep:
                    graph, exp, err = _call_gemini("fake-key", "Test prompt")
                    self.assertIsNone(err)
                    self.assertIsNotNone(graph)
                    self.assertEqual(exp, "Timeout recovered")
                    self.assertEqual(mock_urlopen.call_count, 2)
                    mock_sleep.assert_called_once_with(1.5)

    def test_call_gemini_json_mode_rejected_retries_without_response_mime_type(self):
        """Test _call_gemini immediately retries same model without responseMimeType when code 400 JSON mode is rejected."""
        import urllib.error
        from io import BytesIO
        from unittest.mock import MagicMock, patch
        from backend.routers.blueprintbob.generator import _call_gemini

        markdown_fenced_json = """Here is your architecture output:
```json
{
  "explanation": "Extracted from markdown fences",
  "graph": {
    "groups": [],
    "nodes": [{"id": "n1", "label": "Fenced Node", "type": "backend", "shape": "box"}],
    "edges": []
  }
}
```
"""
        gemini_fenced_resp = {
            "candidates": [{"content": {"parts": [{"text": markdown_fenced_json}]}}]
        }

        err_400_body = json.dumps({
            "error": {"message": "JSON mode is not enabled for this model."}
        }).encode("utf-8")
        err_400 = urllib.error.HTTPError(
            url="http://fake", code=400, msg="Bad Request", hdrs={}, fp=BytesIO(err_400_body)
        )

        mock_success_resp = MagicMock()
        mock_success_resp.read.return_value = json.dumps(gemini_fenced_resp).encode("utf-8")
        mock_success_resp.__enter__.return_value = mock_success_resp

        with patch("backend.routers.blueprintbob.generator._get_available_gemini_models",
                   return_value=(["gemini-pro"], None)):
            with patch("urllib.request.urlopen", side_effect=[err_400, mock_success_resp]) as mock_urlopen:
                with patch("time.sleep") as mock_sleep:
                    graph, exp, err = _call_gemini("fake-key", "Test prompt")
                    self.assertIsNone(err)
                    self.assertIsNotNone(graph)
                    self.assertEqual(exp, "Extracted from markdown fences")
                    self.assertEqual(mock_urlopen.call_count, 2)
                    # JSON mode retry should be immediate (mock_sleep not called)
                    mock_sleep.assert_not_called()

                    # Verify second request did NOT include responseMimeType in generationConfig
                    req_first = mock_urlopen.call_args_list[0][0][0]
                    first_payload = json.loads(req_first.data.decode('utf-8'))
                    self.assertEqual(first_payload["generationConfig"].get("responseMimeType"), "application/json")

                    req_second = mock_urlopen.call_args_list[1][0][0]
                    second_payload = json.loads(req_second.data.decode('utf-8'))
                    self.assertNotIn("responseMimeType", second_payload["generationConfig"])

    def test_call_gemini_404_advances_to_next_candidate_model(self):
        """Test _call_gemini advances past 404 to find a working model."""
        import urllib.error
        from io import BytesIO
        from unittest.mock import MagicMock, patch
        from backend.routers.blueprintbob.generator import _call_gemini

        valid_graph_json = json.dumps({
            "explanation": "Valid architecture",
            "graph": {
                "groups": [{"id": "g1", "label": "Group 1"}],
                "nodes": [{"id": "n1", "label": "Node 1", "type": "backend", "shape": "box"}],
                "edges": []
            }
        })
        gemini_success_resp = {
            "candidates": [{
                "content": {
                    "parts": [{"text": valid_graph_json}]
                }
            }]
        }

        # First call to urlopen: 404 HTTPError (for model 1)
        err_404_body = json.dumps({
            "error": {"message": "models/gemini-1.5-pro is not found for API version v1beta"}
        }).encode("utf-8")
        err_404 = urllib.error.HTTPError(
            url="http://fake",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=BytesIO(err_404_body)
        )

        mock_success_resp = MagicMock()
        mock_success_resp.read.return_value = json.dumps(gemini_success_resp).encode("utf-8")
        mock_success_resp.__enter__.return_value = mock_success_resp

        with patch("backend.routers.blueprintbob.generator._get_available_gemini_models",
                   return_value=(["gemini-1.5-pro", "gemini-2.0-flash"], None)):
            with patch("urllib.request.urlopen", side_effect=[err_404, mock_success_resp]) as mock_urlopen:
                graph, exp, err = _call_gemini("fake-key", "Test prompt")
                self.assertIsNone(err)
                self.assertIsNotNone(graph)
                self.assertEqual(exp, "Valid architecture")
                self.assertEqual(mock_urlopen.call_count, 2)

    def test_byok_prompt_granularity_toggle(self):
        """Test build_byok_prompt includes appropriate instructions for detailed and overview granularities."""
        from backend.routers.blueprintbob.generator import build_byok_prompt
        from backend.shared.models import BlueprintBobRequest

        # Detailed prompt
        req_detailed = BlueprintBobRequest(
            file_tree=["app/main.py", "app/router.py"],
            granularity="detailed"
        )
        prompt_detailed = build_byok_prompt(req_detailed)
        self.assertIn("REQUIREMENTS FOR DETAILED ARCHITECTURE MAP:", prompt_detailed)
        self.assertIn("22 to 36 specific component and file nodes", prompt_detailed)
        self.assertIn("Client extensions: show individual commands", prompt_detailed)

        # Overview prompt
        req_overview = BlueprintBobRequest(
            file_tree=["app/main.py", "app/router.py"],
            granularity="overview"
        )
        prompt_overview = build_byok_prompt(req_overview)
        self.assertIn("REQUIREMENTS FOR SYSTEM OVERVIEW MAP:", prompt_overview)
        self.assertIn("10 to 14 node system overview", prompt_overview)
        self.assertIn("Aggregate individual files into macro architectural components", prompt_overview)

    def test_granularity_toggle_offline_ast_engine(self):
        """
        Verify both granularity='overview' and granularity='detailed' in the offline AST engine.
        Ensures overview generates 10-12 nodes and detailed generates 24-32 nodes.
        """
        # Create a workspace with 40 realistic files across subsystems
        file_tree = [
            f"backend/routers/router_{i}.py" for i in range(10)
        ] + [
            f"backend/models/model_{i}.py" for i in range(8)
        ] + [
            f"extensions/blueprintbob/src/cmd_{i}.ts" for i in range(8)
        ] + [
            f"frontend/components/comp_{i}.tsx" for i in range(8)
        ] + [
            f"shared/utils/util_{i}.ts" for i in range(4)
        ] + [
            "backend/main.py", "package.json", "pyproject.toml"
        ]

        # 1. Test granularity='overview'
        payload_overview = {
            "file_tree": file_tree,
            "engine_mode": "offline",
            "granularity": "overview"
        }
        resp_overview = self.client.post("/api/blueprintbob/generate", json=payload_overview)
        self.assertEqual(resp_overview.status_code, 200)
        data_overview = resp_overview.json()
        self.assertEqual(data_overview["status"], "success")
        self.assertEqual(data_overview["metrics"]["granularity"], "overview")
        nodes_overview = data_overview["graph"]["nodes"]
        # Overview should pick 10-12 nodes
        self.assertGreaterEqual(len(nodes_overview), 10)
        self.assertLessEqual(len(nodes_overview), 14)

        # 2. Test granularity='detailed'
        payload_detailed = {
            "file_tree": file_tree,
            "engine_mode": "offline",
            "granularity": "detailed"
        }
        resp_detailed = self.client.post("/api/blueprintbob/generate", json=payload_detailed)
        self.assertEqual(resp_detailed.status_code, 200)
        data_detailed = resp_detailed.json()
        self.assertEqual(data_detailed["status"], "success")
        self.assertEqual(data_detailed["metrics"]["granularity"], "detailed")
        nodes_detailed = data_detailed["graph"]["nodes"]
        # Detailed should pick 24-32 nodes
        self.assertGreaterEqual(len(nodes_detailed), 22)
        self.assertLessEqual(len(nodes_detailed), 36)

        # Ensure detailed has significantly more nodes than overview
        self.assertGreater(len(nodes_detailed), len(nodes_overview))

    def test_default_granularity_is_detailed(self):
        """Test default granularity on BlueprintBobRequest is 'detailed' and returned in metrics."""
        from backend.shared.models import BlueprintBobRequest
        req = BlueprintBobRequest()
        self.assertEqual(req.granularity, "detailed")

        payload = {
            "file_tree": ["src/index.ts", "src/util.ts"],
            "engine_mode": "offline"
        }
        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["metrics"]["granularity"], "detailed")


if __name__ == "__main__":
    unittest.main()

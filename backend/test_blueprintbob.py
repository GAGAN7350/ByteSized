"""Unit tests for BlueprintBob Architecture Engine.

Verifies the Universal Dual-Engine Architecture:
- Complete removal of hardcoded ByteSized mocks
- Universal Offline AST & Docstring Engine functionality on generic codebases (Python, Next.js, etc.)
- Real AST docstring and JSDoc extraction
- Cross-module import and dependency edge resolution
- BYOK mode graceful fallback on API errors
- Mermaid diagram compiler shapes and styling
"""
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


if __name__ == "__main__":
    unittest.main()

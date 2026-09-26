"""Unit tests for BlueprintBob Architecture Engine."""
import unittest
from fastapi.testclient import TestClient

from backend.main import app
from backend.shared.models import (
    DiagramGraph,
    DiagramNode,
    DiagramEdge,
    DiagramGroup
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

    def test_generate_endpoint_with_sample_tree(self):
        """Test /api/blueprintbob/generate with a sample multi-extension codebase tree."""
        sample_tree = [
            "backend/main.py",
            "backend/shared/models.py",
            "backend/routers/blueprintbob/router.py",
            "backend/routers/rtl/router.py",
            "backend/test_blueprintbob.py",
            "extensions/blueprintbob/src/extension.ts",
            "extensions/siliconbob-rtl/src/extension.ts",
            "extensions/shared/src/index.ts",
            "package.json",
            "README.md",
            "node_modules/dummy/index.js",
            ".git/HEAD",
            "backend/__pycache__/main.cpython-310.pyc"
        ]

        payload = {
            "file_tree": sample_tree,
            "readme": "# ByteSized Project",
            "manifest": "{\"name\": \"bytesized\"}",
            "custom_prompt": None
        }

        resp = self.client.post("/api/blueprintbob/generate", json=payload)
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("flowchart TD", data["mermaid_code"])
        self.assertIn("subgraph", data["mermaid_code"])
        self.assertIn("-->", data["mermaid_code"])
        self.assertIn("BlueprintBob", data["explanation"])

        # Check graph structure
        graph = data.get("graph")
        self.assertIsNotNone(graph)
        self.assertGreater(len(graph["groups"]), 0)
        self.assertGreater(len(graph["nodes"]), 0)
        self.assertGreater(len(graph["edges"]), 0)

        # Check filtering of noise in metrics
        metrics = data.get("metrics")
        self.assertEqual(metrics["total_files"], len(sample_tree))
        # node_modules, .git, and __pycache__ must be filtered out
        self.assertLess(metrics["scanned_files"], len(sample_tree))

    def test_generate_with_custom_prompt(self):
        """Test /api/blueprintbob/generate highlighting components when custom_prompt is provided."""
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
        self.assertIn("subgraph grp1 [\"Core Services\"]", mermaid)
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

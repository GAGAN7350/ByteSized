from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RTLIssue(BaseModel):
    line: int
    column: int
    severity: str  # "error" or "warning"
    message: str
    rule_id: str


class OptimizeRequest(BaseModel):
    code: Optional[str] = None
    verilog_code: Optional[str] = None  # for backward compatibility
    language: Optional[str] = "verilog"
    file_path: Optional[str] = "input.txt"
    target: Optional[str] = "ppa"  # "ppa", "synthesizability", "timing", "performance"

    def get_source_code(self) -> str:
        return self.code if self.code is not None else (self.verilog_code or "")


class OptimizeResponse(BaseModel):
    status: str
    issues: List[RTLIssue]
    optimized_code: str
    metrics: Dict[str, str]


class DiagramNode(BaseModel):
    id: str
    label: str
    type: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    shape: Optional[str] = "box"
    group_id: Optional[str] = None


class DiagramEdge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None
    style: Optional[str] = "solid"


class DiagramGroup(BaseModel):
    id: str
    label: str
    description: Optional[str] = None


class DiagramGraph(BaseModel):
    groups: List[DiagramGroup] = Field(default_factory=list)
    nodes: List[DiagramNode] = Field(default_factory=list)
    edges: List[DiagramEdge] = Field(default_factory=list)


class BlueprintBobRequest(BaseModel):
    file_tree: List[str] = Field(default_factory=list)
    readme: Optional[str] = None
    manifest: Optional[str] = None
    key_files: Dict[str, str] = Field(default_factory=dict)
    custom_prompt: Optional[str] = None
    repo_url: Optional[str] = None
    api_key: Optional[str] = None
    api_provider: Optional[str] = "gemini"  # "gemini" or "openai"
    engine_mode: Optional[str] = "ai"  # "ai" or "offline"
    granularity: Optional[str] = "detailed"  # "overview" or "detailed"


class BlueprintBobResponse(BaseModel):
    status: str
    mermaid_code: str
    explanation: str
    graph: Optional[DiagramGraph] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)


# Backwards compatibility aliases
GitDiagramRequest = BlueprintBobRequest
GitDiagramResponse = BlueprintBobResponse

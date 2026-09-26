from typing import Dict, List, Optional
from pydantic import BaseModel


class RTLIssue(BaseModel):
    line: int
    column: int
    severity: str  # "error" or "warning"
    message: str
    rule_id: str


class OptimizeRequest(BaseModel):
    verilog_code: str
    file_path: Optional[str] = "input.v"
    target: Optional[str] = "ppa"  # "ppa", "synthesizability", "timing"


class OptimizeResponse(BaseModel):
    status: str
    issues: List[RTLIssue]
    optimized_code: str
    metrics: Dict[str, str]

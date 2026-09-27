"""Pydantic models for the CycleSim REST API."""
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel


class GateSpec(BaseModel):
    name: str
    gate_type: str  # "and","or","xor","not","nand","nor","xnor","buf","mux"
    inputs: List[str]
    output: str


class FlipFlopSpec(BaseModel):
    name: str
    ff_type: Literal["dff", "jkff"] = "dff"
    clk: str
    # DFF signals
    d: Optional[str] = None
    q: Optional[str] = None
    q_bar: Optional[str] = None
    # JK-FF signals
    j: Optional[str] = None
    k: Optional[str] = None
    # Reset
    rst: Optional[str] = None
    rst_sync: bool = False
    rst_active: int = 0  # 0 = active-low, 1 = active-high


class StimulusEvent(BaseModel):
    signal: str
    value: int   # 0=L0, 1=L1, 2=LX, 3=LZ
    at_time_ps: int


class SimulateRequest(BaseModel):
    gates: List[GateSpec] = []
    flip_flops: List[FlipFlopSpec] = []
    stimuli: List[StimulusEvent] = []
    clock_signal: Optional[str] = None
    clock_period_ps: int = 10
    run_until_ps: int = 200
    # Shortcut: run a built-in example
    example: Optional[Literal["ripple_counter", "dff_chain"]] = None


class SignalState(BaseModel):
    name: str
    final_value: str   # "L0", "L1", "LX", "LZ"


class SimulateResponse(BaseModel):
    status: str
    vcd: str
    signals: List[SignalState]
    event_count: int
    cycle_count: int
    sim_time_ps: int

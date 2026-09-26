"""
ByteSized Cycle-Accurate 4-State Verilog Logic Simulator
=========================================================

Implements a complete event-driven, delta-cycle–resolved digital logic simulator
supporting the four-value logic system {0, 1, X, Z}, a VCD waveform exporter,
non-blocking assignment (NBA) deferred update queues, sensitivity list evaluation,
and a library of standard combinational gates plus edge-triggered flip-flop registers.

Logic Value Encoding
--------------------
    LOGIC_0 = 0   (strong drive low)
    LOGIC_1 = 1   (strong drive high)
    LOGIC_X = 2   (unknown / indeterminate)
    LOGIC_Z = 3   (high-impedance / tri-state)

Architecture
------------
    SimulationEngine
        ├── SignalNet            — named 4-state signal with change history
        ├── EventQueue          — time-ordered delta-cycle event scheduler
        ├── SensitivityEvaluator — evaluates always-block triggers
        ├── NBAssignQueue       — deferred non-blocking assignment store
        ├── GateLibrary         — AND, OR, XOR, NOT, NAND, NOR, MUX primitives
        ├── FlipFlop            — D/JK/SR flip-flop with sync/async reset
        └── VCDExporter         — IEEE 1364-1995 Value Change Dump writer
"""

from __future__ import annotations

import heapq
import time
import textwrap
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Callable, Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# 1. FOUR-VALUE LOGIC SYSTEM
# ---------------------------------------------------------------------------

class Logic(IntEnum):
    """Four-value logic enumeration matching IEEE 1364 / IEEE 1800 std_logic."""
    L0 = 0   # Strong-drive logic zero
    L1 = 1   # Strong-drive logic one
    LX = 2   # Unknown / uninitialized
    LZ = 3   # High-impedance (tri-state)

    def __str__(self) -> str:
        return {Logic.L0: "0", Logic.L1: "1", Logic.LX: "x", Logic.LZ: "z"}[self]

    def __repr__(self) -> str:
        return f"Logic.{self.name}"


# ---------- Four-value truth tables ----------

_AND_TABLE: Dict[Tuple[Logic, Logic], Logic] = {
    (Logic.L0, Logic.L0): Logic.L0, (Logic.L0, Logic.L1): Logic.L0,
    (Logic.L0, Logic.LX): Logic.L0, (Logic.L0, Logic.LZ): Logic.L0,
    (Logic.L1, Logic.L0): Logic.L0, (Logic.L1, Logic.L1): Logic.L1,
    (Logic.L1, Logic.LX): Logic.LX, (Logic.L1, Logic.LZ): Logic.LX,
    (Logic.LX, Logic.L0): Logic.L0, (Logic.LX, Logic.L1): Logic.LX,
    (Logic.LX, Logic.LX): Logic.LX, (Logic.LX, Logic.LZ): Logic.LX,
    (Logic.LZ, Logic.L0): Logic.L0, (Logic.LZ, Logic.L1): Logic.LX,
    (Logic.LZ, Logic.LX): Logic.LX, (Logic.LZ, Logic.LZ): Logic.LX,
}

_OR_TABLE: Dict[Tuple[Logic, Logic], Logic] = {
    (Logic.L0, Logic.L0): Logic.L0, (Logic.L0, Logic.L1): Logic.L1,
    (Logic.L0, Logic.LX): Logic.LX, (Logic.L0, Logic.LZ): Logic.LX,
    (Logic.L1, Logic.L0): Logic.L1, (Logic.L1, Logic.L1): Logic.L1,
    (Logic.L1, Logic.LX): Logic.L1, (Logic.L1, Logic.LZ): Logic.L1,
    (Logic.LX, Logic.L0): Logic.LX, (Logic.LX, Logic.L1): Logic.L1,
    (Logic.LX, Logic.LX): Logic.LX, (Logic.LX, Logic.LZ): Logic.LX,
    (Logic.LZ, Logic.L0): Logic.LX, (Logic.LZ, Logic.L1): Logic.L1,
    (Logic.LZ, Logic.LX): Logic.LX, (Logic.LZ, Logic.LZ): Logic.LX,
}

_XOR_TABLE: Dict[Tuple[Logic, Logic], Logic] = {
    (Logic.L0, Logic.L0): Logic.L0, (Logic.L0, Logic.L1): Logic.L1,
    (Logic.L0, Logic.LX): Logic.LX, (Logic.L0, Logic.LZ): Logic.LX,
    (Logic.L1, Logic.L0): Logic.L1, (Logic.L1, Logic.L1): Logic.L0,
    (Logic.L1, Logic.LX): Logic.LX, (Logic.L1, Logic.LZ): Logic.LX,
    (Logic.LX, Logic.L0): Logic.LX, (Logic.LX, Logic.L1): Logic.LX,
    (Logic.LX, Logic.LX): Logic.LX, (Logic.LX, Logic.LZ): Logic.LX,
    (Logic.LZ, Logic.L0): Logic.LX, (Logic.LZ, Logic.L1): Logic.LX,
    (Logic.LZ, Logic.LX): Logic.LX, (Logic.LZ, Logic.LZ): Logic.LX,
}

_NOT_TABLE: Dict[Logic, Logic] = {
    Logic.L0: Logic.L1,
    Logic.L1: Logic.L0,
    Logic.LX: Logic.LX,
    Logic.LZ: Logic.LX,
}


def gate_and(a: Logic, b: Logic) -> Logic:
    return _AND_TABLE[(a, b)]

def gate_or(a: Logic, b: Logic) -> Logic:
    return _OR_TABLE[(a, b)]

def gate_xor(a: Logic, b: Logic) -> Logic:
    return _XOR_TABLE[(a, b)]

def gate_not(a: Logic) -> Logic:
    return _NOT_TABLE[a]

def gate_nand(a: Logic, b: Logic) -> Logic:
    return gate_not(gate_and(a, b))

def gate_nor(a: Logic, b: Logic) -> Logic:
    return gate_not(gate_or(a, b))

def gate_xnor(a: Logic, b: Logic) -> Logic:
    return gate_not(gate_xor(a, b))

def gate_mux(sel: Logic, a: Logic, b: Logic) -> Logic:
    """2-to-1 MUX: output = sel ? b : a"""
    if sel == Logic.L0:
        return a
    elif sel == Logic.L1:
        return b
    elif sel == Logic.LX:
        # If both inputs are identical, result is known regardless of select
        if a == b:
            return a
        return Logic.LX
    else:  # LZ
        return Logic.LX

def gate_buf(a: Logic) -> Logic:
    """Buffer gate — drives output equal to input; Z becomes X on driven wire."""
    return Logic.LX if a == Logic.LZ else a


# ---------------------------------------------------------------------------
# 2. SIGNAL NET
# ---------------------------------------------------------------------------

@dataclass
class SignalNet:
    """
    A named 4-state signal that tracks its current value and complete change history.
    Supports scalar and multi-bit (vector) width, though the simulator uses per-bit nets.
    """
    name: str
    width: int = 1
    initial: Logic = Logic.LX

    def __post_init__(self) -> None:
        self._value: Logic = self.initial
        # History: list of (simulation_time_ps, delta, new_logic_value)
        self._history: List[Tuple[int, int, Logic]] = []
        self._change_callbacks: List[Callable[["SignalNet", Logic, Logic], None]] = []

    @property
    def value(self) -> Logic:
        return self._value

    def drive(self, new_val: Logic, sim_time_ps: int, delta: int) -> bool:
        """
        Drive the signal to new_val. Returns True if the value changed.
        Records the transition in history and fires all registered callbacks.
        """
        if new_val == self._value:
            return False
        old_val = self._value
        self._value = new_val
        self._history.append((sim_time_ps, delta, new_val))
        for cb in self._change_callbacks:
            cb(self, old_val, new_val)
        return True

    def register_change_callback(self, cb: Callable[["SignalNet", Logic, Logic], None]) -> None:
        self._change_callbacks.append(cb)

    def get_history(self) -> List[Tuple[int, int, Logic]]:
        return list(self._history)

    def posedge_at(self, sim_time_ps: int, delta: int) -> bool:
        """True if the most recent event at this time/delta is a 0->1 transition."""
        for t, d, v in reversed(self._history):
            if t == sim_time_ps and d == delta:
                idx = self._history.index((t, d, v))
                if idx > 0:
                    prev_v = self._history[idx - 1][2]
                    return prev_v == Logic.L0 and v == Logic.L1
                return False
        return False

    def negedge_at(self, sim_time_ps: int, delta: int) -> bool:
        """True if the most recent event at this time/delta is a 1->0 transition."""
        for t, d, v in reversed(self._history):
            if t == sim_time_ps and d == delta:
                idx = self._history.index((t, d, v))
                if idx > 0:
                    prev_v = self._history[idx - 1][2]
                    return prev_v == Logic.L1 and v == Logic.L0
                return False
        return False

    def __repr__(self) -> str:
        return f"SignalNet({self.name!r}, val={self._value})"


# ---------------------------------------------------------------------------
# 3. EVENT QUEUE (DELTA-CYCLE SCHEDULER)
# ---------------------------------------------------------------------------

@dataclass(order=True)
class SimEvent:
    """
    An immutable simulation event scheduled at (time_ps, delta_cycle).
    Events are ordered first by absolute time, then by delta-cycle depth.
    """
    time_ps: int
    delta: int
    signal: SignalNet = field(compare=False)
    new_value: Logic = field(compare=False)
    event_id: int = field(compare=False, default=0)


class EventQueue:
    """
    Min-heap priority queue for simulation events ordered by (time_ps, delta).
    Supports infinite delta-cycle resolution within a single timestep.
    """

    def __init__(self) -> None:
        self._heap: List[Tuple[int, int, int, SimEvent]] = []
        self._counter: int = 0

    def schedule(self, event: SimEvent) -> None:
        heapq.heappush(self._heap, (event.time_ps, event.delta, self._counter, event))
        self._counter += 1

    def pop_next(self) -> Optional[SimEvent]:
        if not self._heap:
            return None
        _, _, _, event = heapq.heappop(self._heap)
        return event

    def peek_time(self) -> Optional[Tuple[int, int]]:
        """Return (time_ps, delta) of the earliest pending event without removing it."""
        if not self._heap:
            return None
        return (self._heap[0][0], self._heap[0][1])

    def pop_current_timeslot(self) -> List[SimEvent]:
        """Pop all events sharing the earliest (time_ps, delta) tuple."""
        if not self._heap:
            return []
        t, d = self._heap[0][0], self._heap[0][1]
        events: List[SimEvent] = []
        while self._heap and self._heap[0][0] == t and self._heap[0][1] == d:
            _, _, _, ev = heapq.heappop(self._heap)
            events.append(ev)
        return events

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def __len__(self) -> int:
        return len(self._heap)


# ---------------------------------------------------------------------------
# 4. NON-BLOCKING ASSIGNMENT DEFERRED UPDATE QUEUE
# ---------------------------------------------------------------------------

class NBAssignQueue:
    """
    Stores deferred non-blocking assignments (NBA) for the current timestep.
    Per Verilog 2001 §5.4: all NBA RHS values are evaluated first, then all
    LHS signals are updated simultaneously at the end of the Active region.
    """

    def __init__(self) -> None:
        self._pending: List[Tuple[SignalNet, Logic]] = []

    def enqueue(self, target: SignalNet, value: Logic) -> None:
        """Record a deferred assignment: target <= value."""
        self._pending.append((target, value))

    def flush(self, sim_time_ps: int, delta: int, eq: EventQueue) -> List[Tuple[SignalNet, Logic]]:
        """
        Apply all pending non-blocking assignments.
        If any signal actually changes, schedule a new delta event for propagation.
        Returns list of (signal, new_value) pairs that changed.
        """
        changed: List[Tuple[SignalNet, Logic]] = []
        for signal, new_val in self._pending:
            old_val = signal.value
            if signal.drive(new_val, sim_time_ps, delta):
                changed.append((signal, new_val))
                # Schedule propagation event in the next delta cycle
                eq.schedule(SimEvent(
                    time_ps=sim_time_ps,
                    delta=delta + 1,
                    signal=signal,
                    new_value=new_val
                ))
        self._pending.clear()
        return changed


# ---------------------------------------------------------------------------
# 5. SENSITIVITY LIST EVALUATOR
# ---------------------------------------------------------------------------

class SensitivityEdge(IntEnum):
    ANY      = 0
    POSEDGE  = 1
    NEGEDGE  = 2

@dataclass
class SensitivityEntry:
    signal: SignalNet
    edge: SensitivityEdge = SensitivityEdge.ANY

@dataclass
class AlwaysBlock:
    """
    Represents an always @(sensitivity_list) block with an associated Python callable.
    The callable receives (sim_time_ps, delta) and may enqueue NBA updates.
    """
    name: str
    sensitivity: List[SensitivityEntry]
    action: Callable[[int, int, "SimulationEngine"], None]

class SensitivityEvaluator:
    """
    Evaluates whether a given signal change triggers a registered always block.
    Handles posedge, negedge, and any-change sensitivity entries.
    """

    def __init__(self) -> None:
        self._blocks: List[AlwaysBlock] = []
        # Maps signal name -> list of blocks sensitive to that signal
        self._signal_map: Dict[str, List[AlwaysBlock]] = defaultdict(list)

    def register_block(self, block: AlwaysBlock) -> None:
        self._blocks.append(block)
        for entry in block.sensitivity:
            self._signal_map[entry.signal.name].append(block)

    def get_triggered_blocks(
        self,
        changed_signal: SignalNet,
        old_val: Logic,
        new_val: Logic,
        sim_time_ps: int,
        delta: int
    ) -> List[AlwaysBlock]:
        """Return all always blocks triggered by a change on changed_signal."""
        triggered: List[AlwaysBlock] = []
        for block in self._signal_map.get(changed_signal.name, []):
            for entry in block.sensitivity:
                if entry.signal.name != changed_signal.name:
                    continue
                if entry.edge == SensitivityEdge.ANY:
                    triggered.append(block)
                elif entry.edge == SensitivityEdge.POSEDGE:
                    if old_val == Logic.L0 and new_val == Logic.L1:
                        triggered.append(block)
                elif entry.edge == SensitivityEdge.NEGEDGE:
                    if old_val == Logic.L1 and new_val == Logic.L0:
                        triggered.append(block)
        return triggered


# ---------------------------------------------------------------------------
# 6. FLIP-FLOP REGISTER (D, JK, SR)
# ---------------------------------------------------------------------------

class DFlipFlop:
    """
    Positive-edge-triggered D flip-flop with optional synchronous or asynchronous reset.

    Parameters
    ----------
    name        : str        — instance name
    clk         : SignalNet  — clock input (triggered on posedge)
    d           : SignalNet  — data input
    q           : SignalNet  — Q output
    q_bar       : SignalNet  — Q-bar output (optional)
    rst         : SignalNet  — reset input (optional)
    rst_sync    : bool       — True = synchronous reset, False = asynchronous
    rst_active  : Logic      — active level of reset (L1 = active high)
    """

    def __init__(
        self,
        name: str,
        clk: SignalNet,
        d: SignalNet,
        q: SignalNet,
        q_bar: Optional[SignalNet] = None,
        rst: Optional[SignalNet] = None,
        rst_sync: bool = False,
        rst_active: Logic = Logic.L1,
    ) -> None:
        self.name = name
        self.clk = clk
        self.d = d
        self.q = q
        self.q_bar = q_bar
        self.rst = rst
        self.rst_sync = rst_sync
        self.rst_active = rst_active

    def build_always_block(self, nba_queue: NBAssignQueue) -> AlwaysBlock:
        """
        Build and return an AlwaysBlock that implements this flip-flop's behaviour.
        If asynchronous reset: sensitivity includes rst and clk.
        If synchronous reset: sensitivity includes clk only.
        """
        sensitivity: List[SensitivityEntry] = [
            SensitivityEntry(signal=self.clk, edge=SensitivityEdge.POSEDGE)
        ]
        if self.rst is not None and not self.rst_sync:
            # Asynchronous reset — also sensitive to rst edge
            active_edge = SensitivityEdge.POSEDGE if self.rst_active == Logic.L1 else SensitivityEdge.NEGEDGE
            sensitivity.append(SensitivityEntry(signal=self.rst, edge=active_edge))

        ff_self = self

        def ff_action(sim_time_ps: int, delta: int, engine: "SimulationEngine") -> None:
            # Asynchronous reset — check rst regardless of clock edge
            if ff_self.rst is not None and not ff_self.rst_sync:
                if ff_self.rst.value == ff_self.rst_active:
                    nba_queue.enqueue(ff_self.q, Logic.L0)
                    if ff_self.q_bar is not None:
                        nba_queue.enqueue(ff_self.q_bar, Logic.L1)
                    return
            # Synchronous reset — only evaluate on posedge clk
            if ff_self.rst is not None and ff_self.rst_sync:
                if ff_self.rst.value == ff_self.rst_active:
                    nba_queue.enqueue(ff_self.q, Logic.L0)
                    if ff_self.q_bar is not None:
                        nba_queue.enqueue(ff_self.q_bar, Logic.L1)
                    return
            # Normal capture: Q <= D
            nba_queue.enqueue(ff_self.q, ff_self.d.value)
            if ff_self.q_bar is not None:
                nba_queue.enqueue(ff_self.q_bar, gate_not(ff_self.d.value))

        return AlwaysBlock(
            name=f"ff_{self.name}",
            sensitivity=sensitivity,
            action=ff_action
        )


class JKFlipFlop:
    """
    Negative-edge-triggered JK flip-flop with asynchronous preset and clear.

    Truth table:
        J=0 K=0 → hold (Q unchanged)
        J=0 K=1 → reset (Q=0)
        J=1 K=0 → set   (Q=1)
        J=1 K=1 → toggle
    """

    def __init__(
        self,
        name: str,
        clk: SignalNet,
        j: SignalNet,
        k: SignalNet,
        q: SignalNet,
        q_bar: Optional[SignalNet] = None,
        preset: Optional[SignalNet] = None,
        clear: Optional[SignalNet] = None,
    ) -> None:
        self.name = name
        self.clk = clk
        self.j = j
        self.k = k
        self.q = q
        self.q_bar = q_bar
        self.preset = preset
        self.clear = clear

    def build_always_block(self, nba_queue: NBAssignQueue) -> AlwaysBlock:
        sensitivity: List[SensitivityEntry] = [
            SensitivityEntry(signal=self.clk, edge=SensitivityEdge.NEGEDGE)
        ]
        jk_self = self

        def jk_action(sim_time_ps: int, delta: int, engine: "SimulationEngine") -> None:
            # Asynchronous preset
            if jk_self.preset is not None and jk_self.preset.value == Logic.L1:
                nba_queue.enqueue(jk_self.q, Logic.L1)
                if jk_self.q_bar:
                    nba_queue.enqueue(jk_self.q_bar, Logic.L0)
                return
            # Asynchronous clear
            if jk_self.clear is not None and jk_self.clear.value == Logic.L1:
                nba_queue.enqueue(jk_self.q, Logic.L0)
                if jk_self.q_bar:
                    nba_queue.enqueue(jk_self.q_bar, Logic.L1)
                return
            j_val = jk_self.j.value
            k_val = jk_self.k.value
            q_val = jk_self.q.value
            if j_val == Logic.L0 and k_val == Logic.L0:
                pass  # hold
            elif j_val == Logic.L0 and k_val == Logic.L1:
                nba_queue.enqueue(jk_self.q, Logic.L0)
                if jk_self.q_bar:
                    nba_queue.enqueue(jk_self.q_bar, Logic.L1)
            elif j_val == Logic.L1 and k_val == Logic.L0:
                nba_queue.enqueue(jk_self.q, Logic.L1)
                if jk_self.q_bar:
                    nba_queue.enqueue(jk_self.q_bar, Logic.L0)
            elif j_val == Logic.L1 and k_val == Logic.L1:
                # Toggle
                toggled = gate_not(q_val) if q_val in (Logic.L0, Logic.L1) else Logic.LX
                nba_queue.enqueue(jk_self.q, toggled)
                if jk_self.q_bar:
                    nba_queue.enqueue(jk_self.q_bar, gate_not(toggled))
            else:
                nba_queue.enqueue(jk_self.q, Logic.LX)

        return AlwaysBlock(
            name=f"jk_{self.name}",
            sensitivity=sensitivity,
            action=jk_action
        )


# ---------------------------------------------------------------------------
# 7. COMBINATIONAL GATE PRIMITIVE
# ---------------------------------------------------------------------------

class GatePrimitive:
    """
    A single combinational gate instance that auto-propagates via the event queue.
    Inputs are SignalNets; output is a SignalNet. The gate recomputes its output
    whenever any input changes (purely combinational, zero propagation delay).
    """

    SUPPORTED = {"and", "or", "xor", "not", "nand", "nor", "xnor", "buf", "mux"}

    def __init__(
        self,
        name: str,
        gate_type: str,
        inputs: List[SignalNet],
        output: SignalNet,
    ) -> None:
        if gate_type.lower() not in self.SUPPORTED:
            raise ValueError(f"Unsupported gate type: {gate_type!r}. Supported: {self.SUPPORTED}")
        self.name = name
        self.gate_type = gate_type.lower()
        self.inputs = inputs
        self.output = output

    def evaluate(self) -> Logic:
        """Compute the gate output from current input values."""
        gtype = self.gate_type
        vals = [inp.value for inp in self.inputs]
        if gtype == "not" or gtype == "buf":
            if len(vals) != 1:
                raise ValueError(f"{gtype} gate requires exactly 1 input, got {len(vals)}")
            return gate_not(vals[0]) if gtype == "not" else gate_buf(vals[0])
        if gtype == "mux":
            if len(vals) != 3:
                raise ValueError(f"mux gate requires exactly 3 inputs (sel, a, b), got {len(vals)}")
            return gate_mux(vals[0], vals[1], vals[2])
        # Reduce multi-input gates left to right
        result = vals[0]
        op = {"and": gate_and, "or": gate_or, "xor": gate_xor,
              "nand": gate_nand, "nor": gate_nor, "xnor": gate_xnor}[gtype]
        for v in vals[1:]:
            result = op(result, v)
        return result

    def build_always_block(self) -> AlwaysBlock:
        """Return an AlwaysBlock that recomputes and propagates the gate output on any input change."""
        gate_self = self

        def gate_action(sim_time_ps: int, delta: int, engine: "SimulationEngine") -> None:
            new_out = gate_self.evaluate()
            if new_out != gate_self.output.value:
                engine.event_queue.schedule(SimEvent(
                    time_ps=sim_time_ps,
                    delta=delta + 1,
                    signal=gate_self.output,
                    new_value=new_out
                ))

        return AlwaysBlock(
            name=f"gate_{self.name}",
            sensitivity=[SensitivityEntry(s, SensitivityEdge.ANY) for s in self.inputs],
            action=gate_action
        )


# ---------------------------------------------------------------------------
# 8. VCD (VALUE CHANGE DUMP) EXPORTER
# ---------------------------------------------------------------------------

class VCDExporter:
    """
    Produces IEEE 1364-1995 compliant Value Change Dump output from signal histories.

    VCD Format Structure
    --------------------
        $date      <date_string> $end
        $version   ByteSized CycleSim 2.0 $end
        $timescale 1ps $end
        $scope module top $end
            $var wire 1 ! clk $end
            $var reg  1 " d   $end
            ...
        $upscope $end
        $enddefinitions $end
        $dumpvars
            x!
            x"
        $end
        #0
        0!
        1"
        ...
    """

    _VCD_CHARS = "!\"#$%&'()*+,-./:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}"

    def __init__(self, timescale: str = "1ps") -> None:
        self.timescale = timescale
        self._signal_ids: Dict[str, str] = {}
        self._signals: List[SignalNet] = []
        self._id_counter = 0

    def register_signal(self, sig: SignalNet) -> str:
        """Assign a VCD identifier to a signal. Returns the assigned ID string."""
        if sig.name in self._signal_ids:
            return self._signal_ids[sig.name]
        if self._id_counter >= len(self._VCD_CHARS):
            raise RuntimeError("VCD identifier space exhausted (>88 signals). Use multi-char IDs.")
        vcd_id = self._VCD_CHARS[self._id_counter]
        self._signal_ids[sig.name] = vcd_id
        self._signals.append(sig)
        self._id_counter += 1
        return vcd_id

    def export(self, sim_end_time_ps: int, module_name: str = "top") -> str:
        """
        Generate the complete VCD string from all registered signals' histories.
        Merges all change events across all signals into a sorted timeline.
        """
        lines: List[str] = []
        import datetime
        lines.append(f"$date {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} $end")
        lines.append("$version ByteSized CycleSim 2.0 $end")
        lines.append(f"$timescale {self.timescale} $end")
        lines.append(f"$scope module {module_name} $end")

        for sig in self._signals:
            vcd_id = self._signal_ids[sig.name]
            var_type = "wire" if not sig.name.endswith("_q") else "reg"
            lines.append(f"    $var {var_type} 1 {vcd_id} {sig.name} $end")

        lines.append("$upscope $end")
        lines.append("$enddefinitions $end")

        # Initial values dump
        lines.append("$dumpvars")
        for sig in self._signals:
            vcd_id = self._signal_ids[sig.name]
            lines.append(f"x{vcd_id}")
        lines.append("$end")

        # Collect all change events
        # Structure: { time_ps: { signal_name: Logic } }
        timeline: Dict[int, Dict[str, Logic]] = defaultdict(dict)
        for sig in self._signals:
            for (t_ps, _delta, val) in sig.get_history():
                timeline[t_ps][sig.name] = val

        # Emit timeline entries sorted by time
        for t_ps in sorted(timeline.keys()):
            if t_ps > sim_end_time_ps:
                break
            lines.append(f"#{t_ps}")
            for sig_name, val in sorted(timeline[t_ps].items()):
                vcd_id = self._signal_ids.get(sig_name)
                if vcd_id is None:
                    continue
                val_char = {Logic.L0: "0", Logic.L1: "1", Logic.LX: "x", Logic.LZ: "z"}[val]
                lines.append(f"{val_char}{vcd_id}")

        lines.append(f"#{sim_end_time_ps}")
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 9. SIMULATION ENGINE (MAIN ENTRY POINT)
# ---------------------------------------------------------------------------

class SimulationEngine:
    """
    Main cycle-accurate 4-state event-driven simulation engine.

    Simulation Loop (per IEEE 1364 §5 Active-NBA-Monitor regions):
    ---------------------------------------------------------------
    while event_queue is not empty AND time <= max_time:
        1. Pop all events at current (time, delta)
        2. Apply signal changes (Active region)
        3. Trigger sensitivity evaluator → find triggered AlwaysBlocks
        4. Execute triggered AlwaysBlocks (may enqueue NBA updates)
        5. Flush NBA queue → apply deferred updates, schedule delta+1 events
        6. If no new events at same time → advance to next scheduled time
    """

    MAX_DELTA_CYCLES = 1000   # Oscillation guard — abort if exceeded

    def __init__(self) -> None:
        self.signals: Dict[str, SignalNet] = {}
        self.event_queue: EventQueue = EventQueue()
        self.nba_queue: NBAssignQueue = NBAssignQueue()
        self.sensitivity_eval: SensitivityEvaluator = SensitivityEvaluator()
        self.vcd: VCDExporter = VCDExporter()
        self._sim_time_ps: int = 0
        self._current_delta: int = 0
        self._cycle_count: int = 0
        self._event_count: int = 0

    # ---- Signal Management ----

    def add_signal(self, name: str, width: int = 1, initial: Logic = Logic.LX) -> SignalNet:
        """Create and register a new signal net."""
        if name in self.signals:
            raise ValueError(f"Signal '{name}' already exists.")
        sig = SignalNet(name=name, width=width, initial=initial)
        self.signals[name] = sig
        self.vcd.register_signal(sig)
        return sig

    def get_signal(self, name: str) -> SignalNet:
        if name not in self.signals:
            raise KeyError(f"Signal '{name}' not found.")
        return self.signals[name]

    # ---- Component Registration ----

    def add_gate(self, name: str, gate_type: str, inputs: List[str], output: str) -> GatePrimitive:
        """Instantiate a combinational gate and register its always block."""
        in_sigs = [self.get_signal(n) for n in inputs]
        out_sig = self.get_signal(output)
        gate = GatePrimitive(name=name, gate_type=gate_type, inputs=in_sigs, output=out_sig)
        block = gate.build_always_block()
        self.sensitivity_eval.register_block(block)
        return gate

    def add_dff(
        self,
        name: str,
        clk: str,
        d: str,
        q: str,
        q_bar: Optional[str] = None,
        rst: Optional[str] = None,
        rst_sync: bool = False,
        rst_active: Logic = Logic.L1,
    ) -> DFlipFlop:
        """Instantiate a D flip-flop and register its always block."""
        ff = DFlipFlop(
            name=name,
            clk=self.get_signal(clk),
            d=self.get_signal(d),
            q=self.get_signal(q),
            q_bar=self.get_signal(q_bar) if q_bar else None,
            rst=self.get_signal(rst) if rst else None,
            rst_sync=rst_sync,
            rst_active=rst_active,
        )
        block = ff.build_always_block(self.nba_queue)
        self.sensitivity_eval.register_block(block)
        return ff

    def add_jkff(
        self,
        name: str,
        clk: str,
        j: str,
        k: str,
        q: str,
        q_bar: Optional[str] = None,
        preset: Optional[str] = None,
        clear: Optional[str] = None,
    ) -> JKFlipFlop:
        """Instantiate a JK flip-flop and register its always block."""
        jk = JKFlipFlop(
            name=name,
            clk=self.get_signal(clk),
            j=self.get_signal(j),
            k=self.get_signal(k),
            q=self.get_signal(q),
            q_bar=self.get_signal(q_bar) if q_bar else None,
            preset=self.get_signal(preset) if preset else None,
            clear=self.get_signal(clear) if clear else None,
        )
        block = jk.build_always_block(self.nba_queue)
        self.sensitivity_eval.register_block(block)
        return jk

    def add_always_block(self, block: AlwaysBlock) -> None:
        """Register a user-defined always block directly."""
        self.sensitivity_eval.register_block(block)

    # ---- Stimulus Injection ----

    def force(self, signal_name: str, value: Logic, at_time_ps: int, delta: int = 0) -> None:
        """Schedule a stimulus event: drive signal to value at a specific simulation time."""
        sig = self.get_signal(signal_name)
        self.event_queue.schedule(SimEvent(
            time_ps=at_time_ps,
            delta=delta,
            signal=sig,
            new_value=value
        ))

    def generate_clock(
        self,
        signal_name: str,
        period_ps: int,
        duty_cycle: float = 0.5,
        start_time_ps: int = 0,
        end_time_ps: int = 10_000,
        initial_value: Logic = Logic.L0,
    ) -> None:
        """
        Pre-schedule a full clock waveform with the given period and duty cycle.
        high_time_ps = round(period_ps * duty_cycle)
        low_time_ps  = period_ps - high_time_ps
        """
        high_time_ps = round(period_ps * duty_cycle)
        low_time_ps = period_ps - high_time_ps
        t = start_time_ps
        current = initial_value
        while t <= end_time_ps:
            self.force(signal_name, current, t)
            next_val = Logic.L1 if current == Logic.L0 else Logic.L0
            hold = high_time_ps if current == Logic.L0 else low_time_ps
            t += hold
            current = next_val

    # ---- Main Simulation Loop ----

    def run(self, until_time_ps: int) -> None:
        """
        Execute the simulation until no more events are scheduled or until_time_ps is reached.
        Implements the Active → NBA → Active (delta) loop per IEEE 1364 §5.
        """
        start_wall = time.monotonic()
        prev_time = -1
        prev_delta = -1

        while not self.event_queue.is_empty():
            next_t = self.event_queue.peek_time()
            if next_t is None:
                break
            t_ps, delta = next_t
            if t_ps > until_time_ps:
                break

            # Guard against infinite delta oscillation
            if t_ps == prev_time and delta > self.MAX_DELTA_CYCLES:
                raise RuntimeError(
                    f"Delta-cycle limit ({self.MAX_DELTA_CYCLES}) exceeded at time={t_ps}ps. "
                    f"Possible combinational feedback loop (glitch oscillation)."
                )

            self._sim_time_ps = t_ps
            self._current_delta = delta
            prev_time = t_ps
            prev_delta = delta

            # --- ACTIVE REGION: process current timeslot events ---
            events = self.event_queue.pop_current_timeslot()
            self._event_count += len(events)

            for ev in events:
                old_val = ev.signal.value
                changed = ev.signal.drive(ev.new_value, t_ps, delta)
                if changed:
                    # Trigger all sensitive always blocks
                    triggered = self.sensitivity_eval.get_triggered_blocks(
                        ev.signal, old_val, ev.new_value, t_ps, delta
                    )
                    for block in triggered:
                        block.action(t_ps, delta, self)

            # --- NBA REGION: flush deferred non-blocking assignments ---
            self.nba_queue.flush(t_ps, delta, self.event_queue)
            self._cycle_count += 1

        elapsed = time.monotonic() - start_wall
        print(
            f"[CycleSim] Simulation complete. "
            f"sim_time={self._sim_time_ps}ps  "
            f"events_processed={self._event_count}  "
            f"delta_cycles={self._cycle_count}  "
            f"wall_time={elapsed*1000:.2f}ms"
        )

    # ---- Reporting ----

    def dump_signals(self) -> str:
        """Return a formatted string of all signal current values."""
        lines = ["Signal State at sim_time={}ps delta={}:".format(
            self._sim_time_ps, self._current_delta)]
        for name, sig in sorted(self.signals.items()):
            lines.append(f"  {name:30s} = {sig.value}")
        return "\n".join(lines)

    def export_vcd(self, path: str, module_name: str = "top") -> None:
        """Write the VCD waveform file to path."""
        vcd_content = self.vcd.export(self._sim_time_ps, module_name=module_name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(vcd_content)
        print(f"[CycleSim] VCD exported → {path}")


# ---------------------------------------------------------------------------
# 10. EXAMPLE TESTBENCH: 4-Bit Ripple Counter with Async Reset
# ---------------------------------------------------------------------------

def run_ripple_counter_example() -> SimulationEngine:
    """
    Demonstrates the simulator with a 4-bit ripple counter built from JK flip-flops.
    All J and K inputs are tied HIGH (Logic.L1) so each FF toggles on every falling edge.
    FF0 clocked by external clk, FF1 by Q0, FF2 by Q1, FF3 by Q2.
    """
    engine = SimulationEngine()

    # Define signals
    clk   = engine.add_signal("clk",   initial=Logic.L0)
    rst   = engine.add_signal("rst",   initial=Logic.L1)  # start in reset
    j0    = engine.add_signal("j0",    initial=Logic.L1)
    k0    = engine.add_signal("k0",    initial=Logic.L1)
    q0    = engine.add_signal("q0",    initial=Logic.L0)
    q0b   = engine.add_signal("q0b",   initial=Logic.L1)
    q1    = engine.add_signal("q1",    initial=Logic.L0)
    q1b   = engine.add_signal("q1b",   initial=Logic.L1)
    q2    = engine.add_signal("q2",    initial=Logic.L0)
    q2b   = engine.add_signal("q2b",   initial=Logic.L1)
    q3    = engine.add_signal("q3",    initial=Logic.L0)
    q3b   = engine.add_signal("q3b",   initial=Logic.L1)

    # JK Flip-Flops (negedge triggered)
    engine.add_jkff("ff0", clk="clk",  j="j0", k="k0", q="q0",  q_bar="q0b",  clear="rst")
    engine.add_jkff("ff1", clk="q0b",  j="j0", k="k0", q="q1",  q_bar="q1b",  clear="rst")
    engine.add_jkff("ff2", clk="q1b",  j="j0", k="k0", q="q2",  q_bar="q2b",  clear="rst")
    engine.add_jkff("ff3", clk="q2b",  j="j0", k="k0", q="q3",  q_bar="q3b",  clear="rst")

    # J/K inputs held HIGH
    engine.force("j0", Logic.L1, at_time_ps=0)
    engine.force("k0", Logic.L1, at_time_ps=0)

    # Release reset after 5ps
    engine.force("rst", Logic.L0, at_time_ps=5)

    # Generate 10ns clock (500ps high, 500ps low)
    engine.generate_clock("clk", period_ps=1000, duty_cycle=0.5,
                           start_time_ps=0, end_time_ps=20_000)

    engine.run(until_time_ps=20_000)
    engine.export_vcd("/tmp/ripple_counter.vcd", module_name="ripple_counter_tb")
    print(engine.dump_signals())
    return engine


def run_dff_chain_example() -> SimulationEngine:
    """
    Demonstrates a 3-stage D flip-flop shift register with synchronous reset.
    Input data is a PRBS (pseudo-random bit sequence) driven at the first stage.
    """
    engine = SimulationEngine()

    clk  = engine.add_signal("clk",  initial=Logic.L0)
    rst  = engine.add_signal("rst",  initial=Logic.L1)
    d_in = engine.add_signal("d_in", initial=Logic.L0)
    q1   = engine.add_signal("q1",   initial=Logic.LX)
    q2   = engine.add_signal("q2",   initial=Logic.LX)
    q3   = engine.add_signal("q3",   initial=Logic.LX)

    # Three D flip-flops chained
    engine.add_dff("dff0", clk="clk", d="d_in", q="q1", rst="rst", rst_sync=True)
    engine.add_dff("dff1", clk="clk", d="q1",   q="q2", rst="rst", rst_sync=True)
    engine.add_dff("dff2", clk="clk", d="q2",   q="q3", rst="rst", rst_sync=True)

    # Deassert reset at 3ps, drive a data pattern
    engine.force("rst",  Logic.L0, at_time_ps=3)
    prbs = [1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0]
    for i, bit in enumerate(prbs):
        engine.force("d_in", Logic(bit), at_time_ps=5 + i * 1000)

    engine.generate_clock("clk", period_ps=1000, duty_cycle=0.5,
                           start_time_ps=0, end_time_ps=15_000)

    engine.run(until_time_ps=15_000)
    engine.export_vcd("/tmp/dff_chain.vcd", module_name="dff_chain_tb")
    print(engine.dump_signals())
    return engine


if __name__ == "__main__":
    print("=" * 70)
    print("ByteSized CycleSim — Example 1: 4-bit Ripple Counter")
    print("=" * 70)
    run_ripple_counter_example()

    print()
    print("=" * 70)
    print("ByteSized CycleSim — Example 2: 3-Stage DFF Shift Register")
    print("=" * 70)
    run_dff_chain_example()

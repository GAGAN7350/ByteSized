"""FastAPI Router — CycleSim Gate & Flip-Flop Simulation Engine."""
from fastapi import APIRouter, HTTPException

from backend.routers.simulator.models import (
    SimulateRequest,
    SimulateResponse,
    SignalState,
)
from backend.simulators.cycle_sim import Logic, SimulationEngine

router = APIRouter(prefix="/api/simulate", tags=["CycleSim"])


@router.get("/health")
def health():
    return {"status": "online", "service": "CycleSim Gate & Flip-Flop Engine"}


@router.post("/", response_model=SimulateResponse)
def simulate(req: SimulateRequest) -> SimulateResponse:
    """
    Run a gate-level or flip-flop simulation and return waveform data as VCD.

    Pass `example="ripple_counter"` or `example="dff_chain"` to run a built-in
    demonstration without specifying gates/stimuli manually.
    """
    # ── Built-in examples (no disk I/O — inline the simulation setup) ─────
    if req.example == "ripple_counter":
        engine = SimulationEngine()
        engine.add_signal("clk",  initial=Logic.L0)
        engine.add_signal("rst",  initial=Logic.L1)
        engine.add_signal("j0",   initial=Logic.L1)
        engine.add_signal("k0",   initial=Logic.L1)
        engine.add_signal("q0",   initial=Logic.L0)
        engine.add_signal("q0b",  initial=Logic.L1)
        engine.add_signal("q1",   initial=Logic.L0)
        engine.add_signal("q1b",  initial=Logic.L1)
        engine.add_signal("q2",   initial=Logic.L0)
        engine.add_signal("q2b",  initial=Logic.L1)
        engine.add_signal("q3",   initial=Logic.L0)
        engine.add_signal("q3b",  initial=Logic.L1)
        engine.add_jkff("ff0", clk="clk",  j="j0", k="k0", q="q0", q_bar="q0b",  clear="rst")
        engine.add_jkff("ff1", clk="q0b",  j="j0", k="k0", q="q1", q_bar="q1b",  clear="rst")
        engine.add_jkff("ff2", clk="q1b",  j="j0", k="k0", q="q2", q_bar="q2b",  clear="rst")
        engine.add_jkff("ff3", clk="q2b",  j="j0", k="k0", q="q3", q_bar="q3b",  clear="rst")
        engine.force("j0", Logic.L1, at_time_ps=0)
        engine.force("k0", Logic.L1, at_time_ps=0)
        engine.force("rst", Logic.L0, at_time_ps=5)
        engine.generate_clock("clk", period_ps=1000, duty_cycle=0.5, start_time_ps=0, end_time_ps=20_000)
        engine.run(until_time_ps=20_000)

    elif req.example == "dff_chain":
        engine = SimulationEngine()
        engine.add_signal("clk",  initial=Logic.L0)
        engine.add_signal("rst",  initial=Logic.L1)
        engine.add_signal("d_in", initial=Logic.L0)
        engine.add_signal("q1",   initial=Logic.LX)
        engine.add_signal("q2",   initial=Logic.LX)
        engine.add_signal("q3",   initial=Logic.LX)
        engine.add_dff("dff0", clk="clk", d="d_in", q="q1", rst="rst", rst_sync=True)
        engine.add_dff("dff1", clk="clk", d="q1",   q="q2", rst="rst", rst_sync=True)
        engine.add_dff("dff2", clk="clk", d="q2",   q="q3", rst="rst", rst_sync=True)
        engine.force("rst", Logic.L0, at_time_ps=3)
        for i, bit in enumerate([1, 0, 1, 1, 0, 0, 1, 0, 1, 1, 1, 0]):
            engine.force("d_in", Logic(bit), at_time_ps=5 + i * 1000)
        engine.generate_clock("clk", period_ps=1000, duty_cycle=0.5, start_time_ps=0, end_time_ps=15_000)
        engine.run(until_time_ps=15_000)

    else:
        # ── Custom simulation from request ────────────────────────────────
        engine = SimulationEngine()

        # Register gates
        for g in req.gates:
            try:
                engine.add_gate(g.name, g.gate_type, g.inputs, g.output)
            except (KeyError, ValueError) as exc:
                raise HTTPException(status_code=422, detail=f"Invalid gate '{g.name}': {exc}") from exc

        # Register flip-flops
        for ff in req.flip_flops:
            if ff.ff_type == "dff":
                if not ff.d or not ff.q:
                    raise HTTPException(status_code=422, detail=f"DFF '{ff.name}' requires 'd' and 'q' signals.")
                engine.add_dff(
                    name=ff.name,
                    clk=ff.clk,
                    d=ff.d,
                    q=ff.q,
                    q_bar=ff.q_bar,
                    rst=ff.rst,
                    rst_sync=ff.rst_sync,
                    rst_active=Logic(ff.rst_active),
                )
            elif ff.ff_type == "jkff":
                if not ff.j or not ff.k or not ff.q:
                    raise HTTPException(status_code=422, detail=f"JKFF '{ff.name}' requires 'j', 'k', and 'q' signals.")
                engine.add_jkff(
                    name=ff.name,
                    clk=ff.clk,
                    j=ff.j,
                    k=ff.k,
                    q=ff.q,
                    q_bar=ff.q_bar,
                )

        # Apply stimulus events
        for ev in req.stimuli:
            if ev.signal not in engine.signals:
                engine.add_signal(ev.signal)
            engine.force(ev.signal, Logic(ev.value), ev.at_time_ps)

        # Generate clock if requested
        if req.clock_signal:
            if req.clock_signal not in engine.signals:
                engine.add_signal(req.clock_signal)
            engine.generate_clock(req.clock_signal, period_ps=req.clock_period_ps)

        # Run simulation
        engine.run(until_time_ps=req.run_until_ps)

    # ── Build response ────────────────────────────────────────────────────
    vcd_str = engine.vcd.export(
        sim_end_time_ps=engine._sim_time_ps,
        module_name="top"
    )

    signals = [
        SignalState(name=name, final_value=str(sig.value))
        for name, sig in engine.signals.items()
    ]

    return SimulateResponse(
        status="success",
        vcd=vcd_str,
        signals=signals,
        event_count=engine._event_count,
        cycle_count=engine._cycle_count,
        sim_time_ps=engine._sim_time_ps,
    )

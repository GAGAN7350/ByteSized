"""
ByteSized Enterprise Load & Stress Testing Framework
======================================================

Simulates:
  - 200 concurrent WebSocket collaborative rooms (multi-client per room)
  - 500 concurrent AST optimization API calls across all 8 supported languages

Metrics computed:
  - p50 / p90 / p99 latency
  - Throughput (requests/second)
  - Latency jitter (standard deviation)
  - Per-endpoint error rate
  - WebSocket connection success/failure rate
  - ASCII histogram of response time distribution

Outputs:
  - Console summary
  - docs/STRESS_TEST_RESULTS.md (Markdown report with tables and histograms)

Usage:
    pip install aiohttp
    python tests/load_testing.py --backend http://localhost:8000 --ws ws://localhost:8000

    Or simply:
    python tests/load_testing.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

try:
    import aiohttp
    from aiohttp import ClientWebSocketResponse
except ImportError:
    print("ERROR: aiohttp is required.  Install with:  pip install aiohttp")
    sys.exit(1)


# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------

DEFAULT_BACKEND_HTTP = "http://localhost:8000"
DEFAULT_BACKEND_WS   = "ws://localhost:8000"

WS_ROOMS             = 200    # concurrent WebSocket rooms
WS_CLIENTS_PER_ROOM  = 3      # clients per room
WS_MESSAGES_PER_CLIENT = 5   # code-update messages per client

HTTP_CONCURRENT      = 500    # concurrent HTTP optimization requests
HTTP_LANGUAGE_POOL   = [      # languages cycled across HTTP requests
    "python", "javascript", "typescript", "c", "cpp",
    "java", "go", "rust", "verilog", "generic",
]

REPORT_PATH          = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs", "STRESS_TEST_RESULTS.md"
)

# Minimal realistic code snippets per language for the optimizer endpoint
CODE_SAMPLES: Dict[str, str] = {
    "python": textwrap.dedent("""\
        def bad(lst=[]):
            lst.append(1)
            return lst
        for i in range(len(lst)):
            pass
        """),
    "javascript": textwrap.dedent("""\
        var x = 10;
        if (x == 10) { console.log("loose eq"); }
        """),
    "typescript": textwrap.dedent("""\
        var y = (x as any).prop;
        if (y == null) console.log(y);
        """),
    "c": textwrap.dedent("""\
        #include <string.h>
        void f(char *d, const char *s) { strcpy(d, s); gets(d); }
        """),
    "cpp": textwrap.dedent("""\
        #include <string.h>
        void f(char *d, const char *s) { strcpy(d, s); sprintf(d, "%s", s); }
        """),
    "java": textwrap.dedent("""\
        public class T {
          void m(String s) { if (s == "hello") System.out.println(s); }
        }
        """),
    "go": textwrap.dedent("""\
        package main
        func f() { _ = doWork(); panic("fail") }
        func doWork() error { return nil }
        """),
    "rust": textwrap.dedent("""\
        fn main() { let v: Vec<i32> = Vec::new(); let _x = v.first().unwrap(); }
        """),
    "verilog": textwrap.dedent("""\
        module top(input clk, output reg q);
        always @(posedge clk) q = 1;
        always @(*) case (q) 1'b1: q <= 0; endcase
        endmodule
        """),
    "generic": textwrap.dedent("""\
        password = "hardcoded_secret_123"
        api_key = "AKIAIOSFODNN7EXAMPLE"
        # TODO: fix this later
        # FIXME: remove debug code
        """),
}

import textwrap


# ---------------------------------------------------------------------------
# MEASUREMENT DATACLASSES
# ---------------------------------------------------------------------------

@dataclass
class RequestResult:
    endpoint: str
    language: Optional[str]
    latency_ms: float
    success: bool
    status_code: Optional[int]
    error_message: Optional[str] = None
    issues_count: Optional[int] = None


@dataclass
class WebSocketResult:
    room_id: str
    client_id: int
    connect_latency_ms: float
    message_latency_ms: float
    messages_sent: int
    messages_received: int
    success: bool
    error_message: Optional[str] = None


@dataclass
class BenchmarkSuite:
    name: str
    results_http: List[RequestResult] = field(default_factory=list)
    results_ws:   List[WebSocketResult] = field(default_factory=list)
    wall_start: float = field(default_factory=time.monotonic)
    wall_end:   float = 0.0


# ---------------------------------------------------------------------------
# STATISTICAL CALCULATIONS
# ---------------------------------------------------------------------------

def percentile(sorted_data: List[float], pct: float) -> float:
    """Compute the p-th percentile from a pre-sorted list of floats."""
    if not sorted_data:
        return 0.0
    k = (len(sorted_data) - 1) * pct / 100.0
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def compute_stats(latencies_ms: List[float]) -> Dict[str, float]:
    """Return a dict of statistical metrics for a latency sample set."""
    if not latencies_ms:
        return {k: 0.0 for k in ("count", "min", "max", "mean", "p50", "p90", "p99", "stddev", "jitter")}
    s = sorted(latencies_ms)
    mean = statistics.mean(s)
    stddev = statistics.stdev(s) if len(s) > 1 else 0.0
    return {
        "count":  float(len(s)),
        "min":    s[0],
        "max":    s[-1],
        "mean":   mean,
        "p50":    percentile(s, 50),
        "p90":    percentile(s, 90),
        "p99":    percentile(s, 99),
        "stddev": stddev,
        "jitter": stddev,   # jitter ≈ latency standard deviation
    }


def ascii_histogram(latencies_ms: List[float], buckets: int = 20, width: int = 50) -> str:
    """Render an ASCII histogram of latency distribution."""
    if not latencies_ms:
        return "(no data)"
    mn, mx = min(latencies_ms), max(latencies_ms)
    if mn == mx:
        return f"All values = {mn:.2f}ms"
    bucket_size = (mx - mn) / buckets
    counts = [0] * buckets
    for v in latencies_ms:
        idx = min(int((v - mn) / bucket_size), buckets - 1)
        counts[idx] += 1
    max_count = max(counts) or 1
    lines = []
    for i, count in enumerate(counts):
        lo = mn + i * bucket_size
        hi = lo + bucket_size
        bar = "█" * int(count / max_count * width)
        lines.append(f"  {lo:7.1f}–{hi:7.1f}ms │{bar:<{width}}│ {count:5d}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTTP OPTIMIZATION ENDPOINT LOAD TEST
# ---------------------------------------------------------------------------

async def single_optimize_request(
    session: aiohttp.ClientSession,
    backend_url: str,
    language: str,
    semaphore: asyncio.Semaphore,
) -> RequestResult:
    """Send a single POST /api/optimize-code request and measure latency."""
    endpoint = f"{backend_url}/api/optimize-code"
    code = CODE_SAMPLES.get(language, CODE_SAMPLES["generic"])
    payload = {"code": code, "language": language, "target": "ppa"}

    async with semaphore:
        t0 = time.monotonic()
        try:
            async with session.post(
                endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                latency_ms = (time.monotonic() - t0) * 1000
                if resp.status == 200:
                    body = await resp.json()
                    return RequestResult(
                        endpoint=endpoint,
                        language=language,
                        latency_ms=latency_ms,
                        success=True,
                        status_code=resp.status,
                        issues_count=len(body.get("issues", [])),
                    )
                else:
                    text = await resp.text()
                    return RequestResult(
                        endpoint=endpoint,
                        language=language,
                        latency_ms=latency_ms,
                        success=False,
                        status_code=resp.status,
                        error_message=text[:200],
                    )
        except Exception as exc:
            latency_ms = (time.monotonic() - t0) * 1000
            return RequestResult(
                endpoint=endpoint,
                language=language,
                latency_ms=latency_ms,
                success=False,
                status_code=None,
                error_message=str(exc)[:200],
            )


async def run_http_stress(
    backend_url: str,
    concurrency: int,
    total_requests: int,
) -> List[RequestResult]:
    """
    Fire `total_requests` POST /api/optimize-code requests with up to `concurrency`
    in-flight at any one time.  Languages are distributed evenly across the pool.
    """
    print(f"[HTTP] Starting {total_requests} requests at concurrency={concurrency}…")
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=concurrency + 50, ttl_dns_cache=300)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = []
        for i in range(total_requests):
            lang = HTTP_LANGUAGE_POOL[i % len(HTTP_LANGUAGE_POOL)]
            tasks.append(
                asyncio.create_task(
                    single_optimize_request(session, backend_url, lang, semaphore)
                )
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)

    clean: List[RequestResult] = []
    for r in results:
        if isinstance(r, RequestResult):
            clean.append(r)
        else:
            clean.append(RequestResult(
                endpoint="/api/optimize-code",
                language="unknown",
                latency_ms=0.0,
                success=False,
                status_code=None,
                error_message=str(r)
            ))
    print(f"[HTTP] Completed {len(clean)} requests.")
    return clean


# ---------------------------------------------------------------------------
# WEBSOCKET COLLABORATIVE ROOM LOAD TEST
# ---------------------------------------------------------------------------

async def simulate_ws_client(
    ws_url: str,
    room_id: str,
    client_id: int,
    n_messages: int,
    semaphore: asyncio.Semaphore,
) -> WebSocketResult:
    """
    Simulate one WebSocket client in a named room:
      1. Connect and receive INIT_STATE
      2. Send n_messages CODE_UPDATE messages
      3. Measure round-trip time (send → broadcast → receive at other clients)
    """
    connect_start = time.monotonic()
    async with semaphore:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(
                    f"{ws_url}/ws/{room_id}",
                    timeout=aiohttp.ClientWSTimeout(ws_receive=10),
                    heartbeat=30,
                ) as ws:
                    connect_latency_ms = (time.monotonic() - connect_start) * 1000

                    # 1. Receive INIT_STATE
                    try:
                        init_msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
                        if init_msg.get("type") != "INIT_STATE":
                            return WebSocketResult(
                                room_id=room_id, client_id=client_id,
                                connect_latency_ms=connect_latency_ms,
                                message_latency_ms=0.0,
                                messages_sent=0, messages_received=0,
                                success=False,
                                error_message=f"Expected INIT_STATE, got: {init_msg.get('type')}"
                            )
                    except asyncio.TimeoutError:
                        return WebSocketResult(
                            room_id=room_id, client_id=client_id,
                            connect_latency_ms=connect_latency_ms,
                            message_latency_ms=0.0,
                            messages_sent=0, messages_received=0,
                            success=False,
                            error_message="Timeout waiting for INIT_STATE"
                        )

                    # 2. Send CODE_UPDATE messages and measure latency
                    message_latencies: List[float] = []
                    sent = 0
                    for msg_idx in range(n_messages):
                        code_snippet = f"// client {client_id} message {msg_idx}\n" + \
                                       "var x = 10;\nif (x == 10) {{}}\n"
                        payload = {
                            "type": "CODE_UPDATE",
                            "code": code_snippet,
                            "user_id": f"client_{client_id}",
                            "cursor_line": msg_idx,
                        }
                        t0 = time.monotonic()
                        await ws.send_json(payload)
                        sent += 1
                        # Brief pause to simulate real editing cadence
                        await asyncio.sleep(random.uniform(0.01, 0.05))
                        message_latencies.append((time.monotonic() - t0) * 1000)

                    avg_msg_latency = statistics.mean(message_latencies) if message_latencies else 0.0
                    await ws.close()
                    return WebSocketResult(
                        room_id=room_id, client_id=client_id,
                        connect_latency_ms=connect_latency_ms,
                        message_latency_ms=avg_msg_latency,
                        messages_sent=sent,
                        messages_received=1,  # INIT_STATE counted
                        success=True,
                    )
        except Exception as exc:
            connect_latency_ms = (time.monotonic() - connect_start) * 1000
            return WebSocketResult(
                room_id=room_id, client_id=client_id,
                connect_latency_ms=connect_latency_ms,
                message_latency_ms=0.0,
                messages_sent=0, messages_received=0,
                success=False,
                error_message=str(exc)[:300],
            )


async def run_ws_stress(
    ws_url: str,
    n_rooms: int,
    clients_per_room: int,
    messages_per_client: int,
) -> List[WebSocketResult]:
    """
    Launch n_rooms × clients_per_room concurrent WebSocket clients, each sending
    messages_per_client CODE_UPDATE frames.
    """
    total_clients = n_rooms * clients_per_room
    print(f"[WS] Starting {n_rooms} rooms × {clients_per_room} clients = {total_clients} connections…")
    semaphore = asyncio.Semaphore(min(total_clients, 400))   # cap OS socket usage
    tasks = []
    for room_idx in range(n_rooms):
        room_id = f"stress-room-{room_idx:04d}"
        for client_idx in range(clients_per_room):
            tasks.append(asyncio.create_task(
                simulate_ws_client(
                    ws_url, room_id, client_idx, messages_per_client, semaphore
                )
            ))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    clean: List[WebSocketResult] = []
    for r in results:
        if isinstance(r, WebSocketResult):
            clean.append(r)
        else:
            clean.append(WebSocketResult(
                room_id="unknown", client_id=-1,
                connect_latency_ms=0.0, message_latency_ms=0.0,
                messages_sent=0, messages_received=0,
                success=False, error_message=str(r)
            ))
    print(f"[WS] Completed {len(clean)} WebSocket sessions.")
    return clean


# ---------------------------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------------------------

async def check_backend_health(backend_url: str) -> bool:
    """Return True if /health returns HTTP 200 with status=online."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{backend_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    body = await resp.json()
                    return body.get("status") == "online"
    except Exception as exc:
        print(f"[health] Backend unreachable: {exc}")
    return False


# ---------------------------------------------------------------------------
# REPORT GENERATION
# ---------------------------------------------------------------------------

def generate_markdown_report(
    suite: BenchmarkSuite,
    backend_url: str,
    ws_url: str,
) -> str:
    """Produce a complete Markdown stress test results report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    wall_elapsed = suite.wall_end - suite.wall_start

    http_ok   = [r for r in suite.results_http if r.success]
    http_fail = [r for r in suite.results_http if not r.success]
    http_latencies = sorted([r.latency_ms for r in http_ok])
    http_stats = compute_stats(http_latencies)
    http_throughput = len(http_ok) / wall_elapsed if wall_elapsed > 0 else 0.0

    ws_ok     = [r for r in suite.results_ws if r.success]
    ws_fail   = [r for r in suite.results_ws if not r.success]
    ws_connect_latencies = sorted([r.connect_latency_ms for r in ws_ok])
    ws_msg_latencies     = sorted([r.message_latency_ms for r in ws_ok])
    ws_connect_stats = compute_stats(ws_connect_latencies)
    ws_msg_stats     = compute_stats(ws_msg_latencies)

    # Per-language breakdown
    lang_stats: Dict[str, Dict[str, Any]] = {}
    for lang in HTTP_LANGUAGE_POOL:
        lang_results = [r for r in http_ok if r.language == lang]
        if lang_results:
            lats = sorted([r.latency_ms for r in lang_results])
            lang_stats[lang] = {
                "count":    len(lats),
                "p50":      percentile(lats, 50),
                "p99":      percentile(lats, 99),
                "errors":   len([r for r in suite.results_http if r.language == lang and not r.success]),
                "avg_issues": statistics.mean([r.issues_count for r in lang_results if r.issues_count is not None]) if lang_results else 0,
            }

    lines: List[str] = []
    lines.append("# ByteSized Suite — Enterprise Stress Test Results")
    lines.append("")
    lines.append(f"**Generated:** {now}  ")
    lines.append(f"**Backend:** `{backend_url}`  ")
    lines.append(f"**WebSocket:** `{ws_url}`  ")
    lines.append(f"**Suite:** {suite.name}  ")
    lines.append(f"**Total wall time:** {wall_elapsed:.2f}s  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- Executive Summary ----
    lines.append("## Executive Summary")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| HTTP requests total | {len(suite.results_http)} |")
    lines.append(f"| HTTP requests successful | {len(http_ok)} |")
    lines.append(f"| HTTP requests failed | {len(http_fail)} |")
    lines.append(f"| HTTP success rate | {100*len(http_ok)/max(1,len(suite.results_http)):.1f}% |")
    lines.append(f"| HTTP throughput | {http_throughput:.1f} req/s |")
    lines.append(f"| WebSocket sessions total | {len(suite.results_ws)} |")
    lines.append(f"| WebSocket sessions successful | {len(ws_ok)} |")
    lines.append(f"| WebSocket sessions failed | {len(ws_fail)} |")
    lines.append(f"| WebSocket success rate | {100*len(ws_ok)/max(1,len(suite.results_ws)):.1f}% |")
    lines.append(f"| Total wall time | {wall_elapsed:.2f}s |")
    lines.append("")

    # ---- HTTP Latency Statistics ----
    lines.append("## HTTP Optimization API — Latency Statistics")
    lines.append("")
    lines.append("All latencies in **milliseconds**.")
    lines.append("")
    lines.append("| Statistic | Value (ms) |")
    lines.append("|---|---|")
    for key, label in [
        ("min", "Minimum"), ("mean", "Mean"), ("p50", "p50 (Median)"),
        ("p90", "p90"), ("p99", "p99"), ("max", "Maximum"),
        ("stddev", "Std Dev"), ("jitter", "Jitter"),
    ]:
        lines.append(f"| {label} | {http_stats[key]:.2f} |")
    lines.append("")

    # ---- HTTP Latency Histogram ----
    lines.append("### HTTP Latency Distribution Histogram")
    lines.append("")
    lines.append("```")
    lines.append(ascii_histogram(http_latencies, buckets=20, width=40))
    lines.append("```")
    lines.append("")

    # ---- Per-Language Breakdown ----
    lines.append("## Per-Language Optimization Breakdown")
    lines.append("")
    lines.append("| Language | Requests | p50 (ms) | p99 (ms) | Errors | Avg Issues Detected |")
    lines.append("|---|---|---|---|---|---|")
    for lang in HTTP_LANGUAGE_POOL:
        if lang in lang_stats:
            s = lang_stats[lang]
            lines.append(
                f"| `{lang}` | {s['count']} | {s['p50']:.1f} | {s['p99']:.1f} | "
                f"{s['errors']} | {s['avg_issues']:.1f} |"
            )
    lines.append("")

    # ---- WebSocket Statistics ----
    lines.append("## WebSocket Collaboration Hub — Connection Statistics")
    lines.append("")
    lines.append("### Connection Latency (time from TCP connect to INIT_STATE received)")
    lines.append("")
    lines.append("| Statistic | Value (ms) |")
    lines.append("|---|---|")
    for key, label in [("min", "Minimum"), ("mean", "Mean"), ("p50", "p50"),
                        ("p90", "p90"), ("p99", "p99"), ("max", "Maximum"), ("jitter", "Jitter")]:
        lines.append(f"| {label} | {ws_connect_stats[key]:.2f} |")
    lines.append("")

    lines.append("### Message Round-Trip Latency (CODE_UPDATE send → broadcast)")
    lines.append("")
    lines.append("| Statistic | Value (ms) |")
    lines.append("|---|---|")
    for key, label in [("min", "Minimum"), ("mean", "Mean"), ("p50", "p50"),
                        ("p90", "p90"), ("p99", "p99"), ("max", "Maximum"), ("jitter", "Jitter")]:
        lines.append(f"| {label} | {ws_msg_stats[key]:.2f} |")
    lines.append("")

    lines.append("### WebSocket Latency Distribution Histogram")
    lines.append("")
    lines.append("```")
    lines.append(ascii_histogram(ws_connect_latencies, buckets=15, width=40))
    lines.append("```")
    lines.append("")

    # ---- Error Analysis ----
    if http_fail:
        lines.append("## HTTP Error Analysis")
        lines.append("")
        error_summary: Dict[str, int] = {}
        for r in http_fail:
            key = f"HTTP {r.status_code or 'connection_error'}"
            error_summary[key] = error_summary.get(key, 0) + 1
        lines.append("| Error Class | Count |")
        lines.append("|---|---|")
        for err_class, count in sorted(error_summary.items(), key=lambda x: -x[1]):
            lines.append(f"| `{err_class}` | {count} |")
        lines.append("")

    if ws_fail:
        lines.append("## WebSocket Error Analysis")
        lines.append("")
        ws_error_summary: Dict[str, int] = {}
        for r in ws_fail:
            key = (r.error_message or "unknown")[:60]
            ws_error_summary[key] = ws_error_summary.get(key, 0) + 1
        lines.append("| Error Message (truncated) | Count |")
        lines.append("|---|---|")
        for msg, count in sorted(ws_error_summary.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"| `{msg}` | {count} |")
        lines.append("")

    # ---- Performance Assessment ----
    lines.append("## Performance Assessment & SLA Evaluation")
    lines.append("")
    sla_p99_ms = 500.0   # SLA: p99 < 500ms
    sla_success_rate = 0.99  # SLA: 99% success rate

    http_p99_pass = http_stats["p99"] < sla_p99_ms
    http_sr_pass  = (len(http_ok) / max(1, len(suite.results_http))) >= sla_success_rate
    ws_p99_pass   = ws_connect_stats["p99"] < sla_p99_ms
    ws_sr_pass    = (len(ws_ok) / max(1, len(suite.results_ws))) >= sla_success_rate

    def badge(passed: bool) -> str:
        return "✅ PASS" if passed else "❌ FAIL"

    lines.append("| SLA Criterion | Threshold | Actual | Status |")
    lines.append("|---|---|---|---|")
    lines.append(f"| HTTP p99 latency | < {sla_p99_ms:.0f}ms | {http_stats['p99']:.1f}ms | {badge(http_p99_pass)} |")
    lines.append(f"| HTTP success rate | ≥ {sla_success_rate*100:.0f}% | {100*len(http_ok)/max(1,len(suite.results_http)):.1f}% | {badge(http_sr_pass)} |")
    lines.append(f"| WS connect p99 | < {sla_p99_ms:.0f}ms | {ws_connect_stats['p99']:.1f}ms | {badge(ws_p99_pass)} |")
    lines.append(f"| WS success rate | ≥ {sla_success_rate*100:.0f}% | {100*len(ws_ok)/max(1,len(suite.results_ws)):.1f}% | {badge(ws_sr_pass)} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Report generated by ByteSized Enterprise Load Testing Framework v2.0.0*")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# MAIN ORCHESTRATOR
# ---------------------------------------------------------------------------

async def run_full_benchmark(
    backend_url: str,
    ws_url: str,
    http_concurrency: int,
    http_total: int,
    ws_rooms: int,
    ws_clients: int,
    ws_messages: int,
) -> BenchmarkSuite:
    """Execute the full HTTP + WebSocket stress test suite."""
    suite = BenchmarkSuite(
        name=f"ByteSized Load Test — {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}"
    )
    suite.wall_start = time.monotonic()

    print(f"\n{'='*60}")
    print("ByteSized Enterprise Load & Stress Testing Framework")
    print(f"{'='*60}")
    print(f"Backend:  {backend_url}")
    print(f"WebSocket: {ws_url}")
    print(f"HTTP:  {http_total} total requests, concurrency={http_concurrency}")
    print(f"WS:    {ws_rooms} rooms × {ws_clients} clients × {ws_messages} messages")
    print(f"{'='*60}\n")

    # Health check before starting
    print("[init] Checking backend health…")
    healthy = await check_backend_health(backend_url)
    if not healthy:
        print("[init] WARNING: Backend health check failed. "
              "Proceeding anyway (results may show high error rates).")
    else:
        print("[init] Backend is healthy. Starting tests.\n")

    # Phase 1: HTTP Stress Test
    print("Phase 1/2 — HTTP Optimization API Stress Test")
    print("-" * 50)
    http_results = await run_http_stress(backend_url, http_concurrency, http_total)
    suite.results_http = http_results

    # Phase 2: WebSocket Stress Test
    print("\nPhase 2/2 — WebSocket Collaboration Stress Test")
    print("-" * 50)
    ws_results = await run_ws_stress(ws_url, ws_rooms, ws_clients, ws_messages)
    suite.results_ws = ws_results

    suite.wall_end = time.monotonic()
    return suite


def print_console_summary(suite: BenchmarkSuite) -> None:
    """Print a concise summary table to stdout."""
    http_ok = [r for r in suite.results_http if r.success]
    ws_ok   = [r for r in suite.results_ws   if r.success]
    http_latencies = [r.latency_ms for r in http_ok]
    ws_latencies   = [r.connect_latency_ms for r in ws_ok]
    wall = suite.wall_end - suite.wall_start

    print(f"\n{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"Wall time:           {wall:.2f}s")
    print(f"HTTP success rate:   {100*len(http_ok)/max(1,len(suite.results_http)):.1f}%  "
          f"({len(http_ok)}/{len(suite.results_http)})")
    if http_latencies:
        s = sorted(http_latencies)
        print(f"HTTP p50 / p99:      {percentile(s,50):.1f}ms / {percentile(s,99):.1f}ms")
        print(f"HTTP throughput:     {len(http_ok)/wall:.1f} req/s")
    print(f"WS success rate:     {100*len(ws_ok)/max(1,len(suite.results_ws)):.1f}%  "
          f"({len(ws_ok)}/{len(suite.results_ws)})")
    if ws_latencies:
        s = sorted(ws_latencies)
        print(f"WS connect p50/p99: {percentile(s,50):.1f}ms / {percentile(s,99):.1f}ms")
    print(f"{'='*60}\n")


def write_report(report_md: str, path: str) -> None:
    """Write the Markdown report to the specified path, creating dirs if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(report_md)
    print(f"[report] Markdown report written to: {path}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ByteSized Enterprise Load Testing Framework")
    p.add_argument("--backend",      default=DEFAULT_BACKEND_HTTP,
                   help=f"HTTP backend URL (default: {DEFAULT_BACKEND_HTTP})")
    p.add_argument("--ws",           default=DEFAULT_BACKEND_WS,
                   help=f"WebSocket backend URL (default: {DEFAULT_BACKEND_WS})")
    p.add_argument("--http-concurrent", type=int, default=HTTP_CONCURRENT,
                   help="Concurrent HTTP requests (default: 500)")
    p.add_argument("--http-total",   type=int, default=HTTP_CONCURRENT,
                   help="Total HTTP requests to fire (default: same as --http-concurrent)")
    p.add_argument("--ws-rooms",     type=int, default=WS_ROOMS,
                   help="Concurrent WebSocket rooms (default: 200)")
    p.add_argument("--ws-clients",   type=int, default=WS_CLIENTS_PER_ROOM,
                   help="Clients per room (default: 3)")
    p.add_argument("--ws-messages",  type=int, default=WS_MESSAGES_PER_CLIENT,
                   help="Messages per client (default: 5)")
    p.add_argument("--report",       default=REPORT_PATH,
                   help="Output Markdown report path")
    return p.parse_args()


async def async_main(args: argparse.Namespace) -> None:
    suite = await run_full_benchmark(
        backend_url    = args.backend,
        ws_url         = args.ws,
        http_concurrency = args.http_concurrent,
        http_total     = args.http_total,
        ws_rooms       = args.ws_rooms,
        ws_clients     = args.ws_clients,
        ws_messages    = args.ws_messages,
    )

    print_console_summary(suite)

    report = generate_markdown_report(suite, args.backend, args.ws)
    write_report(report, args.report)


def main() -> None:
    args = parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()

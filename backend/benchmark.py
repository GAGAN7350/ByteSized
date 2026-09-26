import urllib.request
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000"
test_dir = os.path.join(os.path.dirname(__file__), "..", "test_samples")
samples = ["alu_with_latch.v", "race_condition.v", "unpipelined_mult.v"]

print("=================================================================")
print("          SILICONBOB HARDWARE ENGINE PERFORMANCE BENCHMARK       ")
print("=================================================================\n")

total_time = 0
total_issues = 0

for filename in samples:
    filepath = os.path.join(test_dir, filename)
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        continue

    with open(filepath, "r") as f:
        code = f.read()

    start = time.perf_counter()
    req = urllib.request.Request(
        f"{BASE_URL}/api/optimize-rtl",
        data=json.dumps({"verilog_code": code, "target": "ppa"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    elapsed_ms = (time.perf_counter() - start) * 1000
    total_time += elapsed_ms
    total_issues += len(data["issues"])

    print(f"[*] TEST FILE: {filename}")
    print(f"    Lines of Code:    {len(code.splitlines())}")
    print(f"    Inference Latency:{elapsed_ms:.2f} ms")
    print(f"    Violations Found: {len(data['issues'])}")
    for issue in data["issues"]:
        print(f"      -> Line {issue['line']}: [{issue['rule_id']}] {issue['message']}")
    print(f"    Power Efficiency: {data['metrics']['power_efficiency']}")
    print(f"    Timing Slack:     {data['metrics']['timing_slack']}")
    print("-" * 65)

print(f"\n[SUMMARY]")
print(f"  Total Processed: {len(samples)} RTL modules")
print(f"  Total Hardware Bugs Fixed: {total_issues}")
print(f"  Average Analysis Latency: {total_time/len(samples):.2f} ms per module")
print("=================================================================")

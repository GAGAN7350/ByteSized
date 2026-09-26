import urllib.request
import json
import time
import os

BASE_URL = "http://127.0.0.1:8000"
test_dir = os.path.join(os.path.dirname(__file__), "..", "test_samples")
samples = ["alu_with_latch.v", "race_condition.v", "unpipelined_mult.v"]

for filename in samples:
    filepath = os.path.join(test_dir, filename)
    with open(filepath, "r") as f:
        code = f.read()

    req = urllib.request.Request(
        f"{BASE_URL}/api/optimize-rtl",
        data=json.dumps({"verilog_code": code, "target": "ppa"}).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())

    print(f"\n=======================================================")
    print(f" FILE: {filename}")
    print(f" Issues Found: {len(data['issues'])}")
    for issue in data['issues']:
        print(f"   Line {issue['line']}: [{issue['rule_id']}] {issue['message']}")
    print(f"--- AUTO-REWRITTEN OPTIMIZED VERILOG ---")
    print(data['optimized_code'])
    print(f"=======================================================\n")

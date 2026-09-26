import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def test_health():
    print("[1] Testing Health Endpoint...")
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print("    Response:", data)

def test_latch_fix():
    print("\n[2] Testing RTL Latch Fix against alu_with_latch.v...")
    with open("../test_samples/alu_with_latch.v", "r") as f:
        code = f.read()

    payload = json.dumps({
        "verilog_code": code,
        "target": "ppa"
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/api/optimize-rtl",
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        print(f"    Status: {data['status']}")
        print(f"    Issues Detected: {len(data['issues'])}")
        for issue in data['issues']:
            print(f"      - Line {issue['line']}: [{issue['rule_id']}] {issue['message']}")
        print(f"    Metrics: {data['metrics']}")
        print("\n[3] Auto-Rewritten Optimized Code Preview:")
        print("--------------------------------------------------")
        print(data['optimized_code'])
        print("--------------------------------------------------")

if __name__ == "__main__":
    test_health()
    test_latch_fix()

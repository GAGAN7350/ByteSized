import urllib.request
import json

BASE_URL = "http://127.0.0.1:8000"

def test_suite():
    print("=============================================================")
    print("    TESTING BYTESIZED BACKEND FOR ALL 3 EXTENSIONS           ")
    print("=============================================================")

    # 1. Health
    req = urllib.request.Request(f"{BASE_URL}/health")
    with urllib.request.urlopen(req) as resp:
        print("\n[1] Health Check:", json.loads(resp.read().decode())["status"])

    # 2. Dev 1: Multi-language Code Optimizer (Python test)
    py_code = "def worker(task_id, task_list=[]):\n    task_list.append(task_id)\n    return task_list"
    payload = json.dumps({"code": py_code, "language": "python"}).encode("utf-8")
    req = urllib.request.Request(f"{BASE_URL}/api/optimize-code", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print("\n[2] Dev 1 - Universal Code Optimizer (Python Test):")
        print(f"    Issues Detected: {len(data['issues'])}")
        print(f"    Summary: {data['summary']}")

    # 3. Dev 2: Microchip & PCB Designer
    req = urllib.request.Request(f"{BASE_URL}/api/chip-pcb/components")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"\n[3] Dev 2 - PCB & Microchip Components Available: {len(data['components'])} IC blocks")

    # 4. Dev 3: Git Architecture Diagram
    req = urllib.request.Request(f"{BASE_URL}/api/git/topology")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"\n[4] Dev 3 - Git Topology Tracked Extensions: {len(data['tracked_extensions'])} modules")

    print("\n=============================================================")
    print("    ALL 3 EXTENSION BACKEND SERVICES ARE OPERATIONAL!        ")
    print("=============================================================")

if __name__ == "__main__":
    test_suite()

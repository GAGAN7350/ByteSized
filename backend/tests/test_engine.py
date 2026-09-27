"""
Unit tests for backend/routers/rtl/engine.py — all 8 language optimizers.

Each test verifies:
  1. The correct rule_id fires on a minimal triggering snippet.
  2. fixed_line is populated (non-None) for rules with a deterministic fix.
  3. Clean code that should NOT trigger the rule produces zero issues.

Run with: pytest backend/tests/test_engine.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.routers.rtl.engine import analyze_and_optimize_code


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def issues_for(code: str, lang: str):
    issues, _, _ = analyze_and_optimize_code(code, lang)
    return issues


def rule_ids(issues):
    return [i.rule_id for i in issues]


def has_fix(issue):
    return issue.fixed_line is not None


# ─────────────────────────────────────────────────────────────────────────────
# VERILOG — RTL-001  Blocking assignment in posedge block
# ─────────────────────────────────────────────────────────────────────────────

RTL001_BAD = """
module m(input clk, input [3:0] a, output reg [3:0] q);
  always @(posedge clk) begin
    q = a;
  end
endmodule
"""

RTL001_CLEAN = """
module m(input clk, input [3:0] a, output reg [3:0] q);
  always @(posedge clk) begin
    q <= a;
  end
endmodule
"""

def test_rtl001_detects():
    iss = issues_for(RTL001_BAD, 'verilog')
    assert any(i.rule_id == 'RTL-001-BLOCKING-IN-SEQ' for i in iss)
    for i in iss:
        if i.rule_id == 'RTL-001-BLOCKING-IN-SEQ':
            assert has_fix(i)
            assert '<=' in i.fixed_line

def test_rtl001_clean():
    iss = issues_for(RTL001_CLEAN, 'verilog')
    assert not any(i.rule_id == 'RTL-001-BLOCKING-IN-SEQ' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# VERILOG — RTL-002  Missing default in case
# ─────────────────────────────────────────────────────────────────────────────

RTL002_BAD = open('test_samples/alu_with_latch.v').read()

RTL002_CLEAN = """
module m(input [1:0] op, output reg [3:0] r);
  always @(*) begin
    case (op)
      2'b00: r = 4'd1;
      2'b01: r = 4'd2;
      default: r = 4'd0;
    endcase
  end
endmodule
"""

def test_rtl002_detects():
    iss = issues_for(RTL002_BAD, 'verilog')
    assert any(i.rule_id == 'RTL-002-INFERRED-LATCH' for i in iss)
    for i in iss:
        if i.rule_id == 'RTL-002-INFERRED-LATCH':
            assert has_fix(i)
            assert 'default' in i.fixed_line

def test_rtl002_clean():
    iss = issues_for(RTL002_CLEAN, 'verilog')
    assert not any(i.rule_id == 'RTL-002-INFERRED-LATCH' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# VERILOG — RTL-003  Non-synthesizable delay
# ─────────────────────────────────────────────────────────────────────────────

RTL003_BAD = open('test_samples/unpipelined_mult.v').read()
RTL003_CLEAN = """
module m(input clk, output reg [31:0] out);
  always @(posedge clk) begin
    out <= 32'd0;
  end
endmodule
"""

def test_rtl003_detects():
    iss = issues_for(RTL003_BAD, 'verilog')
    assert any(i.rule_id == 'RTL-003-DELAY-SYNTH' for i in iss)
    for i in iss:
        if i.rule_id == 'RTL-003-DELAY-SYNTH':
            assert has_fix(i)
            assert '#' not in i.fixed_line

def test_rtl003_clean():
    iss = issues_for(RTL003_CLEAN, 'verilog')
    assert not any(i.rule_id == 'RTL-003-DELAY-SYNTH' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# VERILOG — RTL-004  Critical path / unpipelined MAC
# ─────────────────────────────────────────────────────────────────────────────

RTL004_BAD = "always @(posedge clk) begin\n  out <= (a * b) + c;\nend\n"
RTL004_CLEAN = "always @(posedge clk) begin\n  out <= a + b;\nend\n"

def test_rtl004_detects():
    iss = issues_for(RTL004_BAD, 'verilog')
    assert any(i.rule_id == 'RTL-004-PIPELINE-RETIMING' for i in iss)
    for i in iss:
        if i.rule_id == 'RTL-004-PIPELINE-RETIMING':
            assert has_fix(i)

def test_rtl004_clean():
    iss = issues_for(RTL004_CLEAN, 'verilog')
    assert not any(i.rule_id == 'RTL-004-PIPELINE-RETIMING' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON — PY-001  Mutable default argument
# ─────────────────────────────────────────────────────────────────────────────

PY001_BAD   = "def foo(items=[]):\n    items.append(1)\n    return items\n"
PY001_CLEAN = "def foo(items=None):\n    if items is None:\n        items = []\n    return items\n"

def test_py001_detects():
    iss = issues_for(PY001_BAD, 'python')
    assert any(i.rule_id == 'PY-001-MUTABLE-DEFAULT' for i in iss)
    for i in iss:
        if i.rule_id == 'PY-001-MUTABLE-DEFAULT':
            assert has_fix(i)
            assert '=None' in i.fixed_line

def test_py001_clean():
    iss = issues_for(PY001_CLEAN, 'python')
    assert not any(i.rule_id == 'PY-001-MUTABLE-DEFAULT' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON — PY-002  Bare except
# ─────────────────────────────────────────────────────────────────────────────

PY002_BAD   = "try:\n    x = 1\nexcept:\n    pass\n"
PY002_CLEAN = "try:\n    x = 1\nexcept Exception:\n    pass\n"

def test_py002_detects():
    iss = issues_for(PY002_BAD, 'python')
    assert any(i.rule_id == 'PY-002-BARE-EXCEPT' for i in iss)
    for i in iss:
        if i.rule_id == 'PY-002-BARE-EXCEPT':
            assert has_fix(i)
            assert 'Exception' in i.fixed_line

def test_py002_clean():
    iss = issues_for(PY002_CLEAN, 'python')
    assert not any(i.rule_id == 'PY-002-BARE-EXCEPT' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON — PY-003  range(len())
# ─────────────────────────────────────────────────────────────────────────────

PY003_BAD   = "for i in range(len(items)):\n    print(items[i])\n"
PY003_CLEAN = "for i, item in enumerate(items):\n    print(item)\n"

def test_py003_detects():
    iss = issues_for(PY003_BAD, 'python')
    assert any(i.rule_id == 'PY-003-RANGE-LEN' for i in iss)
    for i in iss:
        if i.rule_id == 'PY-003-RANGE-LEN':
            assert has_fix(i)
            assert 'enumerate' in i.fixed_line

def test_py003_clean():
    iss = issues_for(PY003_CLEAN, 'python')
    assert not any(i.rule_id == 'PY-003-RANGE-LEN' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON — PY-004  type() == instead of isinstance
# ─────────────────────────────────────────────────────────────────────────────

PY004_BAD   = "if type(x) == int:\n    pass\n"
PY004_CLEAN = "if isinstance(x, int):\n    pass\n"

def test_py004_detects():
    iss = issues_for(PY004_BAD, 'python')
    assert any(i.rule_id == 'PY-004-TYPE-CHECK' for i in iss)
    for i in iss:
        if i.rule_id == 'PY-004-TYPE-CHECK':
            assert has_fix(i)
            assert 'isinstance' in i.fixed_line

def test_py004_clean():
    iss = issues_for(PY004_CLEAN, 'python')
    assert not any(i.rule_id == 'PY-004-TYPE-CHECK' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# C/C++ — CPP-001  strcpy
# ─────────────────────────────────────────────────────────────────────────────

CPP001_BAD   = 'strcpy(dest, src);\n'
CPP001_CLEAN = 'strncpy(dest, src, sizeof(dest) - 1);\n'

def test_cpp001_detects():
    iss = issues_for(CPP001_BAD, 'cpp')
    assert any(i.rule_id == 'CPP-001-BUFFER-OVERFLOW' for i in iss)
    for i in iss:
        if i.rule_id == 'CPP-001-BUFFER-OVERFLOW':
            assert has_fix(i)
            assert 'strncpy' in i.fixed_line

def test_cpp001_clean():
    iss = issues_for(CPP001_CLEAN, 'cpp')
    assert not any(i.rule_id == 'CPP-001-BUFFER-OVERFLOW' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# C/C++ — CPP-002  gets()
# ─────────────────────────────────────────────────────────────────────────────

CPP002_BAD   = 'gets(buf);\n'
CPP002_CLEAN = 'fgets(buf, sizeof(buf), stdin);\n'

def test_cpp002_detects():
    iss = issues_for(CPP002_BAD, 'cpp')
    assert any(i.rule_id == 'CPP-002-GETS-INSECURE' for i in iss)
    for i in iss:
        if i.rule_id == 'CPP-002-GETS-INSECURE':
            assert has_fix(i)
            assert 'fgets' in i.fixed_line

def test_cpp002_clean():
    iss = issues_for(CPP002_CLEAN, 'cpp')
    assert not any(i.rule_id == 'CPP-002-GETS-INSECURE' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# C/C++ — CPP-003  sprintf
# ─────────────────────────────────────────────────────────────────────────────

CPP003_BAD   = 'sprintf(buf, "%s", input);\n'
CPP003_CLEAN = 'snprintf(buf, sizeof(buf), "%s", input);\n'

def test_cpp003_detects():
    iss = issues_for(CPP003_BAD, 'cpp')
    assert any(i.rule_id == 'CPP-003-SPRINTF-BOUNDS' for i in iss)
    for i in iss:
        if i.rule_id == 'CPP-003-SPRINTF-BOUNDS':
            assert has_fix(i)
            assert 'snprintf' in i.fixed_line

def test_cpp003_clean():
    iss = issues_for(CPP003_CLEAN, 'cpp')
    assert not any(i.rule_id == 'CPP-003-SPRINTF-BOUNDS' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# JavaScript — JS-001  var
# ─────────────────────────────────────────────────────────────────────────────

JS001_BAD   = 'var x = 1;\n'
JS001_CLEAN = 'const x = 1;\n'

def test_js001_detects():
    iss = issues_for(JS001_BAD, 'javascript')
    assert any(i.rule_id == 'JS-001-NO-VAR' for i in iss)
    for i in iss:
        if i.rule_id == 'JS-001-NO-VAR':
            assert has_fix(i)
            assert 'const' in i.fixed_line

def test_js001_clean():
    iss = issues_for(JS001_CLEAN, 'javascript')
    assert not any(i.rule_id == 'JS-001-NO-VAR' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# JavaScript — JS-002  loose equality
# ─────────────────────────────────────────────────────────────────────────────

JS002_BAD   = 'if (x == null) return;\n'
JS002_CLEAN = 'if (x === null) return;\n'

def test_js002_detects():
    iss = issues_for(JS002_BAD, 'javascript')
    assert any(i.rule_id == 'JS-002-STRICT-EQUAL' for i in iss)
    for i in iss:
        if i.rule_id == 'JS-002-STRICT-EQUAL':
            assert has_fix(i)
            assert '===' in i.fixed_line

def test_js002_clean():
    iss = issues_for(JS002_CLEAN, 'javascript')
    assert not any(i.rule_id == 'JS-002-STRICT-EQUAL' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# Java — JAVA-001  string == comparison
# ─────────────────────────────────────────────────────────────────────────────

JAVA001_BAD   = 'if (name == "admin") { doSomething(); }\n'
JAVA001_CLEAN = 'if ("admin".equals(name)) { doSomething(); }\n'

def test_java001_detects():
    iss = issues_for(JAVA001_BAD, 'java')
    assert any(i.rule_id == 'JAVA-001-STRING-EQUALS' for i in iss)
    for i in iss:
        if i.rule_id == 'JAVA-001-STRING-EQUALS':
            assert has_fix(i)
            assert '.equals(' in i.fixed_line

def test_java001_clean():
    iss = issues_for(JAVA001_CLEAN, 'java')
    assert not any(i.rule_id == 'JAVA-001-STRING-EQUALS' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# Go — GO-001  ignored error
# ─────────────────────────────────────────────────────────────────────────────

GO001_BAD   = '_, _ = fmt.Println("hello")\n'
GO001_CLEAN = 'err := doSomething()\nif err != nil { return err }\n'

def test_go001_detects():
    iss = issues_for(GO001_BAD, 'go')
    assert any(i.rule_id == 'GO-001-IGNORED-ERROR' for i in iss)

def test_go001_clean():
    iss = issues_for(GO001_CLEAN, 'go')
    assert not any(i.rule_id == 'GO-001-IGNORED-ERROR' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# Go — GO-002  panic usage
# ─────────────────────────────────────────────────────────────────────────────

GO002_BAD   = 'panic("unexpected nil pointer")\n'
GO002_CLEAN = 'return fmt.Errorf("unexpected nil pointer")\n'

def test_go002_detects():
    iss = issues_for(GO002_BAD, 'go')
    assert any(i.rule_id == 'GO-002-PANIC-USAGE' for i in iss)

def test_go002_clean():
    iss = issues_for(GO002_CLEAN, 'go')
    assert not any(i.rule_id == 'GO-002-PANIC-USAGE' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# Rust — RUST-001  unwrap panic
# ─────────────────────────────────────────────────────────────────────────────

RUST001_BAD   = 'let val = result.unwrap();\n'
RUST001_CLEAN = 'let val = result.expect("expected a value");\n'

def test_rust001_detects():
    iss = issues_for(RUST001_BAD, 'rust')
    assert any(i.rule_id == 'RUST-001-UNWRAP-PANIC' for i in iss)

def test_rust001_clean():
    iss = issues_for(RUST001_CLEAN, 'rust')
    assert not any(i.rule_id == 'RUST-001-UNWRAP-PANIC' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# Generic — SEC-001  hardcoded secret
# ─────────────────────────────────────────────────────────────────────────────

SEC001_BAD   = 'api_key = "supersecret123"\n'
SEC001_CLEAN = 'api_key = os.environ["API_KEY"]\n'

def test_sec001_detects():
    iss = issues_for(SEC001_BAD, 'plaintext')
    assert any(i.rule_id == 'SEC-001-HARDCODED-SECRET' for i in iss)

def test_sec001_clean():
    iss = issues_for(SEC001_CLEAN, 'plaintext')
    assert not any(i.rule_id == 'SEC-001-HARDCODED-SECRET' for i in iss)


# ─────────────────────────────────────────────────────────────────────────────
# Generic — DEBT-001  TODO marker
# ─────────────────────────────────────────────────────────────────────────────

DEBT001_BAD   = '// TODO: fix this later\n'
DEBT001_CLEAN = '// This is fully implemented.\n'

def test_debt001_detects():
    iss = issues_for(DEBT001_BAD, 'plaintext')
    assert any(i.rule_id == 'DEBT-001-TODO-MARKER' for i in iss)

def test_debt001_clean():
    iss = issues_for(DEBT001_CLEAN, 'plaintext')
    assert not any(i.rule_id == 'DEBT-001-TODO-MARKER' for i in iss)

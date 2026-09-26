# ByteSized: Universal Code Checker & Optimizer ⚡
**Developer:** Dev 1 (You)  
**Track:** Code Quality, Bug Elimination & AI Performance Optimization (All Languages)

### Overview
A universal in-editor copilot that scans source code across multiple programming languages (Verilog, Python, C/C++, JavaScript/TypeScript), detects logic flaws, security vulnerabilities, and anti-patterns, and auto-rewrites the code with optimal implementations.

### Features
* **Multi-Language Support:** Verilog (hardware latches & race conditions), Python (mutable defaults & bare excepts), C/C++ (buffer overflows & RAII), JavaScript (modern ES6+ strict typing).
* **In-Editor Squiggles (`DiagnosticCollection`):** Immediate visual warnings right in the editor gutter.
* **Side-by-Side Diff View (`vscode.diff`):** Live comparison showing original code vs. auto-optimized code.
* **Performance Gains:** Reports execution speed, power efficiency, and memory safety improvements.

### How to Run
```bash
cd extensions/01-code-optimizer
npm install
npm run compile
```
In IBM Bob IDE, right-click any open file $\rightarrow$ **"ByteSized: Check & Optimize Code"**!

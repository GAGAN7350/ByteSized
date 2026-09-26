# ByteSized: Git Architecture & Topology Flow 🌳
**Developer:** Dev 3  
**Track:** Visual Git Commit Graph & Architecture Topology Visualizer

### Overview
A visual extension that renders interactive Git commit graphs, branch lifecycles, and high-level system architecture diagrams directly inside IBM Bob IDE.

### Features
* **Git Commit DAG:** Interactive visualization of branch branches (`main`, `dev1/code-optimizer`, `dev2/pcb-designer`, `dev3/git-diagram`) and merge topologies.
* **System Architecture Flow:** Visual flowchart mapping the relationships between the 3 extensions and backend services.
* **Live Repository Metrics:** Displays tracked modules, contributor counts, and synchronization health.

### How to Run
```bash
cd extensions/03-git-diagram-generator
npm install
npm run compile
```
In IBM Bob IDE, press `Ctrl+Shift+P` $\rightarrow$ type **"ByteSized: View Git Flow & Architecture Diagram"**!

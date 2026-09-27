# ByteSized: Microchip & PCB Visual Designer 🔌
**Developer:** Dev 2  
**Track:** Visual Hardware Architecture & PCB Circuit Schematic Studio

### Overview
An interactive canvas extension inside IBM Bob IDE for hardware engineers to visually design microchip block diagrams, IC pinouts, and PCB circuits.

### Features
* **Component Palette:** Drag-and-drop RISC-V/ARM MCUs, 32-bit ALU cores, SRAM caches, PLL clock generators, and AXI4 bus arbiters.
* **Interactive Canvas:** Draggable chip blocks with pinout indicators and pin definitions.
* **Hardware Netlist Exporter:** Generates netlists and pinout mappings for synthesis tools with a single click.

### How to Run
```bash
cd extensions/02-chip-pcb-designer
npm install
npm run compile
```
In IBM Bob IDE, press `Ctrl+Shift+P` $\rightarrow$ type **"ByteSized: Open Microchip & PCB Visual Designer"**!

// stress_sv_02_covergroup_bottlenecks.sv
// ByteSized Stress Suite — SystemVerilog: covergroup performance bottlenecks,
// over-specified cross products, and functional coverage collection overhead.
`timescale 1ns/1ps

// ============================================================
// ANTI-PATTERN 1: Exponential cross coverage product
// A cross of N bins × M bins × P bins creates N×M×P cross bins.
// Three 256-value fields → 16 million cross bins in simulation memory.
// ============================================================
covergroup OpcodeCross_Explosive @(posedge clk);
    cp_opcode: coverpoint opcode {
        bins ops[] = {[0:255]};   // 256 bins
    }
    cp_operand_a: coverpoint operand_a {
        bins vals[] = {[0:255]};  // 256 bins
    }
    cp_operand_b: coverpoint operand_b {
        bins vals[] = {[0:255]};  // 256 bins
    }
    // ANTI-PATTERN SV-CG-001: full 3-way cross = 256³ = 16,777,216 cross bins.
    // Allocates ~200 MB of simulation state and severely degrades simulation throughput.
    cx_all: cross cp_opcode, cp_operand_a, cp_operand_b;
endgroup

// ============================================================
// ANTI-PATTERN 2: Covergroup instantiated inside a frequently called function
// Creates a new covergroup instance on every function call — O(n) instances.
// ============================================================
function void sample_in_hot_loop(int data);
    // ANTI-PATTERN SV-CG-002: covergroup instantiation inside a function.
    // SystemVerilog creates a new CG instance each call — thousands of instances
    // accumulate for a hot function called millions of times per simulation.
    covergroup InlineHotCG;
        cp_data: coverpoint data { bins lo = {[0:127]}; bins hi = {[128:255]}; }
    endgroup
    automatic InlineHotCG cg = new();
    cg.sample();
    // cg goes out of scope but the coverage database entry persists
endfunction

// ============================================================
// ANTI-PATTERN 3: Covergroup sampling on every simulation time step
// Sampling at posedge of a 1 GHz clock means 10^9 sample() calls per second.
// ============================================================
covergroup TimingCoverageOverkill @(posedge clk_1ghz);
    // ANTI-PATTERN SV-CG-003: sampling CG on every 1 GHz clock edge.
    // 1 billion samples/second overwhelms the coverage database.
    cp_fsm_state: coverpoint fsm_state {
        bins idle   = {3'b000};
        bins fetch  = {3'b001};
        bins decode = {3'b010};
        bins exec   = {3'b011};
        bins mem    = {3'b100};
        bins wb     = {3'b101};
        bins stall  = {3'b110};
        bins err    = {3'b111};
    }
    cp_hazard: coverpoint hazard_flag;
    cx_state_hazard: cross cp_fsm_state, cp_hazard;  // 8×2 = 16 cross bins (okay)
endgroup

// ============================================================
// ANTI-PATTERN 4: Type options.weight=0 causing missed coverage goals
// ============================================================
covergroup WeightedCoverageError;
    // ANTI-PATTERN SV-CG-004: setting per-bin weight=0 silently excludes
    // those bins from the coverage percentage calculation. A regression
    // can pass 100% coverage even though the zero-weighted bin was never hit.
    cp_error_code: coverpoint error_code {
        bins no_error     = {8'h00} iff (valid);
        bins soft_err     = {[8'h01:8'h0F]};
        bins hard_err     = {[8'h10:8'hFF]} { option.weight = 0; }  // silently ignored
    }
endgroup

// ============================================================
// ANTI-PATTERN 5: Ignoring illegal_bins — allows illegal stimulus
// ============================================================
covergroup IllegalBinsIgnored;
    cp_cmd: coverpoint cmd_field {
        bins valid_cmds[] = {8'h01, 8'h02, 8'h03, 8'h04};
        // ANTI-PATTERN SV-CG-005: illegal_bins not declared.
        // Without declaring illegal_bins for other values, the simulator
        // accepts illegal command encodings silently in coverage terms.
        // illegal_bins reserved = {[8'h05:8'hFF]};  // MISSING
    }
endgroup

// ============================================================
// TESTBENCH SIGNALS & MODULE
// ============================================================
module tb_sv_covergroup_bottlenecks;
    reg        clk, clk_1ghz;
    reg [7:0]  opcode, operand_a, operand_b, error_code, cmd_field;
    reg [2:0]  fsm_state;
    reg        valid, hazard_flag;

    always #5   clk     = ~clk;      // 100 MHz
    always #0.5 clk_1ghz = ~clk_1ghz; // 1 GHz

    OpcodeCross_Explosive cg_explosive;
    WeightedCoverageError cg_weight;

    initial begin
        clk = 0; clk_1ghz = 0;
        opcode = 0; operand_a = 0; operand_b = 0;
        error_code = 0; cmd_field = 0;
        fsm_state = 0; valid = 0; hazard_flag = 0;

        // ANTI-PATTERN: instantiating the explosive covergroup
        cg_explosive = new();
        cg_weight    = new();

        // Drive 1000 random stimulus vectors
        repeat (1000) begin
            @(posedge clk);
            opcode     = $urandom;
            operand_a  = $urandom;
            operand_b  = $urandom;
            error_code = $urandom;
            cmd_field  = $urandom_range(0, 10);
            valid      = $urandom_range(0, 1);
            hazard_flag= $urandom_range(0, 1);
            fsm_state  = $urandom_range(0, 7);
            cg_explosive.sample();
            cg_weight.sample();
            // Call the hot function that creates inline CG instances
            sample_in_hot_loop(opcode);
        end

        $display("Coverage collection complete. Check simulator memory usage.");
        $display("Explosive CG cross bins allocated: %0d", 256*256*256);
        $finish;
    end
endmodule

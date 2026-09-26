// stress_verilog_02_metastable_sync.v
// ByteSized Stress Suite — Verilog: Metastable synchronizer anti-patterns
// including reset synchronization failures and false-path constraints
`timescale 1ns/1ps

// ============================================================
// ANTI-PATTERN 1: Asynchronous reset released synchronously wrong domain
// Reset deassertion is itself an asynchronous event; without a reset
// synchronizer it can violate recovery time of the receiving flops.
// ============================================================
module async_reset_no_sync (
    input  wire clk,
    input  wire async_rst_n,    // from power-on-reset or watchdog — truly asynchronous
    output reg  [7:0] count
);
    // DEFECT RTL-META-001: async_rst_n released asynchronously
    // may violate recovery time on some flip-flops → indeterminate reset state.
    always @(posedge clk or negedge async_rst_n) begin
        if (!async_rst_n)
            count <= 8'h00;
        else
            count <= count + 1;
    end
endmodule

// ============================================================
// ANTI-PATTERN 2: Combinational feedback from metastable output
// ============================================================
module meta_feedback_hazard (
    input  wire clk_a, clk_b, rst_n,
    input  wire req_a,    // request in domain A
    output reg  ack_a,    // ack back to domain A
    output reg  proc_b    // processed flag in domain B
);
    reg req_b_sync1, req_b_sync2;  // two-flop sync (partially correct)
    reg ack_b;

    // Two-stage synchronizer (correct for single-bit)
    always @(posedge clk_b or negedge rst_n) begin
        if (!rst_n) begin req_b_sync1 <= 0; req_b_sync2 <= 0; end
        else begin
            req_b_sync1 <= req_a;
            req_b_sync2 <= req_b_sync1;
        end
    end

    // DEFECT RTL-META-002: ack_a is driven by a combinational expression
    // that includes req_b_sync2 — combinational path from synchronizer output
    // back to domain-A logic without re-registering in clk_a domain.
    always @(posedge clk_b or negedge rst_n) begin
        if (!rst_n) begin proc_b <= 0; ack_b <= 0; end
        else if (req_b_sync2) begin
            proc_b <= 1;
            ack_b  <= 1;
        end else begin
            proc_b <= 0;
            ack_b  <= 0;
        end
    end

    // HAZARD: ack_a derives from ack_b (clk_b domain) without a synchronizer
    assign ack_a = ack_b;   // RTL-META-002: missing sync on return path
endmodule

// ============================================================
// ANTI-PATTERN 3: Pulse stretcher without synchronizer
// A short pulse from a fast clock domain may be missed by a slow clock domain.
// ============================================================
module pulse_width_mismatch (
    input  wire clk_fast,   // 200 MHz
    input  wire clk_slow,   // 50 MHz
    input  wire rst_n,
    input  wire pulse_fast, // 1-cycle pulse at 200 MHz = 5 ns
    output reg  pulse_slow  // needs to be visible at 50 MHz = 20 ns per cycle
);
    // DEFECT RTL-META-003: a 5 ns pulse may not be sampled by clk_slow (20 ns period).
    // Correct solution: convert to a toggle (level) and synchronize, or use a
    // pulse stretcher that holds the pulse for at least 1.5× clk_slow periods.
    always @(posedge clk_slow or negedge rst_n) begin
        if (!rst_n) pulse_slow <= 0;
        else        pulse_slow <= pulse_fast;   // direct sampling — may miss short pulses
    end
endmodule

// ============================================================
// ANTI-PATTERN 4: Glitch on gated clock used as data capture clock
// ============================================================
module gated_clock_glitch (
    input  wire clk,
    input  wire enable,     // combinational enable — may glitch
    input  wire [7:0] d,
    output reg  [7:0] q
);
    // DEFECT RTL-META-004: gated clock created combinationally.
    // A glitch on 'enable' during clk=1 creates a spurious clock edge,
    // capturing invalid data. Use an ICG (Integrated Clock Gating) cell instead.
    wire gated_clk = clk & enable;   // HAZARD: combinational glitch on gated_clk

    always @(posedge gated_clk) begin
        q <= d;   // data captured on a glitchy clock
    end
endmodule

// ============================================================
// ANTI-PATTERN 5: Multi-bit control word crossing without valid/ready handshake
// ============================================================
module config_bus_cdc_hazard (
    input  wire        wr_clk,
    input  wire        rd_clk,
    input  wire        rst_n,
    input  wire        cfg_write,
    input  wire [31:0] cfg_data_in,
    output reg  [31:0] cfg_data_out
);
    reg [31:0] cfg_reg_wr;

    always @(posedge wr_clk or negedge rst_n) begin
        if (!rst_n) cfg_reg_wr <= 32'h0;
        else if (cfg_write) cfg_reg_wr <= cfg_data_in;
    end

    // DEFECT RTL-META-005: 32-bit config register sampled directly in rd_clk.
    // Bits may be captured from two different write-clock cycles.
    always @(posedge rd_clk or negedge rst_n) begin
        if (!rst_n) cfg_data_out <= 32'h0;
        else        cfg_data_out <= cfg_reg_wr;   // raw 32-bit CDC — torn read hazard
    end
endmodule

// ============================================================
// TESTBENCH
// ============================================================
module tb_metastable;
    reg clk200, clk50, clk_slow2, rst_n;
    reg pulse_src;

    initial clk200 = 0;
    always #2.5 clk200 = ~clk200;

    initial clk50 = 0;
    always #10 clk50 = ~clk50;

    initial clk_slow2 = 0;
    always #6 clk_slow2 = ~clk_slow2;

    pulse_width_mismatch u_pwm (
        .clk_fast(clk200), .clk_slow(clk50), .rst_n(rst_n),
        .pulse_fast(pulse_src), .pulse_slow()
    );

    initial begin
        $dumpfile("metastable.vcd");
        $dumpvars(0, tb_metastable);
        rst_n = 0; pulse_src = 0;
        #15 rst_n = 1;
        // Issue a single 5 ns pulse — may be completely missed by 50 MHz clock
        #22 pulse_src = 1;
        #5  pulse_src = 0;
        #200 $finish;
    end
endmodule

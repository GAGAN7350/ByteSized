// stress_verilog_01_cdc_hazards.v
// ByteSized Stress Suite — Verilog: Clock Domain Crossing (CDC) hazards
// Run with: iverilog -o cdc_sim stress_verilog_01_cdc_hazards.v && ./cdc_sim

`timescale 1ns/1ps

// ============================================================
// ANTI-PATTERN 1: Single-flop synchronizer — metastability risk
// A one-flop synchronizer does not provide adequate MTBF margin.
// Industry minimum is two flip-flops in series for CDC crossing.
// ============================================================
module single_flop_synchronizer (
    input  wire clk_dst,     // destination clock domain
    input  wire rst_n,
    input  wire data_src,    // signal from source clock domain (ASYNC)
    output reg  data_dst     // HAZARD: single-stage — inadequate metastability rejection
);
    // DEFECT: one register only. If data_src transitions near clk_dst posedge,
    // data_dst can go metastable, violating setup/hold simultaneously.
    always @(posedge clk_dst or negedge rst_n) begin
        if (!rst_n)
            data_dst <= 1'b0;
        else
            data_dst <= data_src;   // RTL-CDC-001: missing second sync stage
    end
endmodule

// ============================================================
// ANTI-PATTERN 2: Multi-bit CDC without handshake or gray encoding
// Sampling a multi-bit bus directly across clock domains causes
// torn reads — bits can belong to different source-clock cycles.
// ============================================================
module multibit_cdc_no_handshake (
    input  wire        clk_src,
    input  wire        clk_dst,
    input  wire        rst_n,
    input  wire [15:0] data_src_bus,   // 16-bit bus in source domain
    output reg  [15:0] data_dst_bus    // HAZARD: sampled in destination domain without sync
);
    // DEFECT: direct register-to-register across clock domains.
    // data_src_bus bits may change in different dst-clock cycles → torn read.
    always @(posedge clk_dst or negedge rst_n) begin
        if (!rst_n)
            data_dst_bus <= 16'h0000;
        else
            data_dst_bus <= data_src_bus;  // RTL-CDC-002: multi-bit raw crossing
    end
endmodule

// ============================================================
// ANTI-PATTERN 3: FIFO write pointer sampled directly in read domain
// ============================================================
module async_fifo_bad #(
    parameter DEPTH = 16,
    parameter WIDTH = 8
)(
    input  wire             wr_clk,
    input  wire             rd_clk,
    input  wire             rst_n,
    input  wire             wr_en,
    input  wire [WIDTH-1:0] wr_data,
    output reg  [WIDTH-1:0] rd_data,
    output wire             full,
    output wire             empty
);
    localparam ADDR_W = $clog2(DEPTH);

    reg [WIDTH-1:0]  mem [0:DEPTH-1];
    reg [ADDR_W:0]   wr_ptr;   // write pointer in wr_clk domain
    reg [ADDR_W:0]   rd_ptr;   // read pointer in rd_clk domain

    // DEFECT: full/empty computed by direct comparison of cross-domain pointers.
    // wr_ptr is in wr_clk domain; comparing it directly in rd_clk domain is a
    // multi-bit CDC hazard — binary pointer may be in transition mid-sample.
    assign empty = (wr_ptr == rd_ptr);    // RTL-CDC-003: cross-domain pointer compare
    assign full  = (wr_ptr[ADDR_W] != rd_ptr[ADDR_W]) &&
                   (wr_ptr[ADDR_W-1:0] == rd_ptr[ADDR_W-1:0]);

    always @(posedge wr_clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr <= {(ADDR_W+1){1'b0}};
        end else if (wr_en && !full) begin
            mem[wr_ptr[ADDR_W-1:0]] <= wr_data;
            wr_ptr <= wr_ptr + 1;
        end
    end

    always @(posedge rd_clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_ptr  <= {(ADDR_W+1){1'b0}};
            rd_data <= {WIDTH{1'b0}};
        end else if (!empty) begin
            rd_data <= mem[rd_ptr[ADDR_W-1:0]];
            rd_ptr  <= rd_ptr + 1;
        end
    end
endmodule

// ============================================================
// ANTI-PATTERN 4: Combinational logic in CDC path
// ============================================================
module cdc_combinational_glitch (
    input  wire clk_src,
    input  wire clk_dst,
    input  wire rst_n,
    input  wire [3:0] sel_src,   // selector in source domain
    output reg        flag_dst
);
    wire decoded;
    // DEFECT: combinational decode of src-domain signal, then crossing to dst domain.
    // Glitches on the combinational path are sampled by clk_dst as real transitions.
    assign decoded = (sel_src == 4'b1010);  // RTL-CDC-004: comb path in CDC

    always @(posedge clk_dst or negedge rst_n) begin
        if (!rst_n) flag_dst <= 1'b0;
        else        flag_dst <= decoded;   // sampling a glitchy combinational signal
    end
endmodule

// ============================================================
// TESTBENCH
// ============================================================
module tb_cdc_hazards;
    reg clk_fast, clk_slow, rst_n, data_in;
    reg [15:0] bus_in;
    wire data_out_single, data_out_multi;

    // 200 MHz fast clock (5ns period)
    initial clk_fast = 0;
    always #2.5 clk_fast = ~clk_fast;

    // 83 MHz slow clock (12ns period) — asynchronous to clk_fast
    initial clk_slow = 0;
    always #6 clk_slow = ~clk_slow;

    single_flop_synchronizer u_single (
        .clk_dst(clk_slow), .rst_n(rst_n),
        .data_src(data_in), .data_dst(data_out_single)
    );

    multibit_cdc_no_handshake u_multi (
        .clk_src(clk_fast), .clk_dst(clk_slow), .rst_n(rst_n),
        .data_src_bus(bus_in), .data_dst_bus()
    );

    initial begin
        $dumpfile("cdc_hazards.vcd");
        $dumpvars(0, tb_cdc_hazards);
        rst_n   = 0; data_in = 0; bus_in = 16'h0;
        #20 rst_n = 1;
        // Drive data_in close to clk_slow edge to provoke metastability window
        #5.9 data_in = 1;
        #3   data_in = 0;
        #5.9 data_in = 1;
        // Drive bus at near-simultaneous transitions
        #4   bus_in = 16'hABCD;
        #1   bus_in = 16'h1234;
        #100 $finish;
    end
endmodule

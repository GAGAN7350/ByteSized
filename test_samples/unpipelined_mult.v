// ============================================================================
// TEST SAMPLE 3: MAC (Multiply-Accumulate) Unit Needing PPA Optimization
// Target: Critical path timing optimization and pipelining
// ============================================================================
module mac_unit (
    input wire clk,
    input wire [15:0] a,
    input wire [15:0] b,
    input wire [31:0] c,
    output reg [31:0] out
);

    always @(posedge clk) begin
        #2; // Non-synthesizable simulation delay artifact
        out <= (a * b) + c; // Deep combinational path creates timing violation at high GHz
    end

endmodule

// ============================================================================
// TEST SAMPLE 1: 4-Bit ALU with Inadvertent Transparent Latch Bug
// Violation: 'case' lacks a default branch, causing unwanted hardware latch.
// ============================================================================
module alu_4bit (
    input wire clk,
    input wire [3:0] a,
    input wire [3:0] b,
    input wire [1:0] opcode,
    output reg [3:0] result
);

    always @(posedge clk) begin
        case (opcode)
            2'b00: result = a + b;
            2'b01: result = a - b;
            2'b10: result = a & b;
            // 2'b11 is missing! And no default is specified.
            // Hardware synthesis will infer an unintended level-sensitive latch!
        endcase
    end

endmodule

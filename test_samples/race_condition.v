// ============================================================================
// TEST SAMPLE 2: Shift Register with Blocking Assignment Race Condition
// Violation: Using '=' inside posedge clk causes simulation/hardware race conditions.
// ============================================================================
module shift_reg (
    input wire clk,
    input wire rst_n,
    input wire data_in,
    output reg data_out
);

    reg q1, q2;

    always @(posedge clk) begin
        if (!rst_n) begin
            q1 = 1'b0;
            q2 = 1'b0;
            data_out = 1'b0;
        end else begin
            // Fatal RTL Design Bug: Blocking assignments in sequential block
            // Data falls through in a single clock cycle instead of shifting!
            q1 = data_in;
            q2 = q1;
            data_out = q2;
        end
    end

endmodule

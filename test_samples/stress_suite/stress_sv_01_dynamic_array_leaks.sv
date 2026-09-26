// stress_sv_01_dynamic_array_leaks.sv
// ByteSized Stress Suite — SystemVerilog: dynamic array leaks, class handle leaks
`timescale 1ns/1ps

// ============================================================
// ANTI-PATTERN 1: Dynamic array grows but is never freed
// In SystemVerilog class context, dynamic arrays allocated with 'new[]'
// must be deleted with 'delete' when no longer needed.
// ============================================================
class PacketBuffer;
    byte data[];    // dynamic array
    int  size;

    function new(int sz);
        size = sz;
        data = new[sz];   // allocates sz bytes on the heap
        foreach (data[i]) data[i] = $urandom_range(0, 255);
    endfunction

    // ANTI-PATTERN SV-001: no destructor / delete[] call.
    // SystemVerilog simulation memory is not returned on handle loss.
    // delete is never called: function void cleanup(); delete data; endfunction
endclass

// ============================================================
// ANTI-PATTERN 2: Class handles stored in dynamic array without cleanup
// ============================================================
class MemoryLeakGenerator;
    PacketBuffer buffers[];   // dynamic array of class handles
    int          count;

    function new();
        count = 0;
        buffers = new[0];   // empty initially
    endfunction

    function void allocate_packet(int sz);
        PacketBuffer pb = new(sz);
        // ANTI-PATTERN SV-002: resize and append without ever calling delete
        buffers = new[count + 1](buffers);
        buffers[count] = pb;
        count++;
    endfunction

    // DEFECT: no cleanup function to iterate and delete each PacketBuffer
endclass

// ============================================================
// ANTI-PATTERN 3: Associative array (mailbox) that fills unboundedly
// ============================================================
class UnboundedMailbox;
    mailbox #(PacketBuffer) mb;

    function new();
        mb = new(0);   // ANTI-PATTERN SV-003: unbounded mailbox (capacity=0 means infinite)
    endfunction

    task fill_forever();
        PacketBuffer pb;
        forever begin
            pb = new(4096);   // 4 KB per iteration
            mb.put(pb);       // LEAK: if consumer is slower than producer, mailbox grows
            #1;
        end
    endtask

    task drain_slowly();
        PacketBuffer pb;
        forever begin
            mb.get(pb);
            #100;   // consumer 100x slower than producer
        end
    endtask
endclass

// ============================================================
// ANTI-PATTERN 4: Recursive class allocation without base case guard
// ============================================================
class RecursiveNode;
    RecursiveNode child;   // strong reference — reference cycle risk in simulation

    function new(int depth);
        if (depth > 0) begin
            // ANTI-PATTERN SV-004: deep recursion allocates unbounded nodes
            child = new(depth - 1);
        end
    endfunction
endclass

// ============================================================
// ANTI-PATTERN 5: Scoreboard with no eviction policy
// ============================================================
class Scoreboard;
    int expected[int];   // associative array: transaction_id -> expected_value
    int hit_count;
    int miss_count;

    function new();
        hit_count = 0;
        miss_count = 0;
    endfunction

    function void record(int txn_id, int value);
        // ANTI-PATTERN SV-005: entries are never removed from the associative array.
        // In a long regression, this grows to millions of entries.
        expected[txn_id] = value;
    endfunction

    function void check(int txn_id, int actual);
        if (expected.exists(txn_id)) begin
            if (expected[txn_id] === actual) hit_count++;
            else miss_count++;
            // DEFECT: expected[txn_id] is never deleted after check
            // expected.delete(txn_id);  // missing cleanup
        end
    endfunction
endclass

// ============================================================
// TESTBENCH
// ============================================================
module tb_sv_dynamic_leaks;
    initial begin
        automatic MemoryLeakGenerator gen = new();
        automatic Scoreboard sb = new();
        automatic UnboundedMailbox umb = new();
        automatic RecursiveNode root;

        // Allocate 10000 packets without ever freeing
        repeat (10000) begin
            gen.allocate_packet($urandom_range(64, 4096));
        end
        $display("Allocated %0d packets, no cleanup performed", gen.count);

        // Fill scoreboard without eviction
        repeat (100000) begin
            automatic int id = $urandom;
            sb.record(id, id * 3);
        end
        $display("Scoreboard entries: %0d (should be pruned after check)", sb.expected.size());

        // Build a deep recursive tree (depth=500 → 500 class allocations)
        root = new(500);
        $display("Recursive tree of depth 500 allocated, never freed");

        #10;
        $display("Simulation complete. Memory usage peak is unbounded.");
        $finish;
    end
endmodule

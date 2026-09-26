/**
 * StressJava02GCPressure.java
 * ByteSized Stress Suite — Java: GC pressure, allocation storms,
 * String concatenation in loops, autoboxing overflow, and finalizer abuse.
 *
 * Compile: javac StressJava02GCPressure.java
 * Run:     java -Xmx256m -verbose:gc StressJava02GCPressure
 */
import java.util.*;
import java.util.stream.*;

public class StressJava02GCPressure {

    // ============================================================
    // ANTI-PATTERN 1: String concatenation in a loop — O(n²) object churn
    // Each += creates a new String object and discards the old one.
    // ============================================================
    static String buildStringConcat(int n) {
        String result = "";
        for (int i = 0; i < n; i++) {
            // HAZARD JAVA-GC-001: creates n String objects, total O(n²) chars copied.
            // Correct: use StringBuilder.append().
            result += "iteration_" + i + "|";
        }
        return result;
    }

    // ============================================================
    // ANTI-PATTERN 2: Autoboxing storm — Integer allocated per loop iteration
    // ============================================================
    static long sumWithAutoboxing(int n) {
        Long sum = 0L;  // HAZARD JAVA-GC-002: Long (boxed) in the accumulator
        for (int i = 0; i < n; i++) {
            sum += i;   // unboxes sum, adds i, autoboxes result → n Long allocations
        }
        return sum;
    }

    // ============================================================
    // ANTI-PATTERN 3: Creating large temporary collections in a hot method
    // ============================================================
    static int processData(int[] data) {
        // HAZARD JAVA-GC-003: boxing every int into Integer for stream processing.
        // A 10M-element int[] becomes a 10M-element boxed Integer stream.
        List<Integer> boxed = Arrays.stream(data)
            .boxed()                          // boxes every int → 10M Integer objects
            .collect(Collectors.toList());    // allocates ArrayList + 10M Integer refs
        return boxed.stream().mapToInt(Integer::intValue).sum();  // unboxes all again
    }

    // ============================================================
    // ANTI-PATTERN 4: Finalizer-based resource management causing GC delay
    // ============================================================
    static class FinalizerResource {
        private final byte[] data;
        private final int id;
        private boolean closed = false;

        FinalizerResource(int id) {
            this.id = id;
            this.data = new byte[64 * 1024];  // 64 KB per object
        }

        // ANTI-PATTERN JAVA-GC-004: relying on finalize() for resource cleanup.
        // finalize() is called by the GC finalizer thread — non-deterministically,
        // possibly never, and always after at least one additional GC cycle.
        // Objects with non-trivial finalize() are "resurrected" to the finalizer queue
        // and survive at least one extra GC pass.
        @Override
        @SuppressWarnings("deprecation")
        protected void finalize() throws Throwable {
            if (!closed) {
                System.out.println("FinalizerResource " + id + " being finalized (late cleanup)");
                closed = true;
            }
            super.finalize();
        }
    }

    static void allocateFinalizerObjects(int n) {
        for (int i = 0; i < n; i++) {
            FinalizerResource r = new FinalizerResource(i);
            // r goes out of scope, but finalize() queue keeps it alive one more GC cycle
        }
    }

    // ============================================================
    // ANTI-PATTERN 5: LinkedList for indexed access — O(n) per get()
    // ============================================================
    static void linkedListIndexedAccess(int n) {
        LinkedList<Integer> list = new LinkedList<>();
        for (int i = 0; i < n; i++) list.add(i);

        int sum = 0;
        // HAZARD JAVA-GC-005: list.get(i) on a LinkedList is O(n) — total O(n²).
        // Also generates garbage from iterator state inside get().
        for (int i = 0; i < list.size(); i++) {
            sum += list.get(i);   // O(n) traversal per access
        }
        System.out.println("LinkedList sum: " + sum);
    }

    // ============================================================
    // ANTI-PATTERN 6: HashMap with poor initial capacity — excessive rehashing
    // ============================================================
    static Map<Integer, String> buildMapWithRehash(int n) {
        // HAZARD JAVA-GC-006: default initial capacity (16) and load factor (0.75).
        // With n=100000, rehashing occurs at sizes 12, 24, 48, ... up to n,
        // each creating a new internal array and rehashing all existing entries.
        Map<Integer, String> map = new HashMap<>();  // should be new HashMap<>(n * 2)
        for (int i = 0; i < n; i++) {
            map.put(i, "value_" + i);
        }
        return map;
    }

    // ============================================================
    // ANTI-PATTERN 7: Allocation in paintComponent / render hot path (simulated)
    // ============================================================
    static volatile long frameCount = 0;

    static void simulateRenderLoop(int frames) {
        for (int frame = 0; frame < frames; frame++) {
            // HAZARD JAVA-GC-007: allocating a new array on every "frame" render call.
            // At 60 fps this is 60 allocations/second of a large array → GC pause jitter.
            int[] frameBuffer = new int[1920 * 1080];   // 8 MB allocation per frame
            Arrays.fill(frameBuffer, frame & 0xFF);
            frameCount++;
        }
        System.out.println("Render loop complete: " + frameCount + " frames");
    }

    // ============================================================
    // MAIN
    // ============================================================
    public static void main(String[] args) {
        System.out.println("=== String Concat in Loop (n=5000) ===");
        long t0 = System.currentTimeMillis();
        String s = buildStringConcat(5000);
        System.out.printf("buildStringConcat: %dms, length=%d%n",
            System.currentTimeMillis() - t0, s.length());

        System.out.println("\n=== Autoboxing Storm (n=10,000,000) ===");
        t0 = System.currentTimeMillis();
        long sum = sumWithAutoboxing(10_000_000);
        System.out.printf("sumWithAutoboxing: %dms, sum=%d%n",
            System.currentTimeMillis() - t0, sum);

        System.out.println("\n=== Boxed Stream Processing (n=1,000,000) ===");
        int[] data = new int[1_000_000];
        Arrays.fill(data, 1);
        t0 = System.currentTimeMillis();
        int streamSum = processData(data);
        System.out.printf("processData (boxed): %dms, sum=%d%n",
            System.currentTimeMillis() - t0, streamSum);

        System.out.println("\n=== Finalizer Objects (n=1000) ===");
        allocateFinalizerObjects(1000);
        System.gc();   // request GC to flush finalizer queue
        System.out.println("GC requested — finalizer queue may be large");

        System.out.println("\n=== LinkedList Indexed Access (n=10000) ===");
        t0 = System.currentTimeMillis();
        linkedListIndexedAccess(10_000);
        System.out.printf("linkedListIndexedAccess: %dms%n", System.currentTimeMillis() - t0);

        System.out.println("\n=== HashMap Without Initial Capacity (n=100000) ===");
        t0 = System.currentTimeMillis();
        Map<Integer, String> bigMap = buildMapWithRehash(100_000);
        System.out.printf("buildMapWithRehash: %dms, size=%d%n",
            System.currentTimeMillis() - t0, bigMap.size());

        System.out.println("\n=== Render Loop Allocation (100 frames × 8MB) ===");
        t0 = System.currentTimeMillis();
        simulateRenderLoop(100);
        System.out.printf("simulateRenderLoop: %dms%n", System.currentTimeMillis() - t0);

        System.out.println("\nAll GC pressure patterns demonstrated.");
    }
}

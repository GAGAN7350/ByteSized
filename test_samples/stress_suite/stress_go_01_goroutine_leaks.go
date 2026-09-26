// stress_go_01_goroutine_leaks.go
// ByteSized Stress Suite — Go: goroutine leaks, context propagation failures,
// blocking channel operations, and WaitGroup misuse.
//
// Run: go run stress_go_01_goroutine_leaks.go
package main

import (
	"context"
	"fmt"
	"math/rand"
	"runtime"
	"sync"
	"time"
)

// ============================================================
// ANTI-PATTERN 1: Goroutine launched but channel receiver never started
// ============================================================
func leakGoroutineWithUnreadChannel() {
	ch := make(chan int)

	// HAZARD GO-GL-001: goroutine writes to ch but no one ever reads.
	// The goroutine blocks forever on ch <- i, consuming a goroutine stack (~2-8 KB).
	go func() {
		for i := 0; i < 1000; i++ {
			ch <- i // BLOCKS: no reader ever consumes from ch
		}
	}()

	// Caller returns without reading from ch — goroutine is permanently blocked.
	fmt.Println("[leakGoroutineWithUnreadChannel] Returned without reading channel")
}

// ============================================================
// ANTI-PATTERN 2: Goroutine launched inside a loop, channel never drained
// ============================================================
func leakGoroutinesInLoop(n int) {
	results := make(chan string) // unbuffered

	for i := 0; i < n; i++ {
		go func(id int) {
			time.Sleep(time.Duration(rand.Intn(100)) * time.Millisecond)
			// HAZARD GO-GL-002: if the caller stops reading from results,
			// all goroutines block on this send forever.
			results <- fmt.Sprintf("worker_%d_done", id)
		}(i)
	}

	// DEFECT: only reads 5 results, then returns.
	// The remaining n-5 goroutines block on results <- ... forever.
	for i := 0; i < 5 && i < n; i++ {
		fmt.Println(<-results)
	}
}

// ============================================================
// ANTI-PATTERN 3: Goroutine ignoring context cancellation
// ============================================================
func workerIgnoringContext(id int) {
	// HAZARD GO-GL-003: goroutine does not select on ctx.Done().
	// When the context is cancelled (e.g., request timeout), the goroutine
	// continues running indefinitely, holding resources.
	for {
		time.Sleep(10 * time.Millisecond)
		fmt.Printf("[worker %d] still running (ignoring context)\n", id)
		if id > 100000 { // unreachable guard — effectively runs forever
			break
		}
	}
}

func launchContextIgnoringWorkers(ctx context.Context, n int) {
	for i := 0; i < n; i++ {
		go workerIgnoringContext(i) // no ctx passed — cannot be cancelled
	}
}

// ============================================================
// ANTI-PATTERN 4: WaitGroup counter decremented before Add completes
// ============================================================
func wgAddInsideGoroutine() {
	var wg sync.WaitGroup

	for i := 0; i < 10; i++ {
		// HAZARD GO-GL-004: wg.Add(1) is called inside the goroutine.
		// The main goroutine may call wg.Wait() before any goroutine runs Add,
		// causing Wait to return immediately while workers are still running.
		go func(id int) {
			wg.Add(1) // WRONG: should be wg.Add(1) BEFORE go func(...)
			defer wg.Done()
			time.Sleep(time.Duration(rand.Intn(50)) * time.Millisecond)
			fmt.Printf("[wg worker %d] done\n", id)
		}(i)
	}

	wg.Wait() // may return before any worker runs
	fmt.Println("[wgAddInsideGoroutine] wg.Wait() returned — workers may still be running")
}

// ============================================================
// ANTI-PATTERN 5: Goroutine created for trivial work — goroutine explosion
// ============================================================
func goroutineExplosion(n int) {
	var mu sync.Mutex
	total := 0

	for i := 0; i < n; i++ {
		// HAZARD GO-GL-005: spawning a goroutine for a trivial increment.
		// With n=1,000,000, this creates 1M goroutines simultaneously,
		// exhausting memory (each goroutine uses ≥2 KB stack → ≥2 GB total).
		go func(val int) {
			mu.Lock()
			total += val
			mu.Unlock()
		}(i)
	}

	time.Sleep(2 * time.Second) // hope all goroutines finish (not deterministic!)
	fmt.Printf("[goroutineExplosion] total=%d (expected=%d)\n", total, n*(n-1)/2)
}

// ============================================================
// ANTI-PATTERN 6: Goroutine leak via panic without recover
// ============================================================
func panicWithoutRecover() {
	defer func() {
		// DEFECT GO-GL-006: recover() is not called — panic propagates to runtime
		// and terminates the entire program, not just the goroutine.
	}()

	go func() {
		defer func() {
			if r := recover(); r != nil {
				fmt.Println("[panicWithoutRecover] Recovered:", r)
			}
		}()
		panic("intentional panic in goroutine")
	}()

	time.Sleep(50 * time.Millisecond)
}

// ============================================================
// MAIN
// ============================================================
func main() {
	fmt.Printf("[Start] Goroutines: %d\n", runtime.NumGoroutine())

	fmt.Println("\n=== Leak: Unread Channel ===")
	leakGoroutineWithUnreadChannel()
	time.Sleep(100 * time.Millisecond)
	fmt.Printf("Goroutines after unread-channel leak: %d\n", runtime.NumGoroutine())

	fmt.Println("\n=== Leak: Loop Goroutines (partial drain) ===")
	leakGoroutinesInLoop(50)
	time.Sleep(500 * time.Millisecond)
	fmt.Printf("Goroutines after loop leak: %d\n", runtime.NumGoroutine())

	fmt.Println("\n=== Leak: Context-Ignoring Workers ===")
	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()
	launchContextIgnoringWorkers(ctx, 5)
	<-ctx.Done()
	time.Sleep(100 * time.Millisecond)
	fmt.Printf("Goroutines after ctx cancel (workers still running): %d\n", runtime.NumGoroutine())

	fmt.Println("\n=== WaitGroup Add Inside Goroutine ===")
	wgAddInsideGoroutine()

	fmt.Println("\n=== Panic Without Recover ===")
	panicWithoutRecover()

	fmt.Printf("\n[End] Final goroutine count: %d\n", runtime.NumGoroutine())
}

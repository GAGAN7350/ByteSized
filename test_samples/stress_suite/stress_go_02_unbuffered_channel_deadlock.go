// stress_go_02_unbuffered_channel_deadlock.go
// ByteSized Stress Suite — Go: unbuffered channel deadlocks, select starvation,
// and channel direction misuse.
//
// Run: go run stress_go_02_unbuffered_channel_deadlock.go
package main

import (
	"fmt"
	"sync"
	"time"
)

// ============================================================
// ANTI-PATTERN 1: Single goroutine sending AND receiving on same channel
// ============================================================
func selfDeadlock() {
	ch := make(chan int) // unbuffered

	// HAZARD GO-CH-001: send on unbuffered channel blocks until a receiver is ready.
	// This goroutine sends, then tries to receive — but it is also the only sender.
	// Both operations are on the same goroutine → instant deadlock.
	// (Wrapped in a goroutine here to avoid killing main)
	done := make(chan struct{})
	go func() {
		defer close(done)
		defer func() {
			if r := recover(); r != nil {
				fmt.Println("[selfDeadlock] panic recovered:", r)
			}
		}()
		ch <- 1       // BLOCKS: no receiver
		val := <-ch   // UNREACHABLE: goroutine is already blocked above
		fmt.Println("val:", val)
	}()

	select {
	case <-done:
	case <-time.After(500 * time.Millisecond):
		fmt.Println("[selfDeadlock] DEADLOCK DETECTED: goroutine timed out")
	}
}

// ============================================================
// ANTI-PATTERN 2: Producer sends more items than consumer reads
// ============================================================
func producerSendsMoreThanConsumed() {
	ch := make(chan int) // unbuffered — each send blocks until receiver reads

	var wg sync.WaitGroup
	wg.Add(1)
	go func() {
		defer wg.Done()
		// Consumer reads only 5 items, then exits
		for i := 0; i < 5; i++ {
			val := <-ch
			fmt.Printf("[consumer] got %d\n", val)
		}
		// HAZARD GO-CH-002: consumer goroutine exits while producer is blocked
		// on the 6th send → producer goroutine leaks
	}()

	for i := 0; i < 100; i++ {
		// Blocks after 5th send — consumer has exited
		select {
		case ch <- i:
		case <-time.After(200 * time.Millisecond):
			fmt.Printf("[producer] blocked at i=%d — consumer exited\n", i)
			return
		}
	}
	wg.Wait()
}

// ============================================================
// ANTI-PATTERN 3: Multiple goroutines racing on close(ch)
// ============================================================
func multipleCloseRace(n int) {
	ch := make(chan int, n)

	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			defer func() {
				if r := recover(); r != nil {
					fmt.Printf("[worker %d] panic on close: %v\n", id, r)
				}
			}()
			ch <- id
			// HAZARD GO-CH-003: multiple goroutines each try to close the same channel.
			// Closing an already-closed channel panics.
			close(ch) // only ONE goroutine should call close — guard with sync.Once
		}(i)
	}
	wg.Wait()
}

// ============================================================
// ANTI-PATTERN 4: Select with no default — starves when all channels busy
// ============================================================
func selectStarvation() {
	ch1 := make(chan int)
	ch2 := make(chan int)

	go func() {
		for i := 0; ; i++ {
			ch1 <- i
			time.Sleep(time.Millisecond)
		}
	}()
	go func() {
		for i := 0; ; i++ {
			ch2 <- i
			time.Sleep(time.Millisecond)
		}
	}()

	// HAZARD GO-CH-004: if both channels are empty simultaneously, select blocks.
	// Without a default case or timeout, this can deadlock if both goroutines exit.
	count := 0
	for count < 20 {
		select {
		case v := <-ch1:
			fmt.Printf("[select] ch1: %d\n", v)
			count++
		case v := <-ch2:
			fmt.Printf("[select] ch2: %d\n", v)
			count++
		// Missing: case <-time.After(1 * time.Second): return  // timeout guard
		}
	}
}

// ============================================================
// ANTI-PATTERN 5: Receiving on a nil channel (blocks forever)
// ============================================================
func receiveOnNilChannel() {
	var ch chan int   // nil channel

	done := make(chan struct{})
	go func() {
		defer close(done)
		defer func() {
			if r := recover(); r != nil {
				fmt.Println("[nilChan] panic:", r)
			}
		}()
		// HAZARD GO-CH-005: receiving from a nil channel blocks forever.
		// This is a common mistake after a conditional channel initialization.
		val := <-ch
		fmt.Println("val:", val)
	}()

	select {
	case <-done:
	case <-time.After(300 * time.Millisecond):
		fmt.Println("[nilChan] DEADLOCK: receive on nil channel blocked")
	}
}

// ============================================================
// ANTI-PATTERN 6: Range over channel without close — range never terminates
// ============================================================
func rangeWithoutClose() {
	ch := make(chan int, 10)
	for i := 0; i < 10; i++ {
		ch <- i
	}
	// HAZARD GO-CH-006: range over channel waits for more values until channel is closed.
	// Forgetting close(ch) causes range to block forever after consuming all 10 items.
	done := make(chan struct{})
	go func() {
		defer close(done)
		for v := range ch {
			fmt.Printf("[range] %d\n", v)
		}
		fmt.Println("[range] channel closed, loop exited (would never print without close)")
	}()

	// close(ch)  // ← INTENTIONALLY MISSING to demonstrate the deadlock

	select {
	case <-done:
		fmt.Println("[rangeWithoutClose] completed (close was called)")
	case <-time.After(500 * time.Millisecond):
		fmt.Println("[rangeWithoutClose] DEADLOCK: range is blocked waiting for close(ch)")
	}
}

// ============================================================
// MAIN
// ============================================================
func main() {
	fmt.Println("=== Self Deadlock ===")
	selfDeadlock()

	fmt.Println("\n=== Producer Sends More Than Consumed ===")
	producerSendsMoreThanConsumed()

	fmt.Println("\n=== Multiple Close Race ===")
	multipleCloseRace(5)

	fmt.Println("\n=== Receive on Nil Channel ===")
	receiveOnNilChannel()

	fmt.Println("\n=== Range Without Close ===")
	rangeWithoutClose()

	fmt.Println("\n=== Select Starvation (20 rounds) ===")
	selectStarvation()

	fmt.Println("\nAll channel deadlock patterns demonstrated.")
}

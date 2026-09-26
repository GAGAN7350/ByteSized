// stress_rust_02_spinlock_contention.rs
// ByteSized Stress Suite — Rust: spinlock contention, busy-wait loops,
// Mutex poisoning, and priority inversion scenarios.
//
// Compile: rustc stress_rust_02_spinlock_contention.rs -o rust_spinlock
// Run:     ./rust_spinlock
use std::sync::atomic::{AtomicBool, AtomicI64, Ordering};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::{Duration, Instant};

// ============================================================
// ANTI-PATTERN 1: Spinlock implemented with AtomicBool — busy-wait
// ============================================================
struct SpinLock {
    locked: AtomicBool,
}

impl SpinLock {
    fn new() -> Self {
        SpinLock { locked: AtomicBool::new(false) }
    }

    fn acquire(&self) {
        // HAZARD RUST-SL-001: busy-wait loop burns 100% CPU on the waiting thread.
        // Under high contention, spinlocks cause cache-line ping-pong between cores,
        // causing memory bus saturation. Use std::sync::Mutex instead.
        while self.locked.compare_exchange_weak(
            false, true,
            Ordering::Acquire,
            Ordering::Relaxed,
        ).is_err() {
            // ANTI-PATTERN: no std::hint::spin_loop() call — prevents CPU relaxation
            // Correct: std::hint::spin_loop();  or use parking_lot::Mutex
        }
    }

    fn release(&self) {
        self.locked.store(false, Ordering::Release);
    }
}

fn demonstrate_spinlock_contention(n_threads: usize, iterations: usize) -> i64 {
    let spinlock = Arc::new(SpinLock::new());
    let counter  = Arc::new(AtomicI64::new(0));
    let mut handles = Vec::new();

    let t0 = Instant::now();
    for _ in 0..n_threads {
        let sl = Arc::clone(&spinlock);
        let ctr = Arc::clone(&counter);
        handles.push(thread::spawn(move || {
            for _ in 0..iterations {
                sl.acquire();
                // Critical section — holding spinlock while doing work
                let v = ctr.load(Ordering::Relaxed);
                thread::sleep(Duration::from_nanos(50));  // simulate work under lock
                ctr.store(v + 1, Ordering::Relaxed);
                sl.release();
            }
        }));
    }

    for h in handles { h.join().unwrap(); }
    let elapsed = t0.elapsed();
    let result = counter.load(Ordering::Relaxed);
    println!(
        "[spinlock] {} threads × {} iters = {} in {:?} (expected {})",
        n_threads, iterations, result, elapsed, (n_threads * iterations) as i64
    );
    result
}

// ============================================================
// ANTI-PATTERN 2: Mutex poisoning — lock poisoned by panicking thread
// ============================================================
fn demonstrate_mutex_poisoning() {
    let mutex = Arc::new(Mutex::new(0i32));
    let mutex2 = Arc::clone(&mutex);

    let panicking_thread = thread::spawn(move || {
        let _guard = mutex2.lock().unwrap();
        // HAZARD RUST-SL-002: thread panics while holding the Mutex.
        // The Mutex becomes "poisoned" — all subsequent lock() calls return Err(PoisonError).
        panic!("panicking while holding mutex");
    });

    let _ = panicking_thread.join();  // expected to panic

    // Subsequent lock attempts fail with PoisonError
    match mutex.lock() {
        Ok(v)  => println!("[mutex] locked: {}", v),
        Err(e) => {
            println!("[mutex] POISONED: {}", e);
            // ANTI-PATTERN: blindly calling into_inner() on a poisoned mutex
            // without checking the data state.
            let recovered = e.into_inner();
            println!("[mutex] Recovered poisoned value: {} (may be corrupt)", recovered);
        }
    }
}

// ============================================================
// ANTI-PATTERN 3: Priority inversion — low-priority thread holds mutex needed by high-priority
// ============================================================
fn demonstrate_priority_inversion() {
    let shared = Arc::new(Mutex::new(0i32));

    let shared_low  = Arc::clone(&shared);
    let shared_high = Arc::clone(&shared);

    // "Low-priority" thread: acquires lock and does long computation
    let low = thread::spawn(move || {
        let mut guard = shared_low.lock().unwrap();
        println!("[low-priority] Acquired lock, starting long work");
        // HAZARD RUST-SL-003: holds the mutex for a long duration.
        // "High-priority" thread blocks indefinitely waiting for this lock.
        thread::sleep(Duration::from_millis(200));
        *guard += 1;
        println!("[low-priority] Releasing lock after 200ms");
    });

    thread::sleep(Duration::from_millis(10));  // let low-priority thread grab lock

    // "High-priority" thread: blocked by low-priority thread
    let high = thread::spawn(move || {
        println!("[high-priority] Waiting for lock (blocked by low-priority)...");
        let t0 = Instant::now();
        let guard = shared_high.lock().unwrap();  // blocks for ~200ms
        println!("[high-priority] Got lock after {:?} (priority inverted)", t0.elapsed());
        drop(guard);
    });

    low.join().unwrap();
    high.join().unwrap();
}

// ============================================================
// ANTI-PATTERN 4: Lock-free counter with SeqCst ordering on every operation
// (unnecessary memory barrier overhead)
// ============================================================
fn demonstrate_excessive_seqcst_ordering(n: usize) {
    let counter = Arc::new(AtomicI64::new(0));
    let mut handles = Vec::new();

    let t0 = Instant::now();
    for _ in 0..8 {
        let c = Arc::clone(&counter);
        handles.push(thread::spawn(move || {
            for _ in 0..n {
                // HAZARD RUST-SL-004: SeqCst ordering on every increment is
                // the strongest memory order — it forces a full memory fence (MFENCE on x86).
                // Relaxed ordering suffices for a simple counter with no ordering requirement.
                c.fetch_add(1, Ordering::SeqCst);  // WRONG: should be Ordering::Relaxed
            }
        }));
    }

    for h in handles { h.join().unwrap(); }
    let elapsed = t0.elapsed();
    println!(
        "[SeqCst counter] 8 threads × {} = {} in {:?}",
        n, counter.load(Ordering::Relaxed), elapsed
    );
}

// ============================================================
// MAIN
// ============================================================
fn main() {
    println!("=== Spinlock Contention (8 threads × 500 iterations) ===");
    demonstrate_spinlock_contention(8, 500);

    println!("\n=== Mutex Poisoning ===");
    demonstrate_mutex_poisoning();

    println!("\n=== Priority Inversion ===");
    demonstrate_priority_inversion();

    println!("\n=== Excessive SeqCst Ordering (8 threads × 1,000,000) ===");
    demonstrate_excessive_seqcst_ordering(1_000_000);

    println!("\nAll spinlock contention patterns demonstrated.");
}

// stress_rust_01_rc_refcell_cycle.rs
// ByteSized Stress Suite — Rust: Rc<RefCell<T>> reference cycles causing memory leaks,
// RefCell borrow panics, and interior mutability misuse.
//
// Compile: rustc stress_rust_01_rc_refcell_cycle.rs -o rust_rc_cycle
// Run:     ./rust_rc_cycle

use std::cell::RefCell;
use std::rc::{Rc, Weak};

// ============================================================
// ANTI-PATTERN 1: Rc<RefCell<T>> reference cycle — leak without Weak
// ============================================================

#[derive(Debug)]
struct Node {
    value: i32,
    // HAZARD RUST-RC-001: strong Rc reference to next node.
    // If two nodes point to each other, neither is ever dropped.
    next: Option<Rc<RefCell<Node>>>,
}

impl Drop for Node {
    fn drop(&mut self) {
        println!("Dropping Node({})", self.value);
    }
}

fn demonstrate_rc_cycle() {
    let node_a = Rc::new(RefCell::new(Node { value: 1, next: None }));
    let node_b = Rc::new(RefCell::new(Node { value: 2, next: None }));

    // Create a cycle: A → B → A
    node_a.borrow_mut().next = Some(Rc::clone(&node_b));
    node_b.borrow_mut().next = Some(Rc::clone(&node_a));  // CYCLE: B holds A

    println!("node_a strong count: {}", Rc::strong_count(&node_a));   // 2
    println!("node_b strong count: {}", Rc::strong_count(&node_b));   // 2

    // node_a and node_b go out of scope here.
    // LEAK: strong count of each drops from 2 to 1, but never reaches 0.
    // Neither Drop impl is ever called.
    println!("End of demonstrate_rc_cycle() — Nodes NOT dropped (leaked)");
}

// ============================================================
// ANTI-PATTERN 2: Deep Rc cycle tree
// ============================================================

#[derive(Debug)]
struct TreeNode {
    id: usize,
    children: Vec<Rc<RefCell<TreeNode>>>,
    parent: Option<Rc<RefCell<TreeNode>>>,  // HAZARD: strong parent reference → cycle
    data: Vec<u8>,
}

fn build_cyclic_tree(depth: usize, branching: usize) -> Rc<RefCell<TreeNode>> {
    let root = Rc::new(RefCell::new(TreeNode {
        id: 0,
        children: Vec::new(),
        parent: None,
        data: vec![0u8; 4096],  // 4 KB payload per node
    }));

    let mut current_level = vec![Rc::clone(&root)];
    for d in 1..=depth {
        let mut next_level = Vec::new();
        for parent in &current_level {
            for b in 0..branching {
                let child = Rc::new(RefCell::new(TreeNode {
                    id: d * branching + b,
                    children: Vec::new(),
                    parent: Some(Rc::clone(parent)),  // CYCLE: child holds strong parent ref
                    data: vec![(d & 0xFF) as u8; 4096],
                }));
                parent.borrow_mut().children.push(Rc::clone(&child));
                next_level.push(child);
            }
        }
        current_level = next_level;
    }
    root  // Entire tree leaks when root is dropped (all nodes have strong parent refs)
}

// ============================================================
// ANTI-PATTERN 3: RefCell borrow panic at runtime
// ============================================================

fn demonstrate_refcell_borrow_panic() {
    let shared = Rc::new(RefCell::new(vec![1, 2, 3]));

    let borrow1 = shared.borrow();   // immutable borrow — OK
    println!("borrow1: {:?}", *borrow1);

    // HAZARD RUST-RC-003: attempting a mutable borrow while an immutable borrow is active.
    // RefCell enforces borrow rules at runtime — this panics instead of compile error.
    let _borrow_mut = shared.borrow_mut();  // PANIC: already immutably borrowed
    println!("This line is never reached");
}

// ============================================================
// ANTI-PATTERN 4: Nested borrow_mut causing panic
// ============================================================

fn nested_borrow_mut_panic() {
    let data = RefCell::new(vec![10, 20, 30]);

    // HAZARD RUST-RC-004: calling a closure that borrows data_ref mutably
    // while data is already borrowed immutably via iter().
    let _ref1 = data.borrow();
    {
        // This borrow_mut panics because _ref1 is still alive
        let _ref2 = data.borrow_mut();  // PANIC: already borrowed
    }
}

// ============================================================
// ANTI-PATTERN 5: Rc<RefCell> in hot loop — reference counting overhead
// ============================================================

fn rc_in_hot_loop(n: usize) -> i64 {
    // HAZARD RUST-RC-005: Rc::clone and RefCell::borrow in a tight loop.
    // Each Rc::clone increments a reference count (atomic on Rc = non-atomic,
    // but still a memory write + branch). RefCell::borrow checks a runtime counter.
    let counter = Rc::new(RefCell::new(0i64));
    for i in 0..n {
        let c = Rc::clone(&counter);   // clone on every iteration
        *c.borrow_mut() += i as i64;  // runtime borrow check on every iteration
    }
    let result = *counter.borrow();
    result
}

// ============================================================
// ANTI-PATTERN 6: Rc leaked via mem::forget
// ============================================================

fn leak_rc_with_mem_forget() {
    let val = Rc::new(RefCell::new(String::from("leaked string")));
    println!("Before forget: strong_count = {}", Rc::strong_count(&val));
    // HAZARD RUST-RC-006: mem::forget prevents Drop from running,
    // intentionally leaking the Rc — the allocation is never freed.
    std::mem::forget(val);
    // val is gone from scope, but the heap allocation remains permanently.
    println!("After mem::forget: allocation leaked, Drop never called");
}

// ============================================================
// MAIN
// ============================================================
fn main() {
    println!("=== Rc Cycle Leak (2 nodes) ===");
    demonstrate_rc_cycle();

    println!("\n=== Deep Cyclic Tree (depth=3, branching=2) ===");
    let _tree = build_cyclic_tree(3, 2);
    println!("Tree built — drops when _tree goes out of scope (but LEAKS due to cycles)");

    println!("\n=== RefCell Borrow Panic ===");
    let result = std::panic::catch_unwind(|| {
        demonstrate_refcell_borrow_panic();
    });
    println!("RefCell borrow panic caught: {}", result.is_err());

    println!("\n=== Nested borrow_mut Panic ===");
    let result2 = std::panic::catch_unwind(|| {
        nested_borrow_mut_panic();
    });
    println!("Nested borrow_mut panic caught: {}", result2.is_err());

    println!("\n=== Rc in Hot Loop (n=1,000,000) ===");
    let t0 = std::time::Instant::now();
    let sum = rc_in_hot_loop(1_000_000);
    println!("Sum={} in {:?}", sum, t0.elapsed());

    println!("\n=== Rc Leaked via mem::forget ===");
    leak_rc_with_mem_forget();

    println!("\nAll Rc/RefCell anti-patterns demonstrated.");
}

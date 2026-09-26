/**
 * stress_cpp_01_dangling_pointers.cpp
 * ByteSized Stress Suite — C++: dangling pointers, use-after-free, wild pointers
 *
 * Compile: g++ -O0 -fsanitize=address -g stress_cpp_01_dangling_pointers.cpp -o dangle
 */
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include <memory>
#include <functional>
#include <iostream>

// ============================================================
// ANTI-PATTERN 1: Raw pointer to stack-allocated object
// returned from a function — classic dangling pointer.
// ============================================================
int* dangling_stack_pointer() {
    int local_value = 42;       // lives on the stack
    return &local_value;        // HAZARD: pointer outlives local_value's lifetime
}                               // local_value is destroyed here — pointer is now dangling

// ============================================================
// ANTI-PATTERN 2: Use-after-free with raw heap pointer
// ============================================================
void use_after_free_demo() {
    int* heap_ptr = new int(100);
    std::printf("Before free: *heap_ptr = %d\n", *heap_ptr);
    delete heap_ptr;
    // HAZARD (CWE-416): Memory is released but pointer is not set to nullptr.
    // The next access reads freed memory — undefined behavior.
    std::printf("After free (UAF): *heap_ptr = %d\n", *heap_ptr);  // UAF
    *heap_ptr = 999;                                                  // UAF write
    delete heap_ptr;    // DOUBLE FREE (CWE-415) — second delete on same pointer
}

// ============================================================
// ANTI-PATTERN 3: Storing raw pointer into container after reallocation
// ============================================================
void invalidated_pointer_after_push_back() {
    std::vector<int> v = {1, 2, 3};
    int* raw_ptr = &v[0];       // pointer into vector internal buffer
    std::printf("Before push_back: *raw_ptr = %d, &v[0] = %p\n", *raw_ptr, (void*)&v[0]);

    // HAZARD: push_back may trigger reallocation, invalidating raw_ptr
    for (int i = 0; i < 1000; ++i) {
        v.push_back(i);
    }
    // raw_ptr now points to freed memory — UB on access
    std::printf("After push_back: *raw_ptr = %d (UB!), &v[0] = %p\n", *raw_ptr, (void*)&v[0]);
}

// ============================================================
// ANTI-PATTERN 4: Storing reference to temporary
// ============================================================
const std::string& dangling_string_reference() {
    std::string temp = "I am a temporary string";
    return temp;    // HAZARD: returning reference to local string — destroyed at return
}

// ============================================================
// ANTI-PATTERN 5: Lambda capturing reference to local variable
// ============================================================
std::function<int()> make_dangling_lambda() {
    int local = 77;
    // HAZARD: lambda captures local by reference; local is destroyed when
    // make_dangling_lambda returns, but the lambda survives.
    return [&local]() -> int { return local; };  // dangling reference capture
}

// ============================================================
// ANTI-PATTERN 6: Iterator invalidation via erase inside range-for
// ============================================================
void iterator_invalidation_erase() {
    std::vector<int> data = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    // HAZARD: erasing elements while iterating with a range-based for loop
    // causes undefined behavior — iterator is invalidated.
    for (auto it = data.begin(); it != data.end(); ++it) {
        if (*it % 2 == 0) {
            data.erase(it);    // HAZARD: invalidates all iterators past the erased element
        }
    }
}

// ============================================================
// ANTI-PATTERN 7: Incorrect shared_ptr cycle causing memory leak
// ============================================================
struct NodeA;
struct NodeB;

struct NodeA {
    std::shared_ptr<NodeB> b_ptr;   // strong reference
    int value;
    explicit NodeA(int v) : value(v) { std::printf("NodeA(%d) constructed\n", v); }
    ~NodeA() { std::printf("NodeA(%d) destructed\n", value); }
};

struct NodeB {
    std::shared_ptr<NodeA> a_ptr;   // HAZARD: strong reference back → CYCLE
    int value;
    explicit NodeB(int v) : value(v) { std::printf("NodeB(%d) constructed\n", v); }
    ~NodeB() { std::printf("NodeB(%d) destructed\n", value); }
};

void shared_ptr_cycle_leak() {
    auto a = std::make_shared<NodeA>(1);
    auto b = std::make_shared<NodeB>(2);
    a->b_ptr = b;   // a holds b
    b->a_ptr = a;   // b holds a → cycle
    // When a and b go out of scope, their use_counts are both 1
    // (each still held by the other), so neither destructor is called.
    std::printf("a.use_count()=%ld  b.use_count()=%ld\n", a.use_count(), b.use_count());
}   // LEAK: NodeA and NodeB are never destroyed

// ============================================================
// ANTI-PATTERN 8: reinterpret_cast violating strict aliasing
// ============================================================
void strict_aliasing_violation() {
    float f = 3.14159f;
    // HAZARD: reinterpret_cast to incompatible type violates strict aliasing rule.
    // Compiler may optimize based on the assumption that int* and float* cannot alias.
    int* ip = reinterpret_cast<int*>(&f);
    *ip = 0x3F800000;   // UB: write through aliased pointer
    std::printf("Float after aliased write: %f\n", f);
}

int main() {
    std::printf("=== Dangling Stack Pointer ===\n");
    int* dp = dangling_stack_pointer();
    std::printf("Dereferencing dangling ptr: %d (UB!)\n", *dp);

    std::printf("\n=== Use-After-Free ===\n");
    use_after_free_demo();

    std::printf("\n=== Invalidated Pointer After push_back ===\n");
    invalidated_pointer_after_push_back();

    std::printf("\n=== Dangling Lambda Capture ===\n");
    auto lambda = make_dangling_lambda();
    std::printf("Lambda result (UB): %d\n", lambda());

    std::printf("\n=== Iterator Invalidation ===\n");
    iterator_invalidation_erase();

    std::printf("\n=== shared_ptr Cycle Leak ===\n");
    shared_ptr_cycle_leak();

    std::printf("\n=== Strict Aliasing Violation ===\n");
    strict_aliasing_violation();

    return 0;
}

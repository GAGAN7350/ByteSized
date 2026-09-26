/**
 * stress_cpp_02_vector_realloc.cpp
 * ByteSized Stress Suite — C++: vector reallocation hazards, iterator invalidation,
 * excessive copy overhead, and reserve() omission causing O(n log n) reallocations.
 *
 * Compile: g++ -O2 -std=c++17 stress_cpp_02_vector_realloc.cpp -o vec_stress
 */
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <functional>
#include <iostream>
#include <numeric>
#include <string>
#include <vector>

// ============================================================
// ANTI-PATTERN 1: push_back in a loop without reserve()
// Triggers O(log n) reallocations, each O(n) copy → total O(n log n) copies.
// ============================================================
std::vector<std::string> build_vector_without_reserve(int n) {
    std::vector<std::string> result;
    // HAZARD: no result.reserve(n) — every reallocation copies all elements
    for (int i = 0; i < n; ++i) {
        result.push_back(std::string(128, 'A' + (i % 26)));
    }
    return result;
}

std::vector<std::string> build_vector_with_reserve(int n) {
    std::vector<std::string> result;
    result.reserve(n);   // CORRECT: pre-allocate exact capacity
    for (int i = 0; i < n; ++i) {
        result.push_back(std::string(128, 'A' + (i % 26)));
    }
    return result;
}

// ============================================================
// ANTI-PATTERN 2: Insert in the middle of a vector — O(n) shift
// ============================================================
void front_insert_hazard(int n) {
    std::vector<int> v;
    v.reserve(n);
    std::iota(v.begin(), v.end(), 0);  // fill [0, n)
    // HAZARD: inserting at front shifts all n elements right → O(n²) total
    for (int i = 0; i < 1000; ++i) {
        v.insert(v.begin(), i);
    }
}

// ============================================================
// ANTI-PATTERN 3: Taking reference to vector element, then push_back
// ============================================================
void reference_invalidation_demo() {
    std::vector<int> v = {10, 20, 30};
    const int& ref = v[0];   // reference into internal buffer
    std::printf("Before push_back: ref = %d\n", ref);
    // HAZARD: push_back may reallocate, invalidating ref
    v.push_back(40);
    v.push_back(50);
    v.push_back(60);
    std::printf("After push_back: ref = %d (may be garbage!)\n", ref);  // UB
}

// ============================================================
// ANTI-PATTERN 4: Sort + erase idiom — wrong (erase-remove missed)
// ============================================================
void wrong_erase_remove(std::vector<int>& v, int target) {
    // HAZARD: std::remove does NOT erase elements; it moves them to the end
    // and returns a past-the-end iterator. Without v.erase(), the vector still
    // contains the "removed" values as garbage past the new logical end.
    std::remove(v.begin(), v.end(), target);
    // Missing: v.erase(std::remove(v.begin(), v.end(), target), v.end());
}

// ============================================================
// ANTI-PATTERN 5: Nested push_back during iteration (range-for)
// ============================================================
void push_back_during_iteration() {
    std::vector<int> v = {1, 2, 3, 4, 5};
    // HAZARD: if push_back reallocates, all iterators (including end()) are
    // invalidated, causing undefined behavior in the range-for loop.
    for (int x : v) {
        if (x < 3) {
            v.push_back(x * 10);   // may invalidate loop's internal iterator
        }
    }
}

// ============================================================
// ANTI-PATTERN 6: Passing vector by value to sorting function — unnecessary copy
// ============================================================
std::vector<int> sort_copy_waste(std::vector<int> v) {  // ANTI-PATTERN: pass by value = copy
    std::sort(v.begin(), v.end());
    return v;
}

// ============================================================
// ANTI-PATTERN 7: Allocating large objects inside vector of objects (SoA vs AoS)
// ============================================================
struct HeavyObject {
    char data[4096];   // 4 KB payload
    int key;
    HeavyObject(int k) : key(k) { std::memset(data, k & 0xFF, sizeof(data)); }
};

void array_of_structs_cache_thrash(int n) {
    // HAZARD: iterating a vector<HeavyObject> for key-only access thrashes
    // the cache because each 4 KB object occupies 64 cache lines.
    std::vector<HeavyObject> objects;
    objects.reserve(n);
    for (int i = 0; i < n; ++i) objects.emplace_back(i);

    long sum = 0;
    for (const auto& obj : objects) {
        sum += obj.key;   // accesses 4 KB object for a single int — poor locality
    }
    std::printf("Key sum (AoS): %ld\n", sum);
}

// ============================================================
// ANTI-PATTERN 8: std::vector<bool> specialization trap
// ============================================================
void vector_bool_trap() {
    std::vector<bool> flags(100, false);
    // HAZARD: std::vector<bool> is specialized — operator[] returns a proxy,
    // not a real bool&. Taking its address or binding to auto& is broken.
    auto bit_ref = flags[0];     // proxy object, NOT a bool reference
    bit_ref = true;              // sets bit 0 correctly
    bool* raw = &flags[0];       // COMPILE ERROR on most compilers — intentional hazard demo
    (void)raw;
    std::printf("flags[0] = %d\n", (bool)flags[0]);
}

int main() {
    constexpr int N = 100'000;

    auto t_start = std::chrono::high_resolution_clock::now();
    auto v_no_reserve = build_vector_without_reserve(N);
    auto t_after_no_reserve = std::chrono::high_resolution_clock::now();
    auto v_with_reserve = build_vector_with_reserve(N);
    auto t_after_reserve = std::chrono::high_resolution_clock::now();

    auto ms_no = std::chrono::duration_cast<std::chrono::microseconds>(t_after_no_reserve - t_start).count();
    auto ms_with = std::chrono::duration_cast<std::chrono::microseconds>(t_after_reserve - t_after_no_reserve).count();

    std::printf("No reserve:   %ld µs  size=%zu\n", ms_no, v_no_reserve.size());
    std::printf("With reserve: %ld µs  size=%zu\n", ms_with, v_with_reserve.size());

    std::printf("\n=== Reference Invalidation ===\n");
    reference_invalidation_demo();

    std::printf("\n=== Wrong Erase-Remove ===\n");
    std::vector<int> nums = {1, 2, 3, 2, 4, 2, 5};
    wrong_erase_remove(nums, 2);
    for (int x : nums) std::printf("%d ", x);
    std::printf("\n(3 stale '2' values linger at end without erase)\n");

    std::printf("\n=== AoS Cache Thrash ===\n");
    array_of_structs_cache_thrash(1000);

    return 0;
}

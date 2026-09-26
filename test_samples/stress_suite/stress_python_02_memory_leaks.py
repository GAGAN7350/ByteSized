"""
stress_python_02_memory_leaks.py
ByteSized Stress Suite — Python: memory leaks, unbounded caches, reference cycles
"""
import gc
import sys
import weakref
from typing import Any, Dict, List, Optional


# ============================================================
# ANTI-PATTERN 1: Unbounded in-process cache — grows forever
# ============================================================
_GLOBAL_CACHE: Dict[str, Any] = {}

def cache_compute(key: str, value: Any) -> Any:
    # MEMORY LEAK: No eviction policy. Cache grows without bound.
    _GLOBAL_CACHE[key] = value
    return value

def populate_cache(n: int = 500_000) -> None:
    for i in range(n):
        cache_compute(f"entry_{i}", b"x" * 1024)  # 1 KB per entry → 512 MB


# ============================================================
# ANTI-PATTERN 2: Reference cycle preventing garbage collection
# ============================================================
class Node:
    """Doubly-linked list node with a reference cycle via parent back-pointer."""

    def __init__(self, value: int, parent: Optional["Node"] = None) -> None:
        self.value = value
        self.parent: Optional["Node"] = parent  # CYCLE: child holds strong ref to parent
        self.children: List["Node"] = []
        # ANTI-PATTERN: large payload held inside cyclic object
        self._payload: bytes = b"Z" * (4 * 1024)  # 4 KB

    def add_child(self, child: "Node") -> None:
        child.parent = self           # forms back-reference
        self.children.append(child)


def build_cyclic_tree(depth: int, branching: int) -> Node:
    """Build a deep tree with reference cycles — CPython refcounting cannot free this."""
    root = Node(0)
    current_level = [root]
    for _d in range(depth):
        next_level: List[Node] = []
        for parent in current_level:
            for b in range(branching):
                child = Node(b)
                parent.add_child(child)  # child.parent = parent → cycle
                next_level.append(child)
        current_level = next_level
    return root


# ============================================================
# ANTI-PATTERN 3: __del__ in cycle prevents gc.collect from freeing
# ============================================================
class LeakyResource:
    _instances: List["LeakyResource"] = []  # LEAK: class-level list holds strong refs

    def __init__(self, name: str) -> None:
        self.name = name
        self._data = bytearray(64 * 1024)  # 64 KB
        LeakyResource._instances.append(self)  # adds to class list — never freed

    def __del__(self) -> None:
        # ANTI-PATTERN: __del__ in a cycle moves object to gc.garbage
        # and prevents the cyclic garbage collector from freeing it.
        pass


class CyclicHolder:
    def __init__(self, resource: LeakyResource) -> None:
        self.resource = resource
        resource._holder_ref = self    # cycle: resource → holder → resource


def create_leaky_resources(n: int = 1000) -> None:
    for i in range(n):
        r = LeakyResource(f"resource_{i}")
        holder = CyclicHolder(r)
        # Neither r nor holder is stored anywhere else, but the cycle prevents
        # immediate collection, and LeakyResource._instances holds a permanent ref.


# ============================================================
# ANTI-PATTERN 4: Generator that is abandoned mid-iteration
# ============================================================
def infinite_data_generator():
    """Generator that allocates large objects and is never closed."""
    while True:
        yield bytearray(256 * 1024)  # 256 KB per yield


def leak_generator() -> None:
    gen = infinite_data_generator()
    for _ in range(10):
        next(gen)
    # LEAK: gen goes out of scope without gen.close() — frame locals including
    # the last yielded bytearray are held alive until GC runs.


# ============================================================
# ANTI-PATTERN 5: Mutable default argument accumulating state
# ============================================================
def accumulate_results(result, history=[]) -> List[Any]:
    # MEMORY LEAK: history persists across all calls — never reset.
    history.append(result)
    return history


# ============================================================
# ANTI-PATTERN 6: Event handler list that is never pruned
# ============================================================
class EventBus:
    def __init__(self) -> None:
        self._handlers: List[Any] = []

    def subscribe(self, handler: Any) -> None:
        # LEAK: no deduplication, no unsubscribe mechanism, no weak references
        self._handlers.append(handler)

    def emit(self, event: str) -> None:
        for h in self._handlers:
            h(event)


_BUS = EventBus()

class SubscriberObject:
    def __init__(self, name: str) -> None:
        self.name = name
        self._data = bytearray(8 * 1024)
        _BUS.subscribe(self.handle)  # stores bound method → holds self alive

    def handle(self, event: str) -> None:
        pass


def register_many_subscribers(n: int = 5000) -> None:
    for i in range(n):
        SubscriberObject(f"sub_{i}")
        # Object goes out of local scope, but EventBus holds its bound method
        # → object is kept alive indefinitely


# ============================================================
# DRIVER
# ============================================================
if __name__ == "__main__":
    print(f"[Before] Objects tracked by gc: {len(gc.get_objects())}")

    print("Building cyclic tree (depth=5, branching=4)...")
    root = build_cyclic_tree(depth=5, branching=4)
    del root

    print("Creating leaky resources...")
    create_leaky_resources(200)

    print("Leaking generator...")
    leak_generator()

    print("Accumulating mutable default results...")
    for i in range(10000):
        accumulate_results(i)

    print("Registering subscribers to EventBus...")
    register_many_subscribers(500)

    gc.collect()
    print(f"[After gc.collect()] Objects tracked by gc: {len(gc.get_objects())}")
    print(f"[gc.garbage (uncollectable)] count: {len(gc.garbage)}")
    print(f"Cache size: {len(_GLOBAL_CACHE)} entries (expected 0 if LRU was used)")
    print(f"LeakyResource._instances: {len(LeakyResource._instances)} (never freed)")

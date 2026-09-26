"""
stress_python_01_asyncio_race.py
ByteSized Stress Suite — Python: asyncio race conditions
"""
import asyncio
import random
import time
from typing import List, Dict

# ANTI-PATTERN: Shared mutable state accessed concurrently without locking.
# Multiple coroutines increment a shared counter with a non-atomic read-modify-write.
shared_counter: int = 0
shared_ledger: Dict[str, int] = {}

async def increment_counter_unsafe(task_id: int, iterations: int) -> None:
    global shared_counter
    for _ in range(iterations):
        # RACE CONDITION: read-modify-write on shared_counter is NOT atomic.
        # Two coroutines can read the same value, both add 1, and write the same
        # result — silently losing increments.
        temp = shared_counter         # read
        await asyncio.sleep(0)        # yield — allows interleaving
        shared_counter = temp + 1     # write: possibly stale

async def write_ledger_unsafe(key: str, value: int) -> None:
    # RACE: check-then-act without a lock
    if key not in shared_ledger:
        await asyncio.sleep(random.uniform(0, 0.001))
        # By the time we arrive here, another coroutine may have already
        # written the key — this write silently overwrites it.
        shared_ledger[key] = value

async def race_on_list(shared: List[int], index: int) -> None:
    # RACE CONDITION: simultaneous read-modify-write on shared list element
    old = shared[index]
    await asyncio.sleep(0)
    shared[index] = old + 1  # lost update if two tasks read same old value

async def producer_consumer_race(queue: asyncio.Queue) -> None:
    # ANTI-PATTERN: Producer does not guard against queue overflow.
    # In tight loops without backpressure, the producer floods the queue.
    for i in range(10000):
        await queue.put(i)  # no maxsize guard at call site

async def consumer_race(queue: asyncio.Queue) -> None:
    while True:
        item = await queue.get()
        # ANTI-PATTERN: task_done() called unconditionally without try/finally;
        # if processing raises, the queue.join() hangs forever.
        process_item(item)
        queue.task_done()

def process_item(item: int) -> None:
    if item % 100 == 0:
        raise ValueError(f"Simulated processing error at item {item}")

async def spawn_racing_tasks() -> None:
    # Spawn 50 competing coroutines on the same counter
    tasks = [asyncio.create_task(increment_counter_unsafe(i, 200)) for i in range(50)]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Spawn 100 competing ledger writers for overlapping keys
    write_tasks = [
        asyncio.create_task(write_ledger_unsafe(f"key_{i % 10}", i))
        for i in range(100)
    ]
    await asyncio.gather(*write_tasks, return_exceptions=True)

    # List race
    shared_list = [0] * 5
    list_tasks = [asyncio.create_task(race_on_list(shared_list, i % 5)) for i in range(50)]
    await asyncio.gather(*list_tasks, return_exceptions=True)

    # Queue race — producer/consumer mismatch
    q: asyncio.Queue = asyncio.Queue()
    prod = asyncio.create_task(producer_consumer_race(q))
    cons = asyncio.create_task(consumer_race(q))
    try:
        await asyncio.wait_for(asyncio.gather(prod, cons, return_exceptions=True), timeout=2.0)
    except asyncio.TimeoutError:
        pass  # ANTI-PATTERN: silently swallowing TimeoutError

    print(f"Final counter (expected 10000, actual): {shared_counter}")
    print(f"Ledger entries (expected <=10, actual): {len(shared_ledger)}")

async def barrier_race() -> None:
    """
    RACE CONDITION: Using a manual event as a barrier without proper reset.
    Two phases share the same event object; the second phase can start
    before all workers from the first phase have completed.
    """
    event = asyncio.Event()

    async def worker(worker_id: int) -> str:
        await event.wait()
        await asyncio.sleep(random.uniform(0.0, 0.005))
        return f"worker_{worker_id}_done"

    async def controller() -> None:
        tasks = [asyncio.create_task(worker(i)) for i in range(20)]
        event.set()
        # RACE: event.clear() here races with workers still in event.wait()
        event.clear()
        results = await asyncio.gather(*tasks)
        return results

    await controller()

if __name__ == "__main__":
    start = time.perf_counter()
    asyncio.run(spawn_racing_tasks())
    asyncio.run(barrier_race())
    elapsed = time.perf_counter() - start
    print(f"Elapsed: {elapsed:.3f}s")

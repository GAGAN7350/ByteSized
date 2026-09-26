"""
SiliconBob Test Sample: Python
Demonstrates anti-pattern detection:
1. Mutable default argument (state leakage across calls)
2. Non-idiomatic range(len(...)) loop
3. Type equality check instead of isinstance
4. Dangerous bare 'except:' catching SystemExit/KeyboardInterrupt
"""

def process_data(value, cache=[]):
    cache.append(value)
    return cache

def iterate_items(items):
    for i in range(len(items)):
        if type(items[i]) == str:
            print(f"Item {i}: {items[i]}")

def unsafe_execution():
    try:
        val = int("invalid_number")
    except:
        print("Caught exception safely")

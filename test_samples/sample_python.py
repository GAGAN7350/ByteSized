# =============================================================================
# Python Test Sample: Anti-Patterns and Inefficiencies
# =============================================================================

# 1. Bug: Mutable default argument traps state across calls
def append_worker(task_id, task_list=[]):
    task_list.append(task_id)
    return task_list

# 2. Bug: Non-idiomatic slow range(len())
def process_data(data_stream):
    for i in range(len(data_stream)):
        print(f"Item {i}: {data_stream[i]}")

# 3. Bug: Bare except suppresses keyboard interrupts & crashes silently
def risky_calculation(val):
    try:
        return 100 / val
    except:
        return 0

/**
 * stress_ts_02_promise_all_rejections.ts
 * ByteSized Stress Suite — TypeScript: unhandled Promise.all rejections,
 * race conditions in async flows, sequential vs parallel misuse.
 *
 * Compile: tsc --strict stress_ts_02_promise_all_rejections.ts
 * Run: node stress_ts_02_promise_all_rejections.js
 */

// ============================================================
// ANTI-PATTERN 1: Promise.all fast-fails on first rejection, losing other results
// ============================================================
async function fetchUserData(userId: number): Promise<{ id: number; name: string }> {
  await new Promise(r => setTimeout(r, Math.random() * 50));
  if (userId % 5 === 0) {
    throw new Error(`User ${userId} not found in database`);
  }
  return { id: userId, name: `User_${userId}` };
}

async function loadAllUsers_FailFast(ids: number[]): Promise<void> {
  // HAZARD TS-PA-001: Promise.all rejects as soon as ANY promise rejects.
  // For ids = [1,5,10], the result for id=1 (successful) is silently discarded.
  const users = await Promise.all(ids.map(fetchUserData));
  console.log('All users loaded:', users.length);
}

// ============================================================
// ANTI-PATTERN 2: Awaiting promises sequentially when they're independent
// ============================================================
async function fetchConfig(): Promise<{ timeout: number }> {
  await new Promise(r => setTimeout(r, 100));
  return { timeout: 5000 };
}

async function fetchFeatureFlags(): Promise<{ darkMode: boolean }> {
  await new Promise(r => setTimeout(r, 80));
  return { darkMode: true };
}

async function fetchUserPrefs(): Promise<{ theme: string }> {
  await new Promise(r => setTimeout(r, 120));
  return { theme: 'dark' };
}

async function loadInitialData_Sequential(): Promise<void> {
  const t0 = Date.now();
  // HAZARD TS-PA-002: three independent async operations awaited sequentially.
  // Total time = 100 + 80 + 120 = 300ms instead of max(100,80,120) = 120ms with Promise.all.
  const config  = await fetchConfig();
  const flags   = await fetchFeatureFlags();
  const prefs   = await fetchUserPrefs();
  console.log(`Sequential load took ${Date.now() - t0}ms (should be ~120ms with Promise.all)`);
  console.log(config, flags, prefs);
}

// ============================================================
// ANTI-PATTERN 3: Promise.race with no timeout — may hang indefinitely
// ============================================================
async function operationThatHangs(): Promise<string> {
  // HAZARD TS-PA-003: promise never resolves or rejects — hangs indefinitely.
  return new Promise((_resolve) => {
    // Intentionally never called
  });
}

async function raceWithoutTimeout(): Promise<void> {
  // HAZARD: if operationThatHangs is the only competitor, this hangs forever.
  const result = await Promise.race([
    operationThatHangs(),
    // Missing timeout competitor:
    // new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 5000))
  ]);
  console.log('Race winner:', result);
}

// ============================================================
// ANTI-PATTERN 4: Mutating shared state from concurrent Promise.all tasks
// ============================================================
interface Counter {
  value: number;
  log: string[];
}

async function incrementCounter(counter: Counter, id: number): Promise<void> {
  const current = counter.value;    // read
  await new Promise(r => setTimeout(r, Math.random() * 10));   // yield
  counter.value = current + 1;      // write — RACE: may overwrite another task's increment
  counter.log.push(`task_${id}_set_${current + 1}`);
}

async function concurrentCounterMutation(): Promise<void> {
  const counter: Counter = { value: 0, log: [] };
  const tasks = Array.from({ length: 20 }, (_, i) =>
    incrementCounter(counter, i)
  );
  await Promise.all(tasks);
  console.log(`Expected counter=20, actual=${counter.value}`);
  console.log(`Log entries: ${counter.log.length} (may show overwrites)`);
}

// ============================================================
// ANTI-PATTERN 5: allSettled result not inspected for rejections
// ============================================================
async function processAllSettledButIgnoreErrors(ids: number[]): Promise<void> {
  const results = await Promise.allSettled(ids.map(fetchUserData));
  // HAZARD TS-PA-005: iterating results without checking 'status' field.
  // Rejected promises are silently treated as fulfilled.
  for (const result of results) {
    // DEFECT: no check for result.status === 'rejected'
    const user = (result as PromiseFulfilledResult<{ id: number; name: string }>).value;
    console.log(`User: ${user?.name ?? 'MISSING_NO_ERROR_CHECK'}`);
  }
}

// ============================================================
// ANTI-PATTERN 6: async function called without await in a loop
// ============================================================
function startBackgroundJobs(n: number): void {
  for (let i = 0; i < n; i++) {
    // HAZARD TS-PA-006: async function called without await.
    // Errors from fetchUserData are swallowed; caller has no way to know about failures.
    fetchUserData(i);   // floating promise — result and errors ignored
  }
}

// ============================================================
// ANTI-PATTERN 7: try/catch around Promise.all catches non-error objects
// ============================================================
async function catchWithWrongType(): Promise<void> {
  try {
    await Promise.all([
      Promise.reject('plain string error'),   // HAZARD: non-Error thrown
      Promise.resolve(42)
    ]);
  } catch (e) {
    // HAZARD TS-PA-007: e may be a string, number, or any non-Error value.
    // Accessing e.message here would return undefined, not throw (in strict mode it throws).
    console.error('Error message:', (e as Error).message ?? 'not an Error object — was:', e);
  }
}

// ============================================================
// DRIVER
// ============================================================
async function main(): Promise<void> {
  const ids = Array.from({ length: 15 }, (_, i) => i + 1);

  console.log('=== Promise.all Fast-Fail ===');
  try {
    await loadAllUsers_FailFast(ids);
  } catch (e) {
    console.log('Caught fast-fail:', (e as Error).message);
  }

  console.log('\n=== Sequential Independent Awaits ===');
  await loadInitialData_Sequential();

  console.log('\n=== Concurrent Counter Mutation ===');
  await concurrentCounterMutation();

  console.log('\n=== allSettled Without Error Check ===');
  await processAllSettledButIgnoreErrors([1, 5, 10, 15]);

  console.log('\n=== Catch Wrong Type ===');
  await catchWithWrongType();

  console.log('\n=== Floating Promises (10 jobs, no await) ===');
  startBackgroundJobs(10);
  await new Promise(r => setTimeout(r, 200));

  console.log('\nAll anti-patterns demonstrated.');
}

main().catch(e => console.error('Top-level:', e));

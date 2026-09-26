/**
 * stress_js_01_event_loop_starvation.js
 * ByteSized Stress Suite — JavaScript: event loop starvation, blocking sync operations,
 * unhandled promise rejections, and recursive setTimeout misuse.
 */
'use strict';

// ============================================================
// ANTI-PATTERN 1: Synchronous CPU-bound loop blocks the event loop
// Node.js is single-threaded; a tight while loop starves I/O and timers.
// ============================================================
function blockingFibonacci(n) {
  // HAZARD JS-001: O(2^n) recursive computation on the event loop thread
  if (n <= 1) return n;
  return blockingFibonacci(n - 1) + blockingFibonacci(n - 2);
}

function demonstrateEventLoopStarvation() {
  console.log('[Before block] Timer fired at:', Date.now());
  setTimeout(() => {
    console.log('[Timer callback] should fire at +100ms:', Date.now());
  }, 100);

  // HAZARD: This blocks the thread for several seconds, delaying the timer above.
  const result = blockingFibonacci(40);
  console.log('[After block] fib(40)=', result, 'at:', Date.now());
}

// ============================================================
// ANTI-PATTERN 2: JSON.parse on huge payload blocks the event loop
// ============================================================
function parseHugeJsonSync() {
  // Simulate a 10 MB JSON string
  const huge = '{"data":' + JSON.stringify(new Array(100000).fill({ x: 1, y: 2, z: 3 })) + '}';
  const t0 = Date.now();
  // HAZARD JS-002: synchronous JSON.parse of a large payload blocks event loop
  const obj = JSON.parse(huge);
  console.log(`JSON.parse took ${Date.now() - t0}ms, keys: ${Object.keys(obj).length}`);
}

// ============================================================
// ANTI-PATTERN 3: Nested setImmediate loop — starves I/O callbacks
// ============================================================
let setImmediateCount = 0;
function recursiveSetImmediate() {
  // HAZARD JS-003: setImmediate re-schedules itself before any I/O callback can run.
  // The I/O phase is perpetually starved — file reads and network replies never fire.
  if (setImmediateCount < 100000) {
    setImmediateCount++;
    setImmediate(recursiveSetImmediate);
  }
}

// ============================================================
// ANTI-PATTERN 4: Promise chain that swallows rejections
// ============================================================
function unreliableFetch(url) {
  return new Promise((resolve, reject) => {
    if (Math.random() < 0.5) reject(new Error(`Fetch failed: ${url}`));
    else resolve({ url, data: 'ok' });
  });
}

async function silentlySwallowRejections() {
  const urls = Array.from({ length: 100 }, (_, i) => `http://example.com/${i}`);
  // HAZARD JS-004: Promise.all without .catch — one rejection rejects the entire batch
  // silently if the caller doesn't attach a rejection handler.
  const results = await Promise.all(urls.map(url => unreliableFetch(url)));
  return results;
}

// ============================================================
// ANTI-PATTERN 5: Unchecked async operation in forEach
// ============================================================
async function forEachAsyncLeak() {
  const items = Array.from({ length: 50 }, (_, i) => i);
  // HAZARD JS-005: Array.forEach does not await async callbacks.
  // All 50 promises are fired concurrently and their results/errors are ignored.
  items.forEach(async (item) => {
    await new Promise(r => setTimeout(r, Math.random() * 50));
    if (item % 7 === 0) throw new Error(`Item ${item} failed`);
  });
  // forEach returns before any async work completes — caller has no visibility.
}

// ============================================================
// ANTI-PATTERN 6: Unbounded event emitter listener accumulation
// ============================================================
const EventEmitter = require('events');
const emitter = new EventEmitter();
emitter.setMaxListeners(0);  // HAZARD JS-006: disables the Node.js listener leak warning

function registerListenersUnbounded(n) {
  for (let i = 0; i < n; i++) {
    // HAZARD: listeners are added but never removed with emitter.off()
    emitter.on('data', (chunk) => {
      // process chunk — closure captures i, preventing GC
      const localBuffer = Buffer.alloc(1024, i & 0xFF);
      void localBuffer;
    });
  }
}

// ============================================================
// ANTI-PATTERN 7: Recursive setTimeout without base case — runs forever
// ============================================================
let recursiveCount = 0;
function runForeverTimeout() {
  // HAZARD JS-007: no termination condition — timer fires indefinitely,
  // accumulating closures and preventing GC of captured variables.
  const capturedData = Buffer.alloc(4096); // 4 KB captured per iteration
  void capturedData;
  recursiveCount++;
  if (recursiveCount < 10000) {
    setTimeout(runForeverTimeout, 0);
  }
}

// ============================================================
// DRIVER
// ============================================================
async function main() {
  console.log('=== Event Loop Starvation ===');
  demonstrateEventLoopStarvation();

  console.log('\n=== Huge JSON Parse ===');
  parseHugeJsonSync();

  console.log('\n=== Recursive setImmediate ===');
  recursiveSetImmediate();
  await new Promise(r => setTimeout(r, 500));
  console.log(`setImmediate iterations: ${setImmediateCount}`);

  console.log('\n=== Silent Promise Rejections ===');
  try {
    await silentlySwallowRejections();
  } catch (e) {
    console.log('Caught (some rejections already lost):', e.message);
  }

  console.log('\n=== Unbounded Event Listeners ===');
  registerListenersUnbounded(10000);
  console.log(`Listener count: ${emitter.listenerCount('data')} (expected: 0 in clean code)`);

  console.log('\n=== Recursive setTimeout ===');
  runForeverTimeout();
  await new Promise(r => setTimeout(r, 2000));
  console.log(`Recursive setTimeout iterations: ${recursiveCount}`);
}

main().catch(err => console.error('Top-level error:', err));

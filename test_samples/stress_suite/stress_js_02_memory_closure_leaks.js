/**
 * stress_js_02_memory_closure_leaks.js
 * ByteSized Stress Suite — JavaScript: closure-based memory leaks,
 * detached DOM node retention, and WeakMap misuse.
 */
'use strict';

// ============================================================
// ANTI-PATTERN 1: Closure retaining large outer scope variable
// ============================================================
function createLeakyClosures(n) {
  const closures = [];
  for (let i = 0; i < n; i++) {
    // HAZARD JS-CL-001: 'hugePaylod' (1 MB) is captured by the closure
    // even though the closure only uses 'i'. The entire 1 MB buffer is kept
    // alive for as long as the closure lives.
    const hugePayload = Buffer.alloc(1024 * 1024);  // 1 MB per iteration
    closures.push(() => {
      return i;  // only uses i, but hugePayload is captured in the same scope
    });
  }
  return closures;  // returns n closures, each retaining 1 MB → n MB total
}

// ============================================================
// ANTI-PATTERN 2: Timer closure retaining DOM-like large objects
// ============================================================
const intervalHandles = [];
function createLeakyIntervals(n) {
  for (let i = 0; i < n; i++) {
    const capturedData = {
      id: i,
      buffer: Buffer.alloc(64 * 1024),   // 64 KB per timer
      timestamp: Date.now()
    };
    // HAZARD JS-CL-002: interval callback captures capturedData.
    // Interval never cleared → capturedData is never GC'd.
    const handle = setInterval(() => {
      void capturedData.timestamp;  // uses capturedData — keeps it alive
    }, 10000);
    intervalHandles.push(handle);
    // DEFECT: intervalHandles grows without bound; handles are never cleared
  }
}

// ============================================================
// ANTI-PATTERN 3: Module-level cache that retains closures indefinitely
// ============================================================
const handlerCache = new Map();

function registerComputedHandler(key, expensiveInput) {
  const snapshot = Buffer.from(expensiveInput);   // deep copy of potentially large input
  // HAZARD JS-CL-003: handlerCache is module-level (never GC'd).
  // Each registration creates a closure over snapshot.
  // Keys are never evicted → unbounded memory accumulation.
  handlerCache.set(key, () => snapshot.length);
}

function populateHandlerCache(n) {
  for (let i = 0; i < n; i++) {
    const bigInput = Buffer.alloc(8 * 1024, i & 0xFF);  // 8 KB per entry
    registerComputedHandler(`handler_${i}`, bigInput);
  }
}

// ============================================================
// ANTI-PATTERN 4: Promise chains that accumulate in an array
// ============================================================
const pendingPromises = [];

async function accumulatePromises(n) {
  for (let i = 0; i < n; i++) {
    // HAZARD JS-CL-004: promises pushed into pendingPromises but never awaited or
    // removed. Each Promise closure captures its iteration state.
    pendingPromises.push(
      new Promise((resolve) => {
        const capturedIdx = i;
        const localBuf = Buffer.alloc(2048);  // 2 KB per promise closure
        setTimeout(() => {
          void localBuf;
          resolve(capturedIdx);
          // After resolve, the promise should be GC'd, but it remains
          // in pendingPromises[] permanently.
        }, 3600000);  // resolves 1 hour later — effectively never
      })
    );
  }
  console.log(`pendingPromises.length = ${pendingPromises.length}`);
}

// ============================================================
// ANTI-PATTERN 5: addEventListener without removeEventListener
// (simulated in Node.js with EventEmitter)
// ============================================================
const EventEmitter = require('events');
const bus = new EventEmitter();
bus.setMaxListeners(0);

class ComponentWithLeak {
  constructor(id) {
    this.id = id;
    this._bigState = Buffer.alloc(32 * 1024);  // 32 KB per component
    // HAZARD JS-CL-005: bound method is registered as a listener.
    // Even if the component goes out of scope, the bus holds a reference
    // to the bound method, which holds a reference to 'this'.
    this._handler = this._onData.bind(this);
    bus.on('data', this._handler);
    // Missing: component must call bus.off('data', this._handler) to avoid leak
  }

  _onData(data) {
    void this._bigState;
    void data;
  }
}

function createComponentsWithoutCleanup(n) {
  for (let i = 0; i < n; i++) {
    // Component goes out of scope here, but EventBus holds it alive
    new ComponentWithLeak(i);
  }
}

// ============================================================
// ANTI-PATTERN 6: Recursive function building deep closure chains
// ============================================================
function buildDeepClosureChain(depth, data) {
  if (depth === 0) return () => data.length;
  // HAZARD JS-CL-006: each level captures 'data' AND the inner closure.
  // The chain retains data at every depth level — O(depth * sizeof(data)).
  const localData = Buffer.alloc(1024);  // 1 KB per level
  const inner = buildDeepClosureChain(depth - 1, data);
  return () => localData.length + inner();
}

// ============================================================
// DRIVER
// ============================================================
async function main() {
  console.log('=== Leaky Closure Array (100 closures × 1 MB each) ===');
  const closures = createLeakyClosures(100);
  console.log(`Created ${closures.length} closures retaining ~100 MB`);

  console.log('\n=== Leaky Intervals (50 intervals × 64 KB each) ===');
  createLeakyIntervals(50);
  console.log(`Active intervals: ${intervalHandles.length}`);

  console.log('\n=== Unbounded Handler Cache (1000 entries × 8 KB each) ===');
  populateHandlerCache(1000);
  console.log(`Cache size: ${handlerCache.size} entries`);

  console.log('\n=== Accumulating Promise Array ===');
  await accumulatePromises(500);

  console.log('\n=== Components without listener cleanup (200 × 32 KB) ===');
  createComponentsWithoutCleanup(200);
  console.log(`Bus 'data' listener count: ${bus.listenerCount('data')}`);

  console.log('\n=== Deep Closure Chain (depth=200) ===');
  const root = buildDeepClosureChain(200, Buffer.alloc(1024));
  console.log(`Chain result: ${root()}`);

  // Clear intervals to allow process to exit (the leaks still happened)
  for (const h of intervalHandles) clearInterval(h);
  console.log('\nDone. All anti-patterns demonstrated.');
}

main().catch(console.error);

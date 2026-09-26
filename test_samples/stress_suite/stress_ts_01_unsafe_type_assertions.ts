/**
 * stress_ts_01_unsafe_type_assertions.ts
 * ByteSized Stress Suite — TypeScript: unsafe type assertions, any-typed escape hatches,
 * missing null checks, and incorrect generic constraints.
 *
 * Compile: tsc --strict stress_ts_01_unsafe_type_assertions.ts
 */

// ============================================================
// ANTI-PATTERN 1: as unknown as T — double-cast type laundering
// Bypasses all type safety; the runtime shape may be completely wrong.
// ============================================================
interface UserProfile {
  id: number;
  username: string;
  email: string;
  role: 'admin' | 'user' | 'guest';
}

function deserializeUserUnsafe(raw: string): UserProfile {
  const parsed = JSON.parse(raw);
  // HAZARD TS-001: double cast bypasses all type checks.
  // parsed may be null, an array, or completely wrong shape.
  return parsed as unknown as UserProfile;
}

function processUser(user: UserProfile): void {
  // RUNTIME HAZARD: if deserializeUserUnsafe returned wrong shape,
  // these property accesses silently produce undefined at runtime.
  console.log(`Processing user: ${user.username.toUpperCase()}`);  // TypeError if username missing
  if (user.role === 'admin') {
    grantAdminAccess(user);
  }
}

function grantAdminAccess(user: UserProfile): void {
  console.log(`Admin access granted to ${user.id}`);
}

// ============================================================
// ANTI-PATTERN 2: any[] array bypassing element type checks
// ============================================================
function sumArray(arr: any[]): number {
  // HAZARD TS-002: arr is typed as any[] — TypeScript provides zero
  // type checking inside the accumulator. A non-number element causes NaN silently.
  return arr.reduce((acc, val) => acc + val, 0);
}

// ============================================================
// ANTI-PATTERN 3: Non-null assertion (!) on potentially null value
// ============================================================
interface Config {
  database?: {
    host?: string;
    port?: number;
  };
}

function getDbHost(config: Config): string {
  // HAZARD TS-003: non-null assertion on optional chained values.
  // If config.database is undefined, config.database!.host throws at runtime.
  return config.database!.host!.trim();
}

// ============================================================
// ANTI-PATTERN 4: Object.keys losing type information
// ============================================================
interface StrictRecord {
  alpha: number;
  beta: string;
  gamma: boolean;
}

function iterateStrictRecord(record: StrictRecord): void {
  // HAZARD TS-004: Object.keys returns string[], not (keyof StrictRecord)[].
  // The cast to any circumvents strict index signature enforcement.
  (Object.keys(record) as Array<keyof StrictRecord>).forEach(key => {
    const val = (record as any)[key];  // 'as any' loses type safety
    console.log(`${key}: ${val}`);
  });
}

// ============================================================
// ANTI-PATTERN 5: Incorrect generic constraint — too permissive
// ============================================================
// HAZARD TS-005: T is constrained to object but the function accesses
// .id and .name which are not guaranteed to exist on all objects.
function mergeRecords<T extends object>(a: T, b: T): T & { merged: boolean } {
  return {
    ...a,
    ...b,
    merged: true,
    // HAZARD: accessing (a as any).id without checking — may be undefined
    id: (a as any).id ?? (b as any).id,
  };
}

// ============================================================
// ANTI-PATTERN 6: Catching Error as any and re-throwing
// ============================================================
async function fetchWithPoorErrorHandling(url: string): Promise<string> {
  try {
    const response = await fetch(url);
    const text = await response.text();
    return text;
  } catch (e: any) {
    // HAZARD TS-006: typed as any — all type safety for the error is lost.
    // e.message may not exist if e is a non-Error throw.
    console.error('Failed:', e.message.toUpperCase());  // runtime error if e is not an Error
    throw e;
  }
}

// ============================================================
// ANTI-PATTERN 7: as const bypassed by subsequent assignment
// ============================================================
const CONFIG_VALUES = {
  maxRetries: 3,
  timeout: 5000,
  endpoint: '/api/v1',
} as const;

function mutateConfig(cfg: typeof CONFIG_VALUES): void {
  // HAZARD TS-007: readonly properties bypassed with type assertion
  (cfg as any).maxRetries = 999;      // silently mutates readonly object
  (cfg as any).endpoint = 'http://evil.com';  // security hazard
}

// ============================================================
// ANTI-PATTERN 8: Overloaded function returning wrong type for input type
// ============================================================
function process(input: string): number;
function process(input: number): string;
function process(input: string | number): string | number {
  // HAZARD TS-008: implementation returns wrong type for the input type.
  // TypeScript checks the overload signature, not the implementation body.
  if (typeof input === 'string') {
    return input; // WRONG: should be number per overload signature
  }
  return input;   // WRONG: should be string per overload signature
}

// ============================================================
// DRIVER
// ============================================================
async function main(): Promise<void> {
  console.log('=== Unsafe Deserialization ===');
  try {
    const user = deserializeUserUnsafe('{"id": 1, "role": "superuser"}');
    processUser(user);  // username is undefined → TypeError
  } catch (e) {
    console.log('Expected runtime error:', (e as Error).message);
  }

  console.log('\n=== any[] Sum ===');
  const mixedArr: any[] = [1, '2', null, 3];
  console.log('Sum of mixed array:', sumArray(mixedArr));  // "12null3" via coercion

  console.log('\n=== Non-null Assertion ===');
  try {
    const cfg: Config = {};
    console.log('Host:', getDbHost(cfg));
  } catch (e) {
    console.log('Expected runtime error:', (e as Error).message);
  }

  console.log('\n=== Config Mutation ===');
  mutateConfig(CONFIG_VALUES as any);
  console.log('After mutation:', (CONFIG_VALUES as any).maxRetries);

  console.log('\n=== Overloaded Function Type Mismatch ===');
  const r1 = process('hello');   // TypeScript says number, runtime returns string
  const r2 = process(42);        // TypeScript says string, runtime returns number
  console.log(`process('hello')=${r1} (runtime type: ${typeof r1})`);
  console.log(`process(42)=${r2} (runtime type: ${typeof r2})`);
}

main();

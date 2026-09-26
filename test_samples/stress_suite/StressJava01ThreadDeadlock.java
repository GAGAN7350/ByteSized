/**
 * StressJava01ThreadDeadlock.java
 * ByteSized Stress Suite — Java: thread deadlock, lock ordering violations,
 * synchronized method chains, and ReentrantLock misuse.
 *
 * Compile: javac StressJava01ThreadDeadlock.java
 * Run:     java StressJava01ThreadDeadlock
 */
import java.util.concurrent.*;
import java.util.concurrent.locks.*;
import java.util.*;

public class StressJava01ThreadDeadlock {

    // ============================================================
    // ANTI-PATTERN 1: Classic two-lock deadlock (lock ordering violation)
    // Thread A holds lockA, waits for lockB.
    // Thread B holds lockB, waits for lockA. → DEADLOCK
    // ============================================================
    static final Object lockA = new Object();
    static final Object lockB = new Object();

    static class TaskAcquireAB implements Runnable {
        @Override
        public void run() {
            synchronized (lockA) {                     // acquires lockA
                System.out.println("[AB] Holding lockA, waiting for lockB...");
                try { Thread.sleep(50); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
                synchronized (lockB) {                 // DEADLOCK: waits for lockB held by TaskAcquireBA
                    System.out.println("[AB] Acquired both locks");
                }
            }
        }
    }

    static class TaskAcquireBA implements Runnable {
        @Override
        public void run() {
            synchronized (lockB) {                     // acquires lockB
                System.out.println("[BA] Holding lockB, waiting for lockA...");
                try { Thread.sleep(50); } catch (InterruptedException e) { Thread.currentThread().interrupt(); }
                synchronized (lockA) {                 // DEADLOCK: waits for lockA held by TaskAcquireAB
                    System.out.println("[BA] Acquired both locks");
                }
            }
        }
    }

    // ============================================================
    // ANTI-PATTERN 2: ReentrantLock acquired but unlock() not in finally block
    // ============================================================
    static final ReentrantLock reentrantLock = new ReentrantLock();

    static void doWorkWithLeak() throws Exception {
        reentrantLock.lock();   // HAZARD JAVA-DL-002: if work() throws, unlock() is never called
        doRiskyWork();          // throws RuntimeException
        reentrantLock.unlock(); // UNREACHABLE if doRiskyWork throws — lock leaked forever
    }

    static void doRiskyWork() {
        if (Math.random() < 0.8) {
            throw new RuntimeException("Simulated failure — lock leaked");
        }
    }

    // ============================================================
    // ANTI-PATTERN 3: Synchronized on non-final field (lock identity can change)
    // ============================================================
    static String mutableLock = "initial";   // ANTI-PATTERN JAVA-DL-003: mutable lock reference

    static void synchronizeOnMutableField(String newData) {
        synchronized (mutableLock) {          // HAZARD: different threads may obtain different
            mutableLock = newData;            // object monitors if mutableLock is reassigned
            System.out.println("In critical section, mutableLock = " + mutableLock);
        }
    }

    // ============================================================
    // ANTI-PATTERN 4: wait() without loop (spurious wakeup vulnerability)
    // ============================================================
    static final Object conditionLock = new Object();
    static boolean dataReady = false;

    static void waitWithoutLoop() throws InterruptedException {
        synchronized (conditionLock) {
            // HAZARD JAVA-DL-004: single if instead of while — spurious wakeups
            // can cause the thread to proceed even when dataReady is still false.
            if (!dataReady) {
                conditionLock.wait();   // must be: while (!dataReady) conditionLock.wait();
            }
            System.out.println("Processing (may have been spuriously woken)");
        }
    }

    // ============================================================
    // ANTI-PATTERN 5: Nested synchronized calls creating potential deadlock
    // ============================================================
    static class Account {
        private double balance;
        private final int id;

        Account(int id, double balance) {
            this.id = id;
            this.balance = balance;
        }

        synchronized void deposit(double amount) { balance += amount; }
        synchronized void withdraw(double amount) { balance -= amount; }

        // HAZARD JAVA-DL-005: synchronized transfer acquires 'this' then 'other'.
        // Another thread calling other.transfer(this, ...) acquires in reverse order → deadlock.
        synchronized void transfer(Account other, double amount) {
            if (balance >= amount) {
                withdraw(amount);
                other.deposit(amount);   // acquires 'other' monitor while holding 'this'
            }
        }

        double getBalance() { return balance; }
        int getId() { return id; }
    }

    static void demonstrateAccountDeadlock() throws InterruptedException {
        Account alice = new Account(1, 1000.0);
        Account bob   = new Account(2, 1000.0);

        Thread t1 = new Thread(() -> {
            for (int i = 0; i < 100; i++) alice.transfer(bob, 1.0);
        });
        Thread t2 = new Thread(() -> {
            for (int i = 0; i < 100; i++) bob.transfer(alice, 1.0);  // reverse order → deadlock
        });

        t1.start();
        t2.start();
        t1.join(2000);
        t2.join(2000);

        if (t1.isAlive() || t2.isAlive()) {
            System.out.println("DEADLOCK DETECTED: threads still alive after 2s timeout");
            t1.interrupt();
            t2.interrupt();
        }
    }

    // ============================================================
    // ANTI-PATTERN 6: ConcurrentHashMap.computeIfAbsent with recursive update
    // ============================================================
    static final ConcurrentHashMap<String, String> concurrentMap = new ConcurrentHashMap<>();

    static void recursiveComputeIfAbsent() {
        // HAZARD JAVA-DL-006: calling computeIfAbsent inside a computeIfAbsent callback
        // on a ConcurrentHashMap can deadlock because the segment is locked during computation.
        concurrentMap.computeIfAbsent("key1", k -> {
            return concurrentMap.computeIfAbsent("key2", k2 -> "value2");  // re-entrant lock
        });
    }

    // ============================================================
    // MAIN
    // ============================================================
    public static void main(String[] args) throws Exception {
        System.out.println("=== Classic Two-Lock Deadlock ===");
        ExecutorService executor = Executors.newFixedThreadPool(2);
        Future<?> f1 = executor.submit(new TaskAcquireAB());
        Future<?> f2 = executor.submit(new TaskAcquireBA());
        try {
            f1.get(3, TimeUnit.SECONDS);
            f2.get(3, TimeUnit.SECONDS);
        } catch (TimeoutException e) {
            System.out.println("DEADLOCK: tasks timed out after 3 seconds");
        } finally {
            executor.shutdownNow();
        }

        System.out.println("\n=== ReentrantLock Without finally ===");
        for (int i = 0; i < 5; i++) {
            try { doWorkWithLeak(); }
            catch (Exception e) {
                System.out.println("Lock leaked: " + e.getMessage());
            }
        }
        System.out.println("Lock held by thread after leak: " + reentrantLock.isLocked());

        System.out.println("\n=== Account Transfer Deadlock ===");
        demonstrateAccountDeadlock();

        System.out.println("\n=== Recursive computeIfAbsent ===");
        try { recursiveComputeIfAbsent(); }
        catch (Exception e) { System.out.println("computeIfAbsent exception: " + e); }

        System.out.println("\nAll deadlock patterns demonstrated.");
    }
}

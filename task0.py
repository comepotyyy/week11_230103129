import multiprocessing as mp
import time

from harness import SEED, emit_verify_tag, SCALE

if __name__ == "__main__":
    n = max(1000, int(10**6 * SCALE))
    plog = mp.cpu_count()
    t0 = time.perf_counter_ns()
    for _ in range(n):
        time.perf_counter_ns()
    avg_ns = (time.perf_counter_ns() - t0) / n
    print(f"P_log (mp.cpu_count) = {plog}")
    print(f"avg perf_counter_ns call latency = {avg_ns:.2f} ns over {n} calls")
    print(emit_verify_tag("PHASE0", SEED, float(plog), avg_ns))
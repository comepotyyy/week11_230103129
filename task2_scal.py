import math
import multiprocessing as mp

from harness import (SEED, SCALE, WARMUP, RUNS, run_benchmark, emit_verify_tag,
                     proc_counts)


def stage_a(n: int) -> float:
    """Serial part: first 5% of elements, 10 sin/sqrt ops per element."""
    acc = 0.0
    for i in range(int(0.05 * n)):
        x = i * 1e-3
        for _ in range(5):                      # 5 x (sin + sqrt) = 10 ops
            x = math.sqrt(abs(math.sin(x)) + 1.0)
        acc += x
    return acc


def stage_b_chunk(se):
    """Parallel part: 30 FMA/trig ops per element (10 x 3), no shared writes."""
    s, e = se
    acc = 0.0
    for i in range(s, e):
        x = i * 1e-6
        for _ in range(10):
            x = x * 1.0000001 + 0.5             # FMA
            x = math.sin(x) + 0.1               # trig + add
            x = x * 0.999 + 0.001               # FMA
        acc += x
    return acc


def chunks(n: int, p: int):
    return [(t * n // p, (t + 1) * n // p) for t in range(p)]


def pipeline(pool, n: int, p: int) -> None:
    stage_a(n)
    pool.map(stage_b_chunk, chunks(n, p), chunksize=1)


if __name__ == "__main__":
    Plog = mp.cpu_count()
    N = int(1.2e6 * SCALE)
    N0 = int(2.0e5 * SCALE)
    ps = list(range(1, Plog + 1))

    ta1 = run_benchmark(lambda: stage_a(N), WARMUP, RUNS).median_ms
    print(f"Stage A serial time at N={N}: {ta1:.1f} ms\n")

    print("## Strong scaling")
    print("| p | T ms | S_p | E_p |")
    print("|---|---|---|---|")
    T, S = {}, {}
    for p in ps:
        pool = mp.Pool(processes=p)          # persistent, created OUTSIDE timed loop
        T[p] = run_benchmark(lambda: pipeline(pool, N, p), WARMUP, RUNS).median_ms
        pool.close(); pool.join()
        S[p] = T[1] / T[p]
        print(f"| {p} | {T[p]:.1f} | {S[p]:.2f} | {S[p]/p:.2f} |")
    s_frac = ta1 / T[1]
    print(f"\nserial fraction s = {s_frac:.4f}  ->  Amdahl cap 1/s = {1/s_frac:.1f}x ; "
          f"observed S(P_log) = {S[Plog]:.2f}x")

    print("\n## Marginal speedup per added process")
    for p in ps[1:]:
        print(f"p {p-1}->{p}: dS = {S[p]-S[p-1]:+.2f}")

    print("\n## Weak scaling (N = p * N0)")
    print("| p | N | T ms | E_weak | alpha | S_Gustafson |")
    print("|---|---|---|---|---|---|")
    TW, G = {}, {}
    for p in ps:
        n = p * N0
        ta = run_benchmark(lambda: stage_a(n), WARMUP, RUNS).median_ms
        pool = mp.Pool(processes=p)
        TW[p] = run_benchmark(lambda: pipeline(pool, n, p), WARMUP, RUNS).median_ms
        pool.close(); pool.join()
        alpha = ta / TW[p]
        G[p] = p - alpha * (p - 1)
        print(f"| {p} | {n} | {TW[p]:.1f} | {TW[1]/TW[p]:.2f} | {alpha:.4f} | {G[p]:.2f} |")

    print()
    print(emit_verify_tag("PHASE2", SEED, S[Plog], G[Plog]))
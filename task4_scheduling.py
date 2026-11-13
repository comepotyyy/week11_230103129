import math
import multiprocessing as mp
import os
import time

from harness import SEED, SCALE, emit_verify_tag, pphys

RUNS4 = int(os.environ.get("RUNS4", "3"))   # each config is slow; 3 runs, median reported


def work(i: int) -> float:
    x = 0.5 + i * 1e-3
    for _ in range(1 + (i * i) // 1600):      # K(i) = 1 + floor((i/40)^2)
        x = math.sqrt(abs(math.sin(x) + math.cos(x))) + 0.1
    return x


def worker(mode, t, p, N, C, counter, tw):
    t0 = time.perf_counter()
    if mode == "block":
        for i in range(t * N // p, (t + 1) * N // p):
            work(i)
    elif mode == "cyclic":
        for i in range(t, N, p):
            work(i)
    else:                                     # dynamic chunk queue
        while True:
            with counter.get_lock():
                s = counter.value
                counter.value = s + C
            if s >= N:
                break
            for i in range(s, min(s + C, N)):
                work(i)
    tw[t] = time.perf_counter() - t0


def run(mode, p, N, C=0):
    counter = mp.Value("i", 0)
    tw = mp.Array("d", p)
    procs = [mp.Process(target=worker, args=(mode, t, p, N, C, counter, tw)) for t in range(p)]
    t0 = time.perf_counter()
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join()
    wall = time.perf_counter() - t0
    ts = list(tw)
    lam = max(ts) / (sum(ts) / p)
    return wall, lam


def median_run(mode, p, N, C=0):
    res = sorted((run(mode, p, N, C) for _ in range(RUNS4)), key=lambda r: r[0])
    return res[len(res) // 2]


if __name__ == "__main__":
    P = pphys()
    N = max(P, int(8000 * SCALE))
    print(f"P_phys={P}  N={N}  runs/config={RUNS4}\n")
    print("| strategy | chunk C | T_wall s | lambda |")
    print("|---|---|---|---|")
    t_block, lam = median_run("block", P, N)
    print(f"| block static | - | {t_block:.2f} | {lam:.3f} |")
    t_cyc, lam = median_run("cyclic", P, N)
    print(f"| cyclic static | - | {t_cyc:.2f} | {lam:.3f} |")
    best = (None, float("inf"))
    for C in (1, 8, 64, 512):
        t, lam = median_run("dynamic", P, N, C)
        if t < best[1]:
            best = (C, t)
        print(f"| dynamic | {C} | {t:.2f} | {lam:.3f} |")
    print(f"\nC* = {best[0]}  T_wall(dynamic, C*) = {best[1]:.2f} s")
    print()
    print(emit_verify_tag("PHASE4", SEED, t_block * 1e3, best[1] * 1e3))
Phase 2 strong scaling (Amdahl) vs weak scaling (Gustafson).
 
Run   python task2_scaling.py          (full lab run, roughly 10-25 min)
Test  python task2_scaling.py --quick  (tiny run just to check for errors)
 
Needs harness.py in the same folder.

import math
import sys
import time
import multiprocessing as mp
 
from harness import emit_verify_tag
 
# ----------------------------- EDIT THESE -----------------------------
STUDENT_SEED = 0      # -- put your numeric Student ID here (same as Phase 1)
P_PHYS = 4            # physical cores (your CPU 4)
P_LOG = 4             # logical threads (your CPU 4)
# ----------------------------------------------------------------------
 
QUICK = --quick in sys.argv
N_STRONG = 16_000 if QUICK else 1_600_000    # fixed size for strong scaling
N0 = 2_500 if QUICK else 250_000             # per-core size for weak scaling
TIMED = 3 if QUICK else 5                    # timed trials per configuration
P_VALUES = list(range(1, P_LOG + 1))         # every integer 1..Plog
 
 
def stage_a(n_total int) - float
    Stage A strictly serial, parent process, first 5% of elements,
    12 transcendental ops per element (6 x (sin + sqrt)).
    n = int(0.05  n_total)
    acc = 0.0
    for i in range(n)
        x = i  1e-3 + 1.0
        for _ in range(6)
            x = math.sqrt(math.sin(x) + 2.0)
        acc += x
    return acc
 
 
def stage_b_chunk(bounds)
    Stage B kernel 35 multiply-add + trig iterations per element,
    no shared writes (returns a partial checksum).
    start, end = bounds
    acc = 0.0
    for i in range(start, end)
        x = i  1e-6 + 0.1
        for _ in range(35)
            x = x  0.999 + 0.001
            x = math.sin(x) + 0.5
        acc += x
    return acc
 
 
def split(n int, p int)
    base, extra = divmod(n, p)
    ranges, start = [], 0
    for t in range(p)
        size = base + (1 if t  extra else 0)
        ranges.append((start, start + size))
        start += size
    return ranges
 
 
def one_trial(pool, p int, n int)
    t0 = time.perf_counter_ns()
    stage_a(n)
    t_a = time.perf_counter_ns()
    pool.map(stage_b_chunk, split(n, p), chunksize=1)
    t1 = time.perf_counter_ns()
    return (t1 - t0)  1e6, (t_a - t0)  1e6      # total ms, Stage A ms
 
 
def median(xs)
    xs = sorted(xs)
    m = len(xs)  2
    return xs[m] if len(xs) % 2 else 0.5  (xs[m - 1] + xs[m])
 
 
def measure(p int, n int)
    Return (median total ms, median Stage A ms) for p workers, size n.
    with mp.Pool(processes=p) as pool            # created OUTSIDE timed region
        pool.map(stage_b_chunk, split(max(200, 50  p), p), chunksize=1)  # warm up
        trials = [one_trial(pool, p, n) for _ in range(TIMED)]
    t_total = median([t[0] for t in trials])
    t_a = median([t[1] for t in trials])
    print(f  p={p} N={n9,} total {t_total9.1f} ms   StageA {t_a7.1f} ms,
          flush=True)
    return t_total, t_a
 
 
def main()
    lines = []
 
    def out(s=)
        print(s)
        lines.append(s)
 
    print(fExperiment 2A strong scaling, N={N_STRONG,})
    strong = {p measure(p, N_STRONG) for p in P_VALUES}
    print(fExperiment 2B weak scaling, N0={N0,})
    weak = {p measure(p, p  N0) for p in P_VALUES}
 
    # ---------------- Table 2A ----------------
    t1 = strong[1][0]
    out()
    out(f### Table 2A Strong scaling (N = {N_STRONG,}))
    out( p  T_p (ms)  S_p  E_p )
    out(------------)
    speed = {}
    for p in P_VALUES
        tp = strong[p][0]
        speed[p] = t1  tp
        out(f {p}  {tp.1f}  {speed[p].3f}  {speed[p]  p.3f} )
 
    # ---------------- Table 2B ----------------
    w1 = weak[1][0]
    out()
    out(f### Table 2B Weak scaling (N0 = {N0,}, N(p) = pN0))
    out( p  N(p)  T_p (ms)  E_weak  Stage A (ms)  alpha  S_Gustafson )
    out(---------------------)
    gust = {}
    for p in P_VALUES
        tp, ta = weak[p]
        alpha = ta  tp
        gust[p] = p - alpha  (p - 1)
        out(f {p}  {p  N0,}  {tp.1f}  {w1  tp.3f}  {ta.1f}  
            f{alpha.4f}  {gust[p].3f} )
 
    # ---------------- Amdahl comparison ----------------
    s = strong[1][1]  strong[1][0]
    s_inf = 1.0  s
    s_amdahl = 1.0  (s + (1.0 - s)  P_LOG)
    out()
    out(### Amdahl comparison)
    out(f- Serial fraction s = T_StageA(1)  T_strong(1) = 
        f{strong[1][1].1f}  {strong[1][0].1f} = {s.4f})
    out(f- Theoretical maximum speedup S_inf = 1s = {s_inf.2f})
    out(f- Amdahl prediction at p = {P_LOG} {s_amdahl.3f})
    out(f- Observed S_strong({P_LOG}) = {speed[P_LOG].3f} 
        f({speed[P_LOG]  s_amdahl  100.1f}% of the Amdahl prediction))
 
    # ---------------- Marginal speedup ----------------
    out()
    out(### Marginal speedup per added worker (ideal = 1.00))
    out( step  marginal dS  % drop vs previous marginal )
    out(---------)
    prev = None
    for p in P_VALUES[1]
        m = speed[p] - speed[p - 1]
        drop = na if prev in (None, 0) else f{(prev - m)  prev  100.1f}%
        out(f {p - 1} - {p}  {m.3f}  {drop} )
        prev = m
    if P_LOG == P_PHYS
        out()
        out(fP_log == P_phys == {P_PHYS} this CPU has no SMT, so there is no 
            f{P_PHYS} - {P_PHYS + 1} boundary to test. Discuss where the marginal 
            fspeedup falls instead (powerclock limits, shared L2 between core pairs).)
 
    out()
    out(emit_verify_tag(PHASE2, STUDENT_SEED, speed[P_LOG], gust[P_LOG]))
 
    with open(phase2_results.md, w, encoding=utf-8) as f
        f.write(n.join(lines) + n)
    print(nSaved to phase2_results.md)
 
 
if __name__ == __main__
    main()
 
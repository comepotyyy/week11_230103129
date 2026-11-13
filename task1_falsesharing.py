"""Phase 1: false sharing stride sweep, process scaling, Karp-Flatt.
 
Run:   python task1_falsesharing.py          (full lab run, ~10-20 min)
Test:  python task1_falsesharing.py --quick  (tiny run just to check for errors)
"""
import ctypes
import sys
import multiprocessing as mp
from multiprocessing import shared_memory
 
from harness import run_benchmark, emit_verify_tag
 
# ----------------------------- EDIT THESE -----------------------------
STUDENT_SEED = 0      # <-- put your numeric Student ID here
P_PHYS = 4            # physical cores (your CPU: 4)
P_LOG = 4             # logical threads (your CPU: 4)
# ----------------------------------------------------------------------
 
QUICK = "--quick" in sys.argv
M = 240_000 if QUICK else 24_000_000
WARMUP = 1 if QUICK else 2
TIMED = 3 if QUICK else 7
 
STRIDES = [1, 2, 4, 8, 16, 32]
 
 
def p_sweep_values():
    vals, p = [], 1
    while p <= P_LOG:
        vals.append(p)
        p *= 2
    if P_LOG not in vals:
        vals.append(P_LOG)
    return vals
 
 
def fs_worker(shm_name: str, slot_idx: int, iters: int) -> None:
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = (ctypes.c_uint64 * 512).from_buffer(shm.buf)
    acc = arr[slot_idx]
    mask = 0xFFFFFFFFFFFFFFFF
    mult = 6364136223846793005
    for i in range(iters):
        acc = (acc * mult + (i | 1)) & mask
        arr[slot_idx] = acc
    del arr          # release buffer export before closing
    shm.close()
 
 
def make_fn(shm, p: int, stride: int):
    iters = M // p
 
    def fn():
        shm.buf[:4096] = bytes(4096)          # reset all slots
        procs = [mp.Process(target=fs_worker, args=(shm.name, t * stride, iters))
                 for t in range(p)]
        for pr in procs:
            pr.start()
        for pr in procs:
            pr.join()
        for pr in procs:
            if pr.exitcode != 0:
                raise RuntimeError(f"worker failed with exit code {pr.exitcode}")
    return fn
 
 
def bench(shm, p, stride):
    st = run_benchmark(make_fn(shm, p, stride), warmup_runs=WARMUP, timed_runs=TIMED)
    print(f"  p={p} stride={stride:>2}: median {st.median_ms:9.1f} ms  "
          f"IQR {st.iqr_ms:8.1f}", flush=True)
    return st
 
 
def karp_flatt(sp, p):
    return (1.0 / sp - 1.0 / p) / (1.0 - 1.0 / p)
 
 
def main():
    lines = []
 
    def out(s=""):
        print(s)
        lines.append(s)
 
    shm = shared_memory.SharedMemory(create=True, size=4096)
    try:
        # ---- Table 1A: stride sweep at p = P_PHYS ----
        print(f"Stride sweep at p={P_PHYS}, M={M:,}")
        sweep = {s: bench(shm, P_PHYS, s) for s in STRIDES}
 
        # ---- Table 1B: process scaling for stride 1 and 16 ----
        scaling = {}
        for stride in (1, 16):
            print(f"Process scaling, stride={stride}")
            for p in p_sweep_values():
                scaling[(stride, p)] = bench(shm, p, stride)
    finally:
        shm.close()
        shm.unlink()
 
    out("")
    out(f"### Table 1A: Stride sensitivity (p = {P_PHYS}, M = {M:,})")
    out("| Stride (words) | Separation (bytes) | Median (ms) | IQR (ms) | Throughput (Mops/s) |")
    out("|---|---|---|---|---|")
    for s in STRIDES:
        st = sweep[s]
        mops = M / (st.median_ms / 1000.0) / 1e6
        out(f"| {s} | {s * 8} | {st.median_ms:.1f} | {st.iqr_ms:.1f} | {mops:.2f} |")
 
    # cache-line boundary: largest relative time drop between consecutive strides
    best_drop, best_i = 0.0, None
    for i in range(len(STRIDES) - 1):
        a, b = sweep[STRIDES[i]].median_ms, sweep[STRIDES[i + 1]].median_ms
        drop = (a - b) / a
        if drop > best_drop:
            best_drop, best_i = drop, i
    out("")
    if best_i is not None and best_drop >= 0.10:
        s_from, s_to = STRIDES[best_i], STRIDES[best_i + 1]
        out(f"Largest drop: stride {s_from} -> {s_to} "
            f"({s_from * 8} B -> {s_to * 8} B), time fell {best_drop * 100:.1f}%.")
        out(f"Estimated cache-line boundary: {s_to * 8} bytes.")
    else:
        out(f"No clear cache-line boundary: largest drop between strides was only "
            f"{best_drop * 100:.1f}%. In pure Python, interpreter overhead per iteration can "
            f"hide the coherence cost; report this honestly and discuss why.")
 
    out("")
    out("### Table 1B: Karp-Flatt diagnostic series")
    for stride in (1, 16):
        out("")
        out(f"stride = {stride} ({stride * 8} bytes)")
        out("| p | T_p (ms) | S_p | E_p | e(p) |")
        out("|---|---|---|---|---|")
        t1 = scaling[(stride, 1)].median_ms
        for p in p_sweep_values():
            tp = scaling[(stride, p)].median_ms
            sp = t1 / tp
            ep = sp / p
            e_txt = f"{karp_flatt(sp, p):.4f}" if p >= 2 else "n/a"
            out(f"| {p} | {tp:.1f} | {sp:.3f} | {ep:.3f} | {e_txt} |")
 
    m1 = sweep[1].median_ms
    m16 = sweep[16].median_ms
    out("")
    out(emit_verify_tag("PHASE1", STUDENT_SEED, m1, m16))
 
    with open("phase1_results.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\nSaved to phase1_results.md")
 
 
if __name__ == "__main__":
    main()
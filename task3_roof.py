import math
import multiprocessing as mp
import os
import random
from multiprocessing import shared_memory

from harness import (SEED, SCALE, WARMUP, RUNS, run_benchmark, emit_verify_tag, pphys)

# ------------------------------------------------------------------ Part 3A
def bw_worker(name_a: str, name_b: str, s: int, e: int) -> None:
    a = shared_memory.SharedMemory(name=name_a)
    b = shared_memory.SharedMemory(name=name_b)
    a.buf[s:e] = b.buf[s:e]
    a.close()
    b.close()


def run_bw(na, nb, size, P):
    procs = [mp.Process(target=bw_worker, args=(na, nb, t * size // P, (t + 1) * size // P))
             for t in range(P)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()


def fma_worker(iters: int) -> None:
    c, d = 1.0000001, 1e-7
    x0 = x1 = x2 = x3 = x4 = x5 = x6 = x7 = 0.1
    x8 = x9 = x10 = x11 = x12 = x13 = x14 = x15 = 0.2
    for _ in range(iters):             # 16 FMAs = 32 FLOPs per iteration
        x0 = x0 * c + d;   x1 = x1 * c + d;   x2 = x2 * c + d;   x3 = x3 * c + d
        x4 = x4 * c + d;   x5 = x5 * c + d;   x6 = x6 * c + d;   x7 = x7 * c + d
        x8 = x8 * c + d;   x9 = x9 * c + d;   x10 = x10 * c + d; x11 = x11 * c + d
        x12 = x12 * c + d; x13 = x13 * c + d; x14 = x14 * c + d; x15 = x15 * c + d


def run_fma(P, flops_per_worker):
    iters = int(flops_per_worker) // 32
    procs = [mp.Process(target=fma_worker, args=(iters,)) for _ in range(P)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()


# ------------------------------------------------------------------ Part 3B
def attach(name):
    shm = shared_memory.SharedMemory(name=name)
    return shm, shm.buf.cast("d")


def detach(shm, mv):
    mv.release()
    shm.close()


def gemm_worker(variant, nA, nB, nC, N, r0, r1, BS):
    sa, A = attach(nA)
    sb, B = attach(nB)
    sc, C = attach(nC)
    if variant == 1:                              # naive i-j-k, strided B
        for i in range(r0, r1):
            for j in range(N):
                s = 0.0
                for k in range(N):
                    s += A[i * N + k] * B[k * N + j]
                C[i * N + j] = s
    elif variant == 2:                            # i-k-j, hoisted a_ik, unit stride
        for i in range(r0, r1):
            base = i * N
            for j in range(N):
                C[base + j] = 0.0
            for k in range(N):
                a = A[base + k]
                bk = k * N
                for j in range(N):
                    C[base + j] += a * B[bk + j]
    else:                                         # 6-loop blocked, (i,k,j) micro-kernel
        for i in range(r0, r1):
            for j in range(N):
                C[i * N + j] = 0.0
        for ii in range(r0, r1, BS):
            ie = min(ii + BS, r1)
            for jj in range(0, N, BS):
                je = min(jj + BS, N)
                for kk in range(0, N, BS):
                    ke = min(kk + BS, N)
                    for i in range(ii, ie):
                        base = i * N
                        for k in range(kk, ke):
                            a = A[base + k]
                            bk = k * N
                            for j in range(jj, je):
                                C[base + j] += a * B[bk + j]
    detach(sa, A); detach(sb, B); detach(sc, C)


def run_gemm(variant, names, N, P, BS=0):
    procs = [mp.Process(target=gemm_worker,
                        args=(variant, *names, N, t * N // P, (t + 1) * N // P, BS))
             for t in range(P)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()


if __name__ == "__main__":
    P = pphys()
    # ---- Part 3A
    size = int(64e6 * SCALE) // 4096 * 4096 or 4096
    sa = shared_memory.SharedMemory(create=True, size=size)
    sb = shared_memory.SharedMemory(create=True, size=size)
    sb.buf[:] = bytes([1]) * size
    t_bw = run_benchmark(lambda: run_bw(sa.name, sb.name, size, P), WARMUP, RUNS).median_ms
    bw = 2 * size / (t_bw / 1e3 * 1e9)
    sa.close(); sa.unlink(); sb.close(); sb.unlink()

    flops = 6.0e7 * SCALE
    t_fma = run_benchmark(lambda: run_fma(P, flops), WARMUP, RUNS).median_ms
    p_sus = P * flops / (t_fma / 1e3 * 1e9)
    ridge = p_sus / bw
    print(f"P_phys={P}")
    print(f"BW_sustained = {bw:.2f} GB/s (median {t_bw:.1f} ms)")
    print(f"P_sustained  = {p_sus:.4f} GFLOP/s (median {t_fma:.1f} ms)")
    print(f"Ridge point I* = {ridge:.4f} FLOP/byte\n")

    # ---- Part 3B
    N = int(os.environ.get("GEMM_N", "256"))
    nbytes = N * N * 8
    shms = [shared_memory.SharedMemory(create=True, size=nbytes) for _ in range(3)]
    names = tuple(s.name for s in shms)
    mvs = [s.buf.cast("d") for s in shms]
    rnd = random.Random(SEED)
    for idx in range(N * N):
        mvs[0][idx] = rnd.random()
        mvs[1][idx] = rnd.random()
    flop_total = 2 * N ** 3

    def gflops(ms):
        return flop_total / (ms * 1e6)

    st1 = run_benchmark(lambda: run_gemm(1, names, N, P), WARMUP, RUNS)
    st2 = run_benchmark(lambda: run_gemm(2, names, N, P), WARMUP, RUNS)
    c2 = list(mvs[2][: N * N])                    # reference from variant 2 (last run)
    g1, g2 = gflops(st1.median_ms), gflops(st2.median_ms)

    print("| variant | median ms | IQR ms | GFLOP/s |")
    print("|---|---|---|---|")
    print(f"| 1 naive i-j-k | {st1.median_ms:.1f} | {st1.iqr_ms:.1f} | {g1:.4f} |")
    print(f"| 2 i-k-j       | {st2.median_ms:.1f} | {st2.iqr_ms:.1f} | {g2:.4f} |")

    print("\n| BS | W_tile (KiB) | I_tiled (FLOP/B) | median ms | GFLOP/s | max|C3-C2| |")
    print("|---|---|---|---|---|---|")
    best = (None, -1.0)
    for BS in (8, 16, 32, 64, 96, 128):
        st = run_benchmark(lambda: run_gemm(3, names, N, P, BS), WARMUP, RUNS)
        diff = max(abs(x - y) for x, y in zip(mvs[2][: N * N], c2))
        assert diff < 1e-9, f"variant 3 mismatch at BS={BS}: {diff}"
        g = gflops(st.median_ms)
        if g > best[1]:
            best = (BS, g)
        print(f"| {BS} | {3*BS*BS*8/1024:.1f} | {BS/12:.2f} | {st.median_ms:.1f} | {g:.4f} | {diff:.1e} |")
    BSs, g3 = best
    print(f"\nBS* = {BSs}  GFLOP/s(V3) = {g3:.4f}  I_tiled(BS*) = {BSs/12:.2f}")
    print(f"Roofline attainable at I_tiled(BS*): {min(p_sus, BSs/12*bw):.4f} GFLOP/s "
          f"(compute roof {p_sus:.4f}, memory roof at that I = {BSs/12*bw:.2f})")
    print()
    print(emit_verify_tag("PHASE3", SEED, g1, g3))

    for mv in mvs:
        mv.release()
    for s in shms:
        s.close(); s.unlink()
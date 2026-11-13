import ctypes
import multiprocessing as mp
from multiprocessing import shared_memory

from harness import (SEED, SCALE, WARMUP, RUNS, run_benchmark, emit_verify_tag,
                     pphys, proc_counts)


def fs_worker(shm_name: str, slot_idx: int, iters: int) -> None:
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = (ctypes.c_uint64 * 512).from_buffer(shm.buf)
    acc = arr[slot_idx]
    for i in range(iters):
        acc = (acc * 6364136223846793005 + (i | 1)) & 0xFFFFFFFFFFFFFFFF
        arr[slot_idx] = acc  # store to the (possibly shared) cache line
    del arr
    shm.close()


def run_once(name: str, p: int, stride: int, M: int) -> None:
    iters = M // p
    procs = [mp.Process(target=fs_worker, args=(name, t * stride, iters)) for t in range(p)]
    for pr in procs:
        pr.start()
    for pr in procs:
        pr.join()


def bench(name, p, stride, M):
    assert (p - 1) * stride < 512, "slot index would leave the 4096-byte block"
    return run_benchmark(lambda: run_once(name, p, stride, M), warmup=WARMUP, runs=RUNS)


if __name__ == "__main__":
    M = int(1.6e7 * SCALE)
    P = pphys()
    Plog = mp.cpu_count()
    shm = shared_memory.SharedMemory(create=True, size=4096)
    try:
        print(f"P_phys={P}  P_log={Plog}  M={M}\n")
        print("## Stride sweep (p = P_phys)")
        print("| stride | bytes | median ms | IQR ms | Mops/s |")
        print("|---|---|---|---|---|")
        med = {}
        for stride in (1, 2, 4, 8, 16, 32):
            st = bench(shm.name, P, stride, M)
            med[stride] = st.median_ms
            print(f"| {stride} | {stride*8} | {st.median_ms:.1f} | {st.iqr_ms:.1f} | "
                  f"{M / (st.median_ms * 1e3):.2f} |")

        print("\n## Process scaling + Karp-Flatt")
        for stride in (1, 16):
            print(f"\nstride = {stride}")
            print("| p | median ms | S_p | E_p | e(p) |")
            print("|---|---|---|---|---|")
            t1 = None
            for p in proc_counts(Plog):
                st = bench(shm.name, p, stride, M)
                if p == 1:
                    t1 = st.median_ms
                sp = t1 / st.median_ms
                ep = sp / p
                e = ((1 / sp - 1 / p) / (1 - 1 / p)) if p >= 2 else float("nan")
                print(f"| {p} | {st.median_ms:.1f} | {sp:.2f} | {ep:.2f} | {e:.3f} |")

        print()
        print(emit_verify_tag("PHASE1", SEED, med[1], med[16]))
    finally:
        shm.close()
        shm.unlink()
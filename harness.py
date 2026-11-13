"""Minimal timing and verification harness (Listing 1) + small shared helpers.

Environment variables (all optional):
  STUDENT_ID  integer seed for VERIFY_HASH (default 0)  -> set this!
  PPHYS       physical core count (default: logical // 2) -> set this!
  RUNS/WARMUP benchmark repetitions (default 7 / 2)
  LAB_SCALE   shrink workloads for smoke tests only (leave unset for the real lab)
"""
from dataclasses import dataclass
import multiprocessing as mp
import os
import time
from typing import Callable


@dataclass
class BenchStats:
    min_ms: float
    median_ms: float
    iqr_ms: float


def fnv1a_hash(s: str) -> int:
    h = 14695981039346656037
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def run_benchmark(fn: Callable[[], None], warmup: int = 2, runs: int = 7) -> BenchStats:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - t0) / 1e6)
    samples.sort()
    med = samples[runs // 2]
    return BenchStats(samples[0], med, samples[(3 * runs) // 4] - samples[runs // 4])


def emit_verify_tag(phase: str, seed: int, m1: float, m2: float) -> str:
    hw = mp.cpu_count()
    sig = fnv1a_hash(f"{phase}|{seed}|{hw}|{m1:.4f}|{m2:.4f}")
    return f"VERIFY_HASH[{phase}]: {sig:016X} (P_log={hw})"


# ---- shared config -------------------------------------------------------
SEED = int(os.environ.get("STUDENT_ID", "0"))
WARMUP = int(os.environ.get("WARMUP", "2"))
RUNS = int(os.environ.get("RUNS", "7"))
SCALE = float(os.environ.get("LAB_SCALE", "1"))


def pphys() -> int:
    v = os.environ.get("PPHYS")
    return int(v) if v else max(1, mp.cpu_count() // 2)


def proc_counts(plog: int):
    """1, 2, 4, ... up to Plog, always including Plog itself."""
    ps, k = [], 1
    while k <= plog:
        ps.append(k)
        k *= 2
    if plog not in ps:
        ps.append(plog)
    return ps
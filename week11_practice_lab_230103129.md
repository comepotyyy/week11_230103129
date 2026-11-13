#phase 0
#P_log (mp.cpu_count) = 4
#avg perf_counter_ns call latency = 241.24 ns over 1000000 calls
#VERIFY_HASH[PHASE0]: 9106552097E108C4 (P_log=4)

### Stride sweep (p = P_phys)
| stride | bytes | median ms | IQR ms | Mops/s |
|---|---|---|---|---|
| 1 | 8 | 6140.3 | 637.3 | 2.61 |
| 2 | 16 | 10582.2 | 3104.8 | 1.51 |
| 8 | 64 | 4968.4 | 331.9 | 3.22 |
| 16 | 128 | 5044.9 | 149.6 | 3.17 |
| 32 | 256 | 4946.1 | 207.7 | 3.23 |

## Process scaling + Karp-Flatt

stride = 1
| p | median ms | S_p | E_p | e(p) |
|---|---|---|---|---|
| 1 | 8695.0 | 1.00 | 1.00 | nan |
| 2 | 6225.1 | 1.40 | 0.70 | 0.432 |
| 4 | 4123.6 | 2.11 | 0.53 | 0.299 |

stride = 16
| p | median ms | S_p | E_p | e(p) |
|---|---|---|---|---|
| 1 | 9163.0 | 1.00 | 1.00 | nan |
| 2 | 5543.5 | 1.65 | 0.83 | 0.210 |
| 4 | 3502.1 | 2.62 | 0.65 | 0.176 |


#PHASE 2 Strong Scaling vs. Weak Scaling (task2_scaling.py)
#Stage A serial time at N=1200000: 166.8 ms

## Strong scaling
| p | T ms | S_p | E_p |
| 1 | 5124.2 | 1.00 | 1.00 |
| 2 | 2682.5 | 1.91 | 0.96 |
| 3 | 2520.6 | 2.03 | 0.68 |
| 4 | 1883.7 | 2.72 | 0.68 |

serial fraction s = 0.0325  ->  Amdahl cap 1/s = 30.7x ; observed S(P_log) = 2.72x

## Marginal speedup per added process
p 1->2: dS = +0.91
p 2->3: dS = +0.12
p 3->4: dS = +0.69

## Weak scaling (N = p * N0)
| p | N | T ms | E_weak | alpha | S_Gustafson |
|---|---|---|---|---|---|
| 1 | 200000 | 853.2 | 1.00 | 0.0311 | 1.00 |
| 2 | 400000 | 884.7 | 0.96 | 0.0602 | 1.94 |
| 3 | 600000 | 1113.9 | 0.77 | 0.0717 | 2.86 |
| 4 | 800000 | 1401.4 | 0.61 | 0.0758 | 3.77 |

VERIFY_HASH[PHASE2]: E40C51A6145ACB30 (P_log=4)


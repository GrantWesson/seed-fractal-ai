# Native branch-free kernels

`seed_kernels.c` is a minimal C reference implementation of the core
packed read/write operations used by Seed-Fractal AI.

## Properties

- Completely data-independent control flow in `read_bits` / `write_bits`.
- Single contiguous array → optimal spatial locality.
- Both the in-word and spanning cases are evaluated; a mask selects.
- No exceptions, no system calls in the hot loop.

## Build

```bash
gcc -O3 -march=native -fno-exceptions -fno-asynchronous-unwind-tables \
    -o seed_kernels_test native/seed_kernels.c
```

## Measure

```bash
perf stat -e cycles,instructions,cache-references,cache-misses,branches,branch-misses \
    ./seed_kernels_test
```

On a modern core you should see:

- Extremely low branch-miss rate (only the loop back-edge).
- Cache-miss rate dominated by compulsory / capacity traffic of the arena,
  not by random pointer chasing.

## Integration path

The Python `SeedArena.read_bits` / `write_bits` are written to match
these semantics exactly so a future Cython / cffi / ctypes binding
(or full rewrite of the hot path) can drop this C in with no behavioural
change.

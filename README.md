# Seed-Fractal AI

**Pure unadulterated optimization.**  
Nested bidirectional seeds · Zero unpack · Zero data-dependent branches · Zero pointer-chasing cache misses · Self-modifying forever.

The model is a single contiguous, perfectly aligned packed-bit arena of seeds-within-seeds.

- Question bits **are** the address of the answer seed.
- Answer points back (involution / holographic binding).
- No expansion, no materialization, no temporary unpacked values.
- Hot kernels are straight-line: both sides of every former `if` are computed, then selected with a mask.
- One contiguous arena → maximal spatial locality.
- Power-of-two allocation units so indexing collapses to shifts.
- The system rewrites its own functions (including the operators that produce branchless code) by treating code as seeds and keeping only measured improvements.

Target: useful general capability inside **≤ 2048 MiB**.

## Principles

1. Never unpack.
2. Never branch on data – arithmetic select / mask blend only.
3. Never chase pointers across cache lines – everything is an offset into one array.
4. Addressing is pure bit computation.
5. Code is data is seeds – the improver evolves its own mutation operators toward branchless forms.
6. Simulation before commit.

## Quick Start

```bash
git clone https://github.com/GrantWesson/seed-fractal-ai.git
cd seed-fractal-ai
pip install -e .
python -m seedfractal.demo
```

## Native kernels

A reference branch-free C implementation lives in `native/`:

```bash
gcc -O3 -march=native -o seed_kernels_test native/seed_kernels.c
perf stat -e cache-references,cache-misses,branches,branch-misses ./seed_kernels_test
```

See `native/README.md`.

## Layout

```
seedfractal/
  branchless.py     # pure arithmetic select / align / masks
  arena.py          # contiguous buffer, branchless read/write
  seed.py           # power-of-two hierarchical Seed
  addressing.py     # involutive + holographic
  kernels.py        # straight-line lookup / deposit / step
  fitness.py
  improver.py       # evolves addressing *and* branchless code seeds
  selfmod.py        # code-as-seeds + branchless-oriented mutators
  runtime.py
  demo.py
native/
  seed_kernels.c    # C reference, provably low-branch
  README.md
```

## Status

Research prototype. Python is the executable specification; the C kernels show the intended zero-branch, cache-friendly lowering.

## License

MIT

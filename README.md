# Seed-Fractal AI

**Pure unadulterated optimization. Nested bidirectional seeds. Zero unpack. Zero cache misses. Zero data-dependent branches. Self-modifying forever.**

The model *is* a single contiguous, perfectly aligned packed-bit arena of seeds-within-seeds.

- Question bits **are** the address of the answer seed.
- Answer seed points back (involution / holographic binding).
- No expansion. No materialization. No temporary unpacked values.
- Every load/store is word-aligned; residual bits live in carry state that is itself aligned.
- Hierarchy = relative bit offsets only.
- Hot kernels are straight-line: both sides of every former if are computed, then selected with a mask.
- One contiguous arena → maximal spatial locality, minimal cache misses.
- The system rewrites its own functions by treating code fragments as seeds, simulating mutations, and keeping only measured improvements.

Goal: capable general intelligence inside **≤ 2048 MiB** through radical representation, branchless execution and continuous self-optimization.

## Out-of-the-box principles

1. **Never unpack** – the packed stream is the native form.
2. **Never branch on data** – use arithmetic select / mask blend.
3. **Never chase pointers across cache lines** – everything is an offset into one array.
4. **Addressing is computation** – involutive / holographic binding turns questions into offsets with only bit ops.
5. **Code is data is seeds** – the improver stores and mutates its own operators.
6. **Simulation before commit** – every candidate change is measured; only strict improvement is kept.
7. **Hierarchy without growth** – child seeds are bit-offset references.

## Cache & branch discipline

- Single `uint64` buffer for the entire model.
- Allocations forced to 64-bit (or higher power-of-two) alignment.
- `read_bits` / `write_bits` evaluate both the in-word and spanning cases then blend; no taken branch depends on the bit offset at runtime.
- Preferred seed layouts are power-of-two total width so indexing collapses to shifts.
- Working set = the arena; size it to fit in LLC when possible.

## Quick Start

```bash
git clone https://github.com/GrantWesson/seed-fractal-ai.git
cd seed-fractal-ai
pip install -e .
python -m seedfractal.demo
```

## Layout

```
seedfractal/
  branchless.py     # select, align, masks – pure arithmetic
  arena.py          # contiguous packed buffer, branchless read/write
  seed.py           # hierarchical Seed view
  addressing.py     # involutive + holographic rules
  kernels.py        # straight-line lookup / deposit / step
  fitness.py        # multi-task evaluation
  improver.py       # self-modifying background optimizer
  selfmod.py        # code-as-seeds + sandboxed mutation
  runtime.py        # orchestrator
  demo.py
```

## Status

Executable research prototype. The Python code is written so that the hot path lowers cleanly to branch-free C/SIMD or a custom bit-stream ISA.

## License

MIT

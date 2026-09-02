# Seed-Fractal AI

**Pure unadulterated optimization. Nested bidirectional seeds. Zero unpack. Self-modifying forever.**

The model *is* a single contiguous, perfectly aligned packed-bit arena of seeds-within-seeds.

- Question bits **are** the address of the answer seed.
- Answer seed points back (involution).
- No expansion. No materialization. No temporary unpacked values.
- Every load/store is word-aligned; residual bits live in carry state that is itself aligned.
- Hierarchy = relative bit offsets only.
- The system rewrites its own functions by treating code fragments as seeds, simulating mutations, and keeping only measured improvements. This runs indefinitely as a background process.

Goal: capable general intelligence inside **≤ 2048 MiB** through radical representation and continuous self-optimization.

## Out-of-the-box principles

1. **Never unpack** – the packed stream is the native form. Extract/deposit are pure shifts + masks.
2. **Addressing is computation** – involutive / holographic / binding operations turn questions into offsets with only bit ops.
3. **Code is data is seeds** – the improver stores mutation operators and fitness functions as packed seeds and evolves them.
4. **Simulation before commit** – every candidate change is measured on a task suite; only strict improvement is kept.
5. **Hierarchy without growth** – child seeds are bit-offset references; depth is addressing, not allocation of dense tensors.
6. **Persistence is the arena itself** – save/load is a single contiguous buffer dump.

## Quick Start

```bash
git clone https://github.com/GrantWesson/seed-fractal-ai.git
cd seed-fractal-ai
pip install -e .
python -m seedfractal.demo
```

## Architecture

```
seedfractal/
  arena.py          # Packed uint64 arena + persistence
  seed.py           # Variable-width hierarchical Seed view
  addressing.py     # Involutive + holographic binding rules
  kernels.py        # Zero-cost lookup / deposit / step
  fitness.py        # Multi-task evaluation suite
  improver.py       # Self-modifying background optimizer
  selfmod.py        # Code-as-seeds, AST/bit mutation, sandboxed eval
  runtime.py        # Orchestrator + daemon
  demo.py           # End-to-end demonstration
```

## Status

Executable research prototype. Python is the specification language. Hot paths are written so they can be lowered later to C++/CUDA/bit-intrinsics or a custom bit-stream ISA without changing semantics.

## License

MIT

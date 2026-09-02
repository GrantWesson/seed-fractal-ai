# Seed-Fractal AI

**Self-improving, bit-packed, nested-seed fractal intelligence.**

The entire model is a single contiguous, perfectly aligned arena of **seeds within seeds**.

- A *question* is a seed.
- That seed *is* the address of its answer.
- The answer is itself a seed that points back.
- No expansion, no unpacking, no materialization.
- Lookups are pure bit-permutes + aligned loads.

The system continuously improves its own functions by running background simulations of candidate changes and keeping only those that measure better. This loop runs indefinitely as a low-priority process.

Target: useful general capability inside **≤ 2048 MiB**.

## Core Ideas

1. **Bidirectional nested seeds**  
   Question ↔ Answer is an involution realized by bit-level addressing rules. No depth unrolling.

2. **Zero-cost packed representation**  
   Everything stays in a packed bit-arena. Extract / deposit / lookup are shifts, masks, and aligned vector loads only.

3. **Self-modification**  
   A background `Improver` mutates addressing rules or payloads, runs cheap simulations, and commits improvements.

4. **Fractal hierarchy without expansion**  
   Seeds contain child-seed references (bit offsets). Hierarchy is pure addressing, never materialised tensors.

## Quick Start

```bash
pip install -e .
python -m seedfractal.demo
```

## Project Layout

```
seedfractal/
  arena.py          # SeedArena – the single packed bit buffer
  seed.py           # Seed view (zero-copy)
  addressing.py     # Involutive / learned bit-permute addressing
  kernels.py        # Fused packed operations
  improver.py       # Background self-improvement loop
  runtime.py        # Tiny runtime + simulation harness
demo.py             # Minimal working example
```

## Status

Research prototype. The Python layer is the executable specification of the ideas. Later stages will lower the hot kernels to C++/CUDA/bit-intrinsics and eventually to a custom bit-stream ISA.

## License

MIT

# Seed-Fractal AI

**Target: ≤ 512 MB (hard ceiling 2048 MB).**  
Pure packed bits · Zero unpack · Zero data-dependent branches · Zero pointer-chasing · Self-modifying representation.

The entire model is one contiguous aligned arena of nested seeds.

## Core optimisations (all active)

1. **Variable bit-width regions** – 1/2/4/8/16/32-bit seeds mixed in the same arena. Improver chooses width by fitness-per-bit.
2. **Prototype / shared seeds** – common payloads and sub-trees live once; ordinary seeds store only a short reference + optional delta.
3. **Holographic multi-pair seeds** – one physical seed can bind several question–answer pairs via XOR/binding; retrieval is unbinding.
4. **Size-penalized fitness** – `score / (used_MB + ε)` so the improver is directly pressured under 512 MB.
5. **Hot/cold reordering** – frequently used seeds are moved to low addresses (still pure offsets).
6. **Representation self-modification** – the improver mutates bit-widths, prototype tables, binding depth and addressing parameters.
7. **Branchless + power-of-two** layouts and mask-select kernels.
8. **Streaming inference** – activations never materialise; each payload is consumed by the next addressing step.
9. **Low-bit C reference kernels** for 1/2/4/8-bit fields.
10. **Single-arena persistence** with structure that admits future seed-aware compression.

## Quick Start

```bash
git clone https://github.com/GrantWesson/seed-fractal-ai.git
cd seed-fractal-ai
pip install -e .
python -m seedfractal.demo
```

## Native kernels

```bash
gcc -O3 -march=native -o seed_kernels_test native/seed_kernels.c
perf stat -e cache-references,cache-misses,branches,branch-misses ./seed_kernels_test
```

## Layout

```
seedfractal/
  branchless.py
  arena.py          # contiguous buffer, variable-width support
  seed.py           # power-of-two + variable logical widths
  prototype.py      # shared prototype table
  addressing.py     # involutive + holographic + perfect-hash style
  kernels.py        # streaming lookup / deposit / step
  fitness.py        # multi-task + size penalty
  improver.py       # evolves code *and* representation
  selfmod.py
  runtime.py
  demo.py
native/
  seed_kernels.c    # branch-free, low-bit capable
  README.md
```

## Status

Research prototype aggressively optimised for density. The improver now treats bytes used as a first-class cost.

## License

MIT

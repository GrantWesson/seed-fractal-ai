"""
Minimal demonstration of the nested-seed, zero-cost lookup,
and background self-improvement ideas.
"""

from __future__ import annotations

import time
from .runtime import Runtime
from .addressing import involutive_permute


def main():
    print("=== Seed-Fractal AI demo ===\n")

    rt = Runtime(capacity_mb=8)  # tiny for the demo

    # Teach a few question ↔ answer pairs
    print("Teaching a handful of associations...")
    for q in range(0, 100, 7):
        a = involutive_permute(q, 16) & 0xFFFF
        rt.teach(q, a)

    # Query
    print("\nQueries:")
    for q in [0, 7, 14, 21, 42]:
        ans = rt.ask(q)
        print(f"  Q={q:4d} → A={ans:#06x}")

    print("\nStarting background self-improvement (daemon)...")
    rt.start_self_improvement(interval_sec=0.5)

    # Let it run a few cycles
    for i in range(8):
        time.sleep(0.6)
        print(f"  [{i}] {rt.status()}")

    rt.stop_self_improvement()
    print("\nDemo finished.")
    print(rt.status())
    print(f"Arena footprint: {rt.arena.used_bytes()} bytes")


if __name__ == "__main__":
    main()

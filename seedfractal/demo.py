"""
End-to-end demonstration of pure packed seeds,
bidirectional addressing, multi-task fitness,
and self-modifying background improvement.
"""

from __future__ import annotations

import time
from .runtime import Runtime
from .addressing import involutive_permute


def main():
    print("=== Seed-Fractal AI — pure optimization demo ===\n")

    rt = Runtime(capacity_mb=16, mode="involutive")

    print("Teaching associations...")
    for q in range(0, 200, 5):
        a = involutive_permute(q, 16) & 0xFFFF
        rt.teach(q, a)

    print("\nInitial queries:")
    for q in [0, 5, 10, 15, 42, 100]:
        print(f"  Q={q:4d} → A={rt.ask(q):#06x}")

    print("\nStarting indefinite self-improvement (daemon thread)...")
    rt.start_self_improvement(interval_sec=0.4)

    for i in range(12):
        time.sleep(0.5)
        print(f"  [{i:02d}] {rt.status()}")

    rt.stop_self_improvement()
    print("\nFinal status:", rt.status())
    print(f"Arena footprint: {rt.arena.used_bytes()} bytes")
    print("Demo complete.")


if __name__ == "__main__":
    main()

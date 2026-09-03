"""
Density-focused demonstration.
"""

from __future__ import annotations

import time
from .runtime import Runtime
from .addressing import involutive_permute


def main():
    print("=== Seed-Fractal AI — density target ≤ 512 MB ===\n")

    rt = Runtime(capacity_mb=32, mode="involutive")

    print("Teaching associations (variable-width)...")
    for q in range(0, 300, 3):
        a = involutive_permute(q, 16) & 0xFFFF
        rt.teach(q, a)

    print("\nQueries:")
    for q in [0, 3, 9, 15, 42, 99]:
        print(f"  Q={q:4d} → A={rt.ask(q):#06x}")

    print("\nStarting density-aware self-improvement...")
    rt.start_self_improvement(interval_sec=0.35)

    for i in range(14):
        time.sleep(0.4)
        print(f"  [{i:02d}] {rt.status()}")

    rt.stop_self_improvement()
    print("\nFinal:", rt.status())
    print("Demo complete.")


if __name__ == "__main__":
    main()

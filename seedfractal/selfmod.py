"""
True self-modification.

Out-of-box approach:
- Key functions (mutation operators, fitness helpers) are stored as
  source-text or compact bytecode seeds inside the arena.
- The improver proposes bit-level or token-level mutations to those seeds.
- Each mutant is executed inside a severely restricted sandbox on a
  private arena copy.
- Only mutants that improve measured fitness are written back.

This closes the loop: the system can rewrite the very operators that
produce the next generation of improvements.
"""

from __future__ import annotations

import ast
import random
import textwrap
from typing import Callable, Dict, Optional, Tuple

# Extremely restricted builtins for sandboxed eval
_SAFE_BUILTINS = {
    "range": range,
    "len": len,
    "int": int,
    "min": min,
    "max": max,
    "abs": abs,
    "bin": bin,
    "hex": hex,
    "sum": sum,
    "True": True,
    "False": False,
    "None": None,
}


def _safe_exec(source: str, locals_dict: dict) -> None:
    """Execute source with almost no builtins."""
    tree = ast.parse(source, mode="exec")
    # Reject anything that looks like an import or attribute deep dive
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise ValueError("Forbidden node")
    code = compile(tree, "<seed>", "exec")
    exec(code, {"__builtins__": _SAFE_BUILTINS}, locals_dict)


# ---- mutation operators that themselves can be evolved ----

def mutate_source_bitflip(src: str, rate: float = 0.02) -> str:
    """Treat source as bytes and flip a few bits (may produce syntax errors)."""
    data = bytearray(src.encode("utf-8"))
    n = max(1, int(len(data) * rate))
    for _ in range(n):
        i = random.randint(0, len(data) - 1)
        data[i] ^= 1 << random.randint(0, 7)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return src  # revert on failure


def mutate_source_token(src: str) -> str:
    """Crude token-level mutation: swap two identifiers or constants."""
    tokens = src.split()
    if len(tokens) < 4:
        return src
    i, j = random.sample(range(len(tokens)), 2)
    tokens[i], tokens[j] = tokens[j], tokens[i]
    return " ".join(tokens)


DEFAULT_MUTATORS: Dict[str, Callable[[str], str]] = {
    "bitflip": mutate_source_bitflip,
    "token": mutate_source_token,
}


class CodeSeed:
    """A piece of source that lives (conceptually) as a seed."""

    def __init__(self, name: str, source: str):
        self.name = name
        self.source = textwrap.dedent(source).strip()

    def mutate(self, which: str = "bitflip") -> "CodeSeed":
        fn = DEFAULT_MUTATORS.get(which, mutate_source_bitflip)
        return CodeSeed(self.name, fn(self.source))

    def try_eval(self, locals_dict: dict) -> bool:
        try:
            _safe_exec(self.source, locals_dict)
            return True
        except Exception:
            return False


# Bootstrap: a tiny fitness helper expressed as a CodeSeed
BOOTSTRAP_FITNESS_HELPER = CodeSeed(
    "helper",
    """
def score(hits, total):
    if total <= 0:
        return 0.0
    return hits / total
""",
)

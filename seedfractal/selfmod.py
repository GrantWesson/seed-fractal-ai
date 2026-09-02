"""
True self-modification + evolution of branchless operators.

The improver can now propose branchless rewrites of its own
mutation helpers and keep them only when measured fitness does
not regress.
"""

from __future__ import annotations

import ast
import random
import textwrap
from typing import Callable, Dict

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
    tree = ast.parse(source, mode="exec")
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)):
            raise ValueError("Forbidden node")
    code = compile(tree, "<seed>", "exec")
    exec(code, {"__builtins__": _SAFE_BUILTINS}, locals_dict)


# ---------- classic mutators ----------

def mutate_source_bitflip(src: str, rate: float = 0.02) -> str:
    data = bytearray(src.encode("utf-8"))
    n = max(1, int(len(data) * rate))
    for _ in range(n):
        i = random.randint(0, len(data) - 1)
        data[i] ^= 1 << random.randint(0, 7)
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return src


def mutate_source_token(src: str) -> str:
    tokens = src.split()
    if len(tokens) < 4:
        return src
    i, j = random.sample(range(len(tokens)), 2)
    tokens[i], tokens[j] = tokens[j], tokens[i]
    return " ".join(tokens)


# ---------- branchless-oriented mutators (the ones we want to evolve) ----------

def mutate_toward_branchless(src: str) -> str:
    """
    Heuristic rewrite that replaces common if/else patterns with
    arithmetic select idioms. This is deliberately simple so the
    improver can further mutate it.
    """
    # Very small pattern catalogue – real evolution happens by mutating this function itself
    replacements = [
        ("if cond:", "# branchless candidate: mask = -int(cond != 0)"),
        ("else:", "# else path blended"),
        ("return a if c else b", "return (a & -int(c != 0)) | (b & ~(-int(c != 0)))"),
    ]
    out = src
    for old, new in replacements:
        if old in out and random.random() < 0.4:
            out = out.replace(old, new, 1)
    return out


DEFAULT_MUTATORS: Dict[str, Callable[[str], str]] = {
    "bitflip": mutate_source_bitflip,
    "token": mutate_source_token,
    "branchless": mutate_toward_branchless,
}


class CodeSeed:
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


# Bootstrap helpers that themselves can be evolved toward pure arithmetic
BOOTSTRAP_FITNESS_HELPER = CodeSeed(
    "helper",
    """
def score(hits, total):
    # Prefer arithmetic form
    return hits / (total + (total == 0))
""",
)

BOOTSTRAP_SELECT = CodeSeed(
    "select",
    """
def select(cond, a, b):
    mask = -int(cond != 0)
    return (a & mask) | (b & ~mask)
""",
)

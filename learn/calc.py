"""Reproducible arithmetic for answer-key verification (check D7).

Evaluates a restricted arithmetic expression with Python's AST; no names except sqrt and pi,
no attribute access, no calls other than sqrt/round/abs.
"""

import ast
import math
import operator
import re

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY = {ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCS = {"sqrt": math.sqrt, "round": round, "abs": abs}
_NAMES = {"pi": math.pi}


class CalcError(ValueError):
    pass


def evaluate(expr: str) -> float:
    expr = (expr or "").replace("×", "*").replace("÷", "/").replace("−", "-").replace("^", "**")
    if len(expr) > 200:
        raise CalcError("expression too long")
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise CalcError(f"cannot parse {expr!r}") from e
    return float(_eval(tree.body))


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise CalcError("exponent too large")
        try:
            return _BINOPS[type(node.op)](left, right)
        except ZeroDivisionError as e:
            raise CalcError("division by zero") from e
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _UNARY[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Name) and node.id in _NAMES:
        return _NAMES[node.id]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in _FUNCS
        and not node.keywords
        and 1 <= len(node.args) <= 2
    ):
        return _FUNCS[node.func.id](*[_eval(a) for a in node.args])
    raise CalcError(f"unsupported expression element: {ast.dump(node)[:60]}")


_NUM_RE = re.compile(r"-?\d[\d,]*(?:\.\d+)?|-?\.\d+")


def first_number(text: str) -> tuple[float, int] | None:
    """First number in an answer string and its number of decimal places."""
    m = _NUM_RE.search((text or "").replace("−", "-"))
    if not m:
        return None
    raw = m.group(0).replace(",", "")
    decimals = len(raw.split(".")[1]) if "." in raw else 0
    return float(raw), decimals


def answer_matches(answer: str, calculation: str) -> tuple[bool, str]:
    """True when the stated answer equals the recomputed value, allowing rounding to the stated decimals."""
    value = evaluate(calculation)
    parsed = first_number(answer)
    if parsed is None:
        return False, f"answer {answer!r} contains no number"
    stated, decimals = parsed
    tol = max(1e-9, 0.5 * 10 ** (-decimals)) + 1e-12
    ok = abs(stated - value) <= tol
    return ok, f"{calculation} = {value:g}; key says {stated:g}"

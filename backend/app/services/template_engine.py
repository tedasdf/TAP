import ast
import itertools
import re
from typing import Any

SUPPORTED_OPS = {ast.Div, ast.Mult, ast.Add, ast.Sub, ast.FloorDiv}

_CONDITIONAL_RE = re.compile(
    r"^(.+?)\s*(<=|>=|!=|<|>|==)\s*(.+?)\s*→\s*(.+?)\s*,\s*else\s*(.+)$"
)


def _parse_number(s: str) -> int | float:
    s = s.strip()
    try:
        return int(s)
    except ValueError:
        return float(s)


def _eval_node(node: ast.expr) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Non-numeric constant: {node.value!r}")
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_node(node.operand)
    if isinstance(node, ast.BinOp):
        if type(node.op) not in SUPPORTED_OPS:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        op = node.op
        if isinstance(op, ast.Add):
            return left + right
        if isinstance(op, ast.Sub):
            return left - right
        if isinstance(op, ast.Mult):
            return left * right
        if isinstance(op, ast.Div):
            return left / right
        if isinstance(op, ast.FloorDiv):
            return left // right
    raise ValueError(f"Unsupported expression syntax: {type(node).__name__}")


def _eval_derive_with_trace(
    expr: str, from_param: str, resolved: dict[str, Any]
) -> tuple[int | float, str]:
    if from_param not in resolved:
        raise ValueError(f"Derive expression references unknown param '{from_param}'")

    from_value = resolved[from_param]
    substituted = expr.replace(from_param, str(from_value))

    # Conditional: `<lhs> <op> <rhs> → <then>, else <else>`
    if "→" in substituted:
        m = _CONDITIONAL_RE.match(substituted)
        if not m:
            raise ValueError(f"Cannot parse conditional expression: '{expr}'")
        lhs_s, op_s, rhs_s, then_s, else_s = m.groups()
        lhs = _parse_number(lhs_s)
        rhs = _parse_number(rhs_s)
        cmp_result = {
            "<=": lhs <= rhs,
            ">=": lhs >= rhs,
            "<": lhs < rhs,
            ">": lhs > rhs,
            "==": lhs == rhs,
            "!=": lhs != rhs,
        }[op_s]
        result = _parse_number(then_s if cmp_result else else_s)
        return result, f"{substituted} = {result}"

    try:
        tree = ast.parse(substituted, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid expression '{expr}': {exc}") from exc

    result = _eval_node(tree.body)
    return result, f"{substituted} = {result}"


def eval_derive_expr(expr: str, from_param: str, resolved: dict[str, Any]) -> int | float:
    """Safe AST-based evaluator.

    Only permits arithmetic on known params.
    Raises ValueError for unsupported operations or unknown param references.
    """
    value, _ = _eval_derive_with_trace(expr, from_param, resolved)
    return value


def expand_template(params: dict[str, Any]) -> list[dict[str, Any]]:
    """Return one resolved combo dict per cartesian-product row of vary params.

    Raises ValueError if a derive expr cannot be evaluated.
    """
    vary_keys = [k for k, v in params.items() if v["role"] == "vary"]
    fixed_keys = [k for k, v in params.items() if v["role"] == "fixed"]
    derive_keys = [k for k, v in params.items() if v["role"] == "derive"]

    vary_lists = [params[k]["values"] for k in vary_keys]
    raw_combos: list[tuple] = list(itertools.product(*vary_lists)) if vary_lists else [()]

    result = []
    for i, combo in enumerate(raw_combos):
        run_params: dict[str, Any] = dict(zip(vary_keys, combo))
        for k in fixed_keys:
            run_params[k] = params[k]["value"]

        derive_trace: dict[str, str] = {}
        for k in derive_keys:
            p = params[k]
            value, trace = _eval_derive_with_trace(p["expr"], p["from"], run_params)
            run_params[k] = value
            derive_trace[k] = trace

        result.append({"combo_index": i, "params": run_params, "derive_trace": derive_trace})

    return result


def validate_template_params(params: dict[str, Any]) -> list[str]:
    """Return a list of validation error strings (empty list = valid).

    Checks:
    - At least one vary param
    - All derive from_param references exist in params
    - No circular derive dependencies
    """
    errors: list[str] = []

    vary_keys = [k for k, v in params.items() if v["role"] == "vary"]
    if not vary_keys:
        errors.append("At least one param must have role 'vary'")

    derive_keys = {k for k, v in params.items() if v["role"] == "derive"}

    for k in derive_keys:
        from_param = params[k].get("from", "")
        if from_param not in params:
            errors.append(
                f"Derive param '{k}' references unknown param '{from_param}'"
            )

    # Cycle detection via DFS on the derive dependency graph
    deps = {k: params[k]["from"] for k in derive_keys if params[k].get("from") in params}
    visited: set[str] = set()
    in_stack: set[str] = set()

    def _has_cycle(node: str) -> bool:
        if node in in_stack:
            return True
        if node in visited or node not in derive_keys:
            return False
        visited.add(node)
        in_stack.add(node)
        dep = deps.get(node)
        cycle = dep is not None and _has_cycle(dep)
        in_stack.discard(node)
        return cycle

    for k in derive_keys:
        if k not in visited and _has_cycle(k):
            errors.append(f"Circular derive dependency involving '{k}'")

    return errors

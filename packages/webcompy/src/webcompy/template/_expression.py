"""Safe compilation and evaluation of template ``{{ }}`` expressions."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from webcompy.exception import WebComPyException
from webcompy.signal import SignalBase
from webcompy.signal._graph import SignalNode, consumer_destroy, set_active_consumer


@dataclass(frozen=True, eq=False)
class ExpressionPlan:
    source: str
    node: ast.Expression
    is_plain_path: bool
    root_names: tuple[str, ...]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ExpressionPlan):
            return NotImplemented
        return (
            self.source == other.source
            and self.is_plain_path == other.is_plain_path
            and self.root_names == other.root_names
        )

    def __hash__(self) -> int:
        return hash((self.source, self.is_plain_path, self.root_names))


_BINOPS: dict[type, Callable[[Any, Any], Any]] = {
    ast.Add: lambda a, b: a + b,
    ast.Sub: lambda a, b: a - b,
    ast.Mult: lambda a, b: a * b,
    ast.Div: lambda a, b: a / b,
    ast.FloorDiv: lambda a, b: a // b,
    ast.Mod: lambda a, b: a % b,
    ast.Pow: lambda a, b: a**b,
    ast.LShift: lambda a, b: a << b,
    ast.RShift: lambda a, b: a >> b,
    ast.BitOr: lambda a, b: a | b,
    ast.BitXor: lambda a, b: a ^ b,
    ast.BitAnd: lambda a, b: a & b,
    ast.MatMult: lambda a, b: a @ b,
}

_CMP_OPS: dict[type, Callable[[Any, Any], bool]] = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}

_ALLOWED_NODES = frozenset(
    {
        ast.Expression,
        ast.BinOp,
        ast.BoolOp,
        ast.UnaryOp,
        ast.Compare,
        ast.IfExp,
        ast.Subscript,
        ast.Attribute,
        ast.Call,
        ast.List,
        ast.Tuple,
        ast.Dict,
        ast.Set,
        ast.Name,
        ast.Constant,
        ast.Slice,
        ast.Load,
        ast.Store,
        ast.Del,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.FloorDiv,
        ast.Mod,
        ast.Pow,
        ast.LShift,
        ast.RShift,
        ast.BitOr,
        ast.BitXor,
        ast.BitAnd,
        ast.MatMult,
        ast.And,
        ast.Or,
        ast.Not,
        ast.UAdd,
        ast.USub,
        ast.Invert,
        ast.Eq,
        ast.NotEq,
        ast.Lt,
        ast.LtE,
        ast.Gt,
        ast.GtE,
        ast.Is,
        ast.IsNot,
        ast.In,
        ast.NotIn,
        ast.keyword,
    }
)


def compile_expression(source: str) -> ExpressionPlan:
    try:
        tree = ast.parse(source, mode="eval")
    except SyntaxError as e:
        raise WebComPyException(f"Invalid template expression {source!r}: {e}") from None
    if not isinstance(tree, ast.Expression):
        raise WebComPyException(f"Invalid template expression {source!r}")
    names_set: set[str] = set()
    for n in ast.walk(tree):
        _validate_node(n, source)
        if isinstance(n, ast.Name):
            names_set.add(n.id)
    body = tree.body
    is_plain_path = _is_plain_path(body)
    names = tuple(sorted(names_set))
    return ExpressionPlan(source=source, node=tree, is_plain_path=is_plain_path, root_names=names)


def _validate_node(node: ast.AST, source: str) -> None:
    if type(node) not in _ALLOWED_NODES:
        raise WebComPyException(
            f"Unsupported construct in template expression {source!r}: {type(node).__name__} is not allowed"
        )
    if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
        raise WebComPyException(
            f"Dunder/private attribute access not allowed in template expression {source!r}: {node.attr}"
        )
    if isinstance(node, ast.Call) and not isinstance(node.func, (ast.Name, ast.Attribute)):
        raise WebComPyException(f"Indirect call is not allowed in template expression {source!r}")


def _is_plain_path(node: ast.AST) -> bool:
    if isinstance(node, ast.Attribute):
        return _is_plain_path(node.value)
    return isinstance(node, ast.Name)


class _EvalState:
    __slots__ = ("saw_signal",)

    def __init__(self) -> None:
        self.saw_signal = False


def resolve_scope(plan: ExpressionPlan, ctx: dict[str, Any]) -> dict[str, Any]:
    scope: dict[str, Any] = {}
    for name in plan.root_names:
        if name in ctx:
            scope[name] = ctx[name]
    return scope


def evaluate(
    plan: ExpressionPlan,
    scope: dict[str, Any],
    state: _EvalState | None = None,
) -> Any:
    probe: SignalNode | None = None
    prev_consumer: SignalNode | None = None
    if state is not None:
        probe = SignalNode()
        prev_consumer = set_active_consumer(probe)
    try:
        try:
            result = _eval_node(plan.node.body, scope, state)
            if probe is not None and state is not None and probe.producers is not None:
                state.saw_signal = True
            return result
        except WebComPyException:
            raise
        except KeyError:
            raise
        except Exception as e:
            raise WebComPyException(f"Error evaluating template expression {plan.source!r}: {e}") from None
    finally:
        if probe is not None:
            set_active_consumer(prev_consumer)
            if probe.producers is not None:
                consumer_destroy(probe)


def _unwrap(v: Any, state: _EvalState | None) -> Any:
    if isinstance(v, SignalBase):
        if state is not None:
            state.saw_signal = True
        return v.value
    return v


def _eval_node(node: ast.AST, scope: dict[str, Any], state: _EvalState | None) -> Any:
    if isinstance(node, ast.Name):
        if node.id in scope:
            value = scope[node.id]
            return _unwrap(value, state)

        available = ", ".join(sorted(scope.keys()))
        raise KeyError(f"Template variable '{node.id}' not found in context (available: {available})")

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Attribute):
        obj = _eval_node(node.value, scope, state)
        obj = _unwrap(obj, state)
        name = node.attr
        if isinstance(obj, dict):
            return _unwrap(obj[name], state)
        return _unwrap(getattr(obj, name), state)

    if isinstance(node, ast.Subscript):
        obj = _eval_node(node.value, scope, state)
        obj = _unwrap(obj, state)
        key = _eval_node(node.slice, scope, state)
        return _unwrap(obj[key], state)

    if isinstance(node, ast.Slice):
        lower = _eval_node(node.lower, scope, state) if node.lower else None
        upper = _eval_node(node.upper, scope, state) if node.upper else None
        step = _eval_node(node.step, scope, state) if node.step else None
        return slice(lower, upper, step)

    if isinstance(node, ast.List):
        return [_eval_node(el, scope, state) for el in node.elts]

    if isinstance(node, ast.Tuple):
        return tuple(_eval_node(el, scope, state) for el in node.elts)

    if isinstance(node, ast.Set):
        return {_eval_node(el, scope, state) for el in node.elts}

    if isinstance(node, ast.Dict):
        keys = [_eval_node(k, scope, state) if k else None for k in node.keys]
        values = [_eval_node(v, scope, state) for v in node.values]
        return dict(zip(keys, values, strict=True))

    if isinstance(node, ast.UnaryOp):
        operand = _eval_node(node.operand, scope, state)
        op = type(node.op)
        if op is ast.Not:
            return not operand
        if op is ast.UAdd:
            return +(_unwrap(operand, state))
        if op is ast.USub:
            return -(_unwrap(operand, state))
        if op is ast.Invert:
            return ~(_unwrap(operand, state))
        raise WebComPyException(f"Unsupported unary operator: {type(node.op).__name__}")

    if isinstance(node, ast.BinOp):
        left = _eval_node(node.left, scope, state)
        op = type(node.op)

        if op is ast.BitOr:
            if isinstance(node.right, ast.Name) and node.right.id in FILTERS:
                return FILTERS[node.right.id](_unwrap(left, state))
            if (
                isinstance(node.right, ast.Call)
                and isinstance(node.right.func, ast.Name)
                and node.right.func.id in FILTERS
            ):
                filter_fn = FILTERS[node.right.func.id]
                args = [_unwrap(_eval_node(a, scope, state), state) for a in node.right.args]
                kwargs = {
                    (str(kw.arg) if kw.arg else ""): _unwrap(_eval_node(kw.value, scope, state), state)
                    for kw in node.right.keywords
                }
                return filter_fn(_unwrap(left, state), *args, **kwargs)

        right = _eval_node(node.right, scope, state)
        left_u = _unwrap(left, state)
        right_u = _unwrap(right, state)

        fn = _BINOPS.get(op)
        if fn is None:
            raise WebComPyException(f"Unsupported binary operator: {type(node.op).__name__}")
        return fn(left_u, right_u)

    if isinstance(node, ast.BoolOp):
        last = _eval_node(node.values[0], scope, state)
        last_u = _unwrap(last, state)
        if type(node.op) is ast.Or and last_u:
            return last_u
        if type(node.op) is ast.And and not last_u:
            return last_u
        for val_node in node.values[1:]:
            last = _eval_node(val_node, scope, state)
            last_u = _unwrap(last, state)
            if type(node.op) is ast.Or and last_u:
                return last_u
            if type(node.op) is ast.And and not last_u:
                return last_u
        return last_u

    if isinstance(node, ast.Compare):
        left = _unwrap(_eval_node(node.left, scope, state), state)
        op = type(node.ops[0])
        right = _unwrap(_eval_node(node.comparators[0], scope, state), state)
        result = _compare_op(op, left, right)
        for i in range(1, len(node.ops)):
            left = right
            op = type(node.ops[i])
            right = _unwrap(_eval_node(node.comparators[i], scope, state), state)
            result = result and _compare_op(op, left, right)
            if not result:
                return False
        return result

    if isinstance(node, ast.IfExp):
        cond = _unwrap(_eval_node(node.test, scope, state), state)
        if cond:
            return _eval_node(node.body, scope, state)
        return _eval_node(node.orelse, scope, state)

    if isinstance(node, ast.Call):
        func = _eval_node(node.func, scope, state)
        func = _unwrap(func, state)
        args = [_unwrap(_eval_node(a, scope, state), state) for a in node.args]
        kwargs = {
            (str(kw.arg) if kw.arg else ""): _unwrap(_eval_node(kw.value, scope, state), state) for kw in node.keywords
        }
        return func(*args, **kwargs)

    raise WebComPyException(f"Unexpected expression node type: {type(node).__name__}")


def _compare_op(op_type: type, left: Any, right: Any) -> bool:
    if op_type is ast.In:
        return left in right
    if op_type is ast.NotIn:
        return left not in right
    if op_type is ast.Is:
        return left is right
    if op_type is ast.IsNot:
        return left is not right
    fn = _CMP_OPS.get(op_type)
    if fn is None:
        raise WebComPyException(f"Unsupported comparison operator: {op_type.__name__}")
    return fn(left, right)


FILTERS: dict[str, Callable[..., Any]] = {
    "upper": lambda v: str(v).upper(),
    "lower": lambda v: str(v).lower(),
    "title": lambda v: str(v).title(),
    "capitalize": lambda v: str(v).capitalize(),
    "trim": lambda v: str(v).strip(),
    "length": lambda v: len(v),
    "join": lambda v, sep="": sep.join(str(x) for x in v),
    "default": lambda v, d="": d if v is None else v,
    "replace": lambda v, old, new: str(v).replace(old, new),
    "round": lambda v, ndigits=None: round(v, ndigits),
    "int": lambda v: int(v),
    "float": lambda v: float(v),
    "string": lambda v: str(v),
    "first": lambda v: v[0],
    "last": lambda v: v[-1],
    "abs": lambda v: abs(v),
}

"""Utilities including a very conservative safe_eval."""
import ast
from typing import Any, Dict

ALLOWED_NODES = (
    ast.Expression, ast.BoolOp, ast.BinOp, ast.UnaryOp, ast.IfExp,
    ast.Compare, ast.Call, ast.Name, ast.Load, ast.Constant,
    ast.And, ast.Or, ast.NotEq, ast.Eq, ast.Gt, ast.GtE, ast.Lt, ast.LtE,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.Pow, ast.USub,
)

def _is_safe(node: ast.AST) -> bool:
    return all(isinstance(n, ALLOWED_NODES) for n in ast.walk(node))

def safe_eval(expr: str, context: Dict[str, Any]) -> Any:
    """Evaluate simple boolean/numeric expressions with a restricted AST."""
    tree = ast.parse(expr, mode='eval')
    if not _is_safe(tree):
        raise ValueError("Disallowed expression in safe_eval")
    return eval(compile(tree, '<safe_eval>', 'eval'), {'__builtins__': {}}, dict(context))

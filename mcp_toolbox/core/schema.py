"""Auto-generate JSON Schema from Python type hints."""

import inspect
import re
from typing import Any, get_type_hints


# Python type -> JSON Schema type mapping
TYPE_MAP = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
    list: {"type": "array"},
    dict: {"type": "object"},
}


def _python_type_to_schema(tp) -> dict:
    """Convert a Python type annotation to a JSON Schema dict."""
    # Direct type match
    if tp in TYPE_MAP:
        return TYPE_MAP[tp].copy()

    # Handle NoneType
    if tp is type(None):
        return {"type": "null"}

    # Handle generic types (list[X], dict[X, Y])
    origin = getattr(tp, "__origin__", None)
    args = getattr(tp, "__args__", None)

    if origin is list:
        if args:
            items_schema = _python_type_to_schema(args[0])
            return {"type": "array", "items": items_schema}
        return {"type": "array"}

    if origin is dict:
        schema = {"type": "object"}
        if args and len(args) == 2:
            schema["additionalProperties"] = _python_type_to_schema(args[1])
        return schema

    # Handle Optional[X] (Union[X, None])
    if origin is type(None) or (hasattr(tp, "__union_params__")):
        return {}

    # Handle Union types
    union_args = getattr(tp, "__args__", None)
    if union_args and type(None) in union_args:
        # Optional[X] = Union[X, None]
        inner = [a for a in union_args if a is not type(None)]
        if inner:
            return _python_type_to_schema(inner[0])

    # Fallback
    return {"type": "string"}


def _parse_docstring_args(docstring: str) -> dict:
    """Extract Args section from Google/NumPy style docstrings.

    Returns dict of {arg_name: description}.
    """
    if not docstring:
        return {}

    args = {}

    # Google style: Args:\n    name: description
    google_match = re.search(r"Args:\s*\n((?:\s+\w+:.+\n?)+)", docstring)
    if google_match:
        block = google_match.group(1)
        for match in re.finditer(r"^\s+(\w+):\s*(.+)$", block, re.MULTILINE):
            args[match.group(1)] = match.group(2).strip()
        return args

    # NumPy style: Parameters\n----------\nname : type\n    description
    numpy_match = re.search(r"Parameters\s*\n-+\s*\n((?:\w+\s*:.+\n(?:\s+.+\n?)+)+)", docstring)
    if numpy_match:
        block = numpy_match.group(1)
        for match in re.finditer(r"^(\w+)\s*:\s*\w+\s*\n(\s+.+)", block, re.MULTILINE):
            args[match.group(1)] = match.group(2).strip()
        return args

    return args


def generate_schema(func, param_descriptions: dict = None, **kwargs) -> dict:
    """Generate a JSON Schema from a function's type hints and docstring.

    Args:
        func: The function to generate schema for
        param_descriptions: Explicit {param_name: description} overrides
        **kwargs: Additional metadata (ignored here)

    Returns a dict like:
        {"type": "object", "properties": {...}, "required": [...]}
    """
    sig = inspect.signature(func)
    docstring_args = _parse_docstring_args(func.__doc__ or "")

    # Merge: explicit descriptions override docstring
    all_descriptions = {**docstring_args, **(param_descriptions or {})}

    # Get type hints (may fail for some builtins)
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {}

    properties = {}
    required = []

    for param_name, param in sig.parameters.items():
        # Skip **kwargs
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            continue
        # Skip *args
        if param.kind == inspect.Parameter.VAR_POSITIONAL:
            continue

        # Get type schema
        tp = hints.get(param_name)
        if tp:
            prop_schema = _python_type_to_schema(tp)
        else:
            prop_schema = {}

        # Add description (explicit > docstring)
        if param_name in all_descriptions:
            prop_schema["description"] = all_descriptions[param_name]

        # Add default value if present
        if param.default is not inspect.Parameter.empty:
            prop_schema["default"] = param.default
        else:
            required.append(param_name)

        properties[param_name] = prop_schema

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }

"""
Minimal TOON encoder for Python objects.

This encoder targets the TOON format per public overview/spec concepts:
- JSON data model (objects, arrays, primitives)
- Indentation for nested objects
- Explicit array lengths `[N]`
- Tabular arrays of uniform objects `{fields}` with comma-separated rows
- Minimal quoting; primitives rendered as-is where safe

Note: This is a lightweight implementation intended for generating LLM-friendly
inputs. For strict conformance and decoding, prefer official libraries when
available.
"""
from typing import Any, Dict, List, Tuple

INDENT = "  "  # two spaces per level


def _is_primitive(value: Any) -> bool:
    return isinstance(value, (str, int, float, bool)) or value is None


def _stringify(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    # Strings: minimize quoting; escape newlines/tabs
    s = str(value)
    s = s.replace("\n", " ").replace("\t", " ")
    # If contains commas or leading/trailing spaces, wrap in quotes
    if "," in s or s.strip() != s:
        return f'"{s}"'
    return s


def _uniform_object_array(arr: List[Dict[str, Any]]) -> Tuple[bool, List[str]]:
    if not arr:
        return True, []
    if not all(isinstance(x, dict) for x in arr):
        return False, []
    # Determine stable field order: intersection of keys across all items
    common_keys = set(arr[0].keys())
    for item in arr[1:]:
        common_keys &= set(item.keys())
    # If some items missing keys, still encode common subset (spec favors consistency)
    fields = list(common_keys)
    # Keep order stable by sorting
    fields.sort()
    return True, fields


def _encode_key_value(key: str, value: Any, indent_level: int, lines: List[str]):
    indent = INDENT * indent_level
    if isinstance(value, dict):
        lines.append(f"{indent}{key}:")
        _encode_object(value, indent_level + 1, lines)
    elif isinstance(value, list):
        _encode_array(key, value, indent_level, lines)
    else:
        lines.append(f"{indent}{key}: {_stringify(value)}")


def _encode_object(obj: Dict[str, Any], indent_level: int, lines: List[str]):
    # Preserve key order as insertion order (Python 3.7+)
    for k, v in obj.items():
        _encode_key_value(k, v, indent_level, lines)


def _encode_array(name: str, arr: List[Any], indent_level: int, lines: List[str]):
    indent = INDENT * indent_level
    n = len(arr)
    # Empty array
    if n == 0:
        lines.append(f"{indent}{name}[0]:")
        return

    # Uniform array of objects → tabular
    if all(isinstance(x, dict) for x in arr):
        uniform, fields = _uniform_object_array(arr)  # returns common keys
        if uniform and fields:
            header = f"{indent}{name}[{n}]{{{','.join(fields)}}}:"
            lines.append(header)
            row_indent = INDENT * (indent_level + 1)
            for item in arr:
                # Row values follow field order; missing fields become empty
                values = [
                    _stringify(item.get(f)) if f in item and item.get(f) is not None else ""
                    for f in fields
                ]
                lines.append(f"{row_indent}{','.join(values)}")
            return

    # Non-uniform or primitives → inline if primitives, else nested list lines
    if all(_is_primitive(x) for x in arr):
        values = ",".join(_stringify(x) for x in arr)
        lines.append(f"{indent}{name}[{n}]: {values}")
    else:
        lines.append(f"{indent}{name}[{n}]:")
        for item in arr:
            if isinstance(item, dict):
                _encode_object(item, indent_level + 1, lines)
            elif isinstance(item, list):
                _encode_array("-", item, indent_level + 1, lines)
            else:
                lines.append(f"{INDENT * (indent_level + 1)}- {_stringify(item)}")


def encode_to_lines(data: Any) -> List[str]:
    """Encode a Python object into TOON lines."""
    lines: List[str] = []
    if isinstance(data, dict):
        _encode_object(data, 0, lines)
    elif isinstance(data, list):
        _encode_array("root", data, 0, lines)
    else:
        lines.append(f"value: {_stringify(data)}")
    return lines

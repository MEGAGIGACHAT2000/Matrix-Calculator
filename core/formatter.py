from .matrix import Matrix, _fmt

def fmt_number(v) -> str:
    return _fmt(v)

def matrix_to_list(m: Matrix) -> list:
    return [[_fmt(v) for v in row] for row in m.data]

def format_result(result) -> dict:
    if isinstance(result, Matrix):
        return {
            "type":   "matrix",
            "shape":  list(result.shape),
            "value":  matrix_to_list(result),
            "pretty": str(result),
        }

    if isinstance(result, list):
        return {
            "type":   "vector",
            "value":  [_fmt(x) for x in result],
            "pretty": "( " + ", ".join(_fmt(x) for x in result) + " )",
        }

    if isinstance(result, bool):
        return {
            "type":   "scalar",
            "value":  "True" if result else "False",
            "pretty": "True" if result else "False",
        }

    if isinstance(result, (int, float, complex)):
        return {
            "type":   "scalar",
            "value":  _fmt(result),
            "pretty": _fmt(result),
        }

    return {
        "type":   "raw",
        "value":  str(result),
        "pretty": str(result),
    }
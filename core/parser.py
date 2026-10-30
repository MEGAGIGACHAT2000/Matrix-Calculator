import ast
from .matrix import Matrix
from .exceptions import ParserError, OperationError

class ExpressionEvaluator:
    FUNCTIONS = {
        "det": lambda m: m.determinant(),
        "inv": lambda m: m.inverse(),
        "rank": lambda m: m.rank(),
        "trace": lambda m: m.trance(),
        "transpose": lambda m: m.transpose(),
        "solve": lambda A, b: Matrix([[v] for v in Matrix.solve_gauss(A, b)]),
    }

    ATTRIBUTES = {
        "T": lambda m: m.transpose(),
        "det": lambda m: m.determinant(),
        "rank": lambda m: m.rank(),
        "trace": lambda m: m.trance(),
        "inv": lambda m: m.inverse(),
        "rows": lambda m: m.rows,
        "cols": lambda m: m.cols,
        "shape": lambda m: list(m.shape),
        "is_square": lambda m: m.is_square(),
    }

    def __init__(self):
        self.env: dict = {}
        self.history: list = []

    def run(self, source: str):
        if not source or not source.strip():
            raise ParserError("Пустое выражение")
        try:
            tree = ast.parse(source.strip(), mode="exec")
        except SyntaxError as e:
            raise ParserError(f"Синтаксическая ошибка: {e.msg} (строка {e.lineno})")
        last = None
        for node in tree.body:
            last = self._eval(node)
            self.history.append((ast.unparse(node), last))
        return last

    def reset(self):
        self.env.clear()
        self.history.clear()

    def _eval(self, node):
        if isinstance(node, ast.Expr):
            return self._eval(node.value)
        if isinstance(node, ast.Assign):
            if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
                raise ParserError("Можно присваивать только в переменную: A = ...")
            name = node.targets[0].id
            value = self._eval(node.value)
            self.env[name] = value
            return value
        if isinstance(node, ast.AugAssign):
            if not isinstance(node.target, ast.Name):
                raise ParserError("Расширенное присваивание только для переменных")
            name = node.target.id
            if name not in self.env:
                raise ParserError(f"Неизвестная переменная: {name}")
            current = self.env[name]
            operand = self._eval(node.value)
            result = self._apply_binop(node.op, current, operand)
            self.env[name] = result
            return result
        if isinstance(node, ast.BinOp):
            left = self._eval(node.left)
            right = self._eval(node.right)
            return self._apply_binop(node.op, left, right)
        if isinstance(node, ast.UnaryOp):
            val = self._eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -val
            if isinstance(node.op, ast.UAdd):
                return val
            raise ParserError("Недопустимый унарный оператор")
        if isinstance(node, ast.Name):
            if node.id in self.env:
                return self.env[node.id]
            raise ParserError(f"Неизвестная переменная: {node.id}")
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                raise ParserError("Логические константы не поддерживаются")
            if isinstance(node.value, (int, float, complex)):
                return node.value
            raise ParserError(f"Недопустимая константа: {node.value!r}")
        if isinstance(node, (ast.List, ast.Tuple)):
            return self._eval_literal(node)
        if isinstance(node, ast.Call):
            return self._eval_call(node)
        if isinstance(node, ast.Attribute):
            base = self._eval(node.value)
            attr = node.attr
            if not isinstance(base, Matrix):
                raise ParserError(f"Свойство .{attr} доступно только для матриц")
            if attr not in self.ATTRIBUTES:
                raise ParserError(f"Неизвестное свойство: .{attr}")
            return self.ATTRIBUTES[attr](base)
        raise ParserError(f"Неподдерживаемая конструкция: {type(node).__name__}")

    def _eval_literal(self, node) -> Matrix:
        items = [self._eval(el) for el in node.elts]
        if not items:
            raise ParserError("Пустой список недопустим")
        if all(isinstance(x, (int, float, complex)) for x in items):
            return Matrix(items)
        if all(isinstance(x, Matrix) and x.rows == 1 for x in items):
            return Matrix([row.data[0] for row in items])
        raise ParserError("Некорректный литерал матрицы (смешанные типы или размеры)")

    def _eval_call(self, node):
        if not isinstance(node.func, ast.Name):
            raise ParserError("Функции вызываются только по имени")
        name = node.func.id
        if name not in self.FUNCTIONS:
            raise ParserError(f"Неизвестная функция: {name}")
        args = [self._eval(a) for a in node.args]
        try:
            return self.FUNCTIONS[name](*args)
        except OperationError:
            raise
        except TypeError as e:
            raise ParserError(f"Неверные аргументы для {name}(): {e}")
        except Exception as e:
            raise OperationError(f"{name}: {e}")

    def _apply_binop(self, op, left, right):
        try:
            if isinstance(op, ast.Add): return left + right
            if isinstance(op, ast.Sub): return left - right
            if isinstance(op, ast.Mult): return left * right
            if isinstance(op, ast.Div): return left / right
            if isinstance(op, ast.MatMult): return left @ right
            if isinstance(op, ast.Pow): return left ** right
        except OperationError:
            raise
        except ZeroDivisionError:
            raise OperationError("Деление на ноль")
        except TypeError as e:
            raise OperationError(f"Несовместимые операнды: {e}")
        raise ParserError(f"Оператор {type(op).__name__} не поддерживается")
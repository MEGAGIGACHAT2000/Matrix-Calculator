import random
from .exceptions import OperationError

def _clean(v, eps: float = 1e-10):
    if isinstance(v, complex):
        return v
    if abs(v) < eps:
        return 0
    if isinstance(v, float) and abs(v - round(v)) < eps:
        return int(round(v))
    return v

def _fmt(v) -> str:
    if isinstance(v, complex):
        re, im = v.real, v.imag
        if abs(im) < 1e-12:
            return _fmt(re)
        if abs(re) < 1e-12:
            return f"{_fmt(im)}j"
        sign = "+" if im >= 0 else "-"
        return f"{_fmt(re)}{sign}{_fmt(abs(im))}j"
    if isinstance(v, float):
        if v.is_integer():
            return str(int(v))
        return f"{v:.6g}"
    return str(v)

class Matrix:
    def __init__(self, data):
        if isinstance(data, (list, tuple)):
            data = list(data)
        else:
            raise OperationError(f"Ожидался list/tuple, получен {type(data).__name__}")

        if len(data) == 0:
            raise OperationError("Матрица не может быть пустой")

        if not isinstance(data[0], (list, tuple)):
            data = [list(data)]

        data = [list(row) for row in data]

        lengths = {len(row) for row in data}
        if len(lengths) != 1:
            raise OperationError(
                f"Строки разной длины: {[len(r) for r in data]}"
            )
        if any(len(row) == 0 for row in data):
            raise OperationError("Строки не могут быть пустыми")

        for i, row in enumerate(data):
            for j, val in enumerate(row):
                if not isinstance(val, (int, float, complex)):
                    raise OperationError(f"Элемент [{i}][{j}]={val!r} не число")

        self._data = data
        self._rows = len(data)
        self._cols = len(data[0])

    @classmethod
    def zeros(cls, rows: int, cols: int) -> "Matrix":
        return cls([[0] * cols for _ in range(rows)])

    @classmethod
    def ones(cls, rows: int, cols: int) -> "Matrix":
        return cls([[1] * cols for _ in range(rows)])

    @classmethod
    def identity(cls, size: int) -> "Matrix":
        return cls([[1 if i == j else 0 for j in range(size)]
                    for i in range(size)])

    @classmethod
    def random(cls, rows: int, cols: int, lo: int = -9, hi: int = 9) -> "Matrix":
        return cls([[random.randint(lo, hi) for _ in range(cols)]
                    for _ in range(rows)])

    #свойства
    @property
    def rows(self) -> int: return self._rows

    @property
    def cols(self) -> int: return self._cols

    @property
    def shape(self) -> tuple: return (self._rows, self._cols)

    @property
    def size(self) -> int: return self._rows * self._cols

    @property
    def data(self) -> list: return [row[:] for row in self._data]

    @property
    def T(self) -> "Matrix": return self.transpose()

    #математические методы
    def __str__(self) -> str:
        if self.size == 0:
            return "Matrix([])"
        strs = [[_fmt(v) for v in row] for row in self._data]
        w = max(len(s) for row in strs for s in row)

        lines = ["| " + " ".join(s.rjust(w) for s in row) + " |" for row in strs]
        total = len(lines[0])
        top = "+" + "-" * (total - 2) + "+"
        botton = "+" + "-" * (total - 2) + "+"
        return "\n".join([top] + lines + [botton])

    def __repr__(self) -> str:
        return f"Matrix({self._data})"

    def __eq__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        return self._data == other._data

    def __hash__(self):
        return hash((self._rows, self._cols,
                     tuple(tuple(r) for r in self._data)))

    def __len__(self): return self._rows
    def __iter__(self): return iter(self._data)

    def __getitem__(self, idx):
        if isinstance(idx, tuple):
            i, j = idx
            return self._data[i][j]
        return self._data[idx]

    def __setitem__(self, idx, val):
        if isinstance(idx, tuple):
            i, j = idx
            self._data[i][j] = val
        else:
            raise OperationError("Используйте A[i, j] = value")

    def __neg__(self) -> "Matrix":
        return Matrix([[-v for v in row] for row in self._data])

    def __add__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        self._check_same(other, "+")
        return Matrix([[self._data[i][j] + other._data[i][j]
                        for j in range(self._cols)]
                       for i in range(self._rows)])

    def __sub__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        self._check_same(other, "-")
        return Matrix([[self._data[i][j] - other._data[i][j]
                        for j in range(self._cols)]
                       for i in range(self._rows)])

    def __mul__(self, k):
        if isinstance(k, Matrix):
            return NotImplemented
        if not isinstance(k, (int, float, complex)):
            return NotImplemented
        return Matrix([[v * k for v in row] for row in self._data])

    __rmul__ = __mul__

    def __truediv__(self, k):
        if isinstance(k, Matrix):
            return NotImplemented
        if k == 0:
            raise OperationError("Деление на ноль")
        return Matrix([[v / k for v in row] for row in self._data])

    def __matmul__(self, other):
        if not isinstance(other, Matrix):
            return NotImplemented
        if self._cols != other._rows:
            raise OperationError(
                f"Несовместимые размеры для @: {self.shape} и {other.shape}"
            )
        n, m, p = self._rows, self._cols, other._cols
        result = [[0] * p for _ in range(n)]
        for i in range(n):
            for k in range(m):
                aik = self._data[i][k]
                if aik == 0:
                    continue
                for j in range(p):
                    result[i][j] += aik * other._data[k][j]
        return Matrix(result)

    def __pow__(self, n):
        if not self.is_square():
            raise OperationError("Возведение в степень - только для квадратных")
        if not isinstance(n, int) or n < 0:
            raise OperationError("Степень должна быть неотрицательным целым")
        result = Matrix.identity(self._rows)
        base = self.copy()
        while n > 0:
            if n & 1:
                result = result @ base
            base = base @ base
            n >>= 1
        return result

    #вспомагательная функция
    def _check_same(self, other, op):
        if self.shape != other.shape:
            raise OperationError(f"Размеры не совпадают: {self.shape} {op} {other.shape}")

    #проверки
    def is_square(self) -> bool: return self._rows == self._cols
    def is_zero(self) -> bool: return all(v == 0 for row in self._data for v in row)

    def is_identity(self) -> bool:
        if not self.is_square():
            return False
        return all(self._data[i][j] == (1 if i == j else 0)
                   for i in range(self._rows)
                   for j in range(self._cols))

    def is_symmetric(self) -> bool:
        if not self.is_square():
            return False
        return all(self._data[i][j] == self._data[j][i]
                   for i in range(self._rows)
                   for j in range(i + 1, self._cols))

    #улититы
    def copy(self) -> "Matrix":
        return Matrix([row[:] for row in self._data])

    def get_row(self, i: int) -> list:
        if not 0 <= i < self._rows:
            raise OperationError(f"Строка {i} вне [0,{self._rows})")
        return self._data[i][:]

    def get_col(self, j: int) -> list:
        if not 0 <= j < self._cols:
            raise OperationError(f"Столбец {j} вне [0,{self._cols})")
        return [self._data[i][j] for i in range(self._rows)]

    def get_diagonal(self) -> list:
        n = min(self._rows, self._cols)
        return [self._data[i][i] for i in range(n)]

    def to_list(self) -> list:
        return [row[:] for row in self._data]

    def to_numpy(self):
        import numpy as np
        return np.array(self._data)

    #линейная алгебра
    def transpose(self) -> "Matrix":
        return Matrix([[self._data[i][j] for i in range(self._rows)]
                       for j in range(self._cols)])

    def minor(self, i: int, j: int) -> "Matrix":
        return Matrix([[self._data[r][c]
                        for c in range(self._cols) if c != j]
                       for r in range(self._rows) if r != i])

    def trance(self):
        if not self.is_square():
            raise OperationError("Следующее только для квадратных")
        return _clean(sum(self.get_diagonal()))

    def determinant(self):
        if not self.is_square():
            raise OperationError("Определитель только для квадратных матриц")
        n = self._rows
        if n == 1:
            return _clean(self._data[0][0])
        if n == 2:
            a, b = self._data[0]
            c, d = self._data[1]
            return _clean(a * d - b * c)
        if n == 3:
            a, b, c = self._data[0]
            d, e, f = self._data[1]
            g, h, i = self._data[2]
            return _clean(
                a * (e * i - f * h)
                - b * (d * i - f * g)
                + c * (d * h - e * g)
            )
        #с частичным выбором ведущего
        mat = [row[:] for row in self._data]
        det = 1
        for i in range(n):
            pivot = max(range(i, n), key = lambda r: abs(mat[r][i]))
            if abs(mat[pivot][i]) < 1e-12:
                return 0
            if pivot != i:
                mat[i], mat[pivot] = mat[pivot], mat[i]
                det = -det
            det *= mat[i][i]
            for k in range(i + 1, n):
                f = mat[k][i] / mat[i][i]
                for j in range(i, n):
                    mat[k][j] -= f * mat[i][j]
        return _clean(det)

    def inverse(self) -> "Matrix":
        if not self.is_square():
            raise OperationError("Обратная только для квадратных")
        n = self._rows
        aug = [self._data[i][:] + [1 if i == j else 0 for j in range(n)]
               for i in range(n)]

        for i in range(n):
            pivot = max(range(i, n), key=lambda r: abs(aug[r][i]))
            if abs(aug[pivot][i]) < 1e-12:
                raise OperationError("Матрица вырождена — обратной нет")
            aug[i], aug[pivot] = aug[pivot], aug[i]
            lead = aug[i][i]
            aug[i] = [v / lead for v in aug[i]]
            for k in range(n):
                if k == i:
                    continue
                f = aug[k][i]
                if f != 0:
                    aug[k] = [aug[k][j] - f * aug[i][j]
                              for j in range(2 * n)]

        inv = [[_clean(aug[i][j]) for j in range(n, 2 * n)]
               for i in range(n)]
        return Matrix(inv)

    def rank(self) -> int:
        mat = [row[:] for row in self._data]
        m, n = self._rows, self._cols
        r = 0
        for col in range(n):
            pivot = None
            for i in range(r, m):
                if abs(mat[i][col]) > 1e-10 :
                    pivot = i
                    break
            if pivot is None:
                continue
            mat[r], mat[pivot] = mat[pivot], mat[r]
            lead = mat[r][col]
            mat[r] = [v / lead for v in mat[r]]
            for i in range(m):
                if i != r and abs(mat[i][col]) > 1e-10:
                    f = mat[i][col]
                    mat[i] = [mat[i][j] - f * mat[r][j]
                              for j in range(n)]
            r += 1
            if r == m:
                break
        return r

    #решение слау
    @staticmethod
    def _to_vector(b, n: int) -> list:
        if isinstance(b, Matrix):
            if b.rows == 1:
                vec = b.data[0]
            elif b.cols == 1:
                vec = [row[0] for row in b.data]
            else:
                raise OperationError("Вектор b должен быть строкой или столбцом")
        else:
            vec = list(b)

        if len(vec) != n:
            raise OperationError(f"Размер b ({len(vec)}) не совпадает с A ({n})")
        return vec

    @staticmethod
    def solve_gauss(A: "Matrix", b) -> list:
        if not A.is_square():
            raise OperationError("Метод Гаусса требует квадратной матрицы")
        n = A.rows
        b = Matrix._to_vector(b, n)
        aug = [A._data[i][:] + [b[i]] for i in range(n)]
        
        # Прямой ход
        for i in range(n):
            pivot = max(range(i, n), key=lambda r: abs(aug[r][i]))
            if abs(aug[pivot][i]) < 1e-12:
                raise OperationError("Система не имеет единственного решения")
            aug[i], aug[pivot] = aug[pivot], aug[i]
            for k in range(i + 1, n):
                f = aug[k][i] / aug[i][i]
                for j in range(i, n + 1):
                    aug[k][j] -= f * aug[i][j]
                    
        # Обратный ход
        x = [0] * n
        for i in range(n - 1, -1, -1):
            s = aug[i][n]
            for j in range(i + 1, n):
                s -= aug[i][j] * x[j]
            x[i] = _clean(s / aug[i][i])
        return x

    @staticmethod
    def solve_cramer(A: "Matrix", b) -> list:
        if not A.is_square():
            raise OperationError("Метод Крамера только для квадратных")
        n = A.rows
        b = Matrix._to_vector(b, n)
        detA = A.determinant()
        if abs(detA) < 1e-12:
            raise OperationError("det(A) = 0, метод Крамера неприменим")
        x = []
        for j in range(n):
            Aj = A.copy()
            for i in range(n):
                Aj[i, j] = b[i]
            x.append(_clean(Aj.determinant() / detA))
        return x

    @staticmethod
    def solve_inverse(A: "Matrix", b) -> list:
        n = A.rows
        b = Matrix._to_vector(b, n)
        inv = A.inverse()
        b_mat = Matrix([[v] for v in b])
        res = inv @ b_mat
        return [_clean(res[i, 0]) for i in range(res.rows)]
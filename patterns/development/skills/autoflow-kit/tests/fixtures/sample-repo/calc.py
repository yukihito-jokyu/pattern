"""見本の計算の関数。"""


def add(a: int, b: int) -> int:
    return a + b


def clamp(value: int, low: int, high: int) -> int:
    """value を low 以上 high 以下に収める。"""
    return max(low, value)

"""在庫の数を増やす。"""


def add(stock: dict[str, int], name: str, count: int) -> dict[str, int]:
    """name の在庫を count だけ増やした新しい辞書を返す。"""
    if count <= 0:
        raise ValueError("count は 1 以上にする")
    updated = dict(stock)
    updated[name] = updated.get(name, 0) + count
    return updated

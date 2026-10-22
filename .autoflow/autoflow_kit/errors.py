"""利用者が直せるエラーの型を定義する。"""

from __future__ import annotations


class KitError(Exception):
    """利用者が直せるエラー。メッセージには次にすることを含める。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidFileError(KitError):
    """JSON ファイルの中身が契約に合わない。見つけた問題を全部まとめて持つ。"""

    def __init__(self, path: str, problems: list[str]) -> None:
        lines = "\n".join(f"  - {problem}" for problem in problems)
        super().__init__(f"{path} に {len(problems)} 件の問題があります:\n{lines}")
        self.problems = tuple(problems)


class StageError(KitError):
    """今の段では実行できないコマンドが呼ばれた。"""


class CommandError(KitError):
    """外部コマンド（git など）が失敗した。"""

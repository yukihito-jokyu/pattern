"""gha が投げる例外。CLI はこの2つだけを捕まえて終了コード2にする。"""

from __future__ import annotations


class UsageError(Exception):
    """引数や前提（git のリポジトリ、ファイルの有無）が満たされていない。"""


class ToolError(Exception):
    """外部コマンドが見つからない、または想定外の出力を返した。"""

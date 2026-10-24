"""利用者が直せるエラーの型。cli が `エラー: ` を付けて標準エラーに出す（ERR-01）。"""

from __future__ import annotations


class KitError(Exception):
    """補助 CLI のエラーの基底。"""


class InvalidFileError(KitError):
    """プロファイル、承認、記録などのファイルの形が正しくない。"""


class StageError(KitError):
    """段の前提（承認、前の段の完了）が満たされていない。"""


class CommandError(KitError):
    """外部コマンド（claude、git、事後の検査）を起動できない。"""


class LeakError(KitError):
    """答えに当たるもの（採点の印、leak_globs のパス）が証拠や候補に入った（STATE-04）。"""

"""見本のリポジトリの検査。inventory の全モジュールを読み込めることと、add の動きを確かめる。"""

import importlib
import pathlib
import sys

# 検査自体の生成物を、評価対象の実装差分へ混ぜない。
sys.dont_write_bytecode = True

for path in sorted(pathlib.Path("inventory").glob("*.py")):
    importlib.import_module(f"inventory.{path.stem}")

from inventory import stock

if stock.add({"apple": 1}, "apple", 2) != {"apple": 3}:
    sys.exit("add が在庫を足していない")
print("check: ok")

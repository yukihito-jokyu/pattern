"""layout のテスト。slot と run の id、置き場の決まり、glob の当て方を確かめる。"""

from __future__ import annotations

import unittest
from pathlib import Path

from forge_kit import layout
from forge_kit.errors import KitError


class LayoutTest(unittest.TestCase):
    def test_make_slot(self) -> None:
        self.assertEqual(layout.make_slot("baseline", 1).name, "round-1-baseline")
        self.assertEqual(layout.make_slot("final", 5), layout.Slot("final", 0))
        with self.assertRaises(KitError):
            layout.make_slot("baseline", 2)
        with self.assertRaises(KitError):
            layout.make_slot("candidate", 0)

    def test_make_layout(self) -> None:
        where = layout.make_layout(Path("/repo"), "dev-orch", Path("/tmp/copies"))
        self.assertEqual(where.charter_path, Path("/repo/.forge/targets/dev-orch/charter.json"))
        slot = layout.make_slot("baseline", 1)
        self.assertEqual(where.copy_dir(slot, "T1-a1"), Path("/tmp/copies/dev-orch/round-1-baseline/T1-a1"))
        with self.assertRaises(KitError):
            layout.make_layout(Path("/repo"), "Dev_Orch", Path("/tmp"))

    def test_run_id_and_is_matched(self) -> None:
        self.assertEqual(layout.run_id("T1", 2), "T1-a2")
        self.assertTrue(layout.is_matched(".github/workflows/ci.yml", (".github/*",)))
        self.assertFalse(layout.is_matched("src/a.py", ("check.py",)))


if __name__ == "__main__":
    unittest.main()

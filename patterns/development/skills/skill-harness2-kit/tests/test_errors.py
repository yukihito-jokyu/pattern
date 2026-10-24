"""errors のテスト。"""

from __future__ import annotations

import unittest

from h2_kit import errors


class ErrorsTest(unittest.TestCase):
    def test_every_error_is_a_kit_error(self) -> None:
        for kind in (errors.InvalidFileError, errors.StageError, errors.CommandError, errors.LeakError):
            with self.subTest(kind=kind.__name__):
                self.assertTrue(issubclass(kind, errors.KitError))

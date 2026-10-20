"""design のテスト。design-schema.md の例が検査を通り、役・手順・人の関所の関係の誤りが落ちることを確かめる。"""

from __future__ import annotations

import json
import re
import unittest

from forge_kit import design, fsops
from forge_kit.errors import InvalidFileError
from tests import support

SCHEMA_MD = support.FIXTURES.parent.parent / "kit/claude/skills/forge-build/references/design-schema.md"


def example() -> dict[str, object]:
    blocks = re.findall(r"```json\n(.*?)```", fsops.read_text(SCHEMA_MD), re.S)
    value = json.loads(blocks[0])
    assert isinstance(value, dict)
    return value


class DesignTest(unittest.TestCase):
    def test_schema_example(self) -> None:
        found = design.parse(example(), "example", skill_name="dev-orch")
        self.assertEqual([role.role for role in found.roles], ["explorer", "implementer", "reviewer"])

    def test_checkpoints(self) -> None:
        data = example()
        data["checkpoints"] = [{"step": "S2", "question": "q", "default": "d"}]
        with self.assertRaises(InvalidFileError) as caught:
            design.parse(data, "example", skill_name="dev-orch")
        self.assertIn("orchestrator の手順にしてください", caught.exception.message)

    def test_steps(self) -> None:
        data = example()
        steps = data["steps"]
        assert isinstance(steps, list)
        steps[0]["id"] = "S9"
        with self.assertRaises(InvalidFileError) as caught:
            design.parse(data, "example", skill_name="dev-orch")
        self.assertIn("S1 から順に", caught.exception.message)

    def test_roles(self) -> None:
        data = example()
        roles = data["roles"]
        assert isinstance(roles, list)
        roles[0]["tools"] = ["Agent"]
        with self.assertRaises(InvalidFileError):
            design.parse(data, "example", skill_name="dev-orch")
        roles[0]["tools"] = ["Read", "Grep", "Bash"]
        with self.assertRaises(InvalidFileError) as caught:
            design.parse(data, "example", skill_name="dev-orch")
        self.assertIn("Bash と Glob・Grep", caught.exception.message)
        with self.assertRaises(InvalidFileError):
            design.parse(example(), "example", skill_name="other")

    def test_digest(self) -> None:
        changed = example()
        changed["summary"] = "別の要約"
        self.assertNotEqual(design.digest(example()), design.digest(changed))
        self.assertEqual(design.digest(example()), design.digest(example()))


if __name__ == "__main__":
    unittest.main()

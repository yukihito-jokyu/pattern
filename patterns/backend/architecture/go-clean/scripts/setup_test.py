"""本物の設定を変更せず、一時コピーでsetupの重要な動作を検証する。"""

import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import setup
import yaml


class SetupTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="go-clean-setup-test-")
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "go-clean"
        shutil.copytree(setup.ROOT, self.root, ignore=shutil.ignore_patterns(".git", "bin", "__pycache__", ".venv", ".env", "setup-answers*.json"))

        # 利用先でDB名や資格情報を変更済みでも、テストは専用の既知の初期値で動かす。
        env = "APP_ADDR=:8080\nDB_PORT=5432\nDATABASE_URL=postgres://app:app@localhost:5432/app?sslmode=disable\nLOG_LEVEL=info\n"
        (self.root / ".env.example").write_text(env)
        compose_path = self.root / "compose.yaml"
        compose = yaml.safe_load(compose_path.read_text())
        compose["services"]["db"]["environment"] = {"POSTGRES_USER": "app", "POSTGRES_PASSWORD": "app", "POSTGRES_DB": "app"}
        compose["services"]["db"]["healthcheck"]["test"] = ["CMD-SHELL", "pg_isready -U app -d app"]
        compose_path.write_text(yaml.safe_dump(compose, sort_keys=False))

    def answer(self, level="important", name="answers.json"):
        path = self.root / name
        setup.init(self.root, level, path)
        return json.loads(path.read_text())

    def confirm(self, answer):
        answer["databaseTarget"] = "local"
        for key, review in answer["reviews"].items():
            if review["status"] == "unanswered":
                answer["reviews"][key] = {"status": "confirmed", "value": answer["settings"][key]}
        return answer

    def test_question_levels_and_unanswered_rejected(self):
        for level, count in [("important", 2), ("normal", 9), ("advanced", 178)]:
            answer = self.answer(level, f"answers-{level}.json")
            self.assertEqual(sum(r["status"] == "unanswered" for r in answer["reviews"].values()), count)
            with self.assertRaisesRegex(ValueError, "未回答"):
                setup.validate(self.root, answer)
            setup.validate(self.root, self.confirm(answer))

    def test_retained_change_and_post_confirmation_change_rejected(self):
        answer = self.confirm(self.answer())
        answer["settings"]["LOG_LEVEL"] = "debug"
        with self.assertRaisesRegex(ValueError, "範囲外"):
            setup.validate(self.root, answer)
        answer["reviews"]["LOG_LEVEL"] = {"status": "confirmed", "value": "debug"}
        setup.validate(self.root, answer)
        answer["settings"]["LOG_LEVEL"] = "error"
        with self.assertRaises(ValueError):
            setup.validate(self.root, answer)

    def test_module_imports_lint_env_and_idempotence(self):
        answer = self.answer()
        old = answer["settings"]["module"]
        answer["settings"]["module"] = "github.com/acme/service"
        self.confirm(answer)
        changed = setup.apply(self.root, answer)
        self.assertIn("go.mod", changed)
        self.assertIn(".golangci.yml", changed)
        self.assertIn("internal/usecase/user.go", changed)
        self.assertNotIn(old, (self.root / "internal/usecase/user.go").read_text())
        self.assertIn("github.com/acme/service/internal/domain", (self.root / ".golangci.yml").read_text())
        self.assertEqual((self.root / ".env").read_bytes(), (self.root / ".env.example").read_bytes())
        next_answer = self.confirm(self.answer(name="next.json"))
        self.assertEqual(setup.apply(self.root, next_answer), [])

    def test_env_preserves_comments_unknown_keys_and_missing_defaults(self):
        content = "# personal settings\nDATABASE_URL=postgres://app:app@localhost:5432/app?sslmode=disable\nCUSTOM=keep\n"
        (self.root / ".env").write_text(content)
        answer = self.confirm(self.answer())
        self.assertIsNone(answer["settings"]["LOG_LEVEL"])
        self.assertEqual(setup.apply(self.root, answer), [])
        self.assertEqual((self.root / ".env").read_text(), content)

    def test_stale_answer_and_new_module_reference_rejected(self):
        answer = self.confirm(self.answer())
        (self.root / "internal/domain/user/new.go").write_text('// ' + answer["settings"]["module"])
        with self.assertRaisesRegex(ValueError, "対象ファイル"):
            setup.apply(self.root, answer)
        self.assertFalse((self.root / ".env").exists())

    def test_invalid_values_do_not_write(self):
        original = self.confirm(self.answer("advanced"))
        for key, value in [("module", "bad path"), ("APP_ADDR", ":99999"), ("DB_PORT", "0"),
                           ("LOG_LEVEL", "verbose"), ("DATABASE_URL", 'postgres://x/$(touch-file)')]:
            answer = copy.deepcopy(original)
            answer["settings"][key] = value
            answer["reviews"][key] = {"status": "confirmed", "value": value}
            with self.assertRaises(ValueError):
                setup.apply(self.root, answer)
        self.assertFalse((self.root / ".env").exists())

    def test_initialization_does_not_overwrite(self):
        path = self.root / "answers.json"
        setup.init(self.root, "important", path)
        before = path.read_bytes()
        with self.assertRaises(FileExistsError):
            setup.init(self.root, "advanced", path)
        self.assertEqual(path.read_bytes(), before)

    def test_partial_write_failure_restores_files(self):
        answer = self.answer()
        answer["settings"]["module"] = "github.com/acme/service"
        self.confirm(answer)
        before = {name: (self.root / name).read_bytes() for name in setup.changes(self.root, answer) if (self.root / name).exists()}
        replace = setup.os.replace
        calls = 0

        def failing_replace(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated write failure")
            return replace(source, destination)

        with patch.object(setup.os, "replace", side_effect=failing_replace):
            with self.assertRaisesRegex(OSError, "simulated"):
                setup.apply(self.root, answer)
        for name, value in before.items():
            self.assertEqual((self.root / name).read_bytes(), value)
        self.assertFalse((self.root / ".env").exists())

    def test_symlink_env_rejected(self):
        (self.root / ".env").symlink_to(self.root / ".env.example")
        with self.assertRaisesRegex(ValueError, "シンボリック"):
            self.answer()


    def test_external_db_skips_local_questions_and_rejects_local_changes(self):
        answer = self.answer("normal")
        self.confirm(answer)
        answer["databaseTarget"] = "external"
        for entry in setup.catalog(self.root):
            key = entry["key"]
            if key == "DB_PORT" or entry["source"] == "compose.yaml":
                answer["reviews"][key] = {"status": "not-applicable", "value": answer["settings"][key], "reason": "既存DBを使うため"}
        setup.validate(self.root, answer)
        answer["settings"]["DB_PORT"] = "15432"
        answer["reviews"]["DB_PORT"] = {"status": "confirmed", "value": "15432"}
        with self.assertRaisesRegex(ValueError, "同梱Compose"):
            setup.validate(self.root, answer)

    def test_local_db_related_values_must_match(self):
        answer = self.confirm(self.answer())
        key = "compose.yaml::/services/db/environment/POSTGRES_DB"
        answer["settings"][key] = "other"
        answer["reviews"][key] = {"status": "confirmed", "value": "other"}
        with self.assertRaisesRegex(ValueError, "接続URL"):
            setup.validate(self.root, answer)

    def test_unlisted_setting_is_detected(self):
        path = self.root / ".vscode/settings.json"
        data = json.loads(path.read_text())
        data["new-setting"] = True
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "台帳"):
            setup.catalog(self.root)

    def test_extended_settings_apply_and_preserve_other_files(self):
        answer = self.confirm(self.answer())
        selected = {
            "internal/infra/database/database.go::/maxOpenConns": "30",
            "cmd/api/main.go::/readTimeout": "15 * time.Second",
            ".golangci.yml::/linters/settings/lll/line-length": 100,
            ".golangci.yml::/formatters/settings/golines/max-len": 100,
            ".vscode/settings.json::/files.insertFinalNewline": False,
            ".editorconfig::/*/indent_size": "4",
        }
        originals = {name: (self.root / name).read_bytes() for name in ["compose.yaml", ".claude/settings.json", ".env.example"]}
        for key, value in selected.items():
            answer["settings"][key] = value
            answer["reviews"][key] = {"status": "confirmed", "value": value}
        setup.apply(self.root, answer)
        actual = setup.read_settings(self.root)
        for key, value in selected.items():
            self.assertEqual(actual[key], value)
        for name, data in originals.items():
            self.assertEqual((self.root / name).read_bytes(), data)
        self.assertIn("# マジックナンバー", (self.root / ".golangci.yml").read_text())

    def test_protected_settings_and_architecture_checks_rejected(self):
        original = self.confirm(self.answer())
        for key, value in [("go.version", "1.28.0"), (".claude/settings.json::/permissions/allow", []),
                           (".golangci.yml::/linters/enable", ["unused"]),
                           ("cmd/api/main.go::/readTimeout", "time.Now()")]:
            answer = copy.deepcopy(original)
            answer["settings"][key] = value
            answer["reviews"][key] = {"status": "confirmed", "value": value}
            with self.assertRaises(ValueError):
                setup.apply(self.root, answer)

    def test_cli_filters_questions_and_hides_credentials(self):
        script = self.root / "scripts/setup.py"
        for level, count in [("important", 2), ("normal", 9), ("advanced", 318)]:
            result = subprocess.run([sys.executable, str(script), "list", "--level", level],
                                    check=True, capture_output=True, text=True)
            self.assertEqual(len(json.loads(result.stdout)), count)
            self.assertTrue("app:app@" not in result.stdout, "資格情報がCLI出力に含まれています")
        answer = self.answer()
        answer["settings"]["DATABASE_URL"] = "postgres://app:private-password@localhost:5432/app"
        self.confirm(answer)
        answer["databaseTarget"] = "external"
        path = self.root / "answers.json"
        path.write_text(json.dumps(answer))
        result = subprocess.run([sys.executable, str(script), "plan", "--answers", str(path)],
                                check=True, capture_output=True, text=True)
        self.assertTrue("private-password" not in result.stdout + result.stderr, "秘密値がplanに含まれています")
        self.assertIn(".env", json.loads(result.stdout)["files"])


if __name__ == "__main__":
    unittest.main()

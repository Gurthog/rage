import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import TestCase


CHECK = Path(__file__).resolve().parents[2] / "scripts" / "check_migration_history.py"


class MigrationHistoryTests(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.repo = Path(self.temp_dir.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.com")
        self.write("core/migrations/0001_initial.py", "original\n")
        self.write("core/migrations/__init__.py", "")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").strip()

    def git(self, *args):
        return subprocess.run(
            ["git", *args], cwd=self.repo, check=True, capture_output=True, text=True
        ).stdout

    def write(self, name, content):
        path = self.repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def commit(self):
        self.git("add", "-A")
        self.git("commit", "-qm", "change")

    def check_history(self, base=None, head="HEAD"):
        return subprocess.run(
            [sys.executable, str(CHECK), base or self.base, head],
            cwd=self.repo,
            capture_output=True,
            text=True,
        )

    def test_unchanged_existing_migration_passes(self):
        result = self.check_history()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_editing_existing_migration_fails(self):
        self.write("core/migrations/0001_initial.py", "changed\n")
        self.commit()
        result = self.check_history()
        self.assertEqual(result.returncode, 1)
        self.assertIn("core/migrations/0001_initial.py", result.stderr)

    def test_deleting_existing_migration_fails(self):
        (self.repo / "core/migrations/0001_initial.py").unlink()
        self.commit()
        result = self.check_history()
        self.assertEqual(result.returncode, 1)
        self.assertIn("core/migrations/0001_initial.py", result.stderr)

    def test_renaming_existing_migration_fails(self):
        self.git("mv", "core/migrations/0001_initial.py", "core/migrations/0002.py")
        self.commit()
        result = self.check_history()
        self.assertEqual(result.returncode, 1)
        self.assertIn("core/migrations/0001_initial.py", result.stderr)

    def test_new_migration_can_be_revised_before_merge(self):
        self.write("new_app/migrations/0001_initial.py", "first draft\n")
        self.commit()
        self.write("new_app/migrations/0001_initial.py", "revised\n")
        self.commit()
        result = self.check_history()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_non_migrations_and_private_modules_are_not_protected(self):
        self.write("core/migrations/__init__.py", "# changed\n")
        self.write("core/migrations/_helper.py", "original\n")
        self.write("core/migrations/notes.txt", "original\n")
        self.write("core/other/0001.py", "original\n")
        self.commit()
        self.write("core/migrations/_helper.py", "changed\n")
        self.write("core/migrations/notes.txt", "changed\n")
        self.write("core/other/0001.py", "changed\n")
        self.commit()
        result = self.check_history()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_merge_result_preserves_migrations_added_to_base_after_branching(self):
        self.git("checkout", "-qb", "feature")
        self.write("core/models.py", "# feature\n")
        self.commit()
        self.git("checkout", "-q", "--detach", self.base)
        self.write("core/migrations/0002_base.py", "base migration\n")
        self.commit()
        updated_base = self.git("rev-parse", "HEAD").strip()
        self.git("merge", "-q", "--no-ff", "feature", "-m", "merge")
        result = self.check_history(base=updated_base)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_migration_added_to_base_is_protected_in_merge_result(self):
        self.write("other_app/migrations/0001_initial.py", "base migration\n")
        self.commit()
        updated_base = self.git("rev-parse", "HEAD").strip()
        self.write("other_app/migrations/0001_initial.py", "changed\n")
        self.commit()
        result = self.check_history(base=updated_base)
        self.assertEqual(result.returncode, 1)
        self.assertIn("other_app/migrations/0001_initial.py", result.stderr)

    def test_invalid_revision_fails_closed(self):
        result = self.check_history(base="not-a-revision")
        self.assertNotEqual(result.returncode, 0)

#!/usr/bin/env python3
"""Reject changes to migration scripts already present in the base tree."""

import os
from pathlib import PurePosixPath
import subprocess
import sys


def is_migration(path):
    path = PurePosixPath(path)
    return (
        path.parent.name == "migrations"
        and path.suffix == ".py"
        and not path.name.startswith("_")
    )


def main():
    if len(sys.argv) != 3:
        print("Usage: check_migration_history.py BASE HEAD", file=sys.stderr)
        return 2

    # Disabling rename detection makes a rename appear as a deletion and an
    # addition, so the old migration path is always checked.
    result = subprocess.run(
        [
            "git", "diff", "--no-renames", "--name-only", "-z",
            "--diff-filter=MDT", sys.argv[1], sys.argv[2], "--",
        ],
        check=True,
        stdout=subprocess.PIPE,
    )
    paths = [os.fsdecode(path) for path in result.stdout.split(b"\0") if path]
    changed = [path for path in paths if is_migration(path)]
    if changed:
        print("Existing migration scripts must not be changed or removed:", file=sys.stderr)
        for path in changed:
            print(f"  {path!r}", file=sys.stderr)
        print("Create a new migration instead.", file=sys.stderr)
        return 1

    print("Existing migration scripts are unchanged.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

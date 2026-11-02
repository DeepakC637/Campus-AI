#!/usr/bin/env python3
"""
check_progress.py - Read-only verification script for project status and progress.

Performs:
1. Prints the last 5 git commits (git log --oneline -5)
2. Prints git status (clean or not)
3. For accounts, students, recruiters, jobs, applications, interviews, and placements
   models.py files, prints the actual line count and the first 15 lines.
4. Runs python manage.py test and prints the final "Ran X tests" line.
5. Does NOT modify anything - strictly read-only.
"""

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

FILES_TO_CHECK = [
    "accounts/models.py",
    "students/models.py",
    "recruiters/models.py",
    "jobs/models.py",
    "applications/models.py",
    "interviews/models.py",
    "placements/models.py",
]


def get_python_executable():
    """Resolve the appropriate Python interpreter to run manage.py."""
    # If the current interpreter can import environ and django, use it
    try:
        import environ  # noqa: F401
        import django  # noqa: F401
        return sys.executable
    except ImportError:
        pass

    # Check for a virtual environment in the project root
    venv_candidates = [
        PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / "venv" / "bin" / "python",
        PROJECT_ROOT / ".venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / ".venv" / "bin" / "python",
    ]
    for candidate in venv_candidates:
        if candidate.exists():
            return str(candidate)

    return sys.executable if sys.executable else "python"


def print_git_commits():
    print("=" * 60)
    print("1. LAST 5 GIT COMMITS (git log --oneline -5)")
    print("=" * 60)
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        commits = result.stdout.strip()
        if commits:
            print(commits)
        else:
            print("No commits found.")
    except Exception as e:
        print(f"Error fetching git commits: {e}")


def print_git_status():
    print("\n" + "=" * 60)
    print("2. GIT STATUS (clean or not)")
    print("=" * 60)
    try:
        # Check porcelain to see if working tree is clean or not
        porcelain = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            check=True,
        )
        is_clean = len(porcelain.stdout.strip()) == 0
        if is_clean:
            print("Git status: Clean (no uncommitted changes)")
        else:
            print("Git status: Not clean (uncommitted changes present)")
            print("\nUncommitted changes:")
            print(porcelain.stdout.strip())
    except Exception as e:
        print(f"Error checking git status: {e}")


def print_model_files():
    print("\n" + "=" * 60)
    print("3. MODEL FILES (Line count and first 15 lines)")
    print("=" * 60)
    for rel_path in FILES_TO_CHECK:
        file_path = PROJECT_ROOT / rel_path
        print(f"\n--- {rel_path} ---")
        if not file_path.exists():
            print("File does not exist.")
            continue

        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            line_count = len(lines)
            print(f"Line count: {line_count}")
            print("First 15 lines:")
            for line in lines[:15]:
                print(line, end="")
            if lines and not lines[min(15, line_count) - 1].endswith("\n"):
                print()
        except Exception as e:
            print(f"Error reading {rel_path}: {e}")


def run_tests():
    print("\n" + "=" * 60)
    print("4. DJANGO TESTS (python manage.py test)")
    print("=" * 60)
    python_bin = get_python_executable()
    manage_py = PROJECT_ROOT / "manage.py"

    cmd = [python_bin, str(manage_py), "test"]
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(PROJECT_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = proc.stdout

        # Search for the final "Ran X tests" line in the output
        ran_line = None
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("Ran ") and "test" in stripped:
                ran_line = stripped

        if ran_line:
            print(ran_line)
        else:
            print("Could not find 'Ran X tests' line in output:")
            print(output)
    except Exception as e:
        print(f"Error running tests: {e}")


def main():
    print_git_commits()
    print_git_status()
    print_model_files()
    run_tests()


if __name__ == "__main__":
    main()

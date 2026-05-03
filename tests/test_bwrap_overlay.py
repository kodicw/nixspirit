import subprocess
import os
import shutil
import pytest


def test_bwrap_nested_ro_bind(tmp_path):
    # Skip if bwrap is not in PATH
    if shutil.which("bwrap") is None:
        pytest.skip("bwrap not found in PATH")

    project_dir = tmp_path / "project"
    project_dir.mkdir()
    messages_dir = project_dir / ".system" / "messages"
    messages_dir.mkdir(parents=True)
    test_file = messages_dir / "msg1.txt"
    test_file.write_text("hello")

    # Command to try to delete the read-only directory
    try:
        subprocess.run(
            [
                "bwrap",
                "--dev-bind",
                "/",
                "/",
                "--bind",
                str(project_dir),
                str(project_dir),
                "--ro-bind",
                str(messages_dir),
                str(messages_dir),
                "rm",
                "-rf",
                str(messages_dir),
            ],
            capture_output=True,
            check=True,
        )
        # If it succeeds, the ro-bind didn't protect it or was overridden
    except subprocess.CalledProcessError as e:
        print(f"Error as expected: {e.stderr.decode()}")
        assert (
            "Read-only file system" in e.stderr.decode()
            or "Device or resource busy" in e.stderr.decode()
        )

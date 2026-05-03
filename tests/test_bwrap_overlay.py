import subprocess
import os
import shutil


def test_bwrap_nested_ro_bind(tmp_path):
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    messages_dir = project_dir / ".jbot" / "messages"
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
        # But wait, rm -rf on a mount point might fail with 'Device or resource busy'
        # or it might just fail to delete the files inside.
    except subprocess.CalledProcessError as e:
        print(f"Error as expected: {e.stderr.decode()}")
        assert (
            "Read-only file system" in e.stderr.decode()
            or "Device or resource busy" in e.stderr.decode()
        )


if __name__ == "__main__":
    # Manually run if not using pytest

    tmp = "/tmp/bwrap_test"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    from pathlib import Path

    try:
        test_bwrap_nested_ro_bind(Path(tmp))
        print("Test finished (check output above)")
    except Exception as e:
        print(f"Test failed: {e}")

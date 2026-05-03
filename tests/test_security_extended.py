import subprocess
import pytest


# Test if bwrap is available
def has_bwrap():
    try:
        subprocess.run(["bwrap", "--version"], capture_output=True, check=True)
        return True
    except Exception:
        return False


@pytest.mark.skipif(not has_bwrap(), reason="bubblewrap not available")
def test_bwrap_sandbox_isolation(tmp_path):
    """
    Verifies that a simple bwrap sandbox (similar to what core uses)
    actually restricts write access.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("sensitive data")

    # Attempt to write to a file outside the sandbox
    # Using similar flags to launcher.sh
    try:
        subprocess.run(
            [
                "bwrap",
                "--ro-bind",
                "/nix/store",
                "/nix/store",
                "--ro-bind",
                "/bin",
                "/bin",
                "--ro-bind",
                "/usr/bin",
                "/usr/bin",
                "--ro-bind",
                "/lib",
                "/lib",
                "--ro-bind",
                "/lib64",
                "/lib64",
                "--proc",
                "/proc",
                "--dev",
                "/dev",
                "--tmpfs",
                "/tmp",
                "--bind",
                str(project_dir),
                str(project_dir),
                "--unshare-all",
                "--chdir",
                str(project_dir),
                "touch",
                str(secret_file),
            ],
            capture_output=True,
            check=True,
            timeout=5,
        )
        pytest.fail("Should not have been able to touch file outside sandbox")
    except subprocess.CalledProcessError:
        # Success - it failed to touch the file
        pass


@pytest.mark.skipif(not has_bwrap(), reason="bubblewrap not available")
def test_bwrap_sandbox_read_access(tmp_path):
    """
    Verifies that files not explicitly bound are not readable.
    """
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    secret_file = tmp_path / "secret.txt"
    secret_file.write_text("sensitive data")

    # Attempt to read a file outside the sandbox
    result = subprocess.run(
        [
            "bwrap",
            "--ro-bind",
            "/nix/store",
            "/nix/store",
            "--ro-bind",
            "/bin",
            "/bin",
            "--ro-bind",
            "/usr/bin",
            "/usr/bin",
            "--ro-bind",
            "/lib",
            "/lib",
            "--ro-bind",
            "/lib64",
            "/lib64",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--bind",
            str(project_dir),
            str(project_dir),
            "--unshare-all",
            "--chdir",
            str(project_dir),
            "ls",
            str(secret_file),
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "No such file or directory" in result.stderr

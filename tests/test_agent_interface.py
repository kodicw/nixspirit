import os
import time
import pytest
from unittest.mock import patch, MagicMock
import sys

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_agent_interface


def test_gemini_interface():
    interface = core_agent_interface.GeminiInterface("/path/to/gemini")
    cmd = interface.get_command("Hello")
    assert cmd == [
        "/path/to/gemini",
        "-y",
        "--output-format",
        "stream-json",
        "-p",
        "Hello",
    ]


def test_opencode_interface():
    interface = core_agent_interface.OpenCodeInterface("/path/to/opencode")
    cmd = interface.get_command("Hello")
    assert cmd == [
        "/path/to/opencode",
        "run",
        "Hello",
        "--dangerously-skip-permissions",
    ]


def test_get_interface():
    # Test Gemini default
    iface = core_agent_interface.get_interface("gemini", "gemini")
    assert isinstance(iface, core_agent_interface.GeminiInterface)

    # Test OpenCode by name
    iface = core_agent_interface.get_interface("opencode", "something")
    assert isinstance(iface, core_agent_interface.OpenCodeInterface)

    # Test OpenCode by binary path
    iface = core_agent_interface.get_interface("any", "/usr/bin/opencode-cli")
    assert isinstance(iface, core_agent_interface.OpenCodeInterface)


def test_interface_run_with_rate_limit(tmp_path):
    os.chdir(tmp_path)
    os.makedirs(".system/locks", exist_ok=True)
    lock_file = ".system/locks/api.lock"

    # Set last run time to now
    with open(lock_file, "w") as f:
        f.write(str(time.time()))

    interface = core_agent_interface.GeminiInterface("echo")

    with patch("subprocess.Popen") as mock_popen, patch("time.sleep") as mock_sleep:
        mock_process = MagicMock()
        mock_process.stdout = ["output\n"]
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        exit_code, stats = interface.run("Hello", "test-agent")

        assert exit_code == 0
        # Should have slept for approximately 2s
        assert mock_sleep.called
        assert mock_sleep.call_args[0][0] > 1.5


def test_interface_run_exception(tmp_path):
    os.chdir(tmp_path)
    interface = core_agent_interface.GeminiInterface("echo")

    with patch("subprocess.Popen") as mock_popen:
        mock_popen.side_effect = Exception("Popen failed")
        exit_code, stats = interface.run("Hello", "test-agent")
        assert exit_code == 1


def test_interface_rate_limit_invalid_lock(tmp_path):
    os.chdir(tmp_path)
    os.makedirs(".system/locks", exist_ok=True)
    lock_file = ".system/locks/api.lock"

    # Invalid lock file content
    with open(lock_file, "w") as f:
        f.write("invalid")

    interface = core_agent_interface.GeminiInterface("echo")
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        exit_code, stats = interface.run("Hello", "test-agent")
        assert exit_code == 0


def test_interface_lock_write_failure(tmp_path):
    os.chdir(tmp_path)
    interface = core_agent_interface.GeminiInterface("echo")
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = []
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        # Patch 'open' specifically for the lock file write
        original_open = open

        def mocked_open(file, mode="r", *args, **kwargs):
            if "api.lock" in str(file) and "w" in mode:
                raise PermissionError("Write failed")
            return original_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=mocked_open):
            exit_code, stats = interface.run("Hello", "test-agent")
            assert exit_code == 0  # Should pass despite lock write failure


def test_abstract_interface():
    # Attempting to instantiate AiInterface should fail
    with pytest.raises(TypeError):
        core_agent_interface.AiInterface("bin")

    # Call pass on a concrete instance if we really want to cover that line 18
    # But usually pass in abstract methods is fine to remain uncovered or is covered by subclassing.
    # We can create a dummy subclass.
    class Dummy(core_agent_interface.AiInterface):
        def get_command(self, prompt):
            super().get_command(prompt)
            return ["dummy"]

        def _parse_output(self, process, agent_name):
            return 0, {}

    d = Dummy("bin")
    assert d.get_command("hi") == ["dummy"]

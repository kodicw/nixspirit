import os
import sys
from unittest.mock import patch

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_logic as core


def test_ensure_single_user_success(tmp_path):
    # Should not exit when current user owns the directory
    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_uid = os.getuid()
        core.ensure_single_user(str(tmp_path))


def test_ensure_single_user_failure(tmp_path):
    # Should exit when current user does not own the directory
    with patch("os.stat") as mock_stat:
        mock_stat.return_value.st_uid = os.getuid() + 1
        with patch("sys.exit") as mock_exit:
            core.ensure_single_user(str(tmp_path))
            mock_exit.assert_called_once_with(1)


def test_ensure_single_user_exception():
    # Should just log a warning and continue if stat fails
    with patch("os.stat", side_effect=Exception("stat error")):
        with patch("core_logic.log") as mock_log:
            core.ensure_single_user("/nonexistent")
            mock_log.assert_any_call(
                "Warning: Could not verify single-user constraint: stat error",
                "Security",
            )

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_tui as tui


def test_run_command_success():
    with patch("subprocess.run") as mock_run:
        mock_result = MagicMock()
        mock_result.stdout = "output\n"
        mock_run.return_value = mock_result

        assert tui.run_command(["cmd"]) == "output"
        mock_run.assert_called_once()


def test_run_command_error_capture():
    with patch("subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")
        assert tui.run_command(["cmd"], capture=True) == "Error: error"


def test_run_command_error_no_capture():
    with patch("subprocess.run") as mock_run:
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")
        assert tui.run_command(["cmd"], capture=False) is None


@patch("core_tui.run_command")
def test_gum_functions(mock_run_cmd):
    mock_run_cmd.return_value = "result"
    assert tui.get_gum_input("p", "h") == "result"
    assert tui.get_gum_write("p", "h") == "result"
    assert tui.get_gum_choose(["a", "b"], "h") == "result"


@patch("core_logic.get_git_status", return_value="git clean")
@patch("core_logic.get_nix_metadata", return_value="nix OK")
@patch(
    "core_infra.get_recent_logs",
    return_value=[{"agent": "A", "content": {"summary": "s"}}],
)
@patch("core_tui.run_command", return_value="refined draft")
def test_ai_refine_idea(mock_run, mock_logs, mock_nix, mock_git):
    result = tui.ai_refine_idea("my idea", "/tmp")
    assert result == "refined draft"
    mock_run.assert_called_once()
    prompt = mock_run.call_args[0][0][-1]
    assert "git clean" in prompt
    assert "nix OK" in prompt
    assert "[A] s" in prompt
    assert "my idea" in prompt


@patch("core_logic.get_project_root", return_value="/tmp")
@patch("core_tui.get_gum_choose")
def test_main_exit(mock_choose, mock_root):
    mock_choose.return_value = "❌ Exit"
    with pytest.raises(SystemExit) as e:
        tui.main()
    assert e.value.code == 0


@patch("core_logic.get_project_root", return_value="/tmp")
@patch("core_tui.get_gum_choose", return_value="💡 New Idea")
@patch("core_tui.get_gum_write", return_value="")
def test_main_empty_draft(mock_write, mock_choose, mock_root):
    with pytest.raises(SystemExit) as e:
        tui.main()
    assert e.value.code == 0


@patch("core_logic.get_project_root", return_value="/tmp")
@patch("core_tui.get_gum_choose")
@patch("core_tui.get_gum_write")
@patch("core_tui.ai_refine_idea", return_value="Refined!")
@patch("core_tui.get_memory_client")
def test_main_idea_accept(mock_nb, mock_ai, mock_write, mock_choose, mock_root):
    mock_choose.side_effect = ["💡 New Idea", "✅ Accept & Push"]
    mock_write.return_value = "rough draft"

    mock_client_inst = MagicMock()
    mock_nb.return_value = mock_client_inst

    tui.main()

    mock_client_inst.add.assert_called_once_with(
        "Idea: rough draft...",
        "Refined!",
        tags=["type:idea", "input:human"],
        overwrite=False,
    )


@patch("core_logic.get_project_root", return_value="/tmp")
@patch("core_tui.get_gum_choose")
@patch("core_tui.get_gum_write")
@patch("core_tui.ai_refine_idea", return_value="Refined!")
def test_main_idea_discard(mock_ai, mock_write, mock_choose, mock_root):
    mock_choose.side_effect = ["💡 New Idea", "❌ Discard"]
    mock_write.return_value = "rough draft"

    with pytest.raises(SystemExit) as e:
        tui.main()
    assert e.value.code == 0


@patch("core_logic.get_project_root", return_value="/tmp")
@patch("core_tui.get_gum_choose")
@patch("core_tui.get_gum_write")
@patch("core_tui.run_command")
@patch("core_tui.ai_refine_idea", return_value="Refined!")
@patch("core_tui.get_memory_client")
def test_main_prompt_edit(
    mock_nb, mock_ai, mock_run, mock_write, mock_choose, mock_root
):
    mock_choose.side_effect = ["🔧 Update Prompt", "✏️ Edit Manually"]
    mock_write.side_effect = ["rough draft", "Final edit!"]

    mock_client_inst = MagicMock()
    mock_nb.return_value = mock_client_inst

    tui.main()

    mock_client_inst.add.assert_called_once_with(
        "System Prompt: rough draft...",
        "Final edit!",
        tags=["type:prompt", "input:human"],
        overwrite=True,
    )

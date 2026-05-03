import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

import jbot_cli
import jbot_infra
import jbot_core


def main_with_args(args):
    with patch("argparse.ArgumentParser.parse_args", return_value=args):
        jbot_cli.main()


# --- jbot_cli.py ---


def test_jbot_cli_push_note_file(tmp_path, capsys):
    note_file = tmp_path / "note.txt"
    note_file.write_text("Hello World")

    class Args:
        command = "maintenance"
        m_action = "push-note"
        file = str(note_file)
        title = "Test Note"
        tags = "test,tag"
        dir = str(tmp_path)

    with patch("jbot_utils.update_note_stably", return_value=True):
        main_with_args(Args())
        captured = capsys.readouterr()
        assert "Successfully pushed stable note" in captured.out


def test_jbot_cli_push_note_fail(capsys):
    class Args:
        command = "maintenance"
        m_action = "push-note"
        file = None
        title = "Test Note"
        tags = "test,tag"
        dir = "."

    with patch("sys.stdin.read", return_value="stdin content"):
        with patch("jbot_utils.update_note_stably", return_value=False):
            with pytest.raises(SystemExit) as cm:
                main_with_args(Args())
            assert cm.value.code == 1
            captured = capsys.readouterr()
            assert "Failed to push note" in captured.out


def test_jbot_cli_agent_tui_cancel(tmp_path):
    class Args:
        command = "agent"
        name = None
        role = None
        desc = None
        prompt = None
        dir = str(tmp_path)

    with patch("jbot_infra.get_team_registry", return_value={"ceo": {"role": "CEO"}}):
        with patch("jbot_tui.get_gum_choose", return_value="❌ Cancel"):
            main_with_args(Args())
            # Should just return


def test_jbot_cli_agent_tui_no_agents(tmp_path, capsys):
    class Args:
        command = "agent"
        name = None
        dir = str(tmp_path)

    with patch("jbot_infra.get_team_registry", return_value={}):
        main_with_args(Args())
        captured = capsys.readouterr()
        assert "No agents found in registry" in captured.out


# --- jbot_infra.py ---


def test_jbot_infra_get_recent_messages_human_exception(tmp_path):
    # Target jbot_infra.py:88-89 (except Exception: pass)
    human_file = tmp_path / "human.txt"
    human_file.write_text("human stuff")

    # We mock core.read_file to raise an exception ONLY for the human.txt path
    original_read_file = jbot_core.read_file

    def side_effect(path):
        if "human.txt" in path:
            raise Exception("Read error")
        return original_read_file(path)

    with patch("jbot_core.read_file", side_effect=side_effect):
        with patch(
            "os.path.exists",
            side_effect=lambda p: True if "human.txt" in p else os.path.exists(p),
        ):
            res = jbot_infra.get_recent_messages(str(tmp_path), include_human=True)
            # Should catch the exception and not include human.txt in results
            assert all(m["filename"] != "human.txt" for m in res)


def test_jbot_infra_sort_key_success():
    # Target jbot_infra.py:156-157
    with patch("jbot_infra.get_memory_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        n1 = MagicMock()
        n1.id = "1"
        n2 = MagicMock()
        n2.id = "adr/10"
        mock_client.ls.return_value = [n1, n2]

        # This will trigger sort_key and int(id_str)
        jbot_infra.get_note_content("type:tasks")


def test_jbot_infra_get_messages_nb_exception():
    # Target jbot_infra.py:73-74
    with patch("jbot_infra.get_memory_client", side_effect=Exception("Client error")):
        with patch("jbot_core.log") as mock_log:
            jbot_infra.get_recent_messages(".", include_human=False)
            mock_log.assert_any_call(
                "Error fetching messages from nb: Client error", "Infra"
            )

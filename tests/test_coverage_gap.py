import os
import sys
import pytest
import runpy
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))

import jbot_cli
import jbot_infra
import nb_client
import jbot_core
import jbot_init
import jbot_utils
import jbot_agent_interface

# --- jbot_cli.py ---


def test_jbot_cli_get_messages_no_dir(capsys):
    # Target jbot_cli.py:91-92
    with patch("os.path.exists", return_value=False):
        # Ensure we are in a clean state
        with patch("jbot_infra.get_recent_messages", return_value=[]):
            jbot_cli.get_messages(".", count=5)
            captured = capsys.readouterr()
            assert "No messages directory found." in captured.out


def test_jbot_cli_maintenance_all(capsys):
    # Target jbot_cli.py:384-397
    class Args:
        command = "maintenance"
        m_action = "run"
        all = True
        dir = "."

    with patch("os.environ.get") as mock_env:
        mock_env.return_value = None
        with pytest.raises(SystemExit):
            jbot_cli.main_with_args(Args())
        captured = capsys.readouterr()
        assert "requires DISCOVERY_ROOT" in captured.out

        mock_env.return_value = "/tmp/discovery"
        with patch("jbot_infra.discover_projects", return_value=[]):
            jbot_cli.main_with_args(Args())
            captured = capsys.readouterr()
            assert "No projects discovered" in captured.out

        with patch("jbot_infra.discover_projects", return_value=["/tmp/p1"]):
            with patch("jbot_infra.run_maintenance") as mock_maint:
                jbot_cli.main_with_args(Args())
                captured = capsys.readouterr()
                assert "Maintaining project: /tmp/p1" in captured.out
                mock_maint.assert_called_once_with("/tmp/p1")


def test_jbot_cli_main_execution():
    # Target jbot_cli.py:466 via runpy
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../scripts/jbot_cli.py")
    )
    with patch("sys.argv", ["jbot_cli.py", "--help"]):
        with patch("sys.exit"):
            try:
                runpy.run_path(script_path, run_name="__main__")
            except SystemExit:
                pass
            # ArgumentParser normally exits on --help


# Helper for jbot_cli
def main_with_args(args):
    with patch("argparse.ArgumentParser.parse_args", return_value=args):
        jbot_cli.main()


jbot_cli.main_with_args = main_with_args


# --- jbot_infra.py ---


def test_jbot_infra_discover_projects(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    assert jbot_infra.discover_projects(str(tmp_path / "nonexistent")) == []

    p1 = root / "p1"
    p1.mkdir()
    (p1 / ".jbot").mkdir()
    (p1 / ".jbot" / "agents.json").write_text("{}")

    projects = jbot_infra.discover_projects(str(root))
    assert len(projects) == 1
    assert str(p1) in projects[0]


def test_jbot_infra_sort_key_exception():
    # Target jbot_infra.py:163-164
    # This is inside get_note_content -> sort_key
    with patch("jbot_infra.get_memory_client") as mock_client_factory:
        mock_client = MagicMock()
        mock_client_factory.return_value = mock_client

        note = MagicMock()
        note.id = "bad_id"  # Will cause ValueError when int() called on it
        mock_client.ls.return_value = [note]

        # We need to trigger the sort_key inside get_note_content
        jbot_infra.get_note_content("type:tasks")
        # If it didn't crash, it handled the exception


# --- jbot_agent.py ---


def test_jbot_agent_main_execution():
    # Target jbot_agent.py:265
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../scripts/jbot_agent.py")
    )
    with patch("sys.argv", ["jbot_agent.py", "--help"]):
        with patch("jbot_agent.run_agent"):
            # Mock run_agent to avoid actual execution
            try:
                runpy.run_path(script_path, run_name="__main__")
            except SystemExit:
                pass


# --- jbot_agent_interface.py ---


def test_jbot_agent_interface_model_coverage():
    # Target jbot_agent_interface.py:81
    iface = jbot_agent_interface.GeminiInterface(binary_path="gemini", model="flash")
    cmd = iface.get_command("hello")
    assert "-m" in cmd
    assert "flash" in cmd


def test_nb_client_clear_cache_exception():
    # Target nb_client.py:37-38
    with patch("os.remove", side_effect=Exception("Perm error")):
        with patch("os.path.exists", return_value=True):
            nb_client.NbClient.clear_cache()  # Should not raise


def test_nb_client_resolve_path_error():
    # Target nb_client.py:96-97
    client = nb_client.NbClient(notebook="test")
    with patch.object(client, "_run", side_effect=Exception("nb fail")):
        nb_client.NbClient._notebook_path_cache.clear()
        assert client._resolve_notebook_path() is None


def test_nb_client_load_save_cache_errors(tmp_path):
    # Target nb_client.py:114-115, 132-133
    client = nb_client.NbClient(notebook="test")
    client._persistent_cache_file = "/non/existent/path"
    client._load_persistent_cache()
    client._save_persistent_cache()


def test_nb_client_show_cache_hit():
    # Target nb_client.py:178
    client = nb_client.NbClient(notebook="test")
    nb_client.NbClient._cache["test:123"] = "Hit"
    assert client.show("123") == "Hit"


def test_nb_client_show_batch_empty():
    # Target nb_client.py:190-191 etc.
    client = nb_client.NbClient(notebook="test")
    assert client.show_batch([]) == {}


def test_nb_client_search_limit():
    # Target nb_client.py:259-260
    client = nb_client.NbClient(notebook="test")
    with patch.object(client, "_parse_ls_output") as mock_parse:
        mock_parse.return_value = [MagicMock(), MagicMock()]
        with patch.object(client, "_run", return_value=MagicMock(returncode=0)):
            assert len(client.search(limit=1)) == 1


def test_nb_client_edit_no_content():
    # Target nb_client.py:283 etc.
    client = nb_client.NbClient(notebook="test")
    with patch.object(client, "_run", return_value=MagicMock(returncode=0)):
        assert client.edit("123", title="New Title") is True


def test_nb_client_parse_ls_filename_only():
    # Target nb_client.py:312-314
    client = nb_client.NbClient(notebook="test")
    output = "[1] only_filename.md"
    notes = client._parse_ls_output(output)
    assert notes[0].filename == "only_filename.md"
    assert notes[0].title == "only_filename.md"


# --- jbot_core.py ---


def test_jbot_core_git_errors():
    # Target jbot_core.py:121-136
    with patch("subprocess.run", side_effect=Exception("Git fail")):
        assert jbot_core.is_git_clean() is False
        assert jbot_core.get_git_status() == "Not a git repository or git error."


def test_jbot_core_commit_all(tmp_path):
    # Target jbot_core.py:224-263
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="")
        assert jbot_core.commit_all(str(tmp_path), "Commit msg") is True

        mock_run.side_effect = Exception("Commit fail")
        assert jbot_core.commit_all(str(tmp_path), "Commit msg") is False


# --- jbot_init.py ---


def test_jbot_init_errors(capsys):
    # Target jbot_init.py:16, 43-44, 245-246
    with patch("os.makedirs", side_effect=Exception("Init fail")):
        assert jbot_init.init_project("/tmp/fail") is False
        captured = capsys.readouterr()
        assert "Initialization failed" in captured.out

    with patch("jbot_core.load_json", side_effect=Exception("Read fail")):
        assert jbot_init._load_agents_config("/tmp/proj") == []


# --- jbot_utils.py ---


def test_jbot_utils_errors():
    # Target jbot_utils.py etc.
    with patch("jbot_utils.get_memory_client", side_effect=Exception("Client fail")):
        assert jbot_utils.update_note_stably("any", "any", []) is False

        assert jbot_utils.get_recent_adrs() == []

    with patch("jbot_infra.get_project_summary", side_effect=Exception("Summary fail")):
        # generate_dashboard should still return True but log error
        assert jbot_utils.generate_dashboard("INDEX.md") is True

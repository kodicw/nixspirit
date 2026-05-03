import os
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
from core_nb_client import NbClient


@pytest.fixture
def client():
    # Clear cache for test isolation
    NbClient.clear_cache()
    # Use a custom env to avoid host pollution
    env = {"EDITOR": "cat", "PAGER": "cat", "NB_USER_NAME": "Test User"}
    return NbClient(notebook="knowledge", env=env)


@patch("subprocess.run")
def test_add_note(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = 'Added: [123] 20260422.md "Test Title"\n'
    mock_run.return_value = mock_result

    note_id = client.add(
        "Test Title", "Test Content", tags=["tag1", "tag2"], overwrite=True
    )

    assert note_id == "123"
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "nb" in args
    assert "knowledge:add" in args
    assert "--title" in args
    assert "Test Title" in args
    assert "--content" in args
    assert "Test Content" in args
    assert "--tags" in args
    assert "tag1,tag2" in args
    assert "--overwrite" in args
    assert "--force" in args


@patch("subprocess.run")
def test_show_note(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Test Content\nLine 2"
    mock_run.return_value = mock_result

    content = client.show("123")

    assert content == "Test Content\nLine 2"
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "knowledge:show" in args
    assert "123" in args
    assert "--print" in args


@patch("subprocess.run")
def test_query_notes(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = """
[knowledge:1] 🔖 Test Bookmark
[knowledge:2] Regular Note Title
[3] Another Note
"""
    mock_run.return_value = mock_result

    notes = client.query("Test")

    assert len(notes) == 3
    assert notes[0].id == "1"
    assert notes[0].title == "Test Bookmark"
    assert notes[1].id == "2"
    assert notes[1].title == "Regular Note Title"
    assert notes[2].id == "3"
    assert notes[2].title == "Another Note"

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "knowledge:search" in args
    assert "Test" in args


@patch("subprocess.run")
def test_ls_notes(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "[knowledge:42] Memory: [agent1] - Summary"
    mock_run.return_value = mock_result

    notes = client.ls(tags=["memory"], limit=5)

    assert len(notes) == 1
    assert notes[0].id == "42"
    assert notes[0].title == "Memory: [agent1] - Summary"

    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "knowledge:search" in args
    assert "--list" in args
    assert "memory" in args


def test_client_default_env():
    # Test without passing env and empty os.environ
    with patch.dict(os.environ, {}, clear=True):
        client = NbClient(notebook="knowledge")
        assert client.env["EDITOR"] == "cat"
        assert client.env["PAGER"] == "cat"


@patch("subprocess.run")
def test_add_note_fail(mock_run, client):
    # Test failed command
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_run.return_value = mock_result

    note_id = client.add("Test Title", "Test Content")
    assert note_id is None

    # Test unexpected output format
    mock_result.returncode = 0
    mock_result.stdout = "Created note"
    note_id = client.add("Test Title", "Test Content")
    assert note_id is None


@patch("subprocess.run")
def test_show_note_fail(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    assert client.show("123") is None


@patch("subprocess.run")
def test_query_notes_fail(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    assert client.query("Test") == []


@patch("subprocess.run")
def test_ls_notes_fail(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_run.return_value = mock_result

    assert client.ls() == []


@patch("subprocess.run")
def test_parse_ls_output_skip_lines(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = """
-
-------------------

[knowledge:42] Valid Note
"""
    mock_run.return_value = mock_result

    notes = client.ls()
    assert len(notes) == 1
    assert notes[0].id == "42"
    assert notes[0].title == "Valid Note"


@patch("subprocess.run")
def test_delete_note(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    success = client.delete("123")

    assert success is True
    mock_run.assert_called_once()
    args = mock_run.call_args[0][0]
    assert "knowledge:delete" in args
    assert "123" in args
    assert "--force" in args


@patch("subprocess.run")
def test_edit_note(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_run.return_value = mock_result

    success = client.edit(
        "123", content="New Content", title="New Title", tags=["t1", "t2"]
    )

    assert success is True
    args = mock_run.call_args[0][0]
    assert "knowledge:edit" in args
    assert "123" in args
    assert "--content" in args
    assert "New Content" in args
    assert "--title" in args
    assert "New Title" in args
    assert "--tags" in args
    assert "t1,t2" in args
    assert "--overwrite" in args


@patch("subprocess.run")
def test_ls_notes_with_limit(mock_run, client):
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "[1] One\n[2] Two\n[3] Three"
    mock_run.return_value = mock_result

    # Test limit when tags are None
    notes = client.ls(limit=2)
    # mock_run might be called with ls --filenames now
    args = mock_run.call_args[0][0]
    assert "knowledge:ls" in args or "knowledge:search" in args

    # Test limit when tags are present
    mock_run.reset_mock()
    notes = client.ls(tags=["tag"], limit=1)
    assert len(notes) == 1
    assert notes[0].id == "1"


def test_client_init_mock_less():
    # Test initialization when less is missing
    with (
        patch("os.path.exists") as mock_exists,
        patch("tempfile.TemporaryDirectory") as mock_tmp,
        patch("builtins.open", create=True) as mock_open,
        patch("os.chmod") as mock_chmod,
    ):
        mock_tmp_inst = MagicMock()
        mock_tmp_inst.name = "/tmp/core_bin_random"
        mock_tmp.return_value = mock_tmp_inst

        # Mock paths: less does not exist
        mock_exists.return_value = False

        client = NbClient(notebook="test")

        assert "/tmp/core_bin_random" in client.env["PATH"]
        mock_open.assert_called()
        mock_chmod.assert_called()

import os
import json
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_infra as infra
import core_utils as utils


def test_get_team_registry(tmp_path):
    system_dir = tmp_path / ".system"
    system_dir.mkdir()
    agents_file = system_dir / "agents.json"
    data = {"agent1": {"role": "Tester"}}
    agents_file.write_text(json.dumps(data))
    assert infra.get_team_registry(str(tmp_path)) == data


@patch("core_infra.get_memory_client")
def test_get_recent_messages(mock_nb, tmp_path):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client

    mock_note = MagicMock()
    mock_note.id = "133"
    mock_note.title = "Message: [ceo] Greetings"
    mock_client.ls.return_value = [mock_note]
    mock_client.show.return_value = "From: ceo\nSubject: Greetings\n\nhi"

    msgs_dir = tmp_path / "messages"
    msgs_dir.mkdir()
    (msgs_dir / "human.txt").write_text("HUMAN FEEDBACK")

    # Fetch with human.txt enabled
    results = infra.get_recent_messages(
        str(msgs_dir), count=5, include_human=True, project_dir=str(tmp_path)
    )
    assert len(results) == 2
    assert results[0]["filename"] == "nb:133"
    assert "hi" in results[0]["content"]
    assert results[1]["filename"] == "human.txt"
    assert "HUMAN FEEDBACK" in results[1]["content"]

    # Fetch without human.txt
    results = infra.get_recent_messages(
        str(msgs_dir), count=5, include_human=False, project_dir=str(tmp_path)
    )
    assert len(results) == 1
    assert results[0]["filename"] == "nb:133"


@patch("core_infra.get_memory_client")
def test_get_recent_logs(mock_nb):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client

    mock_note1 = MagicMock()
    mock_note1.title = "Memory: [a1] - s1"
    mock_note2 = MagicMock()
    mock_note2.title = "Memory: [a2] - s2"
    mock_client.ls.return_value = [mock_note1, mock_note2]

    logs = infra.get_recent_logs(count=1)
    assert len(logs) == 2
    assert logs[1]["agent"] == "a2"


@patch("core_infra.get_memory_client")
def test_get_recent_logs_exception(mock_nb):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client
    mock_client.ls.side_effect = Exception("err")
    assert infra.get_recent_logs() == []


def test_parse_directives(tmp_path):
    dir_path = tmp_path / "directives"
    dir_path.mkdir()
    today = datetime.now().strftime("%Y-%m-%d")
    (dir_path / f"999_{today}_future.txt").write_text("Future")
    (dir_path / "001_2000-01-01_expired.txt").write_text("Expired")
    (dir_path / "002_active.txt").write_text("Active\nExpiration: 2099-01-01")
    directives = infra.parse_directives(str(dir_path))
    filenames = [d["filename"] for d in directives]
    assert f"999_{today}_future.txt" in filenames
    assert "001_2000-01-01_expired.txt" not in filenames
    assert "002_active.txt" in filenames


@patch("core_infra.get_memory_client")
def test_generate_dashboard(mock_nb, tmp_path):
    (tmp_path / ".project_goal").write_text("Vision")
    # Dashboard uses core_tasks.parse_tasks now, so we might need to mock it if we want full isolation,
    # but for now we'll just let it run.
    utils.generate_dashboard("INDEX.md", str(tmp_path))
    assert "Vision" in (tmp_path / "INDEX.md").read_text()


def test_send_message(tmp_path):
    success = infra.send_message(str(tmp_path), "ceo", "hello", subject="Greetings")
    assert success is True
    outbox_dir = tmp_path / ".system" / "outbox"
    assert outbox_dir.exists()
    msg_files = os.listdir(outbox_dir)
    assert len(msg_files) == 1 and "ceo.txt" in msg_files[0]


@patch("core_infra.get_memory_client")
def test_run_maintenance(mock_core_nb_client, tmp_path):
    system_dir = tmp_path / ".system"
    system_dir.mkdir()
    queues_dir = system_dir / "queues"
    queues_dir.mkdir()
    (queues_dir / "tester.json").write_text(json.dumps({"summary": "done"}))
    infra.run_maintenance(str(tmp_path))
    assert not (queues_dir / "tester.json").exists()
    mock_core_nb_client.return_value.add.assert_called_once()


@patch("core_infra.get_memory_client")
def test_get_note_content(mock_nb):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client

    mock_note = MagicMock()
    mock_note.id = "1"
    mock_client.ls.return_value = [mock_note]
    mock_client.show.return_value = "Content"

    # Tag search
    assert infra.get_note_content("type:tasks") == "Content"
    mock_client.ls.assert_called_with(tags=["type:tasks"])
    mock_client.show.assert_called_with("1")

    # Fallback to query
    mock_client.ls.return_value = []
    mock_client.query.return_value = [mock_note]
    assert infra.get_note_content("some query") == "Content"
    mock_client.query.assert_called_with("some query")

    # Fallback to title search for prompt
    # Note: query is called twice, first with type:prompt, then with Authoritative System Prompt
    mock_client.query.side_effect = [[], [mock_note]]
    assert infra.get_note_content("type:prompt") == "Content"

    # Exception handling
    mock_client.ls.side_effect = Exception("Error")
    assert infra.get_note_content("type:idea") is None


@patch("core_infra.get_memory_client")
def test_get_note_content_no_id(mock_nb):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client
    mock_client.ls.return_value = []
    mock_client.query.return_value = []
    assert infra.get_note_content("type:missing") is None


@patch("core_infra.get_memory_client")
def test_get_recent_messages_exc_v2(mock_nb, tmp_path):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client
    mock_client.ls.return_value = []

    assert infra.get_recent_messages(str(tmp_path)) == []


def test_parse_directives_exception(tmp_path):
    assert infra.parse_directives("nonexistent") == []
    dir_path = tmp_path / "dirs"
    dir_path.mkdir()
    f = dir_path / "bad.txt"
    f.mkdir()  # trigger read error
    assert infra.parse_directives(str(dir_path)) == []


@patch("core_infra.get_project_summary")
def test_generate_dashboard_advanced(mock_get_summary, tmp_path):
    mock_get_summary.return_value = {
        "vision": "Test Vision",
        "team": {"agent1": {"role": "dev", "description": "desc"}},
        "tasks": {
            "active": ["- [ ] Task 1 [lead]"],
            "backlog": [],
            "done_count": 0,
            "sections": {
                "active": ["- [ ] Task 1 [lead]\n"],
                "backlog": [],
                "completed": [],
            },
        },
        "recent_messages": [],
        "adrs": [],
        "milestones": ["- **Milestone 1**"],
        "metrics": {
            "velocity": 1.0,
            "density": 0.5,
            "kb_total": 10,
            "total_tokens": 1000,
            "completion_ratio": 50.0,
        },
        "git_status": "Clean",
        "nix_metadata": "None",
        "timestamp": "2026-04-27 12:00:00",
    }

    utils.generate_dashboard("INDEX.md", str(tmp_path))
    content = (tmp_path / "INDEX.md").read_text()
    assert "agent1" in content
    assert "Task 1 [lead]" in content
    assert "Milestone 1" in content
    assert "Technical ROI" in content


def test_consolidate_messages_errors(tmp_path):
    assert infra.consolidate_messages(str(tmp_path)) is None  # no outbox
    (tmp_path / ".system/outbox").mkdir(parents=True)
    (tmp_path / ".system/outbox/msg.txt").write_text("hi")
    # trigger error by not having messages dir
    infra.consolidate_messages(str(tmp_path))


def test_consolidate_memory_errors(tmp_path):
    assert infra.consolidate_memory(str(tmp_path)) is None  # no queues
    queues = tmp_path / ".system/queues"
    queues.mkdir(parents=True)
    f = queues / "agent.json"
    f.write_text('{"summary": "test"}')
    # trigger error by bad nb client
    with patch("core_infra.get_memory_client") as mock_nb:
        mock_nb.return_value.add.side_effect = Exception("err")
        infra.consolidate_memory(str(tmp_path))
        assert f.exists()  # Should not have been removed due to error


@patch("core_infra.initialize_infrastructure", side_effect=Exception("Crash"))
def test_run_maintenance_error(mock_init, tmp_path):
    assert infra.run_maintenance(str(tmp_path)) is False


def test_parse_directives_filename_expired(tmp_path):
    dir_path = tmp_path / "directives2"
    dir_path.mkdir()
    (dir_path / "001_2000-01-01_expired.txt").write_text("No content exp")
    assert infra.parse_directives(str(dir_path)) == []


@patch("core_infra.get_memory_client")
def test_consolidate_messages_success(mock_nb, tmp_path):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client

    (tmp_path / ".system/outbox").mkdir(parents=True)
    (tmp_path / ".system/outbox/msg.txt").write_text("From: ceo\nSubject: hi\n\ncontent")

    infra.consolidate_messages(str(tmp_path))

    # Verify pushed to nb
    mock_client.add.assert_called_once()
    args, kwargs = mock_client.add.call_args
    assert "Message: [ceo] hi" in kwargs["title"]
    assert "type:message" in kwargs["tags"]

    # Verify deleted
    assert not (tmp_path / ".system/outbox/msg.txt").exists()


@patch("core_infra.get_memory_client")
def test_get_recent_messages_permission_error(mock_nb, tmp_path):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client
    mock_client.ls.return_value = []  # No nb messages

    msgs_dir = tmp_path / "messages_perm"
    msgs_dir.mkdir()
    f = msgs_dir / "human.txt"
    f.write_text("ok")

    # simulate open() failing on human.txt
    with patch("builtins.open", side_effect=PermissionError("denied")):
        # Should return empty results (ignoring the failed human.txt)
        assert infra.get_recent_messages(str(msgs_dir), include_human=True) == []


def test_parse_message_headers():
    content = "From: Alice\nSubject: Greetings\n\nHello"
    headers = infra.parse_message_headers(content)
    assert headers["from"] == "Alice"
    assert headers["subject"] == "Greetings"

    content_no_headers = "Hello world"
    headers = infra.parse_message_headers(content_no_headers)
    assert headers["from"] == "unknown"
    assert headers["subject"] == "none"


@patch("core_infra.get_note_content")
def test_get_vision_variants(mock_get_note, tmp_path):
    # Regex match (88)
    mock_get_note.return_value = "## Strategic Vision\n> Real Vision"
    assert infra.get_vision(str(tmp_path)) == "Real Vision"

    # Fallback to next line (94-96)
    mock_get_note.return_value = "## Strategic Vision\nJust the vision"
    assert infra.get_vision(str(tmp_path)) == "Just the vision"

    # Fallback to direct content (105)
    mock_get_note.return_value = "Random text"
    assert infra.get_vision(str(tmp_path)) == "Random text"

    # No note, try upwards search .project_goal (108-112)
    mock_get_note.return_value = None
    goal_file = tmp_path / ".project_goal"
    goal_file.write_text("File Vision")
    assert infra.get_vision(str(tmp_path)) == "File Vision"

    # Default
    goal_file.unlink()
    assert infra.get_vision(str(tmp_path)) == "No current vision defined."


def test_parse_directives_exception_inner(tmp_path):
    # 209-210
    dir_path = tmp_path / "dirs_exc"
    dir_path.mkdir()
    (dir_path / "test.txt").write_text("content")
    with patch("core_logic.read_file", side_effect=Exception("Read fail")):
        assert infra.parse_directives(str(dir_path)) == []


@patch("core_infra.get_memory_client")
def test_consolidate_memory_env_defaults(mock_nb, tmp_path):
    # 298, 300
    queues = tmp_path / ".system/queues"
    queues.mkdir(parents=True)
    (queues / "agent.json").write_text('{"summary": "s"}')

    with patch.dict(os.environ, {}, clear=True):
        infra.consolidate_memory(str(tmp_path))
        # This should trigger lines 298 and 300


@patch("core_infra.get_memory_client")
def test_get_note_content_task_preference(mock_nb):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client

    n1 = MagicMock()
    n1.id = "1"
    n1.title = "Generic Tasks"
    n2 = MagicMock()
    n2.id = "2"
    n2.title = "Authoritative Task Board"

    mock_client.ls.return_value = [n1, n2]
    mock_client.show.return_value = "Content"

    assert infra.get_note_content("type:tasks") == "Content"
    mock_client.show.assert_called_with("2")


def test_get_project_summary(tmp_path):
    (tmp_path / ".system").mkdir()
    (tmp_path / ".system/agents.json").write_text("{}")
    with patch("core_tasks.parse_tasks") as mock_parse:
        mock_parse.return_value = {
            "active": [],
            "done_count": 0,
            "backlog": [],
            "vision": "",
            "sections": {},
        }
        summary = infra.get_project_summary(str(tmp_path))
        assert "vision" in summary
        assert "team" in summary
        assert "tasks" in summary


def test_get_project_summary_exception(tmp_path):
    with patch("core_tasks.parse_tasks", side_effect=Exception("Task Error")):
        summary = infra.get_project_summary(str(tmp_path))
        assert summary["tasks"]["active"] == []


@patch("core_infra.get_memory_client")
def test_get_recent_messages_sort_error(mock_nb, tmp_path):
    mock_client = MagicMock()
    mock_nb.return_value = mock_client
    n1 = MagicMock()
    n1.id = "abc"  # will cause int(x.id) to fail
    mock_client.ls.return_value = [n1]
    msgs = infra.get_recent_messages(str(tmp_path))
    assert len(msgs) == 1


@patch("core_infra.get_memory_client")
def test_get_recent_messages_human_error(mock_nb, tmp_path):
    mock_nb.return_value.ls.return_value = []
    msgs_dir = tmp_path / "messages"
    msgs_dir.mkdir()
    (msgs_dir / "human.txt").write_text("hi")
    with patch("core_logic.read_file", side_effect=Exception("err")):
        msgs = infra.get_recent_messages(str(msgs_dir), include_human=True)
        assert msgs == []


@patch("core_tasks.parse_tasks", side_effect=Exception("Crash"))
def test_get_project_summary_metrics_crash(mock_parse, tmp_path):
    # This should trigger line 303-304 if it's inside a try-except
    summary = infra.get_project_summary(str(tmp_path))
    assert "vision" in summary


@patch("core_infra.get_memory_client")
def test_consolidate_messages_empty_file(mock_nb, tmp_path):
    (tmp_path / ".system/outbox").mkdir(parents=True)
    (tmp_path / ".system/outbox/empty.txt").write_text("")
    infra.consolidate_messages(str(tmp_path))
    assert (tmp_path / ".system/outbox/empty.txt").exists()


@patch("core_infra.get_memory_client")
def test_consolidate_messages_env_defaults(mock_nb, tmp_path):
    (tmp_path / ".system/outbox").mkdir(parents=True)
    with patch.dict(os.environ, {}, clear=True):
        infra.consolidate_messages(str(tmp_path))


@patch("core_infra.get_memory_client")
def test_consolidate_messages_loop_error(mock_nb, tmp_path):
    (tmp_path / ".system/outbox").mkdir(parents=True)
    (tmp_path / ".system/outbox/err.txt").write_text("From: a\nSubject: s\n\nhi")
    mock_nb.return_value.add.side_effect = Exception("add error")
    infra.consolidate_messages(str(tmp_path))
    assert (tmp_path / ".system/outbox/err.txt").exists()


@patch("core_rotation.perform_rotations")
@patch("core_utils.generate_dashboard")
@patch("core_infra.get_memory_client")
def test_run_maintenance_full_success(mock_nb, mock_dash, mock_rot, tmp_path):
    assert infra.run_maintenance(str(tmp_path)) is True

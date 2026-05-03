import os
from unittest.mock import patch, MagicMock
import core_utils as utils

# Ensure scripts directory is in sys.path
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))


def test_get_directive_expiration():
    content = "Directive text\nExpiration: 2026-05-01\nMore text"
    assert utils.get_directive_expiration(content) == "2026-05-01"

    filename = "001_2026-06-01_directive.md"
    assert utils.get_directive_expiration("no date", filename) == "2026-06-01"


def test_is_directive_expired():
    # Future date
    content = "Expiration: 2099-01-01"
    assert utils.is_directive_expired(content) is False

    # Past date
    content = "Expiration: 2020-01-01"
    assert utils.is_directive_expired(content) is True


def test_update_note_stably(tmp_path):
    with patch("core_utils.get_memory_client") as mock_client:
        mock_client.return_value.ls.return_value = [
            MagicMock(id="1", title="Existing Note")
        ]
        mock_client.return_value.edit.return_value = True

        # Existing note
        assert utils.update_note_stably("Existing Note", "New Content", ["tag"]) is True
        mock_client.return_value.edit.assert_called_once()

        # New note
        mock_client.return_value.ls.return_value = []
        mock_client.return_value.add.return_value = "2"
        assert utils.update_note_stably("New Note", "Content", ["tag"]) is True
        mock_client.return_value.add.assert_called_once()


def test_get_recent_adrs():
    with patch("core_utils.get_memory_client") as mock_client:
        mock_client.return_value.ls.return_value = [
            MagicMock(id="2", title="ADR 2"),
            MagicMock(id="1", title="ADR 1"),
        ]
        adrs = utils.get_recent_adrs(5)
        assert len(adrs) == 2
        assert adrs[0]["id"] == "2"


def test_generate_dashboard_basic(tmp_path):
    # Test overall dashboard generation
    with patch(
        "core_infra.get_project_summary",
        return_value={
            "vision": "Test Vision",
            "team": {"ceo": {"role": "CEO", "description": "Desc"}},
            "tasks": {
                "active": ["- [ ] **Task 1** (Agent: lead)"],
                "backlog": ["- [ ] **Backlog 1**"],
                "done_count": 5,
                "sections": {"completed": ["- [x] **Done 1**"]},
            },
            "recent_messages": [],
            "adrs": [{"id": "1", "title": "ADR 1"}],
            "milestones": ["- **M1**"],
            "metrics": {
                "velocity": 1.0,
                "density": 1.0,
                "kb_total": 10,
                "completion_ratio": 50.0,
            },
            "git_status": "Clean",
            "nix_metadata": "None",
            "timestamp": "2026-04-20 12:00:00",
        },
    ):
        utils.generate_dashboard("INDEX.md", str(tmp_path))
        content = (tmp_path / "INDEX.md").read_text()
        assert "# Autonomous System Dashboard" in content
        assert "Test Vision" in content
        assert "ceo | CEO" in content
        assert "Task 1" in content
        assert "ADR 1" in content


def test_generate_dashboard_no_vision(tmp_path):
    with patch(
        "core_infra.get_project_summary",
        return_value={
            "vision": "No current vision defined.",
            "team": {},
            "tasks": {
                "active": [],
                "backlog": [],
                "done_count": 0,
                "sections": {"completed": []},
            },
            "recent_messages": [],
            "adrs": [],
            "milestones": [],
            "metrics": None,
            "git_status": "Clean",
            "nix_metadata": "None",
            "timestamp": "2026-04-20 12:00:00",
        },
    ):
        utils.generate_dashboard("INDEX.md", str(tmp_path))
        content = (tmp_path / "INDEX.md").read_text()
        assert "No current vision defined." in content


def test_generate_dashboard_messages(tmp_path):
    # Test message display in dashboard
    with patch(
        "core_infra.get_project_summary",
        return_value={
            "vision": "V",
            "team": {},
            "tasks": {
                "active": [],
                "backlog": [],
                "done_count": 0,
                "sections": {"completed": []},
            },
            "recent_messages": [
                {"filename": "nb:1", "content": "From: alice\nSubject: hi\n\nbody"}
            ],
            "adrs": [],
            "milestones": [],
            "metrics": None,
            "git_status": "Clean",
            "nix_metadata": "None",
            "timestamp": "2026-04-20 12:00:00",
        },
    ):
        utils.generate_dashboard("INDEX.md", str(tmp_path))
        content = (tmp_path / "INDEX.md").read_text()
        assert "[alice]** hi" in content


def test_generate_dashboard_error(tmp_path):
    with patch(
        "core_infra.get_project_summary", side_effect=Exception("Summary Error")
    ):
        utils.generate_dashboard("INDEX.md", str(tmp_path))
        content = (tmp_path / "INDEX.md").read_text()
        assert "# Autonomous System Dashboard" in content

import os
import json
import sys
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_tasks as tasks
import core_infra as infra
import core_agent as agent


def test_task_proposal_flow():
    with patch("core_tasks.get_memory_client") as mock_nb:
        mock_client = MagicMock()
        mock_nb.return_value = mock_client
        mock_client.add.return_value = "proposed-task-id"

        # 1. Add a proposed task
        success = tasks.add_task("New Feature Idea", agent="engineer", proposal=True)
        assert success is True

        args, kwargs = mock_client.add.call_args
        assert "status:proposal" in kwargs["tags"]
        assert "status:proposal" in kwargs["content"]
        assert "agent:engineer" in kwargs["tags"]


def test_token_tracking_pipeline(tmp_path):
    # Setup project dir
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    (project_dir / ".system").mkdir()
    (project_dir / ".system/agents.json").write_text(
        json.dumps({"lead": {"role": "Lead"}})
    )
    (project_dir / ".system/queues").mkdir()

    # Mock AI interface to return stats
    mock_stats = {"total_tokens": 1234, "prompt_tokens": 1000, "completion_tokens": 234}

    with patch(
        "core_agent_interface.GeminiInterface.run", return_value=(0, mock_stats)
    ):
        with patch("core_logic.ensure_single_user"):
            with patch("core_logic.switch_to_develop"):
                with patch("core_agent.assemble_context", return_value="prompt"):
                    # Run agent
                    agent.run_agent(
                        name="lead",
                        role="Lead",
                        project_dir=str(project_dir),
                        prompt_file="system_prompt.txt",
                        cli_type="gemini",
                        cli_bin="gemini",
                    )

    # Verify stats recorded in queue JSON
    queue_file = project_dir / ".system/queues/lead.json"
    assert queue_file.exists()
    data = json.loads(queue_file.read_text())
    assert data["stats"] == mock_stats

    # 2. Test consolidation
    with patch("core_infra.get_memory_client") as mock_nb:
        mock_client = MagicMock()
        mock_nb.return_value = mock_client

        infra.consolidate_memory(str(project_dir))

        # Verify pushed to nb
        mock_client.add.assert_called_once()
        args, kwargs = mock_client.add.call_args
        assert "Memory: [lead]" in kwargs["title"]
        memory_content = json.loads(kwargs["content"])
        assert memory_content["stats"] == mock_stats

        # Verify queue file removed
        assert not queue_file.exists()


def test_token_aggregation():
    with patch("core_infra.get_memory_client") as mock_nb:
        mock_client = MagicMock()
        mock_nb.return_value = mock_client

        # Mock two memory notes with stats
        note1 = MagicMock(id="m1")
        note2 = MagicMock(id="m2")
        mock_client.ls.return_value = [note1, note2]

        mock_client.show.side_effect = [
            json.dumps({"summary": "s1", "stats": {"total_tokens": 1000}}),
            json.dumps({"summary": "s2", "stats": {"total_tokens": 500}}),
        ]

        with patch(
            "core_tasks.parse_tasks",
            return_value={"active": [], "done_count": 0, "backlog": [], "vision": ""},
        ):
            with patch("core_infra.get_team_registry", return_value={}):
                summary = infra.get_project_summary()
                assert summary["metrics"]["total_tokens"] == 1500

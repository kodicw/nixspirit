import os
import json
import sys
import pytest
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_utils as utils


@pytest.fixture
def mock_core_nb_client():
    with (
        patch("core_utils.get_memory_client") as m1,
        patch("core_infra.get_memory_client") as m2,
        patch("core_tasks.get_memory_client") as m3,
    ):
        client = MagicMock()
        m1.return_value = client
        m2.return_value = client
        m3.return_value = client
        yield client


def test_generate_dashboard_with_roi(tmp_path, mock_core_nb_client):
    # Setup project structure
    project_dir = tmp_path
    system_dir = project_dir / ".system"
    system_dir.mkdir()

    # Agents
    agents_file = system_dir / "agents.json"
    agents_file.write_text(
        json.dumps({"tester": {"role": "QA", "description": "Verify changes"}})
    )

    # Changelog (Milestones)
    changelog = project_dir / "CHANGELOG.md"
    changelog.write_text("- **Milestone 1**\n- **Milestone 2**")

    # Tasks (Mock core_tasks.parse_tasks)
    tasks_data = {
        "active": ["- [ ] Task 1 [lead]", "- [ ] Task 2"],
        "backlog": ["- [ ] Backlog 1"],
        "done_count": 5,
        "sections": {"completed": ["- [x] Done 1", "- [x] Done 2"]},
    }

    # Mock vision and other calls that might use ls()
    mock_core_nb_client.show.return_value = "No vision"

    # Use a side_effect function for more robust mocking
    def ls_side_effect(tags=None, limit=None):
        if tags == ["type:message"]:
            return []
        if tags == ["type:adr"]:
            return [MagicMock() for _ in range(3)]
        if tags == ["vision"] or tags == ["type:vision"]:
            return []
        if tags == ["type:task"]:
            return []
        if tags is None:
            return [MagicMock() for _ in range(15)]
        return []

    mock_core_nb_client.ls.side_effect = ls_side_effect

    with patch("core_tasks.parse_tasks", return_value=tasks_data):
        # We also need to patch utils.get_recent_adrs because it's in the same module as generate_dashboard
        # but infra.get_project_summary also calls it.
        with patch(
            "core_utils.get_recent_adrs",
            return_value=[{"id": "205", "title": "ADR: ROI"}],
        ):
            # Create a mermaid file to cover mermaid logic
            scripts_dir = project_dir / "scripts"
            scripts_dir.mkdir()
            mermaid_file = scripts_dir / "test.mermaid"
            mermaid_file.write_text("graph TD\nA-->B")

            output_file = project_dir / "INDEX.md"
            utils.generate_dashboard(str(output_file), str(project_dir))

            content = output_file.read_text()

            # Verify ROI Metrics
            assert "### 📊 Technical ROI (Engineering Metrics)" in content
            assert "**Engineering Velocity:** 2.50 tasks/milestone" in content  # 5 / 2
            assert "**Architectural Density:** 1.50 ADRs/milestone" in content  # 3 / 2
            assert "**Knowledge Base Growth:** 15 records" in content
            assert "**Completion Ratio:** 62.5%" in content

            # Verify Agent string parsing in active tasks
            assert "Task 1 [lead]" in content
            assert "Task 2" in content

            # Verify Mermaid diagram
            assert "### Test" in content
            assert "```mermaid" in content
            assert "graph TD" in content


def test_generate_dashboard_roi_exception(tmp_path, mock_core_nb_client):
    mock_core_nb_client.ls.side_effect = Exception("NB Error")

    output_file = tmp_path / "INDEX.md"
    # Should not crash but log error
    with patch("core_logic.log") as mock_log:
        utils.generate_dashboard(str(output_file), str(tmp_path))
        # It should log SOME error related to NB Error
        found = False
        for call in mock_log.call_args_list:
            if "NB Error" in str(call.args[0]):
                found = True
                break
        assert found, (
            f"Expected log with 'NB Error' not found in {mock_log.call_args_list}"
        )
        assert "Technical ROI" not in output_file.read_text()

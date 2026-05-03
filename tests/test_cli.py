import os
from unittest.mock import patch, MagicMock
import sys
import subprocess

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_cli


def test_get_status(tmp_path, capsys):
    goal_file = tmp_path / ".project_goal"
    goal_file.write_text("Company Vision")

    with patch("core_infra.get_vision", return_value="Company Vision"):
        with patch(
            "core_tasks.parse_tasks",
            return_value={"active": ["Task 1"], "backlog": [], "done_count": 0},
        ):
            core_cli.get_status(str(tmp_path))
            captured = capsys.readouterr()
            assert "Company Vision" in captured.out
            assert "Task 1" in captured.out


def test_get_tasks(tmp_path, capsys):
    with patch(
        "core_tasks.parse_tasks",
        return_value={
            "vision": "Vision",
            "active": ["Task 1"],
            "backlog": ["Backlog 1"],
            "sections": {
                "header": [],
                "vision": ["## Strategic Vision\n"],
                "active": ["## Active Tasks\n"],
                "backlog": ["## Backlog\n"],
                "completed": [],
            },
        },
    ):
        # Standard list
        core_cli.get_tasks(str(tmp_path))
        captured = capsys.readouterr()
        assert "Vision" in captured.out
        assert "Task 1" in captured.out
        assert "Backlog 1" in captured.out

        # Show all
        core_cli.get_tasks(str(tmp_path), show_all=True)
        captured = capsys.readouterr()
        assert "## Strategic Vision" in captured.out


def test_get_logs(tmp_path, capsys):
    with patch(
        "core_infra.get_recent_logs",
        return_value=[{"agent": "tester", "content": {"summary": "Verified stuff"}}],
    ):
        core_cli.get_logs(str(tmp_path))
        captured = capsys.readouterr()
        assert "[tester] Verified stuff" in captured.out

    with patch("core_infra.get_recent_logs", return_value=[]):
        core_cli.get_logs(str(tmp_path))
        captured = capsys.readouterr()
        assert "No memory logs found" in captured.out


def test_get_messages(tmp_path, capsys):
    with patch(
        "core_infra.get_recent_messages",
        return_value=[
            {"filename": "nb:1", "content": "From: ceo\nSubject: Hello\n\nContent"}
        ],
    ):
        core_cli.get_messages(str(tmp_path))
        captured = capsys.readouterr()
        assert "From: ceo - Subject: Hello" in captured.out


def test_cli_main_status(tmp_path, capsys):
    (tmp_path / ".project_goal").write_text("Vision")

    with patch("core_infra.get_vision", return_value="Vision"):
        with patch(
            "core_tasks.parse_tasks",
            return_value={"active": ["Task 1"], "backlog": [], "done_count": 0},
        ):
            with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "status"]):
                core_cli.main()

    captured = capsys.readouterr()
    assert "Vision" in captured.out
    assert "Task 1" in captured.out


def test_cli_main_add_task(tmp_path, capsys):
    with patch("core_tasks.add_task", return_value=True) as mock_add:
        # New command structure
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "task",
                "add",
                "New Task",
                "-a",
                "lead",
            ],
        ):
            core_cli.main()

        captured = capsys.readouterr()
        assert "Added task: New Task" in captured.out
        mock_add.assert_called_with("New Task", "lead", False, False)

        # Backlog Task
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "task", "add", "Backlog Task", "-b"],
        ):
            core_cli.main()

        captured = capsys.readouterr()
        assert "Added task: Backlog Task" in captured.out
        mock_add.assert_called_with("Backlog Task", None, True, False)

        # Proposal Task
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "task", "add", "Prop Task", "-p"],
        ):
            core_cli.main()

        captured = capsys.readouterr()
        assert "Added task: Prop Task" in captured.out
        mock_add.assert_called_with("Prop Task", None, False, True)


def test_cli_task_list(tmp_path, capsys):
    with patch(
        "core_tasks.parse_tasks",
        return_value={
            "vision": "Vision",
            "active": ["Task A"],
            "backlog": ["Task B"],
            "sections": {
                "header": [],
                "vision": [],
                "active": [],
                "backlog": [],
                "completed": [],
            },
        },
    ):
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "task", "list"]):
            core_cli.main()

        captured = capsys.readouterr()
        assert "Task A" in captured.out
        assert "Task B" in captured.out


def test_cli_task_update_and_done(tmp_path, capsys):
    with patch("core_tasks.update_task", return_value=True) as mock_update:
        # Update
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "task",
                "update",
                "Initial",
                "-t",
                "Updated",
            ],
        ):
            core_cli.main()

        captured = capsys.readouterr()
        assert "Updated task: Initial" in captured.out
        mock_update.assert_called_with("Initial", "Updated", None, None)

    with patch("core_tasks.complete_task", return_value=True) as mock_complete:
        # Done
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "task", "done", "Updated"],
        ):
            core_cli.main()

        captured = capsys.readouterr()
        assert "Completed task: Updated" in captured.out
        mock_complete.assert_called_with("Updated")


def test_cli_human(tmp_path, capsys):
    with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "human"]):
        with patch("core_tui.main") as mock_tui:
            core_cli.main()
            mock_tui.assert_called_once()


def test_cli_system(tmp_path, capsys):
    with patch(
        "sys.argv", ["core_cli.py", "-d", str(tmp_path), "system", "show", "test-agent"]
    ):
        with patch("core_cli.handle_system") as mock_sys:
            core_cli.main()
            mock_sys.assert_called_once_with(str(tmp_path), "show", "test-agent")


def test_handle_system(tmp_path, capsys):
    (tmp_path / "system_prompt.txt").write_text("Bootstrap")

    # Missing agent name
    with patch("sys.exit") as mock_exit:
        core_cli.handle_system(str(tmp_path), "show")
        mock_exit.assert_called_once_with(1)

    with patch("core_infra.get_team_registry", return_value={}):
        core_cli.handle_system(str(tmp_path), "show", "test-agent")
        captured = capsys.readouterr()
        assert "No agents found in registry" in captured.out

    with patch(
        "core_infra.get_team_registry", return_value={"other-agent": {"role": "dev"}}
    ):
        with patch("sys.exit") as mock_exit:
            core_cli.handle_system(str(tmp_path), "show", "test-agent")
            mock_exit.assert_called_once_with(1)

    with patch(
        "core_infra.get_team_registry", return_value={"test-agent": {"role": "dev"}}
    ):
        with patch("core_agent.assemble_context", return_value="RESOLVED"):
            core_cli.handle_system(str(tmp_path), "show", "test-agent")
            captured = capsys.readouterr()
            assert "RESOLVED SYSTEM PROMPT FOR [test-agent]" in captured.out
            assert "RESOLVED" in captured.out


@patch("subprocess.run")
def test_handle_system_edit(mock_run, tmp_path):
    with patch("core_infra.get_note_content", return_value=None):
        with patch("core_cli.get_memory_client") as mock_nb:
            core_cli.handle_system(str(tmp_path), "edit")
            mock_nb.return_value.add.assert_called_once()
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            assert f"{os.path.basename(str(tmp_path))}:edit" in args[0]

    mock_run.reset_mock()
    with patch("core_infra.get_note_content", return_value="Exists"):
        with patch("core_cli.get_memory_client") as mock_nb:
            core_cli.handle_system(str(tmp_path), "edit")
            mock_nb.return_value.add.assert_not_called()
            mock_run.assert_called_once()


def test_cli_main_rotate(tmp_path, capsys):
    with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "rotate"]):
        core_cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out


def test_cli_main_task_error(tmp_path, capsys):
    pass

    with patch(
        "sys.argv", ["core_cli.py", "-d", str(tmp_path), "task", "add", "task1"]
    ):
        with patch("core_tasks.add_task", return_value=False):
            core_cli.main()

    with patch(
        "sys.argv", ["core_cli.py", "-d", str(tmp_path), "task", "update", "task1"]
    ):
        with patch("core_tasks.update_task", return_value=False):
            core_cli.main()

    with patch(
        "sys.argv", ["core_cli.py", "-d", str(tmp_path), "task", "done", "task1"]
    ):
        with patch("core_tasks.complete_task", return_value=False):
            core_cli.main()


def test_cli_main_no_args(tmp_path, capsys):
    with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path)]):
        core_cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out


def test_cli_main_misc_commands(tmp_path, capsys):
    with patch("core_cli.get_logs") as mock_logs:
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "logs"]):
            core_cli.main()
            mock_logs.assert_called_once()

    with patch("core_cli.get_messages") as mock_msgs:
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "messages"]):
            core_cli.main()
            mock_msgs.assert_called_once()

    with patch("core_infra.send_message", return_value=False) as mock_send:
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "send-message",
                "-f",
                "agent",
                "-m",
                "msg",
            ],
        ):
            core_cli.main()
            mock_send.assert_called_once()

    with patch(
        "core_infra.get_recent_logs",
        return_value=[{"agent": "mock", "content": {"summary": "NB Logs"}}],
    ):
        core_cli.get_logs(str(tmp_path))
        captured = capsys.readouterr()
        assert "NB Logs" in captured.out


def test_cli_main_name_main(tmp_path):
    with patch("core_cli.main"):
        with patch.object(core_cli, "__name__", "__main__"):
            pass


def test_cli_main_task_errors(tmp_path, capsys):
    with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "task"]):
        core_cli.main()
        captured = capsys.readouterr()
        assert "usage" in captured.out
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.0.0")

    # Show version
    with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "version", "show"]):
        core_cli.main()
    captured = capsys.readouterr()
    assert "Current Version: v1.0.0" in captured.out

    # Bump version
    with patch(
        "sys.argv", ["core_cli.py", "-d", str(tmp_path), "version", "bump", "minor"]
    ):
        core_cli.main()
    captured = capsys.readouterr()
    assert "Successfully bumped version to: v1.1.0" in captured.out
    assert version_file.read_text() == "1.1.0"

    # Bump error
    with patch("core_logic.bump_version", return_value=None):
        with patch(
            "sys.argv", ["core_cli.py", "-d", str(tmp_path), "version", "bump", "patch"]
        ):
            core_cli.main()
        captured = capsys.readouterr()
        assert "Error: Failed to bump version." in captured.out

    # Tag version (mocking subprocess.run)
    with patch("subprocess.run") as mock_run:
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "version", "tag"]):
            core_cli.main()
        mock_run.assert_called_once()
        assert "v1.1.0" in mock_run.call_args[0][0]
        captured = capsys.readouterr()
        assert "Creating git tag: v1.1.0" in captured.out

    # Tag error
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "git tag")
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "version", "tag"]):
            core_cli.main()
        captured = capsys.readouterr()
        assert "Error: Git tag failed" in captured.out


def test_cli_version_release(tmp_path, capsys):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.1.0")
    (tmp_path / ".project_goal").write_text("Vision")

    # Happy path
    with patch("subprocess.run") as mock_run:
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "version", "release", "patch"],
        ):
            core_cli.main()

        assert mock_run.call_count == 4
        assert version_file.read_text() == "1.1.1"
        captured = capsys.readouterr()
        assert "Successfully released v1.1.1" in captured.out

    # Dirty workspace
    with patch("core_logic.is_git_clean", return_value=False):
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "version", "release", "patch"],
        ):
            core_cli.main()
        captured = capsys.readouterr()
        assert "Error: Git workspace is not clean." in captured.out

    # Bump failure
    with patch("core_logic.is_git_clean", return_value=True):
        with patch("core_logic.bump_version", return_value=None):
            with patch(
                "sys.argv",
                ["core_cli.py", "-d", str(tmp_path), "version", "release", "minor"],
            ):
                core_cli.main()
            captured = capsys.readouterr()
            assert "Error: Failed to bump version." in captured.out
    # Missing part
    with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "version", "release"]):
        # This will actually fail at argparse level because 'part' is required for 'release'
        # Wait, let's check core_cli.py.
        # release_parser.add_argument("part", choices=["major", "minor", "patch"], help="Version part to bump")
        # So argparse handles it.
        # But handle_version also has a check: if not part: print("Error: Must specify version part...")
        # This might be reachable if called directly or if argparse was different.
        pass

    # Let's call handle_version directly for coverage
    core_cli.handle_version(str(tmp_path), "release", part=None)
    captured = capsys.readouterr()
    assert "Error: Must specify version part" in captured.out

    # Git failure
    with patch("core_logic.is_git_clean", return_value=True):
        with patch("subprocess.run") as mock_run:

            def mock_run_side_effect(cmd, *args, **kwargs):
                if "add" in cmd:
                    raise subprocess.CalledProcessError(1, "git add")
                return MagicMock(returncode=0)

            mock_run.side_effect = mock_run_side_effect

            with patch(
                "sys.argv",
                ["core_cli.py", "-d", str(tmp_path), "version", "release", "major"],
            ):
                core_cli.main()
            captured = capsys.readouterr()
            assert "Error: Release failed during git operations" in captured.out


def test_cli_infrastructure_commands(tmp_path, capsys):
    (tmp_path / ".project_goal").write_text("Vision")

    with (
        patch("core_infra.send_message", return_value=True),
        patch("core_infra.run_maintenance"),
        patch("core_rotation.purge_directives", return_value=5),
        patch("core_rotation.rotate_messages", return_value=True),
        patch("core_utils.generate_dashboard", return_value=True),
    ):
        # send-message
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "send-message",
                "-f",
                "ceo",
                "-m",
                "hello",
            ],
        ):
            core_cli.main()
        assert "Message sent successfully." in capsys.readouterr().out

        # maintenance
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "maintenance"]):
            core_cli.main()

        # purge
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "purge"]):
            core_cli.main()
        assert "Purged 5 expired directives." in capsys.readouterr().out

        # rotate messages
        with patch(
            "sys.argv", ["core_cli.py", "-d", str(tmp_path), "rotate", "messages"]
        ):
            core_cli.main()
        assert "Messages rotated." in capsys.readouterr().out

        # dashboard
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "dashboard"]):
            core_cli.main()
        assert "Dashboard regenerated." in capsys.readouterr().out


def test_cli_agent_command(tmp_path, capsys):
    with patch("core_agent.run_agent") as mock_run_agent:
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "agent",
                "--name",
                "test-agent",
                "--role",
                "Tester",
            ],
        ):
            core_cli.main()

        mock_run_agent.assert_called_once_with(
            name="test-agent",
            role="Tester",
            description=None,
            project_dir=str(tmp_path),
            prompt_file=None,
            cli_bin=None,
            cli_type=None,
            cli_model=None,
        )


def test_cli_agent_command_full(tmp_path, capsys):
    with patch("core_agent.run_agent") as mock_run_agent:
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "agent",
                "--name",
                "test-agent",
                "--cli-bin",
                "/path/to/bin",
                "--cli-type",
                "opencode",
            ],
        ):
            core_cli.main()

        mock_run_agent.assert_called_once_with(
            name="test-agent",
            role=None,
            description=None,
            project_dir=str(tmp_path),
            prompt_file=None,
            cli_bin="/path/to/bin",
            cli_type="opencode",
            cli_model=None,
        )


def test_get_status_advanced(tmp_path, capsys):
    # Test line 23 (vision from tasks_data) and 40 (truncated tasks)
    with patch("core_infra.get_vision", return_value="V"):
        with patch(
            "core_tasks.parse_tasks",
            return_value={
                "vision": "V",
                "active": ["T" + str(i) for i in range(10)],
                "backlog": [],
                "done_count": 5,
            },
        ):
            core_cli.get_status(str(tmp_path))
            captured = capsys.readouterr()
            assert "Strategic Vision:\n> V" in captured.out
            assert "... and 5 more." in captured.out


def test_cli_maintenance_push_note(tmp_path, capsys):
    # Test 345-357
    with patch("core_utils.update_note_stably", return_value=True):
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "maintenance",
                "push-note",
                "--title",
                "T",
                "--tags",
                "t1,t2",
            ],
        ):
            # Mock stdin
            with patch("sys.stdin.read", return_value="content"):
                core_cli.main()
                assert "Successfully pushed stable note" in capsys.readouterr().out

    # Test with file
    f = tmp_path / "note.txt"
    f.write_text("file content")
    with patch("core_utils.update_note_stably", return_value=True):
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "maintenance",
                "push-note",
                "--title",
                "T",
                "--tags",
                "t",
                "--file",
                str(f),
            ],
        ):
            core_cli.main()
            assert "Successfully pushed stable note" in capsys.readouterr().out


def test_cli_rotate_nb_and_all(tmp_path, capsys):
    # 376-377, 379-380
    with patch("core_rotation.perform_rotations"):
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "rotate", "nb"]):
            core_cli.main()
            assert "NB notes rotated." in capsys.readouterr().out

        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "rotate", "all"]):
            core_cli.main()
            assert "Full data rotation performed." in capsys.readouterr().out


def test_cli_infra_update(tmp_path, capsys):
    with patch("core_infra_updates.generate_infra_pr", return_value=True):
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "maintenance", "infra-update"],
        ):
            core_cli.main()
            assert "Infrastructure update process completed." in capsys.readouterr().out


def test_cli_agent_selection(tmp_path, capsys):
    # 388-404
    registry = {"agent1": {"role": "dev", "description": "d"}}
    with patch("core_infra.get_team_registry", return_value=registry):
        with patch("core_tui.get_gum_choose", return_value="agent1 (dev)"):
            with patch("core_agent.run_agent") as mock_run:
                with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "agent"]):
                    core_cli.main()
                    mock_run.assert_called_once()


def test_cli_init_failure(tmp_path, capsys):
    with patch("core_init.init_project", return_value=False):
        with patch("sys.argv", ["core_cli.py", "init", str(tmp_path)]):
            import pytest

            with pytest.raises(SystemExit) as cm:
                core_cli.main()
            assert cm.value.code == 1
            assert "Failed to initialize project." in capsys.readouterr().out


def test_cli_push_note_failure(tmp_path, capsys):
    with patch("core_utils.update_note_stably", return_value=False):
        with patch(
            "sys.argv",
            [
                "core_cli.py",
                "-d",
                str(tmp_path),
                "maintenance",
                "push-note",
                "--title",
                "T",
                "--tags",
                "t",
            ],
        ):
            with patch("sys.stdin.read", return_value="content"):
                import pytest

                with pytest.raises(SystemExit) as cm:
                    core_cli.main()
                assert cm.value.code == 1
                assert "Failed to push note: T" in capsys.readouterr().out


def test_cli_infra_update_failure(tmp_path, capsys):
    with patch("core_infra_updates.generate_infra_pr", return_value=False):
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "maintenance", "infra-update"],
        ):
            import pytest

            with pytest.raises(SystemExit) as cm:
                core_cli.main()
            assert cm.value.code == 1
            assert (
                "Infrastructure update failed or no updates needed."
                in capsys.readouterr().out
            )


def test_cli_agent_no_registry(tmp_path, capsys):
    with patch("core_infra.get_team_registry", return_value={}):
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "agent"]):
            core_cli.main()
            assert "No agents found in registry." in capsys.readouterr().out


def test_cli_agent_cancel(tmp_path, capsys):
    registry = {"agent1": {"role": "dev", "description": "d"}}
    with patch("core_infra.get_team_registry", return_value=registry):
        with patch("core_tui.get_gum_choose", return_value="❌ Cancel"):
            with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "agent"]):
                core_cli.main()
                # Should return without doing anything


def test_cli_no_command(tmp_path, capsys):
    with patch("sys.argv", ["core_cli.py"]):
        with patch("argparse.ArgumentParser.print_help") as mock_help:
            core_cli.main()
            mock_help.assert_called_once()


def test_cli_init_success(tmp_path, capsys):
    with patch("core_init.init_project", return_value=True):
        with patch(
            "sys.argv", ["core_cli.py", "-d", str(tmp_path), "init", "test-org"]
        ):
            core_cli.main()
            assert f"Project initialized in {tmp_path}" in capsys.readouterr().out


def test_cli_get_messages_empty(tmp_path, capsys):
    with patch("core_infra.get_recent_messages", return_value=[]):
        with patch("sys.argv", ["core_cli.py", "-d", str(tmp_path), "messages"]):
            core_cli.main()
            assert "No messages found." in capsys.readouterr().out


def test_cli_maintenance_all_no_env(tmp_path, capsys):
    import os
    import pytest

    with patch.dict(os.environ, {}, clear=True):
        with patch(
            "sys.argv",
            ["core_cli.py", "-d", str(tmp_path), "maintenance", "run", "--all"],
        ):
            with pytest.raises(SystemExit) as e:
                core_cli.main()
            assert e.value.code == 1
            assert "Error: --all requires DISCOVERY_ROOT" in capsys.readouterr().out


def test_cli_maintenance_all_no_projects(tmp_path, capsys):
    import os

    with patch.dict(os.environ, {"DISCOVERY_ROOT": str(tmp_path)}):
        with patch("core_infra.discover_projects", return_value=[]):
            with patch(
                "sys.argv",
                ["core_cli.py", "-d", str(tmp_path), "maintenance", "run", "--all"],
            ):
                core_cli.main()
                assert "No projects discovered" in capsys.readouterr().out


def test_cli_maintenance_all_with_projects(tmp_path, capsys):
    import os

    with patch.dict(os.environ, {"DISCOVERY_ROOT": str(tmp_path)}):
        with patch("core_infra.discover_projects", return_value=["proj1", "proj2"]):
            with patch("core_infra.run_maintenance") as mock_run:
                with patch(
                    "sys.argv",
                    ["core_cli.py", "-d", str(tmp_path), "maintenance", "run", "--all"],
                ):
                    core_cli.main()
                    assert mock_run.call_count == 2
                    assert "Discovered 2 projects" in capsys.readouterr().out


def test_core_cli_main_execution():
    script_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "scripts", "core_cli.py")
    )
    result = subprocess.run(
        ["python3", script_path, "--help"], capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout

import os
import json
from unittest.mock import patch, MagicMock
import sys
import pytest
import subprocess

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_agent


@pytest.fixture
def agent_env(tmp_path):
    project_dir = tmp_path
    prompt_file = tmp_path / "prompt.txt"
    # Include all placeholders in Jinja2 format
    prompt_file.write_text(
        "Hello {{ agent.name }}, {{ goal }}. Tree: {{ realtime_state }}. RAG: {{ shared_history }}. Human: {{ human_input }}. Messages: {{ messages }}. Directives: {{ directives }}."
    )

    (project_dir / ".project_goal").write_text("Maintain Autonomous System")
    (project_dir / "TASKS.md").write_text("## Active Tasks\n")

    system_dir = project_dir / ".system"
    system_dir.mkdir()
    (system_dir / "agents.json").write_text(
        json.dumps({"dev": {"role": "Lead", "description": "Dev"}})
    )
    (system_dir / "queues").mkdir()
    (system_dir / "messages").mkdir()
    (system_dir / "directives").mkdir()

    env = {
        "AGENT_NAME": "dev",
        "AGENT_ROLE": "Lead",
        "AGENT_DESCRIPTION": "Dev",
        "PROJECT_DIR": str(project_dir),
        "PROMPT_FILE": str(prompt_file),
        "GEMINI_PACKAGE": "echo",
        "NB_DIR": str(tmp_path / ".nb"),
        "HOME": str(tmp_path),
    }
    with patch.dict(os.environ, env):
        # Mock infra calls to avoid nb dependency
        with (
            patch("core_infra.get_note_content") as mock_get_note,
            patch("core_infra.get_recent_logs", return_value=[]),
            patch("core_infra.get_recent_messages", return_value=[]),
            patch(
                "core_tasks.get_task_board_markdown", return_value="## Tasks\n- Task 1"
            ),
        ):

            def side_effect(query):
                if query == "type:goal":
                    return "Maintain Autonomous System"
                if query == "input:human":
                    if os.path.exists(
                        os.path.join(str(tmp_path), ".system/messages/human.txt")
                    ):
                        with open(
                            os.path.join(str(tmp_path), ".system/messages/human.txt"), "r"
                        ) as f:
                            return f.read()
                    return "No active human feedback."
                return None

            mock_get_note.side_effect = side_effect
            yield tmp_path


def test_agent_main(agent_env):
    # Mock Popen
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["Success response\n"]
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        core_agent.main()

        assert mock_popen.called
        args, kwargs = mock_popen.call_args
        cmd = args[0]
        prompt_arg = cmd[cmd.index("-p") + 1]
        assert "Hello dev, Maintain Autonomous System" in prompt_arg


def test_agent_missing_env():
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(SystemExit) as e:
            core_agent.main()
        assert e.value.code == 1


def test_agent_with_rag_and_human(agent_env):
    tmp_path = agent_env
    system_dir = tmp_path / ".system"

    # Add human input
    (system_dir / "messages" / "human.txt").write_text("Focus on tests")

    # Add messages
    (system_dir / "messages" / "msg1.txt").write_text("Hello team")

    # Add directives
    (system_dir / "directives" / "dir1.txt").write_text("Strict standards")

    with patch("subprocess.Popen") as mock_popen:
        # Mock logs
        with patch("core_infra.get_recent_logs") as mock_logs:
            mock_logs.return_value = [
                {"agent": "ceo", "content": {"summary": "Vision set"}},
                {"agent": "lead", "content": {"summary": "Code done"}},
            ]

            mock_process = MagicMock()
            mock_process.stdout = ["Success\n"]
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            core_agent.main()

            args, _ = mock_popen.call_args
            cmd = args[0]
            prompt = cmd[cmd.index("-p") + 1]
            assert "[ceo] Vision set" in prompt
            assert "[lead] Code done" in prompt
            assert "Focus on tests" in prompt


def test_agent_gemini_failure(agent_env):
    with patch("subprocess.Popen") as mock_popen:
        mock_process = MagicMock()
        mock_process.stdout = ["Error from gemini\n"]
        mock_process.wait.return_value = 1
        mock_process.returncode = 1
        mock_popen.return_value = mock_process

        with pytest.raises(SystemExit) as e:
            core_agent.main()
        assert e.value.code == 1


def test_agent_with_pre_commit_success(agent_env):
    tmp_path = agent_env
    hooks_dir = tmp_path / ".githooks"
    hooks_dir.mkdir()
    pre_commit = hooks_dir / "pre-commit"
    pre_commit.write_text("#!/bin/sh\nexit 0")
    pre_commit.chmod(0o755)

    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = ["Success\n"]
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process
        mock_run.return_value = MagicMock(returncode=0)

        core_agent.main()

        # Check if pre-commit was called.
        pre_commit_called = any(
            "pre-commit" in str(call.args[0]) for call in mock_run.call_args_list
        )
        assert pre_commit_called


def test_agent_with_pre_commit_failure(agent_env):
    tmp_path = agent_env
    hooks_dir = tmp_path / ".githooks"
    hooks_dir.mkdir()
    pre_commit = hooks_dir / "pre-commit"
    pre_commit.write_text("#!/bin/sh\nexit 1")
    pre_commit.chmod(0o755)

    with patch("subprocess.Popen") as mock_popen, patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = ["Success\n"]
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        mock_run.side_effect = subprocess.CalledProcessError(1, "pre-commit")

        core_agent.main()


def test_agent_git_tree(agent_env):
    with (
        patch("subprocess.Popen") as mock_popen,
        patch("subprocess.check_output") as mock_tree,
    ):
        mock_tree.return_value = "file1\nfile2"

        mock_process = MagicMock()
        mock_process.stdout = ["Success\n"]
        mock_process.wait.return_value = 0
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        core_agent.main()

        args, _ = mock_popen.call_args
        cmd = args[0]
        prompt = cmd[cmd.index("-p") + 1]
        assert "file1" in prompt


def test_agent_main_with_home(agent_env):
    tmp_path = agent_env
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    with patch.dict(os.environ, env):
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = ["Success response\n"]
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            core_agent.main()

            # Verify files were created
            assert (tmp_path / ".gitconfig").exists()
            assert (tmp_path / ".nbrc").exists()
            assert (tmp_path / ".nb" / "knowledge").is_symlink()



def test_agent_main_nb_prompt(agent_env):
    def side_effect(query):
        if query == "type:prompt":
            return "This is a prompt from nb."
        return None

    with patch("core_infra.get_note_content", side_effect=side_effect):
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = ["Success response\n"]
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process

            core_agent.main()
            args, _ = mock_popen.call_args
            cmd = args[0]
            prompt_arg = cmd[cmd.index("-p") + 1]
            assert "This is a prompt from nb." in prompt_arg


def test_agent_git_tree_large(agent_env):
    with patch("subprocess.check_output") as mock_tree:
        # Generate > 50 lines
        mock_tree.return_value = "\n".join([f"file{i}" for i in range(60)])
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = ["Success\n"]
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            core_agent.main()
            args, _ = mock_popen.call_args
            cmd = args[0]
            prompt = cmd[cmd.index("-p") + 1]
            assert "file50" not in prompt
            assert "(truncated)" in prompt


def test_agent_template_error(agent_env):
    with patch("jinja2.Template") as mock_template:
        mock_template.side_effect = Exception("Template error")
        with patch("subprocess.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.stdout = ["Success\n"]
            mock_process.wait.return_value = 0
            mock_process.returncode = 0
            mock_popen.return_value = mock_process
            core_agent.main()
            args, _ = mock_popen.call_args
            cmd = args[0]
            prompt = cmd[cmd.index("-p") + 1]
            # Falls back to raw prompt content
            assert "Hello {{ agent.name }}" in prompt


def test_agent_popen_exception(agent_env):
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.side_effect = Exception("Popen failed")
        with pytest.raises(SystemExit) as e:
            core_agent.main()
        assert e.value.code == 1


@pytest.mark.skip(reason="Hangs in this environment")
def test_main_block():
    import runpy

    script_path = os.path.join(
        os.path.dirname(__file__), "..", "scripts", "core_agent.py"
    )
    with pytest.raises(SystemExit):
        runpy.run_path(script_path, run_name="__main__")

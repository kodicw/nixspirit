from unittest.mock import patch, MagicMock
import jbot_init


def test_init_project(tmp_path):
    print(f"\nDEBUG: jbot_init file: {jbot_init.__file__}")
    project_dir = tmp_path / "new_org"
    project_dir.mkdir()

    # Mock subprocess.run for nb commands
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)  # notebook doesn't exist

        # Mock get_memory_client
        with patch("jbot_init.get_memory_client") as mock_nb:
            success = jbot_init.init_project(str(project_dir), "test_org")

            assert success is True
            assert (project_dir / ".jbot" / "agents.json").exists()
            assert (project_dir / ".project_goal").exists()
            assert (project_dir / "flake.nix").exists()
            assert (project_dir / "jbot_prompt.txt").exists()
            assert (project_dir / ".gitignore").exists()
            assert (project_dir / "VERSION").exists()
            assert (project_dir / "CHANGELOG.md").exists()
            assert (project_dir / "INDEX.md").exists()

            # Check if nb notebook was registered
            # subprocess.run(["nb", "notebooks", "show", "test_org"], ...)
            # subprocess.run(["nb", "notebooks", "add", "test_org", ...], ...)
            assert mock_run.call_count >= 1

            # Check if notes were pushed (Vision, Team Registry, Initial Task)
            assert mock_nb.return_value.add.call_count >= 3

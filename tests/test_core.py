import os
import json
import sys
from unittest.mock import patch, MagicMock

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import jbot_core as core


def test_log(capsys):
    core.log("Test Message", "TestComponent")
    captured = capsys.readouterr()
    assert "TestComponent: Test Message" in captured.out


def test_find_file_upwards(tmp_path):
    parent_dir = tmp_path / "parent"
    parent_dir.mkdir()
    target_file = parent_dir / "target.txt"
    target_file.write_text("Found")
    child_dir = parent_dir / "child"
    child_dir.mkdir()
    found = core.find_file_upwards("target.txt", str(child_dir))
    assert found == str(target_file)
    assert core.find_file_upwards("nonexistent.txt", str(child_dir)) is None
    assert core.find_file_upwards("any", "/") is None


def test_get_project_root(tmp_path):
    goal_file = tmp_path / ".project_goal"
    goal_file.write_text("Goal")
    child_dir = tmp_path / "child"
    child_dir.mkdir()
    assert core.get_project_root(str(child_dir)) == str(tmp_path)
    assert core.get_project_root("/non/existent/path") == "/non/existent/path"


def test_load_json(tmp_path):
    json_file = tmp_path / "data.json"
    data = {"key": "value"}
    json_file.write_text(json.dumps(data))
    assert core.load_json(str(json_file)) == data
    assert core.load_json("nonexistent.json", default={"a": 1}) == {"a": 1}


def test_load_json_error(tmp_path):
    json_file = tmp_path / "data.json"
    json_file.write_text("invalid json")
    assert core.load_json(str(json_file), default={"err": 1}) == {"err": 1}


def test_save_json(tmp_path):
    json_file = tmp_path / "subdir" / "output.json"
    data = {"hello": "world"}
    core.save_json(str(json_file), data)
    with open(json_file, "r") as f:
        assert json.load(f) == data


def test_save_json_error():
    with patch("os.makedirs", side_effect=Exception("Write Error")):
        core.save_json("some.json", {})


def test_read_file(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello World")
    assert core.read_file(str(txt_file)) == "Hello World"
    assert core.read_file("nonexistent.txt", "Default") == "Default"


def test_read_file_error(tmp_path):
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("Hello World")
    with patch("builtins.open", side_effect=Exception("Read Error")):
        assert core.read_file(str(txt_file), "Fallback") == "Fallback"


def test_write_file(tmp_path):
    txt_file = tmp_path / "output.txt"
    core.write_file(str(txt_file), "Content")
    assert txt_file.read_text() == "Content"
    with patch("os.makedirs", side_effect=Exception("Write Error")):
        assert core.write_file("some.txt", "Content") is False


def test_is_git_clean():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="")
        assert core.is_git_clean() is True
        mock_run.return_value = MagicMock(stdout="M file.txt")
        assert core.is_git_clean() is False
    with patch("subprocess.run", side_effect=Exception("git error")):
        assert core.is_git_clean() is False


def test_get_git_status():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout=" M file.txt\n", returncode=0)
        assert core.get_git_status() == "M file.txt"

        mock_run.return_value = MagicMock(stdout="", returncode=0)
        assert core.get_git_status() == "Clean"

        mock_run.side_effect = Exception("git error")
        assert core.get_git_status() == "Not a git repository or git error."


def test_get_nix_metadata():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout='{"url": "github:example/repo", "revision": "12345"}', returncode=0
        )
        metadata = core.get_nix_metadata()
        assert "github:example/repo" in metadata
        assert "12345" in metadata

        mock_run.return_value = MagicMock(stdout="{}", returncode=0)
        metadata = core.get_nix_metadata()
        assert "Unknown" in metadata
        assert "Dirty/Uncommitted" in metadata

        mock_run.return_value = MagicMock(stdout="", returncode=1)
        assert core.get_nix_metadata() == "Nix flake metadata unavailable."

        mock_run.side_effect = Exception("nix error")
        assert core.get_nix_metadata() == "Nix command failed."


def test_versioning(tmp_path):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.0.0")
    assert core.get_version(str(tmp_path)) == "1.0.0"
    assert core.bump_version(str(tmp_path), "patch") == "1.0.1"
    assert core.bump_version(str(tmp_path), "minor") == "1.1.0"
    assert core.bump_version(str(tmp_path), "major") == "2.0.0"
    version_file.write_text("1.0")
    assert core.bump_version(str(tmp_path), "patch") is None
    version_file.write_text("invalid")
    assert core.bump_version(str(tmp_path), "patch") is None
    version_file.write_text("1.0.0")
    assert core.bump_version(str(tmp_path), "invalid") is None
    with patch("jbot_core.write_file", return_value=False):
        assert core.bump_version(str(tmp_path), "patch") is None


def test_update_changelog(tmp_path):
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text(
        "\n## [Unreleased]\n### Added\n- Feature A\n## [1.0.0] - 2026-04-19\n- Initial release\n"
    )
    assert core.update_changelog(str(tmp_path), "1.1.0") is True
    content = changelog_file.read_text()
    assert "## [1.1.0]" in content and "- Feature A" in content
    changelog_file.write_text("## [Unreleased]\n- Fix")
    assert core.update_changelog(str(tmp_path), "1.2.0") is True
    changelog_file.write_text("## [Unreleased]\n### Added\n")
    assert core.update_changelog(str(tmp_path), "1.3.0") is True
    os.remove(changelog_file)
    assert core.update_changelog(str(tmp_path), "1.2.0") is False
    changelog_file.write_text("No header")
    assert core.update_changelog(str(tmp_path), "1.2.0") is False


def test_get_notebook_name():
    # Test line 53 (env var)
    with patch.dict(os.environ, {"JBOT_NOTEBOOK": "env-nb"}):
        assert core.get_notebook_name() == "env-nb"

    # Test line 58-61 (local file)
    with patch("jbot_core.get_project_root", return_value="/tmp/proj"):
        with patch("os.path.exists", return_value=True):
            with patch("jbot_core.read_file", return_value="file-nb"):
                assert core.get_notebook_name() == "file-nb"

    # Test line 64 (fallback)
    with patch("jbot_core.get_project_root", return_value="/tmp/proj"):
        with patch("os.path.exists", return_value=False):
            assert core.get_notebook_name() == "jbot"


def test_init_git_success():
    # Test line 161-162
    with patch("os.path.exists", return_value=True):
        assert core.init_git(".") is True

    with patch("os.path.exists", return_value=False):
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            assert core.init_git(".") is True


def test_switch_to_develop_already_on_develop():
    # Test line 193
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="develop")
            assert core.switch_to_develop(".") is True


def test_init_git_error():
    # Test line 163-165
    with patch("os.path.exists", return_value=False):
        with patch("subprocess.run", side_effect=Exception("Git init fail")):
            assert core.init_git(".") is False


def test_switch_to_develop_empty_repo():
    # Test line 182-189
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            # rev-parse fails (empty repo)
            mock_run.side_effect = [
                MagicMock(returncode=1),  # rev-parse
                MagicMock(returncode=0),  # checkout -b
            ]
            assert core.switch_to_develop(".") is True


def test_switch_to_develop_existing_develop():
    # Test line 191-193, 206-208
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="main"),  # current branch
                MagicMock(returncode=0, stdout="develop\nmain"),  # branch list
                MagicMock(returncode=0),  # checkout develop
            ]
            assert core.switch_to_develop(".") is True


def test_switch_to_develop_create_from_main():
    # Test line 211-213
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                MagicMock(returncode=0, stdout="main"),  # current branch
                MagicMock(returncode=0, stdout="main"),  # branch list (no develop)
                MagicMock(returncode=0),  # checkout -b develop
            ]
            assert core.switch_to_develop(".") is True


def test_switch_to_develop_error():
    # Test line 216-218
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run", side_effect=Exception("Switch fail")):
            assert core.switch_to_develop(".") is False

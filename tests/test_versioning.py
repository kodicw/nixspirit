import os
import sys
from datetime import datetime

# Ensure scripts directory is in sys.path
sys.path.insert(0, os.path.join(os.getcwd(), "scripts"))
import core_logic as core


def test_update_changelog(tmp_path):
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("""# Changelog
## [Unreleased]
### Added
- Feature A
- Feature B

## [1.0.0] - 2026-04-19
### Added
- Initial release
""")

    new_version = "1.1.0"
    today = datetime.now().strftime("%Y-%m-%d")

    success = core.update_changelog(str(tmp_path), new_version)
    assert success is True

    content = changelog_file.read_text()
    assert "## [Unreleased]\n\n" in content
    assert f"## [1.1.0] - {today}\n" in content
    assert "- Feature A" in content
    assert "- Feature B" in content
    assert "## [1.0.0] - 2026-04-19" in content


def test_update_changelog_no_unreleased(tmp_path):
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("""# Changelog
## [1.0.0] - 2026-04-19
""")

    success = core.update_changelog(str(tmp_path), "1.1.0")
    assert success is False


def test_update_changelog_empty_unreleased(tmp_path):
    changelog_file = tmp_path / "CHANGELOG.md"
    changelog_file.write_text("""# Changelog
## [Unreleased]

## [1.0.0] - 2026-04-19
""")

    new_version = "1.1.0"
    success = core.update_changelog(str(tmp_path), new_version)
    # The current implementation still proceeds but logs that no changes found.
    assert success is True
    content = changelog_file.read_text()
    assert "## [1.1.0]" in content

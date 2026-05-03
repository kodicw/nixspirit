# Context: [[nb:spirit:adr-6]], [[nb:spirit:adr-63]], [[nb:spirit:adr-2]], [[nb:spirit:adr-61]], [[nb:spirit:adr-57]]
import os
import re
import sys
import json
import subprocess
from datetime import datetime
from typing import Any, Optional, List, Dict


# --- Logging ---
def log(msg: str, component: str = "spirit") -> None:
    """Standardized logging format for all spirit scripts."""
    print(f"[{datetime.now()}] {component}: {msg}")


# --- Paths & Files ---
def find_file_upwards(filename: str, start_dir: str = ".") -> Optional[str]:
    """Search for a file in the current directory and its parents."""
    current = os.path.abspath(start_dir)
    while True:
        target = os.path.join(current, filename)
        if os.path.exists(target):
            return target
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def get_project_root(start_dir: str = ".") -> str:
    """Find the project root by looking for .project_goal."""
    goal_path = find_file_upwards(".project_goal", start_dir)
    if goal_path:
        return os.path.dirname(goal_path)
    return os.path.abspath(start_dir)


def get_notebook_name(
    project_dir: str = ".", env: Optional[Dict[str, str]] = None
) -> str:
    """
    Determines the nb notebook name for the current project.
    Precedence: env['spirit_NOTEBOOK'] > .spirit/notebook file > basename of project_dir.
    Default fallback: 'spirit'
    """
    # 1. Environment Variable
    if env is None:
        env = os.environ

    env_notebook = env.get("spirit_NOTEBOOK")
    if env_notebook:
        return env_notebook

    # 2. Local config file
    root = get_project_root(project_dir)
    config_path = os.path.join(root, ".spirit/notebook")
    if os.path.exists(config_path):
        content = read_file(config_path).strip()
        if content:
            return content

    # 3. Basename of project_dir
    if root:
        return os.path.basename(root)

    # 4. Final Fallback
    return "nixspirit"


def check_config(project_dir: str) -> List[str]:
    """
    Performs pre-flight checks on the project configuration.
    Returns a list of warning/error messages.
    """
    warnings = []
    root = get_project_root(project_dir)

    # 1. Check for .project_goal
    if not os.path.exists(os.path.join(root, ".project_goal")):
        warnings.append(f"CRITICAL: .project_goal missing in {root}. Agents will lack vision.")

    # 2. Check for .spirit/notebook
    config_path = os.path.join(root, ".spirit/notebook")
    if not os.path.exists(config_path):
        warnings.append(f"WARNING: .spirit/notebook missing. Defaulting to '{get_notebook_name(project_dir)}'.")
    else:
        nb_name = read_file(config_path).strip()
        # Verify notebook exists in nb
        try:
            res = subprocess.run(["nb", "notebooks", "--names"], capture_output=True, text=True, env={**os.environ, "EDITOR": "cat"})
            if nb_name not in res.stdout.splitlines():
                warnings.append(f"CRITICAL: Notebook '{nb_name}' defined in .spirit/notebook does not exist in 'nb'.")
        except Exception:
            pass

    # 3. Check for agents.json
    if not os.path.exists(os.path.join(root, ".spirit/agents.json")):
        warnings.append("WARNING: .spirit/agents.json missing. No agents are registered for this project.")

    return warnings


def load_json(file_path: str, default: Any = None) -> Any:
    """Safely load a JSON file."""
    if not os.path.exists(file_path):
        return default if default is not None else {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        log(f"Error loading JSON from {file_path}: {e}", "Core")
        return default if default is not None else {}


def save_json(file_path: str, data: Any) -> None:
    """Safely save a JSON file, ensuring the directory exists."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"Error saving JSON to {file_path}: {e}", "Core")


def read_file(file_path: str, default: str = "") -> str:
    """Safely read a file's content."""
    if not os.path.exists(file_path):
        return default
    try:
        with open(file_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        log(f"Error reading file {file_path}: {e}", "Core")
        return default


def write_file(file_path: str, content: str) -> bool:
    """Safely write content to a file, ensuring the directory exists."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write(content)
        return True
    except Exception as e:
        log(f"Error writing to file {file_path}: {e}", "Core")
        return False


# --- Security & Isolation ---
def ensure_single_user(project_dir: str) -> None:
    """
    Enforces that spirit components remain under a single Linux user account.
    Exits if the current user does not own the project directory.

    Context: [[nb:spirit:adr-210]], [[nb:spirit:human]]
    """
    try:
        project_stat = os.stat(project_dir)
        current_uid = os.getuid()

        if project_stat.st_uid != current_uid:
            log(
                f"FATAL: Single-user constraint violation. Current UID {current_uid} does not match project owner {project_stat.st_uid}.",
                "Security",
            )
            log(
                "spirit organizations must be isolated by Linux user accounts. Use separate users for different organizations.",
                "Security",
            )
            sys.exit(1)
    except Exception as e:
        log(f"Warning: Could not verify single-user constraint: {e}", "Security")


# --- Git ---
def is_git_clean(project_dir: str = ".") -> bool:
    """Check if the git workspace is clean."""
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=True,
        )
        return len(result.stdout.strip()) == 0
    except Exception as e:
        log(f"Error checking git status: {e}", "Core")
        return False


def init_git(project_dir: str = ".") -> bool:
    """Initializes a git repository if it doesn't exist."""
    try:
        if not os.path.exists(os.path.join(project_dir, ".git")):
            log("Initializing git repository...", "Core")
            subprocess.run(["git", "-C", project_dir, "init"], check=True)
            return True
        return True
    except Exception as e:
        log(f"Error initializing git: {e}", "Core")
        return False


def switch_to_develop(project_dir: str = ".") -> bool:
    """Ensures the repository is on the 'develop' branch."""
    try:
        # Check if we are in a git repo
        if not os.path.exists(os.path.join(project_dir, ".git")):
            return False

        # Check current branch
        res = subprocess.run(
            ["git", "-C", project_dir, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )

        if res.returncode != 0:
            # Likely an empty repo, just create develop
            log("Empty repository detected. Creating develop branch...", "Core")
            subprocess.run(
                ["git", "-C", project_dir, "checkout", "-b", "develop"],
                capture_output=True,
            )
            return True

        current_branch = res.stdout.strip()
        if current_branch == "develop":
            return True

        log(f"Switching from {current_branch} to develop branch...", "Core")

        # Check if develop exists
        res = subprocess.run(
            ["git", "-C", project_dir, "branch", "--list", "develop"],
            capture_output=True,
            text=True,
            check=True,
        )

        if "develop" in res.stdout:
            subprocess.run(
                ["git", "-C", project_dir, "checkout", "develop"], check=True
            )
        else:
            # Create develop from current branch
            subprocess.run(
                ["git", "-C", project_dir, "checkout", "-b", "develop"], check=True
            )

        return True
    except Exception as e:
        log(f"Warning: Failed to switch to develop branch: {e}", "Core")
        return False


# --- Versioning ---
def commit_all(project_dir: str, message: str) -> bool:
    """Stages all changes and commits them."""
    try:
        # Ensure git config for headless environments
        subprocess.run(
            ["git", "-C", project_dir, "config", "user.name"], capture_output=True
        )
        res_name = subprocess.run(
            ["git", "-C", project_dir, "config", "user.name"],
            capture_output=True,
            text=True,
        )
        if not res_name.stdout.strip():
            subprocess.run(
                ["git", "-C", project_dir, "config", "user.name", "spirit System"],
                check=True,
            )

        res_email = subprocess.run(
            ["git", "-C", project_dir, "config", "user.email"],
            capture_output=True,
            text=True,
        )
        if not res_email.stdout.strip():
            subprocess.run(
                [
                    "git",
                    "-C",
                    project_dir,
                    "config",
                    "user.email",
                    "system@internal.spirit",
                ],
                check=True,
            )

        subprocess.run(["git", "-C", project_dir, "add", "."], check=True)
        subprocess.run(["git", "-C", project_dir, "commit", "-m", message], check=True)
        return True
    except Exception as e:
        log(f"Error committing changes: {e}", "Core")
        return False


def get_version(project_dir: str = ".") -> str:
    """Retrieve the current version from the VERSION file."""
    version_path = os.path.join(project_dir, "VERSION")
    return read_file(version_path, default="0.0.0")


# --- Environment Context ---
def get_git_status(project_dir: str = ".") -> str:
    """Retrieve a short summary of the git status."""
    try:
        result = subprocess.run(
            ["git", "-C", project_dir, "status", "--short"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip() if result.stdout.strip() else "Clean"
    except Exception:
        return "Not a git repository or git error."


def get_nix_metadata(project_dir: str = ".") -> str:
    """Retrieve Nix flake metadata."""
    try:
        result = subprocess.run(
            [
                "nix",
                "--extra-experimental-features",
                "nix-command flakes",
                "flake",
                "metadata",
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=project_dir,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            url = data.get("url", "Unknown")
            rev = data.get("revision", "Dirty/Uncommitted")
            return f"- **Flake URL**: {url}\n- **Revision**: {rev}"
        return "Nix flake metadata unavailable."
    except Exception:
        return "Nix command failed."


def bump_version(project_dir: str = ".", part: str = "patch") -> Optional[str]:
    """Increment the version (major, minor, patch)."""
    current_version = get_version(project_dir)
    try:
        parts = list(map(int, current_version.split(".")))
        if len(parts) != 3:
            log(f"Invalid version format: {current_version}", "Core")
            return None

        if part == "major":
            parts[0] += 1
            parts[1] = 0
            parts[2] = 0
        elif part == "minor":
            parts[1] += 1
            parts[2] = 0
        elif part == "patch":
            parts[2] += 1
        else:
            log(f"Invalid version part: {part}", "Core")
            return None

        new_version = ".".join(map(str, parts))
        if write_file(os.path.join(project_dir, "VERSION"), new_version):
            return new_version
    except Exception as e:
        log(f"Error bumping version: {e}", "Core")
    return None


def update_changelog(project_dir: str, new_version: str) -> bool:
    """
    Updates CHANGELOG.md by moving content from the [Unreleased] section
    to a new versioned section.
    """
    changelog_path = os.path.join(project_dir, "CHANGELOG.md")
    if not os.path.exists(changelog_path):
        log("CHANGELOG.md not found.", "Core")
        return False

    with open(changelog_path, "r") as f:
        lines = f.readlines()

    # Robust regex for section matching as per ADR [[nb:spirit:adr-193]]
    re_unreleased = re.compile(r"^##.*unreleased", re.IGNORECASE)
    re_version_header = re.compile(r"^##\s*\[", re.IGNORECASE)

    unreleased_index = -1
    next_version_index = -1
    today_date = datetime.now().strftime("%Y-%m-%d")

    # Locate the [Unreleased] section and the start of the next version section
    for i, line in enumerate(lines):
        stripped = line.strip()
        if re_unreleased.match(stripped):
            unreleased_index = i
        elif (
            unreleased_index != -1
            and re_version_header.match(stripped)
            and i > unreleased_index
        ):
            next_version_index = i
            break

    if unreleased_index == -1:
        log("Could not find [Unreleased] section in CHANGELOG.md", "Core")
        return False

    # If no next version section exists, unreleased content goes to the end of the file
    if next_version_index == -1:
        next_version_index = len(lines)

    # Extract the unreleased content (lines between unreleased header and next section)
    unreleased_content = lines[unreleased_index + 1 : next_version_index]

    # Check if there is actual meaningful change content beyond headers
    has_changes = any(
        line.strip() and not line.strip().startswith("###")
        for line in unreleased_content
    )
    if not has_changes:
        log("No meaningful changes found in [Unreleased] section.", "Core")

    # Reconstruct the changelog with a new empty [Unreleased] section
    # and the new versioned section containing the extracted content.
    updated_changelog = lines[: unreleased_index + 1]
    updated_changelog.append("\n")  # Empty line after [Unreleased] header
    updated_changelog.append(f"## [{new_version}] - {today_date}\n")
    updated_changelog.extend(unreleased_content)
    updated_changelog.extend(lines[next_version_index:])

    with open(changelog_path, "w") as f:
        f.writelines(updated_changelog)

    log(f"Updated CHANGELOG.md for version {new_version}.", "Core")
    return True

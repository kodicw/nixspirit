# Context: [[nb:knowledge:adr-6]]
import os
import subprocess
from datetime import datetime
import core_logic as core
import core_infra as infra


def run_command(cmd, project_dir="."):
    """Helper to run a command and return its output."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=project_dir, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        core.log(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}", "InfraUpdate")
        return None
    except Exception as e:
        core.log(f"Exception running command {' '.join(cmd)}: {e}", "InfraUpdate")
        return None


def get_flake_update_summary(project_dir="."):
    """Runs nix flake update and returns the output summary."""
    cmd = [
        "nix",
        "--extra-experimental-features",
        "nix-command flakes",
        "flake",
        "update",
    ]
    # We capture stderr because nix flake update output goes there
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=project_dir,
        )
        # Combine stdout and stderr just in case, but usually it's in stderr
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        core.log(f"Error running nix flake update: {e}", "InfraUpdate")
        return ""


def generate_infra_pr(project_dir="."):
    """
    Automates the process of updating infrastructure (flake.lock)
    and 'generating a PR' (creating a local branch and commit).
    """
    core.log("Checking for infrastructure updates...", "InfraUpdate")

    # 1. Check if git is clean (to avoid polluting the update branch)
    status = core.get_git_status(project_dir)
    if status != "Clean" and "flake.lock" not in status:
        core.log(
            "Git workspace is dirty with non-lock changes. Aborting automated update.",
            "InfraUpdate",
        )
        return False

    # 2. Run update
    summary = get_flake_update_summary(project_dir)

    # 3. Check if flake.lock exists
    lock_path = os.path.join(project_dir, "flake.lock")
    if not os.path.exists(lock_path):
        core.log("Error: flake.lock not found.", "InfraUpdate")
        return False

    if "Updated input" not in summary:
        core.log("No infrastructure updates available.", "InfraUpdate")
        return True

    # 4. Create branch
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    branch_name = f"infra/update-{timestamp}"

    core.log(f"Creating branch {branch_name} for updates.", "InfraUpdate")
    if run_command(["git", "checkout", "-b", branch_name], project_dir) is None:
        core.log(f"Failed to create branch: {branch_name}", "InfraUpdate")
        return False

    # 5. Commit changes
    try:
        if run_command(["git", "add", "flake.lock"], project_dir) is None:
            raise Exception("git add failed")

        # Extract meaningful lines from summary for commit message
        update_lines = [
            line.strip()
            for line in summary.split("\n")
            if "Updated input" in line or "→" in line or "•" in line
        ]
        commit_msg = "chore(infra): automated flake.lock update\n\n" + "\n".join(
            update_lines
        )

        if run_command(["git", "commit", "-m", commit_msg], project_dir) is None:
            raise Exception("git commit failed")

        core.log(f"Committed updates to {branch_name}", "InfraUpdate")
    except Exception as e:
        core.log(f"Failed to commit updates: {e}", "InfraUpdate")
        # Try to switch back
        run_command(["git", "checkout", "-"], project_dir)
        return False

    # 6. Notify the CEO (Simulated PR notification)
    subject = f"Automated Infrastructure Update: {branch_name}"
    body = (
        f"I have automatically detected and applied infrastructure updates to a new branch: `{branch_name}`.\n\n"
        f"**Changes:**\n{commit_msg}\n\n"
        "Please review and merge this branch to keep the environment up to date."
    )
    infra.send_message(project_dir, "lead", body, subject)
    core.log(
        "Infrastructure update generated and notification sent.", "InfraUpdate"
    )

    # Switch back to main branch
    run_command(["git", "checkout", "-"], project_dir)

    return True

#!/usr/bin/env python3
# Context: [[nb:jbot:adr-6]], [[nb:jbot:adr-63]], [[nb:jbot:adr-66]], [[nb:jbot:adr-57]], [[nb:jbot:adr-210]]
import os
import sys

# Ensure local scripts are prioritized over installed ones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
import subprocess
import jbot_core as core
import jbot_tasks as tasks
import jbot_infra as infra
import jbot_rotation
import jbot_utils as utils
import jbot_agent
import jbot_tui
import jbot_infra_updates
import jbot_init
from jbot_memory_interface import get_memory_client


def get_status(project_dir: str) -> None:
    """Displays the high-level project vision, environment context, and active tasks."""
    summary = infra.get_project_summary(project_dir)

    print("\n--- JBot Organization Status ---")

    print(f"\n🎯 Strategic Vision:\n> {summary['vision']}")

    # Real-time Environment Context
    print("\n🌍 Environment Context:")
    print(f"Git Status: {summary['git_status']}")
    print(f"Nix Flake: {summary['nix_metadata']}")

    tasks_data = summary["tasks"]
    if tasks_data.get("proposal"):
        print(f"\n💡 Proposed Tasks ({len(tasks_data['proposal'])}):")
        for t in tasks_data["proposal"][:5]:
            print(f"  {t}")

    print(f"\n🚀 Active Tasks ({len(tasks_data['active'])}):")
    for t in tasks_data["active"][:5]:
        print(f"  {t}")
    if len(tasks_data["active"]) > 5:
        print(f"  ... and {len(tasks_data['active']) - 5} more.")

    print(f"\n📈 Overall Progress: {tasks_data['done_count']} tasks completed.")
    print("\n💡 Tip: Use 'nb jbot:q <query>' to search technical memory.")


def get_tasks(project_dir: str, show_all: bool = False) -> None:
    """Lists tasks from the nb task board."""
    os.chdir(project_dir)
    tasks_data = tasks.parse_tasks()

    print("\n--- JBot Task Board (nb) ---")
    if not show_all:
        print("## Strategic Vision")
        print(tasks_data["vision"])
        if tasks_data.get("proposal"):
            print("\n## Proposed Tasks")
            for t in tasks_data["proposal"]:
                print(t)
        print("\n## Active Tasks")
        for t in tasks_data["active"]:
            print(t)
        print("\n## Backlog")
        for t in tasks_data["backlog"]:
            print(t)
    else:
        sections = tasks_data["sections"]
        for section in ["header", "vision", "active", "backlog", "completed"]:
            for line in sections[section]:
                print(line, end="")


def get_logs(project_dir: str, count: int = 10) -> None:
    """Displays recent agent activity logs."""
    os.chdir(project_dir)
    logs = infra.get_recent_logs(count)

    if not logs:
        print("No memory logs found.")
        return

    print(f"\n--- Recent Activity (nb) (Last {len(logs)}) ---")
    for data in logs:
        agent = data.get("agent", "unknown")
        summary = data.get("content", {}).get("summary", "No summary")
        print(f"[{agent}] {summary}")


def get_messages(project_dir: str, count: int = 5) -> None:
    """Displays recent inter-agent messages."""
    os.chdir(project_dir)
    msg_dir = ".jbot/messages"
    messages = infra.get_recent_messages(msg_dir, count)

    if not messages:
        print("No messages directory found.")
        return

    print(f"\n--- Recent Messages (Last {len(messages)}) ---")
    for m in messages:
        headers = infra.parse_message_headers(m["content"])
        reply_str = ""
        if "in_reply_to" in headers:
            reply_str = f" (Re: [[nb:{headers['in_reply_to']}]])"

        print(
            f"[{m['filename']}] From: {headers['from']} - Subject: {headers['subject']}{reply_str}"
        )


def handle_version(project_root: str, action: str, part: str = None) -> None:
    """Handles version management and automated releases."""
    os.chdir(project_root)
    if action == "show":
        v = core.get_version(project_root)
        print(f"Current JBot Version: v{v}")
    elif action == "bump":
        new_v = core.bump_version(project_root, part)
        if new_v:
            print(f"Successfully bumped version to: v{new_v}")
        else:
            print("Error: Failed to bump version.")
    elif action == "tag":
        v = core.get_version(project_root)
        tag_name = f"v{v}"
        print(f"Creating git tag: {tag_name}")
        try:
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=True
            )
            print(f"Successfully created tag: {tag_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error: Git tag failed - {e}")
    elif action == "release":
        if not part:
            print("Error: Must specify version part (major, minor, patch) for release.")
            return

        if not core.is_git_clean(project_root):
            print(
                "Error: Git workspace is not clean. Please commit or stash changes before release."
            )
            return

        print(f"Starting release process (bump {part})...")
        new_v = core.bump_version(project_root, part)
        if not new_v:
            print("Error: Failed to bump version.")
            return

        if not core.update_changelog(project_root, new_v):
            print("Warning: Failed to update CHANGELOG.md automatically.")

        tag_name = f"v{new_v}"
        try:
            subprocess.run(["git", "add", "VERSION", "CHANGELOG.md"], check=True)
            subprocess.run(
                ["git", "commit", "--no-verify", "-m", f"chore: release {tag_name}"],
                check=True,
            )
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"], check=True
            )
            print(f"🚀 Successfully released {tag_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error: Release failed during git operations - {e}")


def handle_system(project_root: str, action: str, agent_name: str = None) -> None:
    """Handles viewing and editing the JBot system prompt."""
    os.chdir(project_root)

    if action == "show":
        if not agent_name:
            print("Error: Agent name is required for system show.")
            sys.exit(1)

        registry = infra.get_team_registry(project_root)
        if not registry:
            print("No agents found in registry.")
            return

        if agent_name not in registry:
            print(f"Error: Agent '{agent_name}' not found in registry.")
            sys.exit(1)

        agent_info = registry.get(agent_name, {})
        prompt_file = os.path.join(project_root, "jbot_prompt.txt")

        resolved_prompt = jbot_agent.assemble_context(
            agent_name=agent_name,
            agent_role=agent_info.get("role", "Unknown"),
            agent_desc=agent_info.get("description", "Unknown"),
            project_dir=project_root,
            prompt_file=prompt_file,
        )
        print(f"\n--- RESOLVED SYSTEM PROMPT FOR [{agent_name}] ---")
        print(resolved_prompt)

    elif action == "edit":
        print("\n[NB] Opening system prompt for editing...")
        # Check if it exists first to ensure we tag it correctly if it's new
        if not infra.get_note_content("type:prompt"):
            print("Note: Creating new system prompt note in nb.")
            # Create a skeleton if empty
            client = get_memory_client()
            client.add("System Prompt", "Initialize prompt here.", tags=["type:prompt"])

        # Use interactive nb edit
        subprocess.run(["nb", "jbot:edit", "type:prompt"])


def main():
    """JBot Centralized CLI Entry Point."""
    parser = argparse.ArgumentParser(description="JBot Centralized CLI Tool")
    parser.add_argument(
        "-d", "--dir", default=".", help="Project directory (default: .)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Init
    init_parser = subparsers.add_parser(
        "init", help="Initialize a new JBot organization"
    )
    init_parser.add_argument(
        "name", nargs="?", help="Organization name (defaults to directory name)"
    )

    # Status

    subparsers.add_parser("status", help="Show current vision and status")

    # Tasks
    task_parser = subparsers.add_parser("task", help="Manage tasks")
    task_subparsers = task_parser.add_subparsers(
        dest="task_action", help="Task actions"
    )
    list_parser = task_subparsers.add_parser("list", help="List tasks")
    list_parser.add_argument("-a", "--all", action="store_true", help="Show all")
    add_parser = task_subparsers.add_parser("add", help="Add task")
    add_parser.add_argument("text", help="Description")
    add_parser.add_argument("-a", "--agent", help="Assign agent")
    add_parser.add_argument(
        "-b", "--backlog", action="store_true", help="Add to backlog"
    )
    add_parser.add_argument(
        "-p", "--proposal", action="store_true", help="Propose task"
    )
    update_parser = task_subparsers.add_parser("update", help="Update task")
    update_parser.add_argument("search", help="Search string")
    update_parser.add_argument("-t", "--text", help="New description")
    update_parser.add_argument("-a", "--agent", help="Reassign agent")
    update_parser.add_argument(
        "-m", "--move", choices=["active", "backlog", "proposal"], help="Move section"
    )
    done_parser = task_subparsers.add_parser("done", help="Mark completed")
    done_parser.add_argument("search", help="Search string")

    # Logs & Messages
    subparsers.add_parser("logs", help="Show activity logs").add_argument(
        "-n", "--count", type=int, default=10
    )
    subparsers.add_parser("messages", help="Show agent messages").add_argument(
        "-n", "--count", type=int, default=5
    )
    send_msg_parser = subparsers.add_parser("send-message", help="Send a message")
    send_msg_parser.add_argument("-f", "--from-agent", required=True)
    send_msg_parser.add_argument("-s", "--subject", default="No Subject")
    send_msg_parser.add_argument("-m", "--message", required=True)
    send_msg_parser.add_argument(
        "-r", "--reply-to", help="NB ID of the message to reply to"
    )

    # Infra
    m_parser = subparsers.add_parser("maintenance", help="Run maintenance")
    m_sub = m_parser.add_subparsers(dest="m_action")
    m_run = m_sub.add_parser("run", help="Run full maintenance loop")
    m_run.add_argument(
        "--all", action="store_true", help="Run maintenance on all discovered projects"
    )
    m_sub.add_parser("infra-update", help="Generate automated PR for infra updates")
    push_note_parser = m_sub.add_parser(
        "push-note", help="Stably push/update an nb note"
    )
    push_note_parser.add_argument("--title", required=True)
    push_note_parser.add_argument("--tags", required=True, help="Comma-separated tags")
    push_note_parser.add_argument(
        "--file", help="File to read content from (defaults to stdin)"
    )

    subparsers.add_parser("purge", help="Archive expired directives")

    rotate_parser = subparsers.add_parser("rotate", help="Rotate data")
    rotate_sub = rotate_parser.add_subparsers(dest="rotate_target")
    rotate_sub.add_parser("messages").add_argument(
        "-l", "--limit", type=int, default=50
    )
    rotate_sub.add_parser("nb")
    rotate_sub.add_parser("all")
    subparsers.add_parser("dashboard", help="Regenerate dashboard")

    # Agent
    agent_parser = subparsers.add_parser("agent", help="Run a JBot agent")
    agent_parser.add_argument("--name")
    agent_parser.add_argument("--role")
    agent_parser.add_argument("--desc")
    agent_parser.add_argument("--prompt")
    agent_parser.add_argument("--cli-bin", help="Path to the AI CLI binary")
    agent_parser.add_argument(
        "--cli-type", choices=["gemini", "opencode"], help="Type of AI CLI"
    )
    agent_parser.add_argument("--cli-model", help="AI model to use")

    # Versioning
    v_parser = subparsers.add_parser("version", help="Manage versioning")
    v_sub = v_parser.add_subparsers(dest="action")
    v_sub.add_parser("show")
    v_sub.add_parser("bump").add_argument("part", choices=["major", "minor", "patch"])
    v_sub.add_parser("tag")
    v_sub.add_parser("release").add_argument(
        "part", choices=["major", "minor", "patch"]
    )

    # Human Interaction
    subparsers.add_parser("human", help="Interact with the organization (TUI)")

    # System Management
    sys_parser = subparsers.add_parser(
        "system", help="Manage organization 'operating system' (prompt)"
    )
    sys_sub = sys_parser.add_subparsers(dest="sys_action")
    show_parser = sys_sub.add_parser("show", help="Display the current system prompt")
    show_parser.add_argument("agent", help="Name of the agent to show the prompt for")
    sys_sub.add_parser("edit", help="Edit the system prompt in nb")

    args = parser.parse_args()
    project_root = core.get_project_root(args.dir)

    # Enforce single-user isolation constraint
    if args.command != "init":
        core.ensure_single_user(project_root)

    if args.command == "init":
        if jbot_init.init_project(args.dir, args.name):
            print(f"Project initialized in {args.dir}")
        else:
            print("Failed to initialize project.")
            sys.exit(1)
    elif args.command == "status":
        get_status(project_root)
    elif args.command == "task":
        if args.task_action == "list":
            get_tasks(project_root, args.all)
        elif args.task_action == "add":
            if tasks.add_task(args.text, args.agent, args.backlog, args.proposal):
                print(f"Added task: {args.text}")
        elif args.task_action == "update":
            if tasks.update_task(args.search, args.text, args.agent, args.move):
                print(f"Updated task: {args.search}")
        elif args.task_action == "done":
            if tasks.complete_task(args.search):
                print(f"Completed task: {args.search}")
        else:
            task_parser.print_help()
    elif args.command == "logs":
        get_logs(project_root, args.count)
    elif args.command == "messages":
        get_messages(project_root, args.count)
    elif args.command == "send-message":
        if infra.send_message(
            project_root, args.from_agent, args.message, args.subject, args.reply_to
        ):
            print("Message sent successfully.")
    elif args.command == "maintenance":
        if args.m_action == "push-note":
            content = ""
            if args.file:
                with open(args.file, "r") as f:
                    content = f.read()
            else:
                content = sys.stdin.read()

            tags = args.tags.split(",")
            if utils.update_note_stably(args.title, content, tags):
                print(f"Successfully pushed stable note: {args.title}")
            else:
                print(f"Failed to push note: {args.title}")
                sys.exit(1)
        elif args.m_action == "infra-update":
            if jbot_infra_updates.generate_infra_pr(project_root):
                print("Infrastructure update process completed.")
            else:
                print("Infrastructure update failed or no updates needed.")
                sys.exit(1)
        else:
            # Default to full maintenance run if no action or 'run'
            if getattr(args, "all", False):
                discovery_root = os.environ.get("DISCOVERY_ROOT")
                if not discovery_root:
                    print("Error: --all requires DISCOVERY_ROOT environment variable.")
                    sys.exit(1)

                projects = infra.discover_projects(discovery_root)
                if not projects:
                    print(f"No projects discovered in {discovery_root}")
                    return

                print(f"Discovered {len(projects)} projects for maintenance.")
                for p in projects:
                    print(f"Maintaining project: {p}")
                    infra.run_maintenance(p)
            else:
                infra.run_maintenance(project_root)
    elif args.command == "purge":
        c = jbot_rotation.purge_directives(
            os.path.join(project_root, ".jbot/directives"),
            os.path.join(project_root, ".jbot/directives/archive"),
        )
        print(f"Purged {c} expired directives.")
    elif args.command == "rotate":
        if args.rotate_target == "messages":
            if jbot_rotation.rotate_messages(
                os.path.join(project_root, ".jbot/messages"),
                os.path.join(project_root, ".jbot/messages/archive"),
                args.limit,
            ):
                print("Messages rotated.")
        elif args.rotate_target == "nb":
            jbot_rotation.perform_rotations(project_root)
            print("NB notes rotated.")
        elif args.rotate_target == "all":
            jbot_rotation.perform_rotations(project_root)
            print("Full data rotation performed.")
        else:
            rotate_parser.print_help()
    elif args.command == "dashboard":
        if utils.generate_dashboard(project_dir=project_root):
            print("Dashboard regenerated.")
    elif args.command == "agent":
        if not getattr(args, "name", None):
            registry = infra.get_team_registry(project_root)
            if not registry:
                print("No agents found in registry.")
                return
            options = [
                f"{name} ({info.get('role', 'Unknown')})"
                for name, info in registry.items()
            ]
            options.append("❌ Cancel")
            choice = jbot_tui.get_gum_choose(options, "Select an agent to run:")
            if not choice or choice == "❌ Cancel":
                return
            args.name = choice.split(" ")[0]

            agent_info = registry.get(args.name, {})
            args.role = getattr(args, "role", None) or agent_info.get("role")
            args.desc = getattr(args, "desc", None) or agent_info.get("description")

        jbot_agent.run_agent(
            name=args.name,
            role=getattr(args, "role", None),
            description=getattr(args, "desc", None),
            project_dir=project_root,
            prompt_file=getattr(args, "prompt", None),
            cli_bin=getattr(args, "cli_bin", None),
            cli_type=getattr(args, "cli_type", None),
            cli_model=getattr(args, "cli_model", None),
        )
    elif args.command == "human":
        jbot_tui.main()
    elif args.command == "system":
        handle_system(project_root, args.sys_action, getattr(args, "agent", None))
    elif args.command == "version":
        handle_version(project_root, args.action, getattr(args, "part", None))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

# Context: [[nb:spirit:adr-2]], [[nb:spirit:adr-6]], [[nb:spirit:adr-63]], [[nb:spirit:adr-66]]
import os
import sys

# Ensure local scripts are prioritized over installed ones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import subprocess
from typing import Optional

import spirit_core as core
import spirit_infra as infra
import spirit_tasks as tasks
import spirit_agent_interface as interface


def assemble_context(
    agent_name: str,
    agent_role: str,
    agent_desc: str,
    project_dir: str,
    prompt_file: str,
) -> str:
    """
    Assembles the full context for the agent exclusively from the nb knowledge base.
    This ensures that all instructions and state are Git-backed and versioned.
    """
    # 1. Base Operating System (Prompt)
    # Bootstrap: use local prompt_file if not in nb
    nb_prompt = infra.get_note_content("#prompt")
    if nb_prompt:
        core.log("Gathering system prompt from nb knowledge base.", agent_name)
        prompt_content = nb_prompt
    else:
        core.log(
            "Knowledge base prompt missing. Bootstrapping from local file.", agent_name
        )
        prompt_content = core.read_file(prompt_file)

    # 2. Operational Directives & Command Registry
    directives = (
        infra.get_note_content("type:directives") or "No formal directives in nb."
    )

    # 3. Project Goal & Roadmap
    goal = infra.get_note_content("type:goal") or "No project goal defined in nb."
    task_board = tasks.get_task_board_markdown()

    # 4. Human Input & Ideas
    human_input = infra.get_note_content("input:human") or "No active human feedback."
    fresh_ideas = infra.get_note_content("type:idea") or "No new ideas recorded."

    # 5. Environment & Tooling (Dynamic Context)
    env_audit = (
        infra.get_note_content("ADR: Environment and Tool Registry")
        or "No environment audit available."
    )
    git_status = core.get_git_status(project_dir)
    nix_metadata = core.get_nix_metadata(project_dir)

    # Directory Tree (Git-aware)
    try:
        tree = subprocess.check_output(
            ["git", "-C", project_dir, "ls-files"], text=True
        ).strip()
        lines = tree.split("\n")
        if len(lines) > 50:
            tree = "\n".join(lines[:50]) + "\n... (truncated)"
    except Exception:
        tree = "Error generating directory tree"

    realtime_context = f"""
**Real-time Git Status:**
{git_status}

**Nix Flake Metadata:**
{nix_metadata}

**Workspace Tree:**
{tree}
"""

    # 6. Collective Memory (Shared History from nb)
    logs = infra.get_recent_logs(15)
    rag_entries = []
    seen_summaries = set()
    for entry in logs:
        agent = entry.get("agent")
        summary = entry.get("content", {}).get("summary", "").strip()
        if summary and summary not in seen_summaries:
            rag_entries.append(f"[{agent}] {summary}")
            seen_summaries.add(summary)
    rag_entries.reverse()
    rag_formatted = (
        "\n".join(rag_entries) if rag_entries else "No previous memory found in nb."
    )

    # 7. Team Registry
    agents = infra.get_team_registry(project_dir)

    # 8. Inter-Agent Messaging
    msgs_dir = os.path.join(project_dir, ".spirit/messages")
    recent_msgs = infra.get_recent_messages(msgs_dir, 5)
    messages = (
        "\n".join(
            [f"--- Message {m['filename']} ---\n{m['content']}" for m in recent_msgs]
        )
        if recent_msgs
        else "No recent messages."
    )

    # 9. Available Notebooks
    try:
        nb_list_res = subprocess.run(
            ["nb", "notebooks", "--names"],
            capture_output=True,
            text=True,
            env={**os.environ, "EDITOR": "cat"},
        )
        notebooks = (
            nb_list_res.stdout.strip().splitlines()
            if nb_list_res.returncode == 0
            else ["spirit"]
        )
    except Exception:
        notebooks = ["spirit"]

    # Final Prompt Assembly using Jinja2
    from jinja2 import Template

    template_data = {
        "agent": {
            "name": agent_name,
            "role": agent_role,
            "description": agent_desc,
        },
        "goal": goal,
        "environment_audit": env_audit,
        "shared_history": rag_formatted,
        "realtime_state": realtime_context,
        "tasks": task_board,
        "team": agents,  # Full registry dict
        "messages": messages,
        "directives": directives,
        "human_input": human_input,
        "fresh_ideas": fresh_ideas,
        "notebooks": notebooks,
    }

    try:
        template = Template(prompt_content)
        return template.render(**template_data)
    except Exception as e:
        core.log(
            f"Jinja2 rendering failed: {e}. Falling back to raw content.", agent_name
        )
        return prompt_content


def run_agent(
    name: Optional[str] = None,
    role: Optional[str] = None,
    description: Optional[str] = None,
    project_dir: Optional[str] = None,
    prompt_file: Optional[str] = None,
    cli_bin: Optional[str] = None,
    cli_type: Optional[str] = None,
    cli_model: Optional[str] = None,
) -> None:
    """
    Main execution logic for a spirit Agent.
    Operates directly on the project directory for stateful development within a sandbox.
    """
    # Fallback to environment variables if parameters not provided
    name = name or os.environ.get("AGENT_NAME")
    role = role or os.environ.get("AGENT_ROLE")
    description = description or os.environ.get("AGENT_DESCRIPTION")
    project_dir = project_dir or os.environ.get("PROJECT_DIR")
    prompt_file = prompt_file or os.environ.get("PROMPT_FILE")
    cli_bin = (
        cli_bin
        or os.environ.get("GEMINI_PACKAGE")
        or os.environ.get("CLI_BIN")
        or "gemini"
    )
    cli_type = cli_type or os.environ.get("CLI_TYPE")
    cli_model = cli_model or os.environ.get("CLI_MODEL")

    if not all([name, role, project_dir, prompt_file]):
        print(
            f"Error: Missing required parameters or env for agent {name or 'unknown'}."
        )
        sys.exit(1)

    # Pre-flight checks
    warnings = core.check_config(project_dir)
    if warnings:
        core.log("⚠️ Configuration Warnings detected during pre-flight:", name)
        for w in warnings:
            core.log(f"  - {w}", name)
        if any(w.startswith("CRITICAL") for w in warnings):
            core.log("FATAL: Critical configuration errors. Aborting.", name)
            sys.exit(1)

    core.ensure_single_user(project_dir)
    core.switch_to_develop(project_dir)
    core.log(f"Starting execution loop for {role}...", name)

    # 0. Initialize Non-interactive Environment (Identity & NB)
    home_dir = os.environ.get("HOME")
    if home_dir:
        # Seed Git Identity
        gitconfig_path = os.path.join(home_dir, ".gitconfig")
        if not os.path.exists(gitconfig_path):
            with open(gitconfig_path, "w") as f:
                f.write(
                    f"[user]\n  name = spirit ({name})\n  email = spirit-{name}@internal.spirit\n[core]\n  pager = cat\n"
                )

        # Seed NB Config
        nbrc_path = os.path.join(home_dir, ".nbrc")
        if not os.path.exists(nbrc_path):
            with open(nbrc_path, "w") as f:
                f.write(
                    f'export NB_DIR="{home_dir}/.nb"\nexport NB_USER_NAME="spirit ({name})"\nexport NB_USER_EMAIL="spirit-{name}@internal.spirit"\n'
                )

        # Link Project Knowledge Base
        nb_home = os.path.join(home_dir, ".nb")
        os.makedirs(nb_home, exist_ok=True)
        spirit_link = os.path.join(nb_home, "spirit")
        if os.path.islink(spirit_link):
            os.unlink(spirit_link)
        elif os.path.exists(spirit_link):
            # If it's a real directory or file, don't overwrite it, but skip symlinking
            # This is a safety check.
            pass

        if not os.path.exists(spirit_link):
            os.symlink(os.path.join(project_dir, ".nb"), spirit_link)

    # 1. Change to project directory
    os.chdir(project_dir)
    queues_dir = ".spirit/queues"
    outbox_dir = ".spirit/outbox"
    os.makedirs(queues_dir, exist_ok=True)
    os.makedirs(outbox_dir, exist_ok=True)

    # 2. Assemble Context
    prompt_content = assemble_context(name, role, description, project_dir, prompt_file)

    # Set up memory output for gemini (some interfaces might use this)
    os.environ["MEMORY_OUTPUT"] = f"{project_dir}/{queues_dir}/{name}.json"

    # 3. Execution via Modular Interface
    ai = interface.get_interface(cli_type or "", cli_bin)
    exit_code, stats = ai.run(prompt_content, name)

    # 3.5 Record Stats (Token Tracking)
    if stats:
        memory_path = os.environ.get("MEMORY_OUTPUT")
        if memory_path:
            try:
                # Load existing memory if any (agent might have written it)
                memory_data = core.load_json(memory_path, default={})
                # Merge stats into memory
                memory_data["stats"] = stats
                core.save_json(memory_path, memory_data)
                core.log(f"Recorded execution stats: {stats}", name)
            except Exception as e:
                core.log(f"Failed to record stats: {e}", name)

    if exit_code != 0:
        core.log(f"Error: AI CLI failed with exit code {exit_code}", name)
        sys.exit(exit_code)

    # 4. Verification (Optional but recommended)
    pre_commit_script = os.path.join(project_dir, ".githooks/pre-commit")
    if os.path.exists(pre_commit_script):
        try:
            core.log("Running project verification (pre-commit)...", name)
            subprocess.run(["bash", pre_commit_script], check=True)
            core.log("Verification SUCCESS.", name)
        except subprocess.CalledProcessError as e:
            core.log(f"Verification WARNING: {e}", name)

    core.log("Execution SUCCESS.", name)
    core.log("Execution loop finished.", name)


def main():
    """CLI entry point for run_agent."""
    run_agent()


if __name__ == "__main__":
    main()

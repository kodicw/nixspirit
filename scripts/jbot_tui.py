#!/usr/bin/env python3
# Context: [[nb:jbot:adr-6]]
import os
import sys

# Ensure local scripts are prioritized over installed ones
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import subprocess
import jbot_core as core
import jbot_infra as infra
from jbot_memory_interface import get_memory_client


def run_command(cmd, capture=True):
    try:
        result = subprocess.run(cmd, capture_output=capture, text=True, check=True)
        return result.stdout.strip() if capture else None
    except subprocess.CalledProcessError as e:
        if capture:
            return f"Error: {e.stderr}"
        return None


def get_gum_input(placeholder, header):
    return run_command(
        ["gum", "input", "--placeholder", placeholder, "--header", header]
    )


def get_gum_write(placeholder, header):
    return run_command(
        ["gum", "write", "--placeholder", placeholder, "--header", header]
    )


def get_gum_choose(options, header):
    return run_command(["gum", "choose", "--header", header] + options)


def ai_refine_idea(rough_draft, project_dir):
    """Uses Gemini and Jinja2 to refine the human's idea based on project context."""
    from jinja2 import Template

    # Gather high-density context
    git_status = core.get_git_status(project_dir)
    nix_metadata = core.get_nix_metadata(project_dir)

    # Get last 5 memory entries
    logs = infra.get_recent_logs(5)
    memory = "\n".join(
        [f"[{entry['agent']}] {entry['content']['summary']}" for entry in logs]
    )

    prompt_template = """
You are assisting a human developer in refining an idea or feedback for the JBot project.
JBot is a PAO (Professional Autonomous Organization) managed by AI agents.

**PROJECT CONTEXT:**
Git Status: {{ git_status }}
Nix Metadata: {{ nix_metadata }}

**RECENT MEMORY:**
{{ memory }}

**HUMAN'S ROUGH DRAFT:**
{{ rough_draft }}

**YOUR TASK:**
Refine this idea into a high-density, technically grounded, and structured proposal. 
Focus on:
1. Architectural alignment (Flat Organization, Technical Purity).
2. Actionable steps for the agents (Lead, Architect, Tester).

Output ONLY the refined markdown content.
"""

    template = Template(prompt_template)
    prompt = template.render(
        git_status=git_status,
        nix_metadata=nix_metadata,
        memory=memory,
        rough_draft=rough_draft,
    )

    print("\n[AI] Refining your idea with project context...")
    return run_command(["gemini", "-y", "-p", prompt])


def main():
    project_dir = core.get_project_root()
    os.chdir(project_dir)

    # 1. Selection
    action = get_gum_choose(
        ["💡 New Idea", "💬 Feedback", "🔧 Update Prompt", "❌ Exit"],
        "What would you like to contribute?",
    )

    if action == "❌ Exit":
        sys.exit(0)

    tags = "input:human"
    title_prefix = "Feedback"

    if "Idea" in action:
        tags = "type:idea,input:human"
        title_prefix = "Idea"
    elif "Prompt" in action:
        tags = "type:prompt,input:human"
        title_prefix = "System Prompt"

    # 2. Input
    rough_draft = get_gum_write(
        "Enter your rough idea or feedback here (Ctrl+D to finish)...",
        f"Drafting: {action}",
    )

    if not rough_draft:
        print("Cancelled.")
        sys.exit(0)

    # 3. AI Refinement
    refined_idea = ai_refine_idea(rough_draft, project_dir)

    # 4. Verification
    print("\n--- REFINED PROPOSAL ---")
    print(refined_idea)
    print("------------------------")

    confirm = get_gum_choose(
        ["✅ Accept & Push", "✏️ Edit Manually", "🔄 Retry AI", "❌ Discard"],
        "Accept this refined version?",
    )

    if "Discard" in confirm:
        sys.exit(0)

    final_content = refined_idea
    if "Edit" in confirm:
        # Use a temporary file for gum write
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w+") as tf:
            tf.write(refined_idea)
            tf.flush()
            run_command(["gum", "write", "--value", refined_idea], capture=False)
            # Gum write with --value doesn't work as expected for editing.
            # We'll just prompt them to provide the final version.
            final_content = get_gum_write(
                "Provide the final version of your contribution...", "Manual Edit"
            )

    # 5. Push to NB
    title = f"{title_prefix}: {rough_draft[:30]}..."

    client = get_memory_client()
    print("\n[NB] Pushing to knowledge base...")
    overwrite = "Feedback" in action or "Prompt" in action

    tags_list = tags.split(",")
    client.add(title, final_content, tags=tags_list, overwrite=overwrite)

    print(f"\n🚀 Contribution successfully recorded in nb as: {title}")


if __name__ == "__main__":
    main()

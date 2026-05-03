# Context: [[nb:knowledge:adr-6]], [[nb:knowledge:adr-57]], [[nb:knowledge:adr-63]]
import os
import subprocess
from typing import List, Dict
import core_logic as core
import core_infra as infra
import core_utils as utils
import constants
from core_memory_interface import get_memory_client


def init_project(project_dir: str, name: str = None) -> bool:
    """
    Initializes a new autonomous organization project.

    Context: [[nb:knowledge:6]]
    """
    try:
        if not name:
            name = os.path.basename(os.path.abspath(project_dir))

        core.log(f"Initializing organization: {name} in {project_dir}", "Init")

        # 1. Create Infrastructure Directories
        infra.initialize_infrastructure(project_dir)

        # 1.2 Initialize git repository
        core.init_git(project_dir)

        # 1.5 Ensure on develop branch
        core.switch_to_develop(project_dir)

        # 2. Initialize .nb directory if it doesn't exist
        nb_path = os.path.join(project_dir, ".nb")
        if not os.path.exists(nb_path):
            os.makedirs(nb_path, exist_ok=True)

        # Register the notebook globally so it's accessible by name
        try:
            core.log(f"Registering nb notebook '{name}' at {nb_path}", "Init")
            # Check if it already exists
            res = subprocess.run(
                ["nb", "notebooks", "show", name], capture_output=True, text=True
            )
            if res.returncode != 0:
                subprocess.run(["nb", "notebooks", "add", name, nb_path], check=True)
        except Exception as e:
            core.log(f"Warning: Failed to register nb notebook: {e}", "Init")

        # 3. Create notebook local config
        core.write_file(os.path.join(project_dir, constants.NOTEBOOK_CONFIG), name)

        # 4. Create project goal file
        goal_path = os.path.join(project_dir, constants.GOAL_FILE)
        if not os.path.exists(goal_path):
            default_goal = constants.DEFAULT_GOAL_TEMPLATE.format(name=name.title())
            core.write_file(goal_path, default_goal)

        # 5. Create agents.json
        agents_path = os.path.join(project_dir, constants.AGENTS_REGISTRY)
        if not os.path.exists(agents_path):
            core.save_json(agents_path, constants.DEFAULT_AGENTS)

        # 6. Create VERSION and CHANGELOG.md
        version_path = os.path.join(project_dir, constants.VERSION_FILE)
        if not os.path.exists(version_path):
            core.write_file(version_path, constants.INITIAL_VERSION)

        changelog_path = os.path.join(project_dir, constants.CHANGELOG_FILE)
        if not os.path.exists(changelog_path):
            default_changelog = constants.DEFAULT_CHANGELOG_HEADER.format(name=name)
            core.write_file(changelog_path, default_changelog)

        # 6.5 Create .gitignore
        gitignore_path = os.path.join(project_dir, constants.GITIGNORE_FILE)
        if not os.path.exists(gitignore_path):
            gitignore_content = constants.GITIGNORE_CONTENT.format(state_dir=constants.STATE_DIR)
            core.write_file(gitignore_path, gitignore_content)

        # 7. Create flake.nix template
        flake_path = os.path.join(project_dir, constants.FLAKE_FILE)
        if not os.path.exists(flake_path):
            core.write_file(flake_path, constants.FLAKE_TEMPLATE)

        # 7.5 Create system prompt template
        prompt_path = os.path.join(project_dir, constants.PROMPT_FILE)
        if not os.path.exists(prompt_path):
            core.write_file(prompt_path, constants.PROMPT_TEMPLATE)

        # 8. Push Initial Notes to Technical Memory (nb)
        try:
            env = os.environ.copy()
            env[constants.ENV_NOTEBOOK] = name
            client = get_memory_client(env=env)

            # Push Goal
            client.add(
                f"Vision: {name.title()}",
                f"#{constants.TAG_GOAL}\n\n## Strategic Vision\n> {core.read_file(goal_path).strip()}",
                tags=[constants.TAG_GOAL, "vision"],
            )

            # Push Team Registry
            agents = core.load_json(agents_path)
            team_content = "# Team Registry\n\n"
            for agent_name, info in agents.items():
                team_content += (
                    f"- **{agent_name}**: {info['role']} ({info['description']})\n"
                )
            client.add("Team Registry", team_content, tags=[constants.TAG_REGISTRY, "team"])

            # Push Initial Task
            client.add(
                title=f"Define {name.title()} project roadmap",
                content=f"Status: {constants.STATUS_ACTIVE}\nAgent: ceo\n\nDescription: Define the initial project roadmap and key milestones for {name}.",
                tags=[constants.TAG_TASK, constants.STATUS_ACTIVE, "agent:ceo"],
            )

            core.log("Initial notes pushed to technical memory.", "Init")
        except Exception as e:
            core.log(f"Warning: Failed to push initial notes to nb: {e}", "Init")

        # 9. Generate Initial Dashboard
        utils.generate_dashboard(project_dir=project_dir)

        # 10. Initial Commit
        core.commit_all(project_dir, "feat: initial organization bootstrap")

        core.log(f"Successfully initialized organization '{name}'.", "Init")
        return True
    except Exception as e:
        core.log(f"Initialization failed: {e}", "Init")
        return False

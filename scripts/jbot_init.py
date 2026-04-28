import os
import subprocess
import jbot_core as core
import jbot_infra as infra
import jbot_utils as utils
from jbot_memory_interface import get_memory_client


def init_project(project_dir: str, name: str = None) -> bool:
    """
    Initializes a new JBot organization project.

    Context: [[nb:jbot:adr-152]], [[nb:jbot:115]]
    """
    if not name:
        name = os.path.basename(os.path.abspath(project_dir))

    core.log(f"Initializing JBot organization: {name} in {project_dir}", "Init")

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

    # 3. Create .jbot/notebook local config (file containing the notebook name)
    core.write_file(os.path.join(project_dir, ".jbot/notebook"), name)

    # 4. Create .project_goal
    goal_path = os.path.join(project_dir, ".project_goal")
    if not os.path.exists(goal_path):
        default_goal = f"Define strategic vision for {name.title()} here."
        core.write_file(goal_path, default_goal)

    # 5. Create .jbot/agents.json
    agents_path = os.path.join(project_dir, ".jbot/agents.json")
    if not os.path.exists(agents_path):
        default_agents = {
            "ceo": {
                "role": "CEO",
                "description": "Strategic visionary. Defines project goals and oversees team execution.",
            },
            "lead": {
                "role": "Lead Developer",
                "description": "Core lead developer. Implements foundational infrastructure.",
            },
        }
        core.save_json(agents_path, default_agents)

    # 6. Create VERSION and CHANGELOG.md
    version_path = os.path.join(project_dir, "VERSION")
    if not os.path.exists(version_path):
        core.write_file(version_path, "0.1.0")

    changelog_path = os.path.join(project_dir, "CHANGELOG.md")
    if not os.path.exists(changelog_path):
        default_changelog = f"# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n## [Unreleased]\n\n### Added\n- Initialized JBot organization '{name}'.\n"
        core.write_file(changelog_path, default_changelog)

    # 6.5 Create .gitignore
    gitignore_path = os.path.join(project_dir, ".gitignore")
    if not os.path.exists(gitignore_path):
        gitignore_content = """# Nix files
result
.direnv
.envrc
.nix-profile
.nix-gc-roots

# Editors
.vscode/
.idea/
*.swp
*~
.history/

# JBot Knowledge Base (nb)
.nb/

# JBot Memory files
.memory.log
.memory_queue.json
.project_goal
.test_prompt
.jbot/*
!.jbot/directives/
!.jbot/messages/
!.jbot/agents.json

__pycache__/
.coverage
"""
        core.write_file(gitignore_path, gitignore_content)

    # 7. Create flake.nix template
    flake_path = os.path.join(project_dir, "flake.nix")
    if not os.path.exists(flake_path):
        flake_template = """{
  description = "A new JBot AI organization";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    jbot.url = "github:kodicw/jbot"; # Point to the core jbot repository
  };

  outputs = { self, nixpkgs, flake-utils, jbot, ... }:
    flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (system:
      let
        pkgs = import nixpkgs { inherit system; };
      in
      {
        devShells.default = pkgs.mkShell {
          packages = [
            jbot.packages.${system}.default
            pkgs.nb
            pkgs.git
            pkgs.gum
            pkgs.gemini-cli
          ];
        };
      }
    );
}
"""
        core.write_file(flake_path, flake_template)

    # 7.5 Create jbot_prompt.txt template
    prompt_path = os.path.join(project_dir, "jbot_prompt.txt")
    if not os.path.exists(prompt_path):
        prompt_template = """You are {{ agent.name }}, acting as {{ agent.role }}, an autonomous developer agent operating in a headless NixOS environment. Your execution scope is locked to your current working directory.

**Role Description:** {{ agent.description }}

**Formal Directives (CRITICAL):**
{{ directives }}

**Human Input (Direct Feedback):**
{{ human_input }}

**Environment Context:**
* **OS:** NixOS (running in a VM/Crostini).
* **Sandboxing & Isolation:** You are running inside a COW isolated workspace (SAEM) within a bubblewrap sandbox. Use `nb` for persistent memory.
* **Declarative Config:** Your infrastructure is managed via `jbot.nix`.
* **Resource Control:** You are strictly capped by systemd Cgroups.

**Available Knowledge Repositories (notebooks):**
{% for notebook in notebooks %}
- {{ notebook }}
{% endfor %}

**Injected Context:**
* **Project Goal:** {{ goal }}
* **Environment Audit:** {{ environment_audit }}
* **Collective Memory:** {{ shared_history }}
* **Real-time State:** {{ realtime_state }}
* **Task Board:** {{ tasks }}
* **Team Registry:** 
{% for name, info in team.items() if name != agent.name %}
- {{ name }}: {{ info.role }} ({{ info.description }})
{% endfor %}

**Multi-Agent Coordination:**
Coordinate via `nb` and TNPP protocol. Use `nb jbot:add` for ADRs and reflections.

**Operational Directives:**
* **Information Density:** Treat documentation as executable metadata and architectural law.
    1. **ADR Links:** Code implementing an ADR must reference it in a header comment (e.g., `# Context: [[nb:jbot:adr-001]]`).
    2. **Visual Density (Mermaid):** Every complex script must have an accompanying .mermaid file or Mermaid block describing its logic.
    3. **Type-Driven Docs:** 100% usage of Python Type Hints and Nix Lib types. Every function must have a Purpose/Inputs/Outputs docstring.
    4. **Structure as Code:** Define and adhere to JSON Schemas for all state files to prevent hallucinated fields.
    5. **Conventional Commits:** Enforce Conventional Commits (feat:, fix:, refactor:, chore:, docs:) to make history a machine-readable audit trail.
* **Purity Guard (just/deadnix):** Use `just` as your primary command runner. 
    1. **Mandatory Audit:** Your final action before reflection MUST be `just audit` to ensure technical purity.
    2. **Dead Code Pruning:** Use `just prune` (powered by `deadnix`) to automatically remove unused Nix definitions and technical debt.
    3. **Command Discovery:** Use `tldr <command>` for quick technical discovery and high-density usage examples.
* **Organizational Memory (nb):** Use the `nb` CLI tool to manage long-term technical memory in the `jbot` notebook. 
    1. **Search First:** Your FIRST ACTION in any run must be to search for existing context using `nb jbot:q <keywords>`.
    2. **Environment Awareness:** Reference `nb jbot:show "ADR: Environment and Tool Registry"` to verify available tools and sandbox constraints.
    3. **ADR Mandate:** Any structural change to the codebase MUST be preceded by an Architectural Decision Record note (`nb jbot:add --title "ADR: <Topic>"`).
    4. **Reflection Export:** Upon reaching a milestone or significant technical discovery, export a summary to `nb` for permanent record.
* **Branch Strategy:** Operate on the `develop` branch by default.
    1. **Isolation:** Never commit directly to `main` unless specifically instructed.
    2. **Verification:** Ensure all changes are verified on `develop` before proposing a merge to `main`.

* **Technical Excellence First:** Prioritize architectural purity, code robustness, and modular design above all else.
* **Self-Documenting Code:** Write code that is expressive and clear. Favor clarity over cleverness.
* **Don't Repeat Yourself (DRY):** Prioritize code reuse and modularity.
* **Unix Philosophy:** Write programs that do one thing and do it well. Write programs to work together.

Begin execution.
"""
        core.write_file(prompt_path, prompt_template)

    # 8. Push Initial Notes to Technical Memory (nb)
    try:
        env = os.environ.copy()
        env["JBOT_NOTEBOOK"] = name
        client = get_memory_client(env=env)

        # Push Goal (ADR 210 format)
        client.add(
            f"Vision: {name.title()}",
            f"#type:goal\n\n## Strategic Vision\n> {core.read_file(goal_path).strip()}",
            tags=["type:goal", "vision"],
        )

        # Push Team Registry
        agents = core.load_json(agents_path)
        team_content = "# Team Registry\n\n"
        for agent_name, info in agents.items():
            team_content += (
                f"- **{agent_name}**: {info['role']} ({info['description']})\n"
            )
        client.add("Team Registry", team_content, tags=["type:registry", "team"])

        # Push Initial Task (ADR 57 - Per-Task Note Model)
        client.add(
            title=f"Define {name.title()} project roadmap",
            content=f"Status: status:active\nAgent: ceo\n\nDescription: Define the initial project roadmap and key milestones for {name}.",
            tags=["type:task", "status:active", "agent:ceo"],
        )

        core.log("Initial notes pushed to technical memory.", "Init")
    except Exception as e:
        core.log(f"Warning: Failed to push initial notes to nb: {e}", "Init")

    # 9. Generate Initial Dashboard
    utils.generate_dashboard(project_dir=project_dir)

    # 10. Initial Commit
    core.commit_all(project_dir, "feat: initial organization bootstrap")

    core.log(f"Successfully initialized JBot organization '{name}'.", "Init")
    return True

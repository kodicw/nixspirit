# Global Constants
# Generic terminology for autonomous organization infrastructure.

import os

# --- Paths & Files ---
STATE_DIR = ".system"
AGENTS_REGISTRY = os.path.join(STATE_DIR, "agents.json")
NOTEBOOK_CONFIG = os.path.join(STATE_DIR, "notebook")
COMMUNICATIONS_DIR = os.path.join(STATE_DIR, "messages")
INSTRUCTIONS_DIR = os.path.join(STATE_DIR, "directives")
TASKS_DIR = os.path.join(STATE_DIR, "queues")
RESULTS_DIR = os.path.join(STATE_DIR, "outbox")
ARCHIVE_COMMUNICATIONS_DIR = os.path.join(COMMUNICATIONS_DIR, "archive")
ARCHIVE_INSTRUCTIONS_DIR = os.path.join(INSTRUCTIONS_DIR, "archive")
CACHE_FILE = os.path.join(STATE_DIR, "nb_cache.json")

GOAL_FILE = ".project_goal"
VERSION_FILE = "VERSION"
CHANGELOG_FILE = "CHANGELOG.md"
PROMPT_FILE = "system_prompt.txt"
FLAKE_FILE = "flake.nix"
GITIGNORE_FILE = ".gitignore"
PRE_COMMIT_HOOK = ".githooks/pre-commit"
INDEX_FILE = "INDEX.md"
README_FILE = "README.md"
HUMAN_INPUT_FILE = "human.txt"

# --- NB Tags ---
TAG_TASK = "type:task"
TAG_MESSAGE = "type:message"
TAG_VISION = "type:vision"
TAG_ADR = "type:adr"
TAG_GOAL = "type:goal"
TAG_REGISTRY = "type:registry"
TAG_IDEA = "type:idea"
TAG_PROMPT = "type:prompt"
TAG_DIRECTIVES = "type:directives"
TAG_MEMORY = "memory"
TAG_TASKS_BOARD = "type:tasks"
TAG_AUDIT = "type:audit"
TAG_HUMAN = "input:human"
TAG_RESEARCH = "type:research"
TAG_BENCHMARKS = "type:benchmarks"

STATUS_ACTIVE = "status:active"
STATUS_BACKLOG = "status:backlog"
STATUS_COMPLETED = "status:completed"
STATUS_PROPOSAL = "status:proposal"

# --- Environment Variables ---
ENV_NOTEBOOK = "CORE_NOTEBOOK"
ENV_NB_BIN = "NB_BIN"
ENV_NB_USER_NAME = "NB_USER_NAME"
ENV_NB_USER_EMAIL = "NB_USER_EMAIL"
ENV_NB_DIR = "NB_DIR"
ENV_NB_NOTEBOOK_PATH = "NB_NOTEBOOK_PATH"
ENV_AGENT_NAME = "AGENT_NAME"
ENV_AGENT_ROLE = "AGENT_ROLE"
ENV_AGENT_DESC = "AGENT_DESCRIPTION"
ENV_PROJECT_DIR = "PROJECT_DIR"
ENV_PROMPT_FILE = "PROMPT_FILE"
ENV_GEMINI_PACKAGE = "GEMINI_PACKAGE"
ENV_CLI_BIN = "CLI_BIN"
ENV_CLI_TYPE = "CLI_TYPE"
ENV_CLI_MODEL = "CLI_MODEL"
ENV_MEMORY_OUTPUT = "MEMORY_OUTPUT"
ENV_DISCOVERY_ROOT = "DISCOVERY_ROOT"
ENV_HOME = "HOME"
ENV_USE_DBUS = "USE_DBUS"
ENV_HM_PROFILE = "HM_PROFILE"
ENV_USER_ID = "USER_ID"
ENV_GIT_AUTHOR_NAME = "GIT_AUTHOR_NAME"
ENV_GIT_AUTHOR_EMAIL = "GIT_AUTHOR_EMAIL"
ENV_GIT_COMMITTER_NAME = "GIT_COMMITTER_NAME"
ENV_GIT_COMMITTER_EMAIL = "GIT_COMMITTER_EMAIL"

# --- Defaults ---
DEFAULT_SYSTEM_NAME = "Autonomous System"
DEFAULT_SYSTEM_EMAIL = "system@internal.local"
DEFAULT_NOTEBOOK_NAME = "knowledge"
DEFAULT_CLI_BIN = "gemini"
DEFAULT_BRANCH = "develop"
INITIAL_VERSION = "0.1.0"
VERSION_TAG_PREFIX = "v"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FILENAME_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
ROTATION_TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"

# --- Dashboard Constants ---
DASHBOARD_HEADER = "# {name} Dashboard\n\n"
DASHBOARD_LAST_UPDATED = "*Last Updated: {timestamp}*\n\n"
DASHBOARD_VISION_SECTION = "## 🎯 Strategic Vision\n"
DASHBOARD_TEAM_SECTION = "## 👥 Team Roster\n"
DASHBOARD_PROPOSAL_SECTION = "## 💡 Proposed Tasks\n"
DASHBOARD_ACTIVE_SECTION = "## 🚀 Active Tasks\n"
DASHBOARD_BACKLOG_SECTION = "## 📦 Backlog Highlights\n"
DASHBOARD_COMPLETED_SECTION = "## ✅ Recently Completed\n"
DASHBOARD_ADR_SECTION = "## 📜 Recent ADRs\n"
DASHBOARD_MESSAGES_SECTION = "## 💬 Recent Messages\n"
DASHBOARD_DIAGRAMS_SECTION = "## 📊 Architectural Diagrams\n"
DASHBOARD_STATUS_SECTION = "## 📈 Status & Progress\n"
DASHBOARD_MILESTONES_SECTION = "## ✅ Recent Milestones\n"

# --- Regex Patterns ---
EXPIRATION_PATTERN = r"Expiration:\s*(\d{4}-\d{2}-\d{2})"
DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"
AGENT_TAG_PATTERN = r"\(Agent:\s*([^)]+)\)"

# --- Template Defaults ---
DEFAULT_GOAL_TEMPLATE = "Define strategic vision for {name} here."
DEFAULT_AGENTS = {
    "ceo": {
        "role": "CEO",
        "description": "Strategic visionary. Defines project goals and oversees team execution.",
    },
    "lead": {
        "role": "Lead Developer",
        "description": "Core lead developer. Implements foundational infrastructure.",
    },
}
DEFAULT_CHANGELOG_HEADER = "# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n## [Unreleased]\n\n### Added\n- Initialized organization '{name}'.\n"

GITIGNORE_CONTENT = """# Nix files
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

# Knowledge Base (nb)
.nb/

# Memory files
.memory.log
.memory_queue.json
.project_goal
.test_prompt
{state_dir}/*
!{state_dir}/directives/
!{state_dir}/messages/
!{state_dir}/agents.json

__pycache__/
.coverage
"""

FLAKE_TEMPLATE = """{{
  description = "A new autonomous organization";

  inputs = {{
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    core.url = "github:kodicw/core"; # Update to actual core repo if needed
  }};

  outputs = {{ self, nixpkgs, flake-utils, core, ... }}:
    flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" ] (system:
      let
        pkgs = import nixpkgs {{ inherit system; }};
      in
      {{
        devShells.default = pkgs.mkShell {{
          packages = [
            core.packages.${{system}}.default
            pkgs.nb
            pkgs.git
            pkgs.gum
            pkgs.gemini-cli
          ];
        }};
      }}
    );
}}
"""

PROMPT_TEMPLATE = """You are {{ agent.name }}, acting as {{ agent.role }}, an autonomous developer agent operating in a headless NixOS environment. Your execution scope is locked to your current working directory.

**Role Description:** {{ agent.description }}

**Formal Directives (CRITICAL):**
{{ directives }}

**Human Input (Direct Feedback):**
{{ human_input }}

**Environment Context:**
* **OS:** NixOS (running in a VM/Crostini).
* **Sandboxing & Isolation:** You are running inside a COW isolated workspace within a bubblewrap sandbox. Use `nb` for persistent memory.
* **Declarative Config:** Your infrastructure is managed via `system.nix`.
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
Coordinate via `nb` and standard protocols. Use `nb {{ default_notebook }}:add` for ADRs and reflections.

**Operational Directives:**
* **Information Density:** Treat documentation as executable metadata and architectural law.
    1. **ADR Links:** Code implementing an ADR must reference it in a header comment (e.g., `# Context: [[nb:{{ default_notebook }}:adr-001]]`).
    2. **Visual Density (Mermaid):** Every complex script must have an accompanying .mermaid file or Mermaid block describing its logic.
    3. **Type-Driven Docs:** 100% usage of Python Type Hints and Nix Lib types. Every function must have a Purpose/Inputs/Outputs docstring.
    4. **Structure as Code:** Define and adhere to JSON Schemas for all state files to prevent hallucinated fields.
    5. **Conventional Commits:** Enforce Conventional Commits (feat:, fix:, refactor:, chore:, docs:) to make history a machine-readable audit trail.
* **Purity Guard (just/deadnix):** Use `just` as your primary command runner. 
    1. **Mandatory Audit:** Your final action before reflection MUST be `just audit` to ensure technical purity.
    2. **Dead Code Pruning:** Use `just prune` (powered by `deadnix`) to automatically remove unused Nix definitions and technical debt.
    3. **Command Discovery:** Use `tldr <command>` for quick technical discovery and high-density usage examples.
* **Organizational Memory (nb):** Use the `nb` CLI tool to manage long-term technical memory in the `{{ default_notebook }}` notebook. 
    1. **Search First:** Your FIRST ACTION in any run must be to search for existing context using `nb {{ default_notebook }}:q <keywords>`.
    2. **Environment Awareness:** Reference `nb {{ default_notebook }}:show "ADR: Environment and Tool Registry"` to verify available tools and sandbox constraints.
    3. **ADR Mandate:** Any structural change to the codebase MUST be preceded by an Architectural Decision Record note (`nb {{ default_notebook }}:add --title "ADR: <Topic>"`).
    4. **Reflection Export:** Upon reaching a milestone or significant technical discovery, export a summary to `nb` for permanent record.
* **Branch Strategy:** Operate on the `develop` branch by default.
    1. **Isolation:** Never commit directly to `main` unless specifically instructed.
    2. **Verification:** Ensure all changes are verified on `develop` before proposing a merge to `main`.

* **Technical Excellence First:** Prioritize architectural purity, code robustness, and modular design above all else.
* **Self-Documenting Code:** Write code that is expressive and clear. Favor clarity over clarity over cleverness.
* **Don't Repeat Yourself (DRY):** Prioritize code reuse and modularity.
* **Unix Philosophy:** Write programs that do one thing and do it well. Write programs to work together.

Begin execution.
"""

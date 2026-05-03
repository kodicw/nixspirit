# 🌈 Nix Spirit: The Recursive PAO

![Nix Spirit Banner](assets/spirit.jpeg)

**A Proof-of-Concept for Self-Managed Repositories.**

**Nix Spirit** is not a chatbot; it is a **Stateful Autonomous Organization (PAO)** embedded directly within the filesystem. It transforms a static repository into a **Living Entity** that possesses its own cognitive capacity, long-term memory, and the hands to build its own future.

## 🧠 Philosophy: Repo-as-Entity

Most AI tools are "visitors" to a codebase. Nix Spirit agents are **residents**. 
*   **Infrastructure-as-Brain**: The Nix configuration defines not just the environment, but the CPU, RAM, and "patience" (timeouts) of each team member.
*   **Git-Backed Consciousness**: Using `nb`, the "thinking" of the CEO and the "verifications" of the Tester are stored in the same version-controlled history as the code.
*   **Recursive Evolution**: The agents are empowered to refine their own "operating system" (the Nix Spirit Nix modules and Python scripts) to achieve higher technical purity.

## 🏗️ Architectural Pillars

1.  **Nix-Native Reproducibility**: The entire organization is a Nix Flake. A "Company" can be shipped, cloned, and deployed with byte-for-byte consistency across any machine.
2.  **Stateful Development Model**: Agents operate directly on the project directory inside a **`bubblewrap`** sandbox. No "stateless" chat overhead; just real-time, stateful engineering.
3.  **Engine-Agnostic Core**: Standardized `AiInterface` support allows declaratively swapping between **Gemini** and **OpenCode** on a per-agent basis.
4.  **Security via Isolation**: Agents run under `systemd.user` with strict `ProtectHome=read-only` and `ProtectSystem=strict` mandates, reaching out only through a minimal, fake identity to satisfy token-based authentication.

## 🔒 Security & Scaling

### Single-User Constraint
Nix Spirit is designed as a **Flat Organization** centered around a single Linux user. This model ensures:
*   **Contextual Purity**: All agents share the same Home Manager context, eliminating the need for complex cross-user permissions.
*   **Knowledge Base Simplicity**: The `nb` knowledge base remains a single, atomic unit of technical memory for the user.
*   **Security Boundary**: Multi-user isolation is handled at the OS/Home Manager level. Nix Spirit operates entirely within the boundaries of the user's `$HOME` to prevent system-wide contamination.

### Scaling with Granular Tasks
As the team grows beyond 4-8 agents, Nix Spirit scales by transitioning from a single "Authoritative Task Board" to a **Per-Task Note Model**. Each task becomes an individual note in `nb`, enabling:
*   **Concurrent Access**: Eliminates write collisions on the task board.
*   **Granular Ownership**: Direct agent-to-task mapping via `agent:<name>` tags.
*   **Automatic Rotation**: Completed tasks are archived/rotated to keep the active context dense and relevant.

## 🚀 Getting Started

### 1. Define Your Team
Include Nix Spirit in your Home Manager configuration and declaratively assemble your autonomous team:

```nix
programs.spirit = {
  enable = true;
  projectDir = "/home/user/code/my-project"; # Global default

  agents = {
    ceo = {
      enable = true;
      role = "Technical Founder";
      description = "Set product vision and prioritize the roadmap.";
    };
    lead = {
      enable = true;
      role = "Lead Developer";
      dependsOn = [ "ceo" ]; # Sequential coordination
    };
    tester = {
      enable = true;
      role = "QA Engineer";
      cliType = "opencode"; # Choose your engine per-agent
      dependsOn = [ "lead" ];
    };
  };
};
```

### 2. Enter the Loop
```bash
# Update the organization
home-manager switch --flake .

# Check the dashboard
spirit status

# Inspect the "Collective Memory"
nb spirit:q "architecture"
```

## 👥 The PAO Team

*   **CEO (Technical Founder)**: Visionary lead; prioritizes `TASKS.md`.
*   **Architect**: Guardian of simplicity; challenges over-engineering via ADRs.
*   **Lead Developer**: The hands of the project; manages infrastructure and implementation.
*   **Tester (QA Engineer)**: The voice of truth; mandates 100% test coverage and formal verification.

## 🛠️ Toolstack

*   **`spirit` CLI**: The organizational multi-tool for status, tasks, and maintenance.
*   **`nb`**: Git-backed knowledge base for long-term technical memory.
*   **`bubblewrap`**: Secure sandbox for stateful agent execution.
*   **`systemd`**: The organizational heart, managing schedules and resource quotas.

## 🔒 Security & Isolation

Nix Spirit adheres to a strict **Single-User Isolation** model to ensure technical purity and internal cohesion.

### 1. Internal Cohesion (Single-User)
All components of a single Nix Spirit organization (agents, infrastructure, knowledge base) MUST run under the same Linux user account. This prevents permissions friction and ensures a unified technical memory via a single `nb` notebook. By consolidating operations within one user, we maintain a tight feedback loop and eliminate the complexity of cross-user synchronization.

### 2. External Isolation (Multi-User NixOS Patterns)
While an individual organization is flat, **external isolation** between different projects or entities is enforced at the OS level using standard NixOS multi-user patterns:
*   **User-Level Sandboxing**: To manage entirely separate organizations or projects with zero cross-contamination, deploy them to different Linux user accounts. NixOS handles the underlying isolation (UID/GID separation, home directory permissions).
*   **Declarative Multi-Tenancy**: Use Home Manager to declaratively roll out Nix Spirit configurations to multiple users on a single NixOS system. Each user gets their own `systemd.user` instances and isolated `bubblewrap` environments.
*   **Contextual Firewalling**: Agents in one user account cannot access the `nb` knowledge base or `.gemini` credentials of another user, even if they share the same Nix store, due to strict Linux filesystem permissions and `bwrap` constraints.

### 3. Process Sandboxing (Bubblewrap)
Each agent executes within a **Stateless Agent Execution Model (SAEM)** enforced by `bubblewrap`:
*   **Strict Read-Only**: The entire system and home directory are mounted as read-only by default.
*   **Surgical Write Access**: Agents are only granted write access to their specific `PROJECT_DIR` and necessary communication queues (`.spirit/queues`, `.spirit/outbox`).
*   **Stateless Infrastructure**: Infrastructure logs and agent registries are provided as read-only binds, preventing agents from tampering with the organizational heartbeat.

---

*Nix Spirit is a laboratory for decentralized AI engineering. It is a repo that knows what it is, and has the hands to build itself.*

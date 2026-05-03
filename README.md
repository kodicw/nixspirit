# 🌈 Autonomous Organization Core: The Recursive PAO

**A Proof-of-Concept for Self-Managed Repositories.**

This project provides a framework for a **Stateful Autonomous Organization (PAO)** embedded directly within the filesystem. It transforms a static repository into a **Living Entity** that possesses its own cognitive capacity, long-term memory, and the hands to build its own future.

## 🧠 Philosophy: Repo-as-Entity

Most AI tools are "visitors" to a codebase. Core agents are **residents**. 
*   **Infrastructure-as-Brain**: The Nix configuration defines not just the environment, but the CPU, RAM, and "patience" (timeouts) of each team member.
*   **Git-Backed Consciousness**: Using `nb`, the "thinking" of the lead and the "verifications" of the tester are stored in the same version-controlled history as the code.
*   **Recursive Evolution**: The agents are empowered to refine their own "operating system" (the Nix modules and Python scripts) to achieve higher technical purity.

## 🏗️ Architectural Pillars

1.  **Nix-Native Reproducibility**: The entire organization is a Nix Flake. A "Company" can be shipped, cloned, and deployed with byte-for-byte consistency across any machine.
2.  **Stateful Development Model**: Agents operate directly on the project directory inside a **`bubblewrap`** sandbox. No "stateless" chat overhead; just real-time, stateful engineering.
3.  **Engine-Agnostic Core**: Standardized AI interface support allows declaratively swapping between different LLM engines on a per-agent basis.
4.  **Security via Isolation**: Agents run under `systemd.user` with strict `ProtectHome=read-only` and `ProtectSystem=strict` mandates.

## 🔒 Security & Scaling

### Single-User Constraint
The system is designed as a **Flat Organization** centered around a single Linux user. This model ensures:
*   **Contextual Purity**: All agents share the same Home Manager context, eliminating the need for complex cross-user permissions.
*   **Knowledge Base Simplicity**: The `nb` knowledge base remains a single, atomic unit of technical memory for the user.
*   **Security Boundary**: Multi-user isolation is handled at the OS/Home Manager level. The system operates entirely within the boundaries of the user's `$HOME` to prevent system-wide contamination.

### Scaling with Granular Tasks
As the team grows, the system scales by transitioning from a single "Authoritative Task Board" to a **Per-Task Note Model**. Each task becomes an individual note in `nb`, enabling:
*   **Concurrent Access**: Eliminates write collisions on the task board.
*   **Granular Ownership**: Direct agent-to-task mapping via `agent:<name>` tags.
*   **Automatic Rotation**: Completed tasks are archived/rotated to keep the active context dense and relevant.

## 🚀 Getting Started

### 1. Define Your Team
Include the core module in your Home Manager configuration and declaratively assemble your autonomous team:

```nix
programs.core-system = {
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
  };
};
```

### 2. Enter the Loop
```bash
# Update the organization
home-manager switch --flake .

# Check the status
core-cli status

# Inspect the "Collective Memory"
nb knowledge:q "architecture"
```

## 🛠️ Toolstack

*   **`core-cli`**: The organizational multi-tool for status, tasks, and maintenance.
*   **`nb`**: Git-backed knowledge base for long-term technical memory.
*   **`bubblewrap`**: Secure sandbox for stateful agent execution.
*   **`systemd`**: The organizational heart, managing schedules and resource quotas.

---

*This project is a laboratory for decentralized AI engineering. It is a repo that knows what it is, and has the hands to build itself.*

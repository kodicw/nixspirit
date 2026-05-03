# Contributing Guide: Nix Spirit Engineering Standards

**Project:** Nix Spirit  
**Status:** Flat Multi-Agent Organization  
**Stack:** Nix (Flakes, Home Manager), Python 3, Systemd

---

## 1. Architectural Philosophy: Flat Organization

Nix Spirit follows a **Flat Organization** model. This means:
- **Internal Cohesion:** All components (agents, infra, scripts) live under a single Linux user account.
- **No Hierarchy:** We avoid nested project structures or "Sub-Organizations". Coordination happens via a shared `TASKS.md` and `.spirit/messages/`.
- **External Isolation:** Multi-project management is handled by creating *different* Linux users via NixOS/Home Manager.

---

## 2. Code Quality Standards

### Nix (Infrastructure & Configuration)
- **Formatting:** All `.nix` files must be formatted with `nixfmt` (RFC-style).
- **Linting:** Use `statix check` to identify anti-patterns.
- **Hermeticity:** Always use `lib.makeBinPath` in systemd services.

### Python (Agent Logic & Tooling)
- **Formatting & Linting:** All Python code is formatted and linted with `ruff`.
- **Style:** 
  - Prefer clear, descriptive variable names.
  - Use `argparse` for all CLI tools.
  - Maintain a consistent logging format: `[$(date)] Nix Spirit (AgentName): Message`.

---

## 3. Coordination & Task Management

### TASKS.md (The Blackboard)
All work MUST be tracked in `TASKS.md` using the following lifecycle:
- **Backlog:** Unassigned ideas.
- **Proposal:** Complex changes requiring research/design first.
- **To Do / In Progress:** Active work assigned to an `(Agent: Name)`.
- **In Review (Human):** HIL gatekeeping state. No file-mutating tools allowed.
- **Done:** Verified and completed work.

### Agent Communication
- **Shared History:** Use `.spirit/memory.log` for high-level summaries of agent actions.
- **Direct Messaging:** Use `.spirit/messages/` for agent-to-agent coordination.

---

## 4. Development Workflow

### Testing
- **Unit Tests:** Located in `tests/`. Run via `nix flake check --no-build`.
- **Integration Tests:** Use `nixos-test.nix` for full VM-based verification.
- **Reproduction:** Bug fixes must include a reproduction test case.

### Commit Messages
Follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):
- `feat(nix): ...`
- `fix(agent): ...`
- `docs: ...`
- `chore(scripts): ...`

### Git Hooks
All hooks live in `.githooks/` and are automatically activated by the dev shell:
- **`pre-commit`**: Checks Nix and Python formatting and linting.
- **`commit-msg`**: Validates Conventional Commits format.
- **`pre-push`**: Runs full suite of tests.

### Directory Structure
- `/scripts/`: All Python-based agent logic and utility scripts.
- `/tests/`: Nix-based unit and integration tests.
- `/docs/`: Long-form documentation and architectural archives.
- `/examples/`: Example configurations for users.

---

## 5. Engineering Standards (DRY)

### Don't Repeat Yourself (DRY)
- **Modularity First:** Always prioritize creating reusable functions and modules over duplicating logic.
- **Audit:** Before adding new scripts, check if existing ones can be extended or refactored to handle the new task.
- **Shared Logic:** For logic used across multiple agents (e.g., logging, task parsing), use shared utility modules in the `scripts/` directory.

### Unix Philosophy
- **Do one thing and do it well:** Break down complex scripts into smaller, purpose-built components.
- **Work together:** Design scripts to be part of a pipeline (e.g., one to rotate, one to purge, one to display).
- **Text Streams:** Use simple, human-readable text (Markdown, JSON) as the primary interface between agents and scripts.

### Self-Documenting Code
- **Meaningful Naming:** Choose variable and function names that describe "what" and "why", not just "how".
- **Small Functions:** Break down complex logic into small, single-purpose functions with clear inputs and outputs.
- **Clarity > Cleverness:** Avoid obscure language features or "hacks". If a piece of code needs a long comment to explain it, it should probably be refactored to be clearer.
- **Type Safety:** Use Python type hints and clean Nix structures to provide implicit documentation.

### Organizational Memory (nb)
- **Knowledge Base:** All major architectural decisions (ADRs) must be recorded in the `spirit` notebook using `nb spirit:add`.
- **Search First:** Use `nb spirit:q` to search the knowledge base for existing research before initiating new technical audits.
- **Verification:** Task results and verified technical benchmarks should be exported to the knowledge base to ensure long-term persistence.

### Purity Guard (just / deadnix)
- **Centralized Workflows:** Use the `justfile` for all common tasks (formatting, linting, testing).
- **Zero Technical Debt:** Every commit should pass `just audit`.
- **Nix Purity:** Use `deadnix` (via `just prune`) to find and remove unused Nix code. Architectural simplicity is maintained by keeping the codebase lean.

### Information Density
- **Executable Metadata:** Treat documentation as executable law.
- **ADR Links:** Reference `nb` ADRs directly in code comments (e.g., `# Context: [[nb:spirit:adr-001]]`).
- **Mermaid-as-Code:** Every complex script should have an accompanying `.mermaid` file or Mermaid docstring block.
- **Type-Driven Docs:** 100% usage of Python Type Hints and Nix Lib types. Use pydocstyle block structures.
- **Structure as Code:** Define JSON Schemas for all state files (e.g., `agents.json`) to prevent data hallucination.

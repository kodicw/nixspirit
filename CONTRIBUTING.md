# Contributing Guide: Engineering Standards

This project follows a **Flat Organization** model. This means:

- **No Hierarchy:** We avoid nested project structures or "Sub-Organizations". Coordination happens via shared tasks and communication queues.
- **Single-User Scope:** The entire organization operates within a single Linux user context. Multi-user isolation is handled at the OS/Home Manager level.
- **Text-First Purity:** The ultimate source of truth is the filesystem and the knowledge base.

## 🛠️ Standards & Practices

### 1. Versioning & Commits
- **Semantic Versioning:** We follow SemVer for all releases.
- **Conventional Commits:** All commits must follow the Conventional Commits specification (`feat:`, `fix:`, `refactor:`, `chore:`, `docs:`).
- **No-Verify Commits:** Use `--no-verify` sparingly; it bypasses quality checks.

### 2. Logging & Identity
- **Standardized Logging:** All scripts must use the standardized logging format: `[$(date)] System (AgentName): Message`.
- **Standard Identity:** Agents should use standard environment variables for identity (`NB_USER_NAME`, `NB_USER_EMAIL`).

### 3. Knowledge Management (`nb`)
- **Git-Backed Memory:** All thinking, reflections, and ADRs are stored in technical memory.
- **Search First:** Search the knowledge base for existing research before initiating new technical audits.
- **ADR Mandate:** Any structural change to the codebase MUST be preceded by an Architectural Decision Record note.
- **ADR Links:** Reference ADRs directly in code comments (e.g., `# Context: [[nb:knowledge:adr-001]]`).

## 🏗️ Technical Purity

- **100% Type Hints:** All Python code must use 100% type hinting.
- **Docstrings:** Every function must have a docstring describing its Purpose, Inputs, and Outputs.
- **Verification:** Changes are not complete until they are verified by the automated test suite.
- **Purity Audit:** Run `just audit` before proposing any major change.

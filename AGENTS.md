# 🌈 Nix Spirit Agent Instructions

![Nix Spirit Banner](assets/spirit.jpeg)

This repository contains strict architectural constraints and specialized tooling. Read this before taking action.

## 🛠️ Tooling & Environment
- **Environment:** Always run commands within the Nix development shell (`nix develop`). This activates required Git hooks and ensures the correct toolchain.
- **Task Runner:** `just` is the sole task runner. Do not use raw `pytest` or `nixfmt` unless debugging a specific failure.
  - `just audit`: Runs format, lint, prune, and test sequentially. **Run this before finishing any task.**
  - `just format`: Formats Nix and Python code.
  - `just lint`: Runs `statix` and `ruff check`.
  - `just test`: Runs both Nix flake checks and the Python test suite.
  - `just prune`: Removes dead Nix code and cleans up pycache.

## 🧠 Memory & Context (`nb` CLI)
- **Mandatory Memory Tool:** ALL long-term memory, context, and architectural decisions are stored using the `nb` CLI tool in the `jbot` notebook.
- **Search First:** Before making structural changes or asking questions, search the knowledge base: `nb jbot:q "<keywords>"`.
- **Record Decisions:** Record architectural changes or milestones using: `nb jbot:add --title "ADR: <Topic>"`.

## 🏗️ Architecture & Constraints
- **Strict Sandboxing:** Nix Spirit agents execute inside a `bubblewrap` sandbox with `ProtectSystem=strict` and `ProtectHome=read-only`. **Never attempt to loosen sandboxing** without a documented security rationale.
- **No Local Resource Policing:** Agents must not implement local budget or token tracking logic. This is handled strictly by the backend API providers.

## ⚠️ Operational Gotchas
- **API Quota Exhaustion:** The `jbot-agent-*` services share a Gemini API quota. If systemd services are failing with `exit-code 1`, check the logs (`journalctl --user -u jbot-agent-<name>`); it is likely a `429 Too Many Requests` error.
- **Agent Looping:** Agents (especially the `tester`) will enter infinite loops (e.g., repeatedly logging "done" to `nb`) and burn through API quota if they lack explicit, actionable items. Ensure `TASKS.md` is populated with clear objectives.

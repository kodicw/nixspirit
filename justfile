# Autonomous Organization Core Justfile
set shell := ["bash", "-c"]

# Perform a full Purity Audit
audit: format lint prune test

# Format all project files
format:
    nixfmt **/*.nix
    ruff format .

# Run all project linters
lint:
    statix check .
    ruff check .
    bandit -r scripts/ -ll

# Prune unused Nix code and dead files
prune:
    deadnix --edit .
    # Prune empty __pycache__ or temporary files
    find . -type d -name "__pycache__" -exec rm -rf {} +
    find . -type f -name "*.tmp" -delete

# Run all project checks (Flake-level)
check:
    nix --extra-experimental-features "nix-command flakes" flake check --no-build --max-jobs 1 --cores 1

# Run the exhaustive test suite
test: check
    pytest --cov=scripts tests/

# Synchronize long-term memory to knowledge base
sync-memory:
    nb knowledge:sync

# Initialize a new agent run context
init-run:
    nb knowledge:q "technical purity"
    just audit

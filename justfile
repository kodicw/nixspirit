# JBot Technical Excellence Justfile
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

# Run the exhaustive test suite
test:
    nix --extra-experimental-features "nix-command flakes" flake check --no-build
    pytest --cov=scripts tests/

# Synchronize long-term memory to nb
sync-memory:
    nb jbot:sync

# Initialize a new agent run context
init-run:
    nb jbot:q "technical excellence"
    just audit

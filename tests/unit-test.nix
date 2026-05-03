{
  pkgs,
  core-scripts,
  system_prompt.txt,
  ...
}:
let
  mockGemini = pkgs.writeShellScriptBin "gemini" ''
    echo "MOCK GEMINI CALLED with args: $@"
    # Store the prompt passed via -p
    while [[ $# -gt 0 ]]; do
      case "$1" in
        -p)
          echo "$2" > "$PROJECT_DIR/.prompt_received"
          shift 2
          ;;
        *)
          shift
          ;;
      esac
    done
    echo '{"scope": "local", "status": "success", "summary": "Mock unit test success"}' > "$MEMORY_OUTPUT"
  '';
in
pkgs.runCommand "core-unit-test"
  {
    nativeBuildInputs = [
      pkgs.python3
      pkgs.coreutils
      pkgs.findutils
      pkgs.jq
      mockGemini
    ];
  }
  ''
    export PROJECT_DIR=$TMPDIR/project
    mkdir -p $PROJECT_DIR
    cd $PROJECT_DIR

    # Initial files
    ln -s ${core-scripts} scripts

    echo "Goal: Test the unit test" > .project_goal
    echo "# Task Board" > TASKS.md
    echo "- [x] Task 1" >> TASKS.md

    mkdir -p .system/directives
    echo "This is a test directive" > .system/directives/001_test.txt
    mkdir -p .system
    echo '{"dev": {"role": "Lead", "description": "Lead Dev", "projectDir": "'$PROJECT_DIR'"}}' > .system/agents.json

    export AGENT_NAME="dev"
    export AGENT_ROLE="Lead"
    export AGENT_DESCRIPTION="Lead Dev"
    export PROJECT_DIR="$PROJECT_DIR"
    export PROMPT_FILE="${system_prompt.txt}"
    export GEMINI_PACKAGE="gemini"
    export MEMORY_OUTPUT=".system/queues/dev.json"
    export PYTHONPATH=$PYTHONPATH:$(pwd)/scripts

    python3 scripts/core_cli.py agent

    # Verifications for 
    if ! grep -q "You are dev, acting as Lead" .prompt_received; then
      echo "Error: Prompt did not contain agent identity"
      exit 1
    fi

    if ! grep -q "Goal: Test the unit test" .prompt_received; then
      echo "Error: Prompt did not contain project goal"
      exit 1
    fi

    if [ ! -f .system/queues/dev.json ]; then
      echo "Error: Memory output not created in queue"
      exit 1
    fi

    if [ -f INDEX.md ]; then
      echo "Error: INDEX.md was created by agent (stateful execution!)"
      exit 1
    fi

    # Run Maintenance (Centralized CLI)
    export PYTHONPATH=$PYTHONPATH:$(pwd)/scripts
    python3 scripts/core_cli.py maintenance

    # Verifications for Maintenance
    if [ ! -f .system/memory.log ]; then
      echo "Error: memory.log not created by maintenance"
      exit 1
    fi

    if ! grep -q "Mock unit test success" .system/memory.log; then
      echo "Error: Memory not consolidated into memory.log"
      exit 1
    fi

    if [ -f .system/queues/dev.json ]; then
      echo "Error: Queue file not removed after consolidation"
      exit 1
    fi

    if [ ! -f INDEX.md ]; then
      echo "Error: INDEX.md not created by maintenance"
      exit 1
    fi

    if ! grep -q "Autonomous System Dashboard" INDEX.md; then
      echo "Error: INDEX.md content incorrect"
      exit 1
    fi

    touch $out
  ''

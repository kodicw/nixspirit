{
  pkgs,
  core-scripts,
  system_prompt.txt,
  ...
}:
let
  mockGemini = pkgs.writeShellScriptBin "gemini" ''
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
    echo '{"scope": "local", "status": "success", "summary": "Multi-agent test success"}' > "$MEMORY_OUTPUT"
  '';
in
pkgs.runCommand "core-multi-agent-unit-test"
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

    echo "Goal: Test multi-agent" > .project_goal
    echo "# Task Board" > TASKS.md
    mkdir -p .system/queues

    # Simulate another agent's memory
    echo '{"summary": "Task 1 completed"}' > .system/queues/lead.json

    mkdir -p .system
    echo '{"tester": {"role": "QA", "description": "QA Tester", "projectDir": "'$PROJECT_DIR'"}, "lead": {"role": "Lead", "description": "Lead Dev", "projectDir": "'$PROJECT_DIR'"}}' > .system/agents.json

    export AGENT_NAME="tester"
    export AGENT_ROLE="QA"
    export AGENT_DESCRIPTION="QA Tester"
    export PROMPT_FILE="${system_prompt.txt}"
    export GEMINI_PACKAGE="gemini"
    export MEMORY_OUTPUT=".system/queues/tester.json"

    # Run maintenance to consolidate memory from other agents (lead.json) into memory.log
    export PYTHONPATH=$PYTHONPATH:${core-scripts}
    python3 ${core-scripts}/core_cli.py maintenance

    python3 ${core-scripts}/core_cli.py agent

    # Verifications
    if ! grep -q "\[lead\] Task 1 completed" .prompt_received; then
      echo "Error: Prompt did not contain other agent's memory"
      exit 1
    fi

    if [ ! -f .system/memory.log ]; then
      echo "Error: memory.log not created from queues"
      exit 1
    fi

    if [ -f .system/queues/lead.json ]; then
      echo "Error: lead.json not consolidated"
      exit 1
    fi

    touch $out
  ''

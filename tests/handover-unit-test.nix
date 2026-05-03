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
    echo '{"scope": "local", "status": "success", "summary": "Handover test success"}' > "$MEMORY_OUTPUT"
  '';
in
pkgs.runCommand "core-handover-unit-test"
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

    echo "Goal: Test handover" > .project_goal

    # Setup a stateful task simulation
    cat <<EOF > TASKS.md
    # Autonomous System Task Board
    ## Active Tasks
    - [ ] Implement new feature (Agent: lead) - Status: Done
    - [ ] Verify new feature (Agent: tester) - Status: To Do
    EOF

    mkdir -p .system
    echo '{"tester": {"role": "QA", "description": "QA Tester", "projectDir": "'$PROJECT_DIR'"}, "lead": {"role": "Lead", "description": "Lead Dev", "projectDir": "'$PROJECT_DIR'"}}' > .system/agents.json

    export AGENT_NAME="tester"
    export AGENT_ROLE="QA"
    export AGENT_DESCRIPTION="QA Tester"
    export PROMPT_FILE="${system_prompt.txt}"
    export GEMINI_PACKAGE="gemini"
    export MEMORY_OUTPUT=".system/queues/tester.json"
    export PYTHONPATH=$PYTHONPATH:${core-scripts}

    python3 ${core-scripts}/core_cli.py agent

    # Verifications
    if ! grep -q "Implement new feature (Agent: lead) - Status: Done" .prompt_received; then
      echo "Error: Prompt did not contain completed task for handover"
      exit 1
    fi

    if ! grep -q "Verify new feature (Agent: tester) - Status: To Do" .prompt_received; then
      echo "Error: Prompt did not contain pending task for handover"
      exit 1
    fi

    echo "Handover verification successful."
    touch $out
  ''

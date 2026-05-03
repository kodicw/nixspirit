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
    echo '{"scope": "local", "status": "success", "summary": "Directive expiration test success"}' > "$MEMORY_OUTPUT"
  '';
in
pkgs.runCommand "core-directive-expiration-test"
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
            echo "Goal: Test directive expiration" > .project_goal
            echo "# Task Board" > TASKS.md
            mkdir -p .system/directives
            
            # 1. Active directive (no date)
            echo "Active directive content" > .system/directives/001_active.txt
            
            # 2. Expired directive (filename date in the past)
            echo "Expired filename directive content" > .system/directives/002_2020-01-01_expired.md
            
            # 3. Future directive (filename date in the future)
            echo "Future filename directive content" > .system/directives/003_2099-01-01_future.md
            
            # 4. Expired directive (content expiration in the past)
            cat <<EOF > .system/directives/004_expired_content.md
    # Directive 004
    Expiration: 2020-01-01
    Expired content directive content
    EOF

            # 5. Future directive (content expiration in the future)
            cat <<EOF > .system/directives/005_future_content.md
    # Directive 005
    Expiration: 2099-01-01
    Future content directive content
    EOF

            mkdir -p .system
            echo '{"dev": {"role": "Lead", "description": "Lead Dev", "projectDir": "'$PROJECT_DIR'"}}' > .system/agents.json

            export AGENT_NAME="dev"
            export AGENT_ROLE="Lead"
            export AGENT_DESCRIPTION="Lead Dev"
            export PROMPT_FILE="${system_prompt.txt}"
            export GEMINI_PACKAGE="gemini"
            export MEMORY_OUTPUT=".system/queues/dev.json"
            export PYTHONPATH=$PYTHONPATH:${core-scripts}

            python3 ${core-scripts}/core_cli.py agent

            # Verifications
            echo "Verifying prompt content..."
            
            if ! grep -q "Active directive content" .prompt_received; then
              echo "Error: Active directive not found in prompt"
              exit 1
            fi

            if grep -q "Expired filename directive content" .prompt_received; then
              echo "Error: Expired filename directive FOUND in prompt"
              exit 1
            fi

            if ! grep -q "Future filename directive content" .prompt_received; then
              echo "Error: Future filename directive not found in prompt"
              exit 1
            fi

            if grep -q "Expired content directive content" .prompt_received; then
              echo "Error: Expired content directive FOUND in prompt"
              exit 1
            fi

            if ! grep -q "Future content directive content" .prompt_received; then
              echo "Error: Future content directive not found in prompt"
              exit 1
            fi

            echo "All directive expiration checks passed!"
            touch $out
  ''

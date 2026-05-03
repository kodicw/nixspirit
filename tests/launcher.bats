#!/usr/bin/env bats
# Autonomous System Launcher behavioral tests

setup() {
    export AGENT_NAME="test-agent"
    export AGENT_ROLE="tester"
    export AGENT_DESCRIPTION="Test agent"
    export PROJECT_DIR="/tmp/system-test"
    export PROMPT_FILE="/tmp/core_prompt.txt"
    export CLI_BIN="echo"
    export CLI_TYPE="gemini"
    export NB_DIR="/tmp/nb"
    export HM_PROFILE="/tmp/hm-profile"
    export USER_ID="1000"
    export MKDIR_BIN="mkdir"
    export CP_BIN="cp"
    export ID_BIN="id"
    export DATE_BIN="date"
    export MKTEMP_BIN="mktemp"
    export TIMEOUT_BIN="echo"
    export BWRAP_BIN="echo"
    export AGENTS_JSON="/tmp/agents.json"
    export CORE_CLI_BIN="echo"
    
    mkdir -p "$PROJECT_DIR"
    touch "$PROMPT_FILE"
    echo "{}" > "$AGENTS_JSON"
}

teardown() {
    rm -rf "$PROJECT_DIR"
    rm -f "$PROMPT_FILE"
    rm -f "$AGENTS_JSON"
}

@test "launcher script exists and is executable" {
    [ -x "scripts/launcher.sh" ]
}

@test "launcher script fails if required variables are missing" {
    unset AGENT_NAME
    run bash scripts/launcher.sh
    [ "$status" -ne 0 ]
}

@test "launcher script correctly identifies sandbox command (dry run)" {
    # Since we mocked BWRAP_BIN and TIMEOUT_BIN to echo, 
    # the script should print the command it would run.
    run bash scripts/launcher.sh
    if [ "$status" -ne 0 ]; then
        echo "Status: $status"
        echo "Output: $output"
    fi
    [ "$status" -eq 0 ]
    [[ "$output" == *"Launching agent runner in sandbox..."* ]]
}

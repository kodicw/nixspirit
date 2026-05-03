#!/usr/bin/env bash
# Global Agent Launcher
# Generic terminology for autonomous organization infrastructure.
set -euo pipefail

# Required environment variables (provided by systemd environment):
# AGENT_NAME, AGENT_ROLE, AGENT_DESCRIPTION, PROJECT_DIR, PROMPT_FILE,
# CLI_BIN, CLI_TYPE, CLI_MODEL, NB_DIR, HM_PROFILE,
# AGENTS_JSON, CORE_CLI_BIN

STATE_DIR=".system"
TASKS_DIR="${STATE_DIR}/queues"
RESULTS_DIR="${STATE_DIR}/outbox"
AGENTS_REGISTRY="${STATE_DIR}/agents.json"
MEMORY_LOG="${STATE_DIR}/memory.log"
COMMUNICATIONS_DIR="${STATE_DIR}/messages"
INSTRUCTIONS_DIR="${STATE_DIR}/directives"

echo "[$(date "+%Y-%m-%d %H:%M:%S")] System (${AGENT_NAME}): Launching agent runner in sandbox..."

# Ensure we are on the develop branch
if [ -d "${PROJECT_DIR}/.git" ]; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] System (${AGENT_NAME}): Ensuring develop branch..."
    git -C "${PROJECT_DIR}" rev-parse --verify develop >/dev/null 2>&1 || git -C "${PROJECT_DIR}" branch develop
    git -C "${PROJECT_DIR}" checkout develop || echo "Warning: Could not switch to develop branch."
fi

mkdir -p "${PROJECT_DIR}/${TASKS_DIR}"
mkdir -p "${PROJECT_DIR}/${RESULTS_DIR}"

# Provide the agent registry to the project directory
if [ "$(realpath "${AGENTS_JSON}")" != "$(realpath "${PROJECT_DIR}/${AGENTS_REGISTRY}" 2>/dev/null)" ]; then
    cp -f "${AGENTS_JSON}" "${PROJECT_DIR}/${AGENTS_REGISTRY}" || echo "Warning: Could not copy agents.json"
fi

# Determine numeric UID
USER_ID=$(id -u)

# Create a minimal fake passwd file
FAKE_PASSWD=$(mktemp)
echo "${AGENT_NAME}:x:${USER_ID}:${USER_ID}:Agent:${HOME}:/bin/bash" > "${FAKE_PASSWD}"

# Execute agent in bubblewrap sandbox
timeout 30m bwrap \
  --ro-bind /nix/store /nix/store \
  --ro-bind /etc/resolv.conf /etc/resolv.conf \
  --ro-bind /etc/hosts /etc/hosts \
  --ro-bind /etc/ssl/certs /etc/ssl/certs \
  --ro-bind-try /etc/static/charsets /etc/static/charsets \
  --ro-bind "${FAKE_PASSWD}" /etc/passwd \
  --dev /dev \
  --proc /proc \
  --tmpfs /tmp \
  --tmpfs /home \
  --bind "${PROJECT_DIR}" "${PROJECT_DIR}" \
  --ro-bind-try "${PROJECT_DIR}/${MEMORY_LOG}" "${PROJECT_DIR}/${MEMORY_LOG}" \
  --ro-bind-try "${PROJECT_DIR}/${AGENTS_REGISTRY}" "${PROJECT_DIR}/${AGENTS_REGISTRY}" \
  --ro-bind-try "${PROJECT_DIR}/${COMMUNICATIONS_DIR}" "${PROJECT_DIR}/${COMMUNICATIONS_DIR}" \
  --ro-bind-try "${PROJECT_DIR}/${INSTRUCTIONS_DIR}" "${PROJECT_DIR}/${INSTRUCTIONS_DIR}" \
  --bind "${PROJECT_DIR}/${TASKS_DIR}" "${PROJECT_DIR}/${TASKS_DIR}" \
  --bind "${PROJECT_DIR}/${RESULTS_DIR}" "${PROJECT_DIR}/${RESULTS_DIR}" \
  --ro-bind-try "${HOME}/.gemini" "${HOME}/.gemini" \
  --ro-bind-try "${HOME}/.config/gh" "${HOME}/.config/gh" \
  --bind "${HOME}/.nb" "${HOME}/.nb" \
  --ro-bind-try "${HOME}/.nbrc" "${HOME}/.nbrc" \
  --ro-bind-try "${HOME}/.gitconfig" "${HOME}/.gitconfig" \
  --ro-bind-try "${HM_PROFILE}" "${HM_PROFILE}" \
  ${USE_DBUS:+--ro-bind "/run/user/${USER_ID}/bus" "/run/user/${USER_ID}/bus"} \
  --setenv HOME "${HOME}" \
  --setenv PATH "${PATH}" \
  --setenv NB_DIR "${NB_DIR}" \
  --setenv NB_USER_NAME "${NB_USER_NAME}" \
  --setenv NB_USER_EMAIL "${NB_USER_EMAIL}" \
  --setenv GIT_AUTHOR_NAME "${GIT_AUTHOR_NAME}" \
  --setenv GIT_AUTHOR_EMAIL "${GIT_AUTHOR_EMAIL}" \
  --setenv GIT_COMMITTER_NAME "${GIT_COMMITTER_NAME}" \
  --setenv GIT_COMMITTER_EMAIL "${GIT_COMMITTER_EMAIL}" \
  --setenv CLI_BIN "${CLI_BIN}" \
  --setenv CLI_TYPE "${CLI_TYPE}" \
  --setenv CLI_MODEL "${CLI_MODEL}" \
  --setenv AGENT_NAME "${AGENT_NAME}" \
  --setenv AGENT_ROLE "${AGENT_ROLE}" \
  --setenv AGENT_DESCRIPTION "${AGENT_DESCRIPTION}" \
  --setenv PROJECT_DIR "${PROJECT_DIR}" \
  --setenv PROMPT_FILE "${PROMPT_FILE}" \
  --setenv CORE_CLI_BIN "${CORE_CLI_BIN}" \
  --setenv EDITOR "${EDITOR:-cat}" \
  --setenv TERM "${TERM:-dumb}" \
  --setenv PAGER "${PAGER:-cat}" \
  --setenv DBUS_SESSION_BUS_ADDRESS "${DBUS_SESSION_BUS_ADDRESS:-""}" \
  --chdir "${PROJECT_DIR}" \
  --unshare-all \
  --share-net \
  --die-with-parent \
  "${CORE_CLI_BIN}" agent \
    --name "${AGENT_NAME}" \
    --role "${AGENT_ROLE}" \
    --desc "${AGENT_DESCRIPTION}" \
    --prompt "${PROMPT_FILE}" \
    --cli-bin "${CLI_BIN}" \
    --cli-type "${CLI_TYPE}" \
    --cli-model "${CLI_MODEL}"

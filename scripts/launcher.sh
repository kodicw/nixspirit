#!/usr/bin/env bash
# spirit Agent Launcher Script
# Context: [[nb:spirit:adr-2]], [[nb:spirit:adr-6]], [[nb:spirit:adr-61]], [[nb:spirit:adr-63]]
set -euo pipefail

# Required environment variables:
# AGENT_NAME, AGENT_ROLE, AGENT_DESCRIPTION, PROJECT_DIR, PROMPT_FILE,
# CLI_BIN, CLI_TYPE, CLI_MODEL, NB_DIR, HM_PROFILE, USER_ID,
# AGENTS_JSON, spirit_CLI_BIN

# Optional environment variables (with defaults):
# NB_USER_NAME, NB_USER_EMAIL, GIT_AUTHOR_NAME, GIT_AUTHOR_EMAIL,
# GIT_COMMITTER_NAME, GIT_COMMITTER_EMAIL, EDITOR, TERM, PAGER,
# DBUS_SESSION_BUS_ADDRESS

echo "[$(date "+%Y-%m-%d %H:%M:%S")] spirit (${AGENT_NAME}): Launching agent runner in sandbox..."

# Ensure we are on the develop branch before entering the sandbox
# This provides a consistent environment for the agent.
if [ -d "${PROJECT_DIR}/.git" ]; then
    echo "[$(date "+%Y-%m-%d %H:%M:%S")] spirit (${AGENT_NAME}): Ensuring develop branch..."
    # Check if develop exists, create it if not, then checkout
    git -C "${PROJECT_DIR}" rev-parse --verify develop >/dev/null 2>&1 || git -C "${PROJECT_DIR}" branch develop
    git -C "${PROJECT_DIR}" checkout develop || echo "Warning: Could not switch to develop branch."
fi

mkdir -p "${PROJECT_DIR}/.spirit/queues"
mkdir -p "${PROJECT_DIR}/.spirit/outbox"

# Provide the agent registry to the project directory
cp "${AGENTS_JSON}" "${PROJECT_DIR}/.spirit/agents.json"

# Create a minimal fake passwd file to satisfy Node.js os.userInfo()
FAKE_PASSWD=$(mktemp)
echo "${AGENT_NAME}:x:${USER_ID}:${USER_ID}:spirit Agent:${HOME}:/bin/bash" > "${FAKE_PASSWD}"

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
  --ro-bind-try "${PROJECT_DIR}/.spirit/memory.log" "${PROJECT_DIR}/.spirit/memory.log" \
  --ro-bind-try "${PROJECT_DIR}/.spirit/agents.json" "${PROJECT_DIR}/.spirit/agents.json" \
  --ro-bind-try "${PROJECT_DIR}/.spirit/messages" "${PROJECT_DIR}/.spirit/messages" \
  --ro-bind-try "${PROJECT_DIR}/.spirit/directives" "${PROJECT_DIR}/.spirit/directives" \
  --bind "${PROJECT_DIR}/.spirit/queues" "${PROJECT_DIR}/.spirit/queues" \
  --bind "${PROJECT_DIR}/.spirit/outbox" "${PROJECT_DIR}/.spirit/outbox" \
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
  --setenv NB_USER_NAME "${NB_USER_NAME:-"spirit Agent"}" \
  --setenv NB_USER_EMAIL "${NB_USER_EMAIL:-"spirit@internal"}" \
  --setenv GIT_AUTHOR_NAME "${GIT_AUTHOR_NAME:-"spirit Agent"}" \
  --setenv GIT_AUTHOR_EMAIL "${GIT_AUTHOR_EMAIL:-"spirit@internal"}" \
  --setenv GIT_COMMITTER_NAME "${GIT_COMMITTER_NAME:-"spirit Agent"}" \
  --setenv GIT_COMMITTER_EMAIL "${GIT_COMMITTER_EMAIL:-"spirit@internal"}" \
  --setenv CLI_BIN "${CLI_BIN}" \
  --setenv CLI_TYPE "${CLI_TYPE}" \
  --setenv CLI_MODEL "${CLI_MODEL}" \
  --setenv EDITOR "${EDITOR:-cat}" \
  --setenv TERM "${TERM:-dumb}" \
  --setenv PAGER "${PAGER:-cat}" \
  --setenv DBUS_SESSION_BUS_ADDRESS "${DBUS_SESSION_BUS_ADDRESS:-""}" \
  --chdir "${PROJECT_DIR}" \
  --unshare-all \
  --share-net \
  --die-with-parent \
  "${spirit_CLI_BIN}" agent \
    --name "${AGENT_NAME}" \
    --role "${AGENT_ROLE}" \
    --desc "${AGENT_DESCRIPTION}" \
    --prompt "${PROMPT_FILE}" \
    --cli-bin "${CLI_BIN}" \
    --cli-type "${CLI_TYPE}" \
    --cli-model "${CLI_MODEL}"

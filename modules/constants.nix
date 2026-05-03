{ lib }:
rec {
  # --- Module & Service Metadata ---
  namespace = "core-system";
  servicePrefix = "core-agent-";
  maintenanceService = "core-maintenance";
  knowledgeService = "core-knowledge-base";

  # --- Internal Paths ---
  stateDir = ".system";
  agentsRegistry = "${stateDir}/agents.json";
  tasksQueueDir = "${stateDir}/queues";
  outputDir = "${stateDir}/outbox";
  communicationDir = "${stateDir}/messages";
  instructionDir = "${stateDir}/directives";
  memoryLog = "${stateDir}/memory.log";

  # --- Sandboxing Defaults ---
  commonSandbox = {
    ProtectSystem = "strict";
    ProtectHome = "read-only";
    PrivateTmp = true;
    PrivateDevices = true;
    ProtectControlGroups = true;
    ProtectKernelTunables = true;
    ProtectKernelModules = true;
    RestrictAddressFamilies = [
      "AF_UNIX"
      "AF_INET"
      "AF_INET6"
    ];
    RestrictRealtime = true;
    RestrictNamespaces = false; # Needed for bubblewrap
    LockPersonality = true;
  };

  # --- Resource Limits ---
  resourceLimits = {
    cpuQuota = "25%";
    memoryLimit = "2G";
    timeoutStartSec = "30min";
    timeoutStopSec = "5min";
    killMode = "mixed";
  };

  # --- Agent Defaults ---
  agentDefaults = {
    role = "General Developer";
    description = "An autonomous AI agent managing the codebase.";
    interval = "hourly";
    cliType = "gemini";
    model = "gemini-1.5-pro";
  };
}

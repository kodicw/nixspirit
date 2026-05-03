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
  # Softer sandbox for better compatibility with Crostini/restricted environments.
  # bubblewrap within the launcher provides the primary filesystem isolation.
  commonSandbox = {
    ProtectSystem = "strict";
    ProtectHome = "read-only";
    PrivateTmp = true;
    # Some options are disabled to avoid CAPABILITIES errors in unprivileged containers.
    # PrivateDevices = true;
    # ProtectControlGroups = true;
    # ProtectKernelTunables = true;
    # ProtectKernelModules = true;
    # LockPersonality = true;
    # RestrictRealtime = true;
    
    RestrictAddressFamilies = [
      "AF_UNIX"
      "AF_INET"
      "AF_INET6"
    ];
    RestrictNamespaces = false; # Needed for bubblewrap
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

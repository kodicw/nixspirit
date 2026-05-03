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
  # Minimum sandboxing for maximum compatibility in Crostini.
  # bubblewrap within the launcher provides the actual filesystem isolation.
  commonSandbox = {
    # Most systemd sandboxing is disabled here because it often fails in 
    # unprivileged containers like Crostini/ChromeOS.
    # The agent-launcher.sh uses 'bwrap' which is more reliable for our needs.
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

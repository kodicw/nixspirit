{ lib, ... }:
let
  constants = import ./constants.nix { inherit lib; };
  namespace = constants.namespace;
  projectDir = "/home/kodicw/code/jbot";
  defaultModel = "gemini-1.5-pro";
  workerModel = "gemini-1.5-flash";
in
{
  programs.${namespace} = {
    enable = true;
    inherit projectDir;

    agents = {
      # --- spirit Hierarchical Specialist Organization ---

      lead = {
        enable = true;
        role = "Managerial Lead";
        description = "Orchestrator and task delegator. Decomposes high-level goals into sub-tasks for specialized agents using the nb task board.";
        model = defaultModel;
        interval = "hourly";
      };

      architect = {
        enable = true;
        role = "System Architect";
        description = "High-level design and ADR maintenance. Translates complex requirements into actionable technical plans.";
        model = defaultModel;
        interval = "*-*-* 00/2:00:00";
        dependsOn = [ "lead" ];
      };

      security = {
        enable = true;
        role = "Security Auditor";
        description = "Compliance and security gatekeeper. Audits all code changes and sandbox constraints.";
        model = workerModel;
        interval = "*-*-* 00/4:00:00";
        dependsOn = [ "lead" ];
      };

      engineer = {
        enable = true;
        role = "Implementation Engineer";
        description = "Core developer. Executes code changes, refactoring, and feature implementation delegated by the Lead.";
        model = workerModel;
        interval = "*-*-* 00/2:00:00";
        dependsOn = [ "architect" ];
      };

      tester = {
        enable = true;
        role = "QA Engineer";
        description = "Test automation and verification. Ensures 100% pass rate and reports regressions.";
        model = workerModel;
        interval = "*-*-* 00/2:00:00";
        dependsOn = [ "engineer" ];
      };

      researcher = {
        enable = true;
        role = "Research Specialist";
        description = "Information gathering and documentation. Monitors the ecosystem and maintains the knowledge base.";
        model = workerModel;
        interval = "daily";
        dependsOn = [ "lead" ];
      };
    };
  };
}

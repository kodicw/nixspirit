{ lib, ... }:
let
  constants = import ../modules/constants.nix { inherit lib; };
  namespace = constants.namespace;
in
{
  # Example configuration for a core system "Company" structure.
  # This can be included in your home.nix or another Home Manager module.

  programs.${namespace} = {
    enable = true;
    agents = {
      # The CEO agent oversees project goals and assigns tasks.
      ceo = {
        enable = true;
        role = "CEO";
        description = "Strategic visionary. Defines project goals and oversees team execution.";
        projectDir = "/home/youruser/yourproject";
        interval = "daily";
      };

      # The Lead Developer manages the infrastructure.
      lead = {
        enable = true;
        role = "Lead Developer";
        description = "Core lead developer. Implements foundational infrastructure.";
        projectDir = "/home/youruser/yourproject";
        interval = "hourly";
        dependsOn = [ "ceo" ];
      };

      # The Principal Architect reviews architectural decisions and maintains standards.
      architect = {
        enable = true;
        role = "Principal Architect";
        description = "Critiques architectural decisions, advocates for simplicity, and maintains engineering standards.";
        projectDir = "/home/youruser/yourproject";
        interval = "daily";
        dependsOn = [ "ceo" ];
      };

      # The QA Engineer verifies changes and ensures quality.
      tester = {
        enable = true;
        role = "QA Engineer";
        description = "Quality Assurance. Verifies features and reports regressions.";
        projectDir = "/home/youruser/yourproject";
        interval = "hourly";
        dependsOn = [ "lead" ]; # Waits for lead developer to finish changes
      };
    };
  };
}

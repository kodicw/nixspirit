{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.programs.nixspirit;

  # We expect the package to be passed in or use the one from corePackages
  spirit-cli = pkgs.callPackage ../pkgs/spirit-cli.nix { scripts = ../scripts; };
  spiritPython = spirit-cli.python;

  agentModule = _: {
    options = {
      enable = lib.mkEnableOption "this Nix Spirit agent";
      role = lib.mkOption {
        type = lib.types.str;
        default = "General Developer";
        description = "The role name for this agent (e.g., QA, CEO, Lead Developer).";
      };
      description = lib.mkOption {
        type = lib.types.str;
        default = "An autonomous AI agent managing the codebase.";
        description = "A description of this agent's purpose.";
      };
      projectDir = lib.mkOption {
        type = lib.types.path;
        default = cfg.projectDir;
        description = "The project directory to manage.";
      };
      interval = lib.mkOption {
        type = lib.types.str;
        default = "hourly";
        description = "Systemd calendar interval for the Nix Spirit agent.";
      };
      geminiPackage = lib.mkOption {
        type = lib.types.package;
        default = pkgs.gemini-cli;
        description = "The Gemini CLI package to use for this agent.";
      };
      opencodePackage = lib.mkOption {
        type = lib.types.package;
        default = pkgs.hello; # Placeholder until provided or used
        description = "The OpenCode CLI package to use for this agent.";
      };
      cliType = lib.mkOption {
        type = lib.types.enum [
          "gemini"
          "opencode"
        ];
        default = "gemini";
        description = "The type of AI CLI interface to use.";
      };
      model = lib.mkOption {
        type = lib.types.str;
        default = "gemini-1.5-pro";
        description = "The AI model to use (e.g., gemini-1.5-flash for worker agents).";
      };
      promptFile = lib.mkOption {
        type = lib.types.path;
        default = cfg.promptFile;
        description = "The base prompt file to use.";
      };
      extraPackages = lib.mkOption {
        type = lib.types.listOf lib.types.package;
        default = [ ];
        description = "Additional packages for this agent's sandbox.";
      };
      dependsOn = lib.mkOption {
        type = lib.types.listOf lib.types.str;
        default = [ ];
        description = "Other agents this agent depends on (systemd After/Wants).";
      };
      cpuQuota = lib.mkOption {
        type = lib.types.str;
        default = "25%";
        description = "Percentage of CPU time cap (systemd CPUQuota).";
      };
      memoryLimit = lib.mkOption {
        type = lib.types.str;
        default = "2G";
        description = "Maximum memory usage (systemd MemoryMax).";
      };
      timeoutStartSec = lib.mkOption {
        type = lib.types.str;
        default = "30min";
        description = "Systemd TimeoutStartSec for this agent.";
      };
      timeoutStopSec = lib.mkOption {
        type = lib.types.str;
        default = "5min";
        description = "Systemd TimeoutStopSec for this agent.";
      };
      killMode = lib.mkOption {
        type = lib.types.str;
        default = "mixed";
        description = "Systemd KillMode for this agent.";
      };
      useDBus = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Whether to expose the D-Bus session bus to the agent.";
      };
    };
  };

  agentsJson = pkgs.writeText "agents.json" (
    builtins.toJSON (
      lib.mapAttrs (_name: agent: {
        inherit (agent) role description interval;
        projectDir = toString agent.projectDir;
      }) allAgents
    )
  );

  # Discovery Logic
  discoveredAgents =
    if cfg.discoveryRoot != null then
      let
        root = toString cfg.discoveryRoot;
        dirContent = builtins.readDir root;
        subDirs = lib.filterAttrs (_name: type: type == "directory") dirContent;
        processDir =
          name: _:
          let
            projectDir = root + "/${name}";
            agentsFile = projectDir + "/.spirit/agents.json";
          in
          if builtins.pathExists agentsFile then
            let
              agentsData = builtins.fromJSON (builtins.readFile agentsFile);
            in
            lib.mapAttrs' (
              agentName: agentInfo:
              lib.nameValuePair "${name}-${agentName}" (
                agentInfo
                // {
                  inherit projectDir;
                  enable = agentInfo.enable or true;
                }
              )
            ) agentsData
          else
            { };
        allAgentsList = lib.mapAttrsToList processDir subDirs;
      in
      lib.foldl (a: b: a // b) { } allAgentsList
    else
      { };

  # Merge discovered agents with manually defined ones (manual overrides discovery)
  allAgents = discoveredAgents // cfg.agents;

  corePackages = [
    pkgs.coreutils
    pkgs.bash
    pkgs.procps
    pkgs.nix
    pkgs.bubblewrap
    pkgs.git
    pkgs.gh
    pkgs.curl
    pkgs.findutils
    pkgs.gnused
    pkgs.gnugrep
    pkgs.gawk
    pkgs.bc
    pkgs.jq
    pkgs.nixfmt-rfc-style
    pkgs.statix
    pkgs.ruff
    pkgs.deadnix
    pkgs.shellcheck
    pkgs.bats
    pkgs.just
    pkgs.nb
    pkgs.tealdeer
    pkgs.bat
    pkgs.ripgrep
    pkgs.gum
    pkgs.pandoc
    pkgs.w3m
    pkgs.bandit
    spiritPython
    spirit-cli
  ];

  # Pick a representative project directory for maintenance if multiple exist
  firstAgent = lib.head (lib.attrValues allAgents ++ [ { projectDir = "/dev/null"; } ]);
  maintenanceProjectDir = firstAgent.projectDir;
in
{
  options.programs.nixspirit = {
    enable = lib.mkEnableOption "Nix Spirit AI Agent Scheduler";
    projectDir = lib.mkOption {
      type = lib.types.path;
      default = config.home.homeDirectory + "/code/spirit";
      description = "The default project directory for all agents.";
    };
    discoveryRoot = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Root directory to scan for Nix Spirit projects (requires --impure if outside flake).";
    };
    promptFile = lib.mkOption {
      type = lib.types.path;
      default = ../spirit_prompt.txt;
      description = "The default base prompt file for all agents.";
    };
    maintenanceInterval = lib.mkOption {
      type = lib.types.str;
      default = "hourly";
      description = "Systemd calendar interval for the Nix Spirit maintenance service.";
    };
    agents = lib.mkOption {
      type = lib.types.attrsOf (lib.types.submodule agentModule);
      default = { };
      description = "Map of agents to run.";
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.all (agent: lib.hasPrefix config.home.homeDirectory (toString agent.projectDir)) (
          lib.attrValues allAgents
        );
        message = "Nix Spirit agents must operate within the user's home directory (${config.home.homeDirectory}) to maintain single-user isolation.";
      }
    ];

    home.packages = [
      spirit-cli
      spiritPython
      pkgs.nb
      pkgs.gum
      pkgs.tealdeer
      pkgs.bat
      pkgs.ripgrep
    ];

    home.activation.spiritEnvironmentAudit = config.lib.dag.entryAfter [ "writeBoundary" ] ''
      # Generate Technical Environment Note for nb
      AUDIT_CONTENT=$(cat <<EOF
      # ADR: Technical Environment & Tool Registry (Deep Audit)
      *Automated Environment Audit generated from Nix configuration on $(date).*

      #type:adr

      ## 🛠️ Comprehensive Toolstack
      $(echo "${
        lib.concatStringsSep "\n" (
          map (
            p: "- **${p.pname or p.name}**: ${p.version or "Nix Managed"} (${lib.getBin p}/bin)"
          ) corePackages
        )
      }")

      ## 👥 Active Agent Registry
      $(echo "${
        lib.concatStringsSep "\n" (
          lib.mapAttrsToList (
            name: agent:
            "- **${name}**: ${agent.role} (Interval: ${agent.interval or "hourly"}, DependsOn: ${
              lib.concatStringsSep ", " (agent.dependsOn or [ ])
            })"
          ) allAgents
        )
      }")

      ## 📜 Architectural Directives
      1. **Technical Purity**: 100% test coverage and zero technical debt.
      2. **Information Density**: Documentation as executable metadata.
      3. **Internal Cohesion**: Single-user organization model.
      EOF
      )

      # Push to nb stably via spirit CLI
      spirit_BIN="${spirit-cli}/bin/spirit"
      if [ -x "$spirit_BIN" ]; then
        export EDITOR=cat
        export PATH="$PATH:${
          lib.makeBinPath [
            pkgs.git
            pkgs.nb
          ]
        }"
        export NB_BIN="${pkgs.nb}/bin/nb"
        export NB_USER_NAME="Nix Spirit (${config.home.username})"
        export NB_USER_EMAIL="${config.home.username}@nixos"
        echo "$AUDIT_CONTENT" | "$spirit_BIN" maintenance push-note --title "ADR: Environment and Tool Registry" --tags "type:adr,type:audit" || true
      fi
    '';

    systemd.user.services =
      (lib.mapAttrs' (
        name: agent:
        lib.nameValuePair "spirit-agent-${name}" (
          lib.mkIf (agent.enable or true) {
            Unit = {
              Description = "Scheduled Nix Spirit AI Developer: ${agent.role}";
              After = map (n: "spirit-agent-${n}.service") (agent.dependsOn or [ ]);
              Wants = map (n: "spirit-agent-${n}.service") (agent.dependsOn or [ ]);
            };
            Service = {
              CPUQuota = agent.cpuQuota or "25%";
              MemoryMax = agent.memoryLimit or "2G";
              TimeoutStartSec = agent.timeoutStartSec or "30min";
              TimeoutStopSec = agent.timeoutStopSec or "5min";
              KillMode = agent.killMode or "mixed";
              Delegate = true;
              Environment = [
                "PATH=${
                  lib.makeBinPath (
                    corePackages
                    ++ [
                      pkgs.bubblewrap
                      pkgs.coreutils
                      (agent.geminiPackage or pkgs.gemini-cli)
                      (agent.opencodePackage or pkgs.hello)
                    ]
                    ++ (agent.extraPackages or [ ])
                  )
                }"
                "SKIP_VM_TESTS=1"
              ];

              # Systemd sandboxing for extra security
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

              BindPaths = [
                (toString agent.projectDir)
                "${config.home.homeDirectory}/.nb"
              ];
              BindReadOnlyPaths = [
                "${config.home.homeDirectory}/.gemini"
                "${config.home.homeDirectory}/.config/gh"
              ]
              ++ lib.optional agent.useDBus "/run/user/%U/bus";
              ExecStart = "${pkgs.writeShellScript "spirit-launcher-${name}" ''
                set -euo pipefail

                # Export all required environment variables for the standalone launcher
                export AGENT_NAME="${name}"
                export AGENT_ROLE="${agent.role}"
                export AGENT_DESCRIPTION="${agent.description or ""}"
                export PROJECT_DIR="${toString agent.projectDir}"
                export PROMPT_FILE="${agent.promptFile or cfg.promptFile}"
                export CLI_BIN="${
                  if (agent.cliType or "gemini") == "gemini" then
                    "${agent.geminiPackage or pkgs.gemini-cli}/bin/gemini"
                  else
                    "${agent.opencodePackage or pkgs.hello}/bin/opencode"
                }"
                export CLI_TYPE="${agent.cliType or "gemini"}"
                export CLI_MODEL="${agent.model or "gemini-1.5-pro"}"
                export AGENTS_JSON="${agentsJson}"
                export spirit_CLI_BIN="${spirit-cli}/bin/spirit"
                ${lib.optionalString agent.useDBus "export USE_DBUS=1"}

                # Environment paths
                export HM_PROFILE="${config.home.homeDirectory}/.nix-profile"
                export USER_ID=$(${pkgs.coreutils}/bin/id -u)
                export NB_DIR="${config.home.homeDirectory}/.nb"

                # Standard Identity
                export GIT_AUTHOR_NAME="Nix Spirit (${name})"
                export GIT_AUTHOR_EMAIL="spirit-${name}@internal.spirit"
                export GIT_COMMITTER_NAME="$GIT_AUTHOR_NAME"
                export GIT_COMMITTER_EMAIL="$GIT_AUTHOR_EMAIL"
                export NB_USER_NAME="$GIT_AUTHOR_NAME"
                export NB_USER_EMAIL="$GIT_AUTHOR_EMAIL"

                # Call the formally verified standalone launcher
                exec "${spirit-cli}/scripts/launcher.sh"
              ''}";

              WorkingDirectory = toString agent.projectDir;
            };
          }
        )
      ) allAgents)
      // {
        spirit-maintenance = {
          Unit = {
            Description = "Nix Spirit Infrastructure Maintenance Service";
          };
          Service = {
            Environment = [
              "PATH=${
                lib.makeBinPath [
                  pkgs.coreutils
                  pkgs.bash
                  pkgs.git
                  pkgs.python3
                  pkgs.findutils
                  pkgs.gnused
                  pkgs.gnugrep
                  pkgs.gawk
                  pkgs.which
                  spirit-cli
                ]
              }"
              "PROJECT_DIR=${maintenanceProjectDir}"
              "DISCOVERY_ROOT=${if cfg.discoveryRoot != null then toString cfg.discoveryRoot else ""}"
            ];

            # Systemd sandboxing
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
            RestrictNamespaces = false;
            LockPersonality = true;

            BindPaths = [
              maintenanceProjectDir
              "${config.home.homeDirectory}/.nb"
            ]
            ++ (if cfg.discoveryRoot != null then [ (toString cfg.discoveryRoot) ] else [ ]);

            ExecStart = "${spirit-cli}/bin/spirit maintenance run${
              if cfg.discoveryRoot != null then " --all" else ""
            }";
            WorkingDirectory = maintenanceProjectDir;
          };
        };
        spirit-knowledge-base = {
          Unit = {
            Description = "Nix Spirit Knowledge Base HTTP Server (nb browse)";
            After = [ "network.target" ];
          };
          Service = {
            Environment = [
              "PATH=${lib.makeBinPath corePackages}"
              "NB_DIR=${config.home.homeDirectory}/.nb"
              "HOME=${config.home.homeDirectory}"
            ];

            # Systemd sandboxing
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
            RestrictNamespaces = false;
            LockPersonality = true;

            BindReadOnlyPaths = [
              "${config.home.homeDirectory}/.nb"
            ];

            ExecStart = "${pkgs.nb}/bin/nb spirit:browse --serve";
            Restart = "always";
            RestartSec = "10";
            WorkingDirectory = config.home.homeDirectory;
          };
          Install.WantedBy = [ "default.target" ];
        };
      };

    systemd.user.timers =
      (lib.mapAttrs' (
        name: agent:
        lib.nameValuePair "spirit-agent-${name}" (
          lib.mkIf (agent.enable or true) {
            Timer.OnCalendar = agent.interval or "hourly";
            Install.WantedBy = [ "timers.target" ];
          }
        )
      ) allAgents)
      // {
        spirit-maintenance = {
          Timer.OnCalendar = cfg.maintenanceInterval;
          Install.WantedBy = [ "timers.target" ];
        };
      };

  };
}

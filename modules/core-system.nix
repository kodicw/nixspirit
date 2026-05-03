{
  config,
  lib,
  pkgs,
  ...
}:
let
  constants = import ./constants.nix { inherit lib; };
  namespace = constants.namespace;
  cfg = config.programs.${namespace};

  # Helper to get bin path
  binPath = packages: lib.makeBinPath packages;

  # We expect the package to be passed in or use the one from corePackages
  core-cli = pkgs.callPackage ../pkgs/core-cli.nix { scripts = ../scripts; };
  corePython = core-cli.python;

  agentModule = _: {
    options = {
      enable = lib.mkEnableOption "this autonomous agent";
      role = lib.mkOption {
        type = lib.types.str;
        default = constants.agentDefaults.role;
        description = "The role name for this agent.";
      };
      description = lib.mkOption {
        type = lib.types.str;
        default = constants.agentDefaults.description;
        description = "A description of this agent's purpose.";
      };
      projectDir = lib.mkOption {
        type = lib.types.path;
        default = cfg.projectDir;
        description = "The project directory to manage.";
      };
      interval = lib.mkOption {
        type = lib.types.str;
        default = constants.agentDefaults.interval;
        description = "Systemd calendar interval for the agent.";
      };
      geminiPackage = lib.mkOption {
        type = lib.types.package;
        default = pkgs.gemini-cli;
        description = "The Gemini CLI package to use.";
      };
      opencodePackage = lib.mkOption {
        type = lib.types.package;
        default = pkgs.hello;
        description = "The OpenCode CLI package to use.";
      };
      cliType = lib.mkOption {
        type = lib.types.enum [
          "gemini"
          "opencode"
        ];
        default = constants.agentDefaults.cliType;
        description = "The type of AI CLI interface to use.";
      };
      model = lib.mkOption {
        type = lib.types.str;
        default = constants.agentDefaults.model;
        description = "The AI model to use.";
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
        description = "Other agents this agent depends on.";
      };
      cpuQuota = lib.mkOption {
        type = lib.types.str;
        default = constants.resourceLimits.cpuQuota;
        description = "Percentage of CPU time cap.";
      };
      memoryLimit = lib.mkOption {
        type = lib.types.str;
        default = constants.resourceLimits.memoryLimit;
        description = "Maximum memory usage.";
      };
      timeoutStartSec = lib.mkOption {
        type = lib.types.str;
        default = constants.resourceLimits.timeoutStartSec;
        description = "Systemd TimeoutStartSec.";
      };
      timeoutStopSec = lib.mkOption {
        type = lib.types.str;
        default = constants.resourceLimits.timeoutStopSec;
        description = "Systemd TimeoutStopSec.";
      };
      killMode = lib.mkOption {
        type = lib.types.str;
        default = constants.resourceLimits.killMode;
        description = "Systemd KillMode.";
      };
      useDBus = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = "Whether to expose D-Bus.";
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
            agentsFile = projectDir + "/${constants.agentsRegistry}";
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
    corePython
    core-cli
  ];

  firstAgent = lib.head (lib.attrValues allAgents ++ [ { projectDir = "/dev/null"; } ]);
  maintenanceProjectDir = firstAgent.projectDir;
in
{
  options.programs.${constants.namespace} = {
    enable = lib.mkEnableOption "Autonomous Organization Core";
    projectDir = lib.mkOption {
      type = lib.types.path;
      default = config.home.homeDirectory + "/code/core";
      description = "The default project directory.";
    };
    discoveryRoot = lib.mkOption {
      type = lib.types.nullOr lib.types.path;
      default = null;
      description = "Root directory to scan for projects.";
    };
    promptFile = lib.mkOption {
      type = lib.types.path;
      default = ../system_prompt.txt;
      description = "The default base prompt file.";
    };
    maintenanceInterval = lib.mkOption {
      type = lib.types.str;
      default = "hourly";
      description = "Systemd calendar interval for maintenance.";
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
        message = "Agents must operate within the user's home directory.";
      }
    ];

    home.packages = [
      core-cli
      corePython
      pkgs.nb
      pkgs.gum
    ];

    systemd.user.services =
      (lib.mapAttrs' (
        name: agent:
        lib.nameValuePair "${constants.servicePrefix}${name}" (
          lib.mkIf (agent.enable or true) {
            Unit = {
              Description = "Scheduled Autonomous Developer: ${agent.role}";
              After = map (n: "${constants.servicePrefix}${n}.service") (agent.dependsOn or [ ]);
              Wants = map (n: "${constants.servicePrefix}${n}.service") (agent.dependsOn or [ ]);
            };
            Service = constants.commonSandbox // {
              CPUQuota = agent.cpuQuota;
              MemoryMax = agent.memoryLimit;
              TimeoutStartSec = agent.timeoutStartSec;
              TimeoutStopSec = agent.timeoutStopSec;
              KillMode = agent.killMode;
              Delegate = true;
              Environment = lib.mapAttrsToList (n: v: "${n}=${lib.escapeShellArg (toString v)}") {
                PATH = binPath (
                  corePackages
                  ++ [
                    pkgs.bubblewrap
                    pkgs.coreutils
                    agent.geminiPackage
                    agent.opencodePackage
                  ]
                  ++ agent.extraPackages
                );
                AGENT_NAME = name;
                AGENT_ROLE = agent.role;
                AGENT_DESCRIPTION = agent.description;
                PROJECT_DIR = toString agent.projectDir;
                PROMPT_FILE = toString (agent.promptFile or cfg.promptFile);
                CLI_BIN =
                  if agent.cliType == "gemini" then
                    "${agent.geminiPackage}/bin/gemini"
                  else
                    "${agent.opencodePackage}/bin/opencode";
                CLI_TYPE = agent.cliType;
                CLI_MODEL = agent.model;
                AGENTS_JSON = agentsJson;
                CORE_CLI_BIN = "${core-cli}/bin/core-cli";
                HM_PROFILE = "${config.home.homeDirectory}/.nix-profile";
                NB_DIR = "${config.home.homeDirectory}/.nb";
                GIT_AUTHOR_NAME = "Autonomous System (${name})";
                GIT_AUTHOR_EMAIL = "agent-${name}@internal.local";
                GIT_COMMITTER_NAME = "Autonomous System (${name})";
                GIT_COMMITTER_EMAIL = "agent-${name}@internal.local";
                NB_USER_NAME = "Autonomous System (${name})";
                NB_USER_EMAIL = "agent-${name}@internal.local";
                USE_DBUS = if agent.useDBus then "1" else "";
              };

              BindPaths = [
                (toString agent.projectDir)
                "${config.home.homeDirectory}/.nb"
              ];
              BindReadOnlyPaths = [
                "${config.home.homeDirectory}/.gemini"
                "${config.home.homeDirectory}/.config/gh"
              ]
              ++ lib.optional agent.useDBus "/run/user/%U/bus";

              ExecStart = "${pkgs.writeShellScript "core-launcher-${name}" ''
                set -euo pipefail
                exec "${core-cli}/scripts/launcher.sh"
              ''}";

              WorkingDirectory = toString agent.projectDir;
            };
          }
        )
      ) allAgents)
      // {
        "${constants.maintenanceService}" = {
          Unit = {
            Description = "Autonomous Infrastructure Maintenance Service";
          };
          Service = constants.commonSandbox // {
            Environment = lib.mapAttrsToList (n: v: "${n}=${lib.escapeShellArg (toString v)}") {
              PATH = binPath [
                pkgs.coreutils
                pkgs.bash
                pkgs.git
                pkgs.python3
                pkgs.findutils
                pkgs.gnused
                pkgs.gnugrep
                pkgs.gawk
                pkgs.which
                core-cli
              ];
              PROJECT_DIR = maintenanceProjectDir;
              DISCOVERY_ROOT = if cfg.discoveryRoot != null then toString cfg.discoveryRoot else "";
            };

            BindPaths = [
              maintenanceProjectDir
              "${config.home.homeDirectory}/.nb"
            ]
            ++ (if cfg.discoveryRoot != null then [ (toString cfg.discoveryRoot) ] else [ ]);

            ExecStart = "${core-cli}/bin/core-cli maintenance run${
              if cfg.discoveryRoot != null then " --all" else ""
            }";
            WorkingDirectory = maintenanceProjectDir;
          };
        };
        "${constants.knowledgeService}" = {
          Unit = {
            Description = "Autonomous Knowledge Base HTTP Server (nb browse)";
            After = [ "network.target" ];
          };
          Service = constants.commonSandbox // {
            Environment = lib.mapAttrsToList (n: v: "${n}=${lib.escapeShellArg (toString v)}") {
              PATH = binPath corePackages;
              NB_DIR = "${config.home.homeDirectory}/.nb";
              HOME = "${config.home.homeDirectory}";
            };

            BindReadOnlyPaths = [
              "${config.home.homeDirectory}/.nb"
            ];

            ExecStart = "${pkgs.nb}/bin/nb knowledge:browse --serve";
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
        lib.nameValuePair "${constants.servicePrefix}${name}" (
          lib.mkIf (agent.enable or true) {
            Timer.OnCalendar = agent.interval or "hourly";
            Install.WantedBy = [ "timers.target" ];
          }
        )
      ) allAgents)
      // {
        "${constants.maintenanceService}" = {
          Timer.OnCalendar = cfg.maintenanceInterval;
          Install.WantedBy = [ "timers.target" ];
        };
      };
  };
}

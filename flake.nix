{
  description = "Nix Spirit — Nix-based AI agent scheduler and Home Manager module";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
      ...
    }:
    flake-utils.lib.eachSystem [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ] (
      system:
      let
        pkgs = import nixpkgs { inherit system; };
        spirit-cli = pkgs.callPackage ./pkgs/spirit-cli.nix { scripts = ./scripts; };
      in
      {
        packages.default = spirit-cli;
        packages.spirit-cli = spirit-cli;

        devShells.default = pkgs.mkShell {
          packages = [
            pkgs.nixfmt-rfc-style
            pkgs.statix
            pkgs.ruff
            pkgs.bandit
            pkgs.shellcheck
            pkgs.bats
            pkgs.gemini-cli
            pkgs.python3
            pkgs.python3Packages.pytest
            pkgs.python3Packages.pytest-cov
            pkgs.python3Packages.pytest-mock
            pkgs.python3Packages.jinja2
            pkgs.jq
            pkgs.gnugrep
            pkgs.which
            spirit-cli
          ];

          shellHook = ''
            git config core.hooksPath .githooks
            echo "Git hooks activated from .githooks/"
          '';
        };

        checks = {
          shellcheck = pkgs.runCommand "shellcheck" { nativeBuildInputs = [ pkgs.shellcheck ]; } ''
            shellcheck ${./scripts}/*.sh
            shellcheck ${./.githooks}/*
            touch $out
          '';

          python-tests =
            pkgs.runCommand "python-tests"
              {
                nativeBuildInputs = [
                  pkgs.python3
                  pkgs.python3Packages.pytest
                  pkgs.python3Packages.pytest-cov
                  pkgs.python3Packages.pytest-mock
                  pkgs.git
                  pkgs.gum
                  pkgs.gemini-cli
                  pkgs.nb
                  pkgs.bandit
                  spirit-cli.python
                ];
              }
              ''
                mkdir -p scripts tests
                cp ${./scripts}/*.py scripts/
                cp ${./tests}/*.py tests/
                export PYTHONPATH=$PYTHONPATH:$(pwd)/scripts

                echo "Running Bandit security audit..."
                bandit -r scripts/ -ll

                pytest --cov=scripts --cov-report=term-missing tests/
                touch $out
              '';
          bash-tests =
            pkgs.runCommand "bash-tests"
              {
                nativeBuildInputs = [
                  pkgs.shellcheck
                  pkgs.bats
                ];
              }
              ''
                echo "Running ShellCheck..."
                shellcheck ${./scripts}/*.sh ${./.githooks}/*

                echo "Running BATS tests..."
                # Only run if tests exist
                if [ -d ${./tests} ] && ls ${./tests}/*.bats >/dev/null 2>&1; then
                  bats ${./tests}/*.bats
                fi
                touch $out
              '';
        };
      }
    )
    // {
      homeManagerModules = {
        nixspirit = import ./modules/nixspirit.nix;
        ai-company = import ./modules/ai-company.nix;
        default = self.homeManagerModules.nixspirit;
      };
    };
}
